import streamlit as st
import pandas as pd
from engine.stage1_gemini import scan_company
from engine.stage2_gemini import generate_situation_notes, generate_positioning_notes
from engine.html_output import generate_html

st.set_page_config(page_title="XIMPAX Outreach Engine", page_icon="⚡", layout="wide")

st.title("⚡ XIMPAX Outreach Engine")
st.caption("Research a company and generate tailored outreach proposals for a specific contact.")

with st.sidebar:
    st.header("🔑 Settings")
    gemini_key = st.text_input("Gemini API Key", type="password", 
                             value=st.secrets.get("GEMINI_API_KEY", ""))
    st.divider()
    st.markdown("""
**Closeness scale:**
`1` = close colleague
`2` = professional contact
`3` = barely know them
""")
    st.divider()
    st.markdown("""
**Signals:**
🔴 RC — Resource Constraints
🟠 MP — Margin Pressure
🟢 SG — Significant Growth
🔵 SCD — Supply Chain Disruption
""")

# Input Fields
st.subheader("👤 Target Contact")
col1, col2 = st.columns(2)
with col1:
    target_name = st.text_input("Full Name", placeholder="e.g. John Doe")
    target_company = st.text_input("Company Name", placeholder="e.g. Nestle")
with col2:
    target_function = st.text_input("Function / Job Title", placeholder="e.g. Head of Procurement")
    closeness_level = st.select_slider("Closeness Level", options=[1, 2, 3], value=3, 
                                     help="1: Close, 2: Professional, 3: Cold/New")

if st.button("🚀 Generate Outreach Analysis", type="primary"):
    if not gemini_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    elif not target_company or not target_name:
        st.warning("Please provide at least a name and company.")
    else:
        with st.spinner(f"Researching {target_company} and drafting proposals..."):
            try:
                # Stage 1: Research
                research = scan_company(target_company, gemini_key)
                active_situations = research.get("active_situations", [])
                
                # Stage 2: Drafting
                situations = generate_situation_notes(target_company, target_function, active_situations, gemini_key)
                positioning = generate_positioning_notes(target_company, target_function, gemini_key)
                
                # Store in session state
                st.session_state["result"] = {
                    "name": target_name,
                    "company": target_company,
                    "function": target_function,
                    "research": research,
                    "situations": situations,
                    "positioning": positioning
                }
            except Exception as e:
                st.error(f"Error during generation: {e}")

# Output Display
if "result" in st.session_state:
    res = st.session_state["result"]
    research = res["research"]
    
    st.divider()
    
    # 1. Research Overview
    st.header(f"📊 Situation Overview: {res['company']}")
    st.info(research.get("SUMMARY", "No summary available."))
    
    # Signals Grid
    cols = st.columns(4)
    codes = [("RC", "Resource"), ("MP", "Margin"), ("SG", "Growth"), ("SCD", "Supply Chain")]
    for i, (code, label) in enumerate(codes):
        with cols[i]:
            status = research.get(f"{code}_status", "UNCLEAR")
            signal = research.get(f"{code}_signal", "No specific signals found.")
            st.markdown(f"**{label}** ({status})")
            st.caption(signal)

    # 2. Outreach Proposals
    st.header("📝 Outreach Proposals")
    tab1, tab2 = st.tabs(["🎯 Situational Notes (3 Options)", "🏢 XIMPAX Positioning (3 Options)"])
    
    with tab1:
        st.write(res["situations"])
        
    with tab2:
        st.write(res["positioning"])

    # 3. Downloads
    st.divider()
    # Create a simple DF for the HTML generator
    data = {
        "name": [res["name"]],
        "company": [res["company"]],
        "known_function": [res["function"]],
        "situation_notes": [res["situations"]],
        "company_summary": [research.get("SUMMARY", "")],
        "RC_status": [research.get("RC_status", "")], "RC_signal": [research.get("RC_signal", "")],
        "MP_status": [research.get("MP_status", "")], "MP_signal": [research.get("MP_signal", "")],
        "SG_status": [research.get("SG_status", "")], "SG_signal": [research.get("SG_signal", "")],
        "SCD_status": [research.get("SCD_status", "")], "SCD_signal": [research.get("SCD_signal", "")]
    }
    df = pd.DataFrame(data)
    html_str = generate_html(df)
    
    st.download_button(
        label="🌐 Download HTML Report",
        data=html_str.encode("utf-8"),
        file_name=f"outreach_{res['company'].lower()}.html",
        mime="text/html",
        use_container_width=True
    )
