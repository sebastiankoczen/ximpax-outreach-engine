import os, io
import streamlit as st
import pandas as pd
from engine.pipeline import run_pipeline

st.set_page_config(page_title="XIMPAX Outreach Engine", page_icon="⚡", layout="wide")
st.title("⚡ XIMPAX LinkedIn Outreach Engine")
st.caption("Upload contacts → Serper finds company → Gemini researches signals → Gemini writes tailored message")

with st.sidebar:
    st.header("🔑 API Keys")
    serper_key = st.text_input("Serper API Key", type="password",
                               value=st.secrets.get("SERPER_API_KEY", ""))
    gemini_key = st.text_input("Gemini API Key", type="password",
                               value=st.secrets.get("GEMINI_API_KEY", ""))
    st.divider()
    st.markdown("**Required CSV columns:**")
    st.code("name\nknown_function\ncloseness_level\n\nOptional:\nknown_company\ncompany_situation")
    st.divider()
    st.markdown("**Signal legend**")
    st.markdown("""
- 🔴 **RC** — Resource Constraints
- 🟠 **MP** — Margin Pressure
- 🟢 **SG** — Significant Growth
- 🔵 **SCD** — Supply Chain Disruption

`CONFIRMED` = strong public evidence  
`LIKELY` = indirect signals  
`UNCLEAR` = nothing found
    """)

uploaded = st.file_uploader("Upload contacts CSV", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")

    st.subheader(f"📋 {len(df)} contacts loaded")
    st.dataframe(df, use_container_width=True)

    required = ["name", "known_function", "closeness_level"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(
            f"❌ Missing columns: **{', '.join(missing)}**\n\n"
            f"Detected: `{', '.join(df.columns.tolist())}`\n\n"
            "Please rename to: `name`, `known_function`, `closeness_level`"
        )
        st.stop()

    if st.button("🚀 Run Pipeline", type="primary"):
        if not (serper_key and gemini_key):
            st.error("Please fill in both API keys in the sidebar.")
            st.stop()

        progress_bar = st.progress(0)
        status_text  = st.empty()

        def cb(done, total, msg):
            progress_bar.progress(int(done / total * 100) if total else 0)
            status_text.info(msg)

        with st.spinner("Running pipeline — ~15s per contact (Gemini Google Search grounding)..."):
            all_df, review_df, raw_df = run_pipeline(
                df=df, serper_key=serper_key, gemini_key=gemini_key, progress_cb=cb,
            )

        status_text.success("✅ Pipeline complete!")
        progress_bar.progress(100)

        # ── 4 tabs ──────────────────────────────────────────────────────────
        tab1, tab2, tab3, tab4 = st.tabs([
            "💬 Messages", "📊 Signals", "⚠️ Needs Review", "🔬 Raw Gemini Output"
        ])

        with tab1:
            st.markdown("### LinkedIn Messages + Company")
            msg_cols = ["name", "company", "company_confidence",
                        "active_situations", "linkedin_message", "notes"]
            st.dataframe(all_df[[c for c in msg_cols if c in all_df.columns]],
                         use_container_width=True)

        with tab2:
            st.markdown("### Company Situation Signals (from Gemini + Google Search)")
            st.caption("These signals feed directly into the message. CONFIRMED/LIKELY = used in message. UNCLEAR = not referenced.")
            signal_cols = [
                "name", "company", "company_summary",
                "RC_score", "RC_status", "RC_signal",
                "MP_score", "MP_status", "MP_signal",
                "SG_score", "SG_status", "SG_signal",
                "SCD_score", "SCD_status", "SCD_signal",
            ]
            st.dataframe(all_df[[c for c in signal_cols if c in all_df.columns]],
                         use_container_width=True)

        with tab3:
            if not review_df.empty:
                st.markdown("### Contacts flagged for manual review (low confidence company lookup)")
                st.dataframe(review_df, use_container_width=True)
            else:
                st.success("No contacts need manual review!")

        with tab4:
            if not raw_df.empty:
                st.markdown("### Raw Gemini Stage 1 output (full text per company)")
                st.dataframe(raw_df, use_container_width=True)
            else:
                st.info("No raw output — Stage 1 may have been skipped for all contacts.")

        # ── Download ────────────────────────────────────────────────────────
        st.divider()
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            all_df.to_excel(writer,    sheet_name="All Contacts", index=False)
            if not review_df.empty:
                review_df.to_excel(writer, sheet_name="Needs Review", index=False)
            if not raw_df.empty:
                raw_df.to_excel(writer, sheet_name="Stage1 Raw",   index=False)
        output.seek(0)
        st.download_button(
            label="⬇️ Download outreach_output.xlsx",
            data=output,
            file_name="outreach_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
