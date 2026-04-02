import streamlit as st
import pandas as pd
from engine.stage1_gemini import scan_company
from engine.stage2_gemini import generate_situation_notes, generate_positioning_notes
from engine.html_output import generate_html
from engine.pipeline import run_pipeline

st.set_page_config(page_title="XIMPAX Outreach Engine", page_icon="⚡", layout="wide")
st.title("⚡ XIMPAX Outreach Engine")
st.caption("Research a company and generate tailored outreach proposals for a specific contact.")

CLOSENESS_OPTIONS = [
    "🧊 Cold — never met or exchanged messages",
    "🤝 Know professionally — met once or twice",
    "👋 Regular contact — speak fairly often",
]

with st.sidebar:
    st.header("🔑 Settings")
    gemini_key = st.text_input("Gemini API Key", type="password", 
                             value=st.secrets.get("GEMINI_API_KEY", ""))
    st.divider()
    st.markdown("""
**Closeness level — affects message tone:**
🧊 **Cold** — formal, open with a specific public fact
🤝 **Professional** — warmer, reference shared context
👋 **Regular** — direct, skip intro, get to the point
""")
    st.divider()
    st.markdown("""
**Signals:**
🔴 RC — Resource Constraints
🟠 MP — Margin Pressure
🟢 SG — Significant Growth
🔵 SCD — Supply Chain Disruption
""")

tab_single, tab_batch = st.tabs(["👤 Single Contact", "📂 Batch Processing"])

with tab_single:
    st.subheader("Target Contact")
    col1, col2 = st.columns(2)
    with col1:
        target_name = st.text_input("Full Name", placeholder="e.g. John Doe")
        target_company = st.text_input("Company Name", placeholder="e.g. Nestle")
    with col2:
        target_function = st.text_input("Function / Job Title", placeholder="e.g. Head of Procurement")
        closeness = st.select_slider(
            "How well do you know this contact?",
            options=CLOSENESS_OPTIONS,
            value=CLOSENESS_OPTIONS[0],
            help="Adjusts the opening tone and directness of the outreach messages",
        )

    if st.button("🚀 Generate Outreach Analysis", type="primary"):
        if not gemini_key:
            st.error("Please enter your Gemini API Key in the sidebar.")
        elif not target_company or not target_name:
            st.warning("Please provide at least a name and company.")
        else:
            with st.spinner(f"Researching {target_company} and drafting proposals..."):
                try:
                    research = scan_company(target_company, gemini_key)
                    active_situations = research.get("active_situations", [])
                    situations = generate_situation_notes(
                        target_company, target_function, active_situations, gemini_key, closeness)
                    positioning = generate_positioning_notes(
                        target_company, target_function, gemini_key, closeness)
                    
                    st.session_state["result"] = {
                        "name": target_name,
                        "company": target_company,
                        "function": target_function,
                        "closeness": closeness,
                        "research": research,
                        "situations": situations,
                        "positioning": positioning,
                    }
                except Exception as e:
                    st.error(f"Error during generation: {e}")

    if "result" in st.session_state:
        res = st.session_state["result"]
        research = res["research"]
        
        st.divider()
        st.header(f"📊 Situation Overview: {res['company']}")
        st.info(research.get("SUMMARY", "No summary available."))
        
        cols = st.columns(4)
        codes = [("RC", "🔴 Resource"), ("MP", "🟠 Margin"), ("SG", "🟢 Growth"), ("SCD", "🔵 Supply Chain")]
        for i, (code, label) in enumerate(codes):
            with cols[i]:
                score = research.get(f"{code}_score", 0)
                status = research.get(f"{code}_status", "UNCLEAR")
                signal = research.get(f"{code}_signal", "No specific signals found.")
                st.markdown(f"**{label}** — {status} ({score}/10)")
                st.caption(signal)

        st.header("📝 Outreach Proposals")
        t1, t2 = st.tabs(["🎯 Situation Notes (3 Options)", "🏢 XIMPAX Positioning (3 Options)"])
        with t1: st.write(res["situations"])
        with t2: st.write(res["positioning"])

        st.divider()
        # Requirement: Column 4 or 5 message output + Signals in separate columns
        data = {
            "name": [res["name"]],
            "known_function": [res["function"]],
            "company": [res["company"]],
            "situation_notes": [res["situations"]],
            "RC": [research.get("RC_signal", "")],
            "SCD": [research.get("SCD_signal", "")],
            "MP": [research.get("MP_signal", "")],
            "SG": [research.get("SG_signal", "")],
            "closeness_level": [res["closeness"]],
            "company_summary": [research.get("SUMMARY", "")],
            "RC_score": [research.get("RC_score", 0)],
            "MP_score": [research.get("MP_score", 0)],
            "SG_score": [research.get("SG_score", 0)],
            "SCD_score": [research.get("SCD_score", 0)],
        }
        df = pd.DataFrame(data)
        html_str = generate_html(df)
        st.download_button(
            label="🌐 Download HTML Report",
            data=html_str.encode("utf-8"),
            file_name=f"outreach_{res['company'].lower().replace(' ', '_')}.html",
            mime="text/html",
            use_container_width=True,
        )

with tab_batch:
    st.subheader("Batch Process Contacts")
    uploaded_file = st.file_uploader("Upload CSV with columns: name, known_company, known_function, closeness_level", type="csv")
    
    if uploaded_file and gemini_key:
        if st.button("▶️ Start Batch Processing"):
            df_in = pd.read_csv(uploaded_file)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(current, total, msg):
                progress_bar.progress(current / total)
                status_text.text(msg)
                
            res_df, raw_df = run_pipeline(df_in, gemini_key, update_progress)
            
            st.success("Batch processing complete!")
            
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("📥 Download Excel Results", 
                                 data=res_df.to_csv(index=False).encode("utf-8"),
                                 file_name="ximpax_results.csv",
                                 mime="text/csv")
            with col_dl2:
                html_report = generate_html(res_df)
                st.download_button("🌐 Download HTML Report",
                                 data=html_report.encode("utf-8"),
                                 file_name="ximpax_report.html",
                                 mime="text/html")
            
            st.dataframe(res_df)
