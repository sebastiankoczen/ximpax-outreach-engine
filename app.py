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
    "❄️ Cold — never met or exchanged messages",
    "🤝 Know professionally — met once or twice",
    "📞 Regular contact — speak fairly often",
]

with st.sidebar:
    st.header("🔍 Settings")
    gemini_key = st.text_input("Gemini API Key", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
    st.divider()
    st.markdown("""
**Closeness level** — affects message tone:
- **Cold**: Evidence-heavy, formal.
- **Professional**: Warm, collegial.
- **Regular**: Direct, brief, personal.
""")

tab_single, tab_batch = st.tabs(["👤 Single Contact", "📂 Batch Processing"])

with tab_single:
    st.subheader("Target Contact")
    col1, col2 = st.columns(2)
    with col1:
        target_name = st.text_input("Full Name", placeholder="e.g. Chris Bokkers")
        target_company = st.text_input("Company Name", placeholder="e.g. Novo Nordisk")
    with col2:
        target_function = st.text_input("Function / Job Title", placeholder="e.g. Supply Chain Planning")
        closeness = st.select_slider(
            "Relationship level",
            options=CLOSENESS_OPTIONS,
            value=CLOSENESS_OPTIONS[0]
        )

    if st.button("🚀 Generate Analysis", type="primary"):
        if not gemini_key:
            st.error("Please enter your Gemini API Key.")
        elif not target_company or not target_name:
            st.warning("Name and Company are required.")
        else:
            with st.spinner(f"Analyzing {target_company}..."):
                try:
                    # Stage 1: Research
                    research = scan_company(target_company, gemini_key, target_function)

                    # Stage 2: Drafting
                    situations = generate_situation_notes(
                        target_company, target_function, research["active_situations"], gemini_key, closeness
                    )
                    positioning = generate_positioning_notes(
                        target_company, target_function, gemini_key, closeness
                    )

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
                    st.error(f"Generation error: {e}")

    if "result" in st.session_state:
        res = st.session_state["result"]
        research = res["research"]

        st.divider()
        st.header(f"📊 {res['company']} Situation")
        st.info(research.get("SUMMARY", "No summary available."))

        # Signals in order: RC, SCD, MP, SG with correct colors and full names
        codes = [
            ("RC",  "🟡 Resource Constraints"),
            ("SCD", "🔵 Supply Chain Disruption"),
            ("MP",  "🔴 Margin Pressure"),
            ("SG",  "🟢 Significant Growth"),
        ]
        cols = st.columns(4)
        for i, (code, label) in enumerate(codes):
            with cols[i]:
                score = research.get(f"{code}_score", 0)
                status = research.get(f"{code}_status", "UNCLEAR")
                signal = research.get(f"{code}_signal", "")
                st.markdown(f"**{label}**")
                st.markdown(f"`{status}` ({score}/10)")
                if signal:
                    # Render bullet points: signal is space-collapsed, split on " - " pattern
                    bullets = [b.strip() for b in signal.split("- ") if b.strip()]
                    if len(bullets) > 1:
                        for b in bullets:
                            st.markdown(f"- {b}")
                    else:
                        st.caption(signal)

        st.divider()
        st.header("📝 Outreach Proposals")
        st.write(res["situations"])

        st.divider()
        st.header("🏢 XIMPAX Positioning")
        st.write(res["positioning"])

        # Data for export
        data = {
            "name": [res["name"]],
            "known_function": [res["function"]],
            "company": [res["company"]],
            "situation_notes": [res["situations"]],
            "positioning_notes": [res["positioning"]],
            "RC_score": [research.get("RC_score", 0)],
            "RC_signal": [research.get("RC_signal", "")],
            "SCD_score": [research.get("SCD_score", 0)],
            "SCD_signal": [research.get("SCD_signal", "")],
            "MP_score": [research.get("MP_score", 0)],
            "MP_signal": [research.get("MP_signal", "")],
            "SG_score": [research.get("SG_score", 0)],
            "SG_signal": [research.get("SG_signal", "")],
            "summary": [research.get("SUMMARY", "")]
        }
        df = pd.DataFrame(data)
        html_report = generate_html(df)
        st.download_button(
            "🌐 Download Report",
            data=html_report.encode("utf-8"),
            file_name=f"ximpax_{res['company'].lower().replace(' ', '_')}.html",
            mime="text/html",
            use_container_width=True
        )

with tab_batch:
    st.subheader("Batch Process")
    uploaded_file = st.file_uploader("Upload CSV (name, known_company, known_function, closeness_level)", type="csv")
    if uploaded_file and gemini_key:
        if st.button("▶️ Start Process"):
            df_in = pd.read_csv(uploaded_file)
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(current, total, msg):
                progress_bar.progress(current / total)
                status_text.text(msg)

            res_df, _ = run_pipeline(df_in, gemini_key, update_progress)
            st.success("Complete!")
            html_batch = generate_html(res_df)
            st.download_button(
                "🌐 Download HTML Report",
                data=html_batch.encode("utf-8"),
                file_name="ximpax_batch_report.html",
                mime="text/html"
            )
            st.dataframe(res_df)
