import os, io, time
import streamlit as st
import pandas as pd
from engine.pipeline import run_pipeline
from engine.stage0_serper import lookup_company

st.set_page_config(page_title="XIMPAX Outreach Engine", page_icon="⚡", layout="wide")
st.title("⚡ XIMPAX LinkedIn Outreach Engine")

with st.sidebar:
    st.header("🔑 API Keys")
    serper_key = st.text_input("Serper API Key", type="password",
                               value=st.secrets.get("SERPER_API_KEY", ""))
    gemini_key = st.text_input("Gemini API Key", type="password",
                               value=st.secrets.get("GEMINI_API_KEY", ""))
    st.divider()
    mode = st.radio("Mode", [
        "🔍 Step 1 — Enrich Companies",
        "🚀 Step 2 — Full Pipeline",
    ])
    st.divider()
    st.markdown("**Required CSV columns:**")
    st.code("name\nknown_function\ncloseness_level\n\nOptional:\nknown_company\ncompany_situation")

# ─────────────────────────────────────────────────────────────────────────────
if mode == "🔍 Step 1 — Enrich Companies":
    st.subheader("🔍 Step 1 — Company Enrichment")
    st.markdown("""
Upload your contacts CSV. This step **only** runs the Serper company lookup (Stage 0) — fast and cheap.

It outputs a new CSV with a `known_company` column pre-filled.  
**Download it, open in Excel, manually fix any wrong entries, then use it in Step 2.**
    """)

    uploaded = st.file_uploader("Upload contacts CSV", type="csv", key="enrich")
    if uploaded:
        df = pd.read_csv(uploaded)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")

        required = ["name", "known_function"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"❌ Missing columns: {', '.join(missing)}")
            st.stop()

        st.dataframe(df, use_container_width=True)

        if st.button("🔍 Enrich Companies", type="primary"):
            if not serper_key:
                st.error("Please enter your Serper API Key in the sidebar.")
                st.stop()

            progress = st.progress(0)
            status   = st.empty()
            results  = []
            total    = len(df)

            for idx, row in df.iterrows():
                name     = str(row.get("name", "")).strip()
                function = str(row.get("known_function", "")).strip()
                status.info(f"[{idx+1}/{total}] Looking up: {name}...")

                # Skip if already has a known company
                existing = str(row.get("known_company", "")).strip()
                if existing and existing.lower() not in ("nan", ""):
                    results.append({**row.to_dict(), "known_company": existing,
                                    "lookup_confidence": 1.0, "lookup_strategy": "provided"})
                    progress.progress(int((idx+1)/total*100))
                    continue

                lk = lookup_company(name, function, serper_key)
                rec = row.to_dict()
                rec["known_company"]      = lk.get("company") or ""
                rec["lookup_confidence"]  = lk.get("confidence", 0.0)
                rec["lookup_strategy"]    = lk.get("strategy", "")
                results.append(rec)
                progress.progress(int((idx+1)/total*100))
                time.sleep(1.5)

            out_df = pd.DataFrame(results)
            status.success("✅ Enrichment complete!")

            # Highlight low-confidence rows
            low_conf = out_df[out_df["lookup_confidence"] < 0.5]

            st.subheader("Results")
            st.dataframe(
                out_df[["name", "known_function", "known_company",
                         "lookup_confidence", "lookup_strategy"]],
                use_container_width=True
            )

            if not low_conf.empty:
                st.warning(
                    f"⚠️ **{len(low_conf)} contact(s) have low confidence or no company found** "
                    f"(highlighted below). Please fill these in manually in Excel before running Step 2."
                )
                st.dataframe(
                    low_conf[["name", "known_function", "known_company", "lookup_confidence"]],
                    use_container_width=True
                )

            st.info("👇 Download this CSV → open in Excel → fix any wrong companies → upload in Step 2")
            csv_bytes = out_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download enriched_contacts.csv",
                data=csv_bytes,
                file_name="enriched_contacts.csv",
                mime="text/csv",
            )

# ─────────────────────────────────────────────────────────────────────────────
else:
    st.subheader("🚀 Step 2 — Full Pipeline")
    st.markdown("""
Upload your **enriched** contacts CSV (from Step 1, with `known_company` column filled).  
This runs Gemini research + message generation for each contact (~15s per contact).
    """)

    uploaded = st.file_uploader("Upload enriched contacts CSV", type="csv", key="pipeline")
    if uploaded:
        df = pd.read_csv(uploaded)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")

        required = ["name", "known_function", "closeness_level"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(
                f"❌ Missing columns: **{', '.join(missing)}**\n\n"
                f"Detected: `{', '.join(df.columns.tolist())}`"
            )
            st.stop()

        # Show warning if any known_company is blank
        if "known_company" in df.columns:
            blank = df[df["known_company"].astype(str).str.strip().isin(["", "nan"])]
            if not blank.empty:
                st.warning(
                    f"⚠️ {len(blank)} contact(s) have no `known_company` — "
                    "the pipeline will attempt Serper lookup, results may be inaccurate. "
                    "Consider going back to Step 1 first."
                )

        st.dataframe(df, use_container_width=True)

        if st.button("🚀 Run Full Pipeline", type="primary"):
            if not (serper_key and gemini_key):
                st.error("Please fill in both API keys in the sidebar.")
                st.stop()

            progress_bar = st.progress(0)
            status_text  = st.empty()

            def cb(done, total, msg):
                progress_bar.progress(int(done/total*100) if total else 0)
                status_text.info(msg)

            with st.spinner("Running pipeline — ~15s per contact..."):
                all_df, review_df, raw_df = run_pipeline(
                    df=df, serper_key=serper_key, gemini_key=gemini_key, progress_cb=cb,
                )

            status_text.success("✅ Pipeline complete!")
            progress_bar.progress(100)

            tab1, tab2, tab3, tab4 = st.tabs([
                "💬 Messages", "📊 Signals", "⚠️ Needs Review", "🔬 Raw Output"
            ])

            with tab1:
                msg_cols = ["name", "known_function", "company", "linkedin_message",
                            "active_situations", "notes"]
                st.dataframe(all_df[[c for c in msg_cols if c in all_df.columns]],
                             use_container_width=True)
            with tab2:
                signal_cols = ["name", "company", "company_summary",
                               "RC_score","RC_status","RC_signal",
                               "MP_score","MP_status","MP_signal",
                               "SG_score","SG_status","SG_signal",
                               "SCD_score","SCD_status","SCD_signal"]
                st.dataframe(all_df[[c for c in signal_cols if c in all_df.columns]],
                             use_container_width=True)
            with tab3:
                if not review_df.empty:
                    st.dataframe(review_df, use_container_width=True)
                else:
                    st.success("No contacts need manual review!")
            with tab4:
                if not raw_df.empty:
                    st.dataframe(raw_df, use_container_width=True)
                else:
                    st.info("No raw output available.")

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                all_df.to_excel(writer,    sheet_name="All Contacts", index=False)
                if not review_df.empty:
                    review_df.to_excel(writer, sheet_name="Needs Review", index=False)
                if not raw_df.empty:
                    raw_df.to_excel(writer,    sheet_name="Stage1 Raw",  index=False)
            output.seek(0)
            st.download_button(
                label="⬇️ Download outreach_output.xlsx",
                data=output,
                file_name="outreach_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
