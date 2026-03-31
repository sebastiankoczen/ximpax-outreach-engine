import io
import streamlit as st
import pandas as pd
from engine.pipeline import run_pipeline
from engine.html_output import generate_html

st.set_page_config(page_title="XIMPAX Outreach Engine", page_icon="⚡", layout="wide")
st.title("⚡ XIMPAX Outreach Engine")
st.caption("Upload contacts with company names → Gemini researches each company → tailored LinkedIn messages")

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
    missing  = [c for c in required if c not in df.columns]
    if missing:
        st.error(
            f"❌ Missing columns: **{', '.join(missing)}**\n\n"
            f"Columns in your file: `{', '.join(df.columns.tolist())}`"
        )
        st.stop()

    blank = df[df["known_company"].astype(str).str.strip().isin(["", "nan"])]
    if not blank.empty:
        st.warning(f"⚠️ {len(blank)} contacts have no company — they will be skipped.")

    st.subheader(f"📋 {len(df)} contacts loaded")
    st.dataframe(df[["name", "known_function", "closeness_level", "known_company"]],
                 use_container_width=True)

    if st.button("🚀 Generate Messages", type="primary"):
        if not gemini_key:
            st.error("Please enter your Gemini API Key in the sidebar.")
            st.stop()

        progress_bar = st.progress(0)
        status_text  = st.empty()

        def cb(done, total, msg):
            progress_bar.progress(int(done / total * 100) if total else 0)
            status_text.info(msg)

        with st.spinner("Researching companies and writing messages (~15s per contact)..."):
            all_df, raw_df = run_pipeline(
                df=df, gemini_key=gemini_key, progress_cb=cb,
            )

        status_text.success("✅ Done!")
        progress_bar.progress(100)

        # Store results in session state so downloads survive reruns
        xlsx = io.BytesIO()
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            all_df.to_excel(writer, sheet_name="All Contacts", index=False)
            if not raw_df.empty:
                raw_df.to_excel(writer, sheet_name="Stage1 Raw", index=False)
        xlsx.seek(0)

        st.session_state["all_df"]     = all_df
        st.session_state["raw_df"]     = raw_df
        st.session_state["xlsx_bytes"] = xlsx.read()
        st.session_state["html_str"]   = generate_html(all_df)

    # ── Show results + downloads whenever session state has data ──────────────
    if "all_df" in st.session_state:
        all_df = st.session_state["all_df"]
        raw_df = st.session_state["raw_df"]

        tab1, tab2, tab3 = st.tabs(["💬 Messages", "📊 Signals", "🔬 Raw Output"])

        with tab1:
            st.dataframe(
                all_df[["name", "known_function", "company", "linkedin_message", "notes"]],
                use_container_width=True)
        with tab2:
            sig_cols = ["name", "company", "company_summary",
                        "RC_score","RC_status","RC_signal",
                        "MP_score","MP_status","MP_signal",
                        "SG_score","SG_status","SG_signal",
                        "SCD_score","SCD_status","SCD_signal"]
            st.dataframe(all_df[[c for c in sig_cols if c in all_df.columns]],
                         use_container_width=True)
        with tab3:
            if not raw_df.empty:
                st.dataframe(raw_df, use_container_width=True)
            else:
                st.info("No raw output available.")

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
        st.caption("HTML: open in any browser — click any message to copy it to clipboard.")
