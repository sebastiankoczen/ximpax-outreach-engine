import io
import streamlit as st
import pandas as pd
from engine.pipeline import run_pipeline
from engine.html_output import generate_html

st.set_page_config(page_title="XIMPAX Outreach Engine", page_icon="⚡", layout="wide")

st.title("⚡ XIMPAX Outreach Engine")
st.caption("Upload contacts → Research company signals → Generate 3 tailored outreach proposals")

with st.sidebar:
    st.header("🔑 Gemini API Key")
    gemini_key = st.text_input("Gemini API Key", type="password", 
                             value=st.secrets.get("GEMINI_API_KEY", ""))
    st.divider()
    st.markdown("**Required CSV columns:**")
    st.code("name\nknown_function\ncloseness_level\nknown_company\n\nOptional:\ncompany_situation")
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

uploaded = st.file_uploader("Upload contacts CSV (must include known_company column)", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")
    
    required = ["name", "known_function", "closeness_level", "known_company"]
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ Missing columns: **{', '.join(missing)}**")
        st.stop()
        
    blank = df[df["known_company"].astype(str).str.strip().isin(["", "nan"])]
    if not blank.empty:
        st.warning(f"⚠️ {len(blank)} contacts have no company — they will be skipped.")
        
    st.subheader(f"📋 {len(df)} contacts loaded")
    st.dataframe(df[["name", "known_function", "closeness_level", "known_company"]], use_container_width=True)

    if st.button("🚀 Generate Proposals", type="primary"):
        if not gemini_key:
            st.error("Please enter your Gemini API Key in the sidebar.")
            st.stop()
            
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def cb(done, total, msg):
            progress_bar.progress(int(done / total * 100) if total else 0)
            status_text.info(msg)
            
        with st.spinner("Researching and writing proposals..."):
            all_df, raw_df = run_pipeline(
                df=df,
                gemini_key=gemini_key,
                progress_cb=cb,
            )
            
        status_text.success("✅ Done!")
        progress_bar.progress(100)

        # Store in session state
        xlsx = io.BytesIO()
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            all_df.to_excel(writer, sheet_name="All Contacts", index=False)
        xlsx.seek(0)
        
        st.session_state["all_df"] = all_df
        st.session_state["xlsx_bytes"] = xlsx.read()
        st.session_state["html_str"] = generate_html(all_df)

if "all_df" in st.session_state:
    all_df = st.session_state["all_df"]
    
    tab1, tab2 = st.tabs(["💬 Outreach Proposals", "📊 Research Signals"])
    
    with tab1:
        st.dataframe(
            all_df[["name", "company", "situation_notes", "known_function"]], 
            use_container_width=True)
            
    with tab2:
        sig_cols = ["name", "company", "company_summary", 
                   "RC_status", "RC_signal", 
                   "MP_status", "MP_signal", 
                   "SG_status", "SG_signal", 
                   "SCD_status", "SCD_signal"]
        st.dataframe(all_df[[c for c in sig_cols if c in all_df.columns]], use_container_width=True)
        
    st.divider()
    st.markdown("### ⬇️ Download Results")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📊 Download Excel",
            data=st.session_state["xlsx_bytes"],
            file_name="outreach_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            label="🌐 Download HTML Report",
            data=st.session_state["html_str"].encode("utf-8"),
            file_name="outreach_messages.html",
            mime="text/html",
            use_container_width=True,
        )
