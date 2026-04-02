import streamlit as st
import pandas as pd
from engine.stage1_gemini import scan_company
from engine.stage2_gemini import generate_situation_notes, generate_positioning_notes
from engine.html_output import generate_html

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
🧊 **Cold** — formal, reference a specific public fact to open
🤝 **Professional** — slightly warmer, reference shared context
👋 **Regular** — direct, skip the intro, get to the point
""")
    st.divider()
    st.markdown("""
**Signals:**
🔴 RC — Resource Constraints
🟠 MP — Margin Pressure
🟢 SG — Significant Growth
🔵 SCD — Supply Chain Disruption
""")

st.subheader("👤 Target Contact")
col1, col2 = st.columns(2)
with col1:
    target_name    = st.text_input("Full Name",        placeholder="e.g. John Doe")
    target_company = st.text_input("Company Name",     placeholder="e.g. Nestle")
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
                research         = scan_company(target_company, gemini_key)
                active_situations = research.get("active_situations", [])
                situations       = generate_situation_notes(
                    target_company, target_function, active_situations, gemini_key, closeness)
                positioning      = generate_positioning_notes(
                    target_company, target_function, gemini_key, closeness)
                st.session_state["result"] = {
                    "name":      target_name,
                    "company":   target_company,
                    "function":  target_function,
                    "closeness": closeness,
                    "research":  research,
                    "situations": situations,
                    "positioning": positioning,
                }
            except Exception as e:
                st.error(f"Error during generation: {e}")

if "result" in st.session_state:
    res      = st.session_state["result"]
    research = res["research"]

    st.divider()
    st.header(f"📊 Situation Overview: {res['company']}")
    st.info(research.get("SUMMARY", "No summary available."))

    cols  = st.columns(4)
    codes = [("RC", "🔴 Resource"), ("MP", "🟠 Margin"), ("SG", "🟢 Growth"), ("SCD", "🔵 Supply Chain")]
    for i, (code, label) in enumerate(codes):
        with cols[i]:
            score  = research.get(f"{code}_score", 0)
            status = research.get(f"{code}_status", "UNCLEAR")
            signal = research.get(f"{code}_signal", "No specific signals found.")
            st.markdown(f"**{label}** — {status} ({score}/10)")
            st.caption(signal)

    st.header("📝 Outreach Proposals")
    tab1, tab2 = st.tabs(["🎯 Situation Notes (3 Options)", "🏢 XIMPAX Positioning (3 Options)"])
    with tab1:
        st.write(res["situations"])
    with tab2:
        st.write(res["positioning"])

    st.divider()
    data = {
        "name":           [res["name"]],
        "company":        [res["company"]],
        "known_function": [res["function"]],
        "situation_notes":  [res["situations"]],
        "positioning_notes": [res["positioning"]],
        "company_summary":  [research.get("SUMMARY", "")],
        "linkedin_message": [""],
        "notes":            [""],
        "RC_score":  [research.get("RC_score",  0)], "RC_status":  [research.get("RC_status",  "UNCLEAR")], "RC_signal":  [research.get("RC_signal",  "")],
        "MP_score":  [research.get("MP_score",  0)], "MP_status":  [research.get("MP_status",  "UNCLEAR")], "MP_signal":  [research.get("MP_signal",  "")],
        "SG_score":  [research.get("SG_score",  0)], "SG_status":  [research.get("SG_status",  "UNCLEAR")], "SG_signal":  [research.get("SG_signal",  "")],
        "SCD_score": [research.get("SCD_score", 0)], "SCD_status": [research.get("SCD_status", "UNCLEAR")], "SCD_signal": [research.get("SCD_signal", "")],
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
