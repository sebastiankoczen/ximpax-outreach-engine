import os, io
import streamlit as st
import pandas as pd
from engine.pipeline import run_pipeline

st.set_page_config(page_title="XIMPAX Outreach Engine", page_icon="⚡", layout="wide")
st.title("⚡ XIMPAX LinkedIn Outreach Engine")
st.caption("Upload your contact list → auto-research → tailored LinkedIn messages")

with st.sidebar:
    st.header("🔑 API Keys")
    serper_key = st.text_input("Serper API Key", type="password",
                               value=st.secrets.get("SERPER_API_KEY", ""))
    gemini_key = st.text_input("Gemini API Key", type="password",
                               value=st.secrets.get("GEMINI_API_KEY", ""))
    st.divider()
    st.markdown("**Required CSV columns:**")
    st.code("name, known_function, closeness_level\n(optional: known_company, company_situation)")

uploaded = st.file_uploader("Upload contacts CSV", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    st.subheader(f"Preview — {len(df)} contacts loaded")
    st.dataframe(df, use_container_width=True)

    if st.button("🚀 Run Pipeline", type="primary"):
        if not (serper_key and gemini_key):
            st.error("Please fill in both API keys in the sidebar.")
            st.stop()

        progress_bar  = st.progress(0)
        status_text   = st.empty()

        def cb(done, total, msg):
            progress_bar.progress(int(done / total * 100) if total else 0)
            status_text.info(msg)

        with st.spinner("Running pipeline — ~15s per contact (Gemini grounding)..."):
            all_df, review_df, raw_df = run_pipeline(
                df=df,
                serper_key=serper_key,
                gemini_key=gemini_key,
                progress_cb=cb,
            )

        status_text.success("✅ Pipeline complete!")
        progress_bar.progress(100)

        tab1, tab2, tab3 = st.tabs(["📋 All Contacts", "⚠️ Needs Review", "🔬 Stage 1 Raw"])

        with tab1:
            st.dataframe(all_df[["name","company","company_confidence",
                                  "active_situations","linkedin_message","notes"]],
                         use_container_width=True)
        with tab2:
            if not review_df.empty:
                st.dataframe(review_df, use_container_width=True)
            else:
                st.success("No contacts need manual review!")
        with tab3:
            if not raw_df.empty:
                st.dataframe(raw_df, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            all_df.to_excel(writer, sheet_name="All Contacts", index=False)
            if not review_df.empty:
                review_df.to_excel(writer, sheet_name="Needs Review", index=False)
            if not raw_df.empty:
                raw_df.to_excel(writer, sheet_name="Stage1 Raw", index=False)
        output.seek(0)

        st.download_button(
            label="⬇️ Download outreach_output.xlsx",
            data=output,
            file_name="outreach_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
