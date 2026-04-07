import re
import streamlit as st
import pandas as pd
from engine.stage1_gemini import scan_company
from engine.stage2_gemini import generate_situation_notes, generate_positioning_notes
from engine.html_output import generate_html
from engine.pipeline import run_pipeline

st.set_page_config(page_title="XIMPAX Outreach Engine", page_icon="⚡", layout="wide")
st.title("⚡ XIMPAX Outreach Engine")
st.caption("Research a company and generate tailored outreach proposals for a specific contact.")


def _strip_preamble(text):
    """Remove any introductory sentence before the first numbered option."""
    if not text:
        return text
    m = re.search(r"(1\.\s+.+)", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def _render_sources(sources):
    """Render sources (list of dicts or string) as markdown links."""
    links = []
    if isinstance(sources, list):
        for s in sources:
            if isinstance(s, dict):
                title = s.get("title", "") or s.get("uri", "")
                uri = s.get("uri", "")
                if uri:
                    links.append(f"[{title}]({uri})")
                elif title:
                    links.append(title)
    elif isinstance(sources, str) and sources.strip():
        for ln in sources.strip().splitlines():
            ln = ln.strip().strip("-").strip()
            if not ln:
                continue
            if "|" in ln:
                title, url = ln.split("|", 1)
                title, url = title.strip(), url.strip()
                links.append(f"[{title}]({url})" if url.startswith("http") else title)
            elif ln.startswith("http"):
                links.append(f"[{ln}]({ln})")
            else:
                links.append(ln)
    return links


with st.sidebar:
    st.header("🔍 Settings")
    gemini_key = st.text_input("Gemini API Key", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))

tab_single, tab_batch = st.tabs(["👤 Single Contact", "📂 Batch Processing"])

with tab_single:
    st.subheader("Target Contact")
    col1, col2 = st.columns([2, 3])
    with col1:
        target_company = st.text_input("Company", placeholder="e.g. Company AG")
    with col2:
        target_function = st.text_input("Function / Job Title", placeholder="e.g. Head of Procurement")

    if st.button("🚀 Generate Analysis", type="primary"):
        if not gemini_key:
            st.error("Please enter your Gemini API Key.")
        elif not target_company:
            st.warning("Company is required.")
        else:
            with st.spinner(f"Analyzing {target_company}..."):
                try:
                    research = scan_company(target_company, gemini_key, target_function)
                    situations = generate_situation_notes(
                        target_company, target_function, research["active_situations"], gemini_key
                    )
                    positioning = generate_positioning_notes(
                        target_company, target_function, gemini_key
                    )
                    st.session_state["result"] = {
                        "company": target_company,
                        "function": target_function,
                        "research": research,
                        "situations": _strip_preamble(situations),
                        "positioning": _strip_preamble(positioning),
                    }
                except Exception as e:
                    st.error(f"Generation error: {e}")

if "result" in st.session_state:
    res = st.session_state["result"]
    research = res["research"]

    st.divider()
    st.header(f"📊 {res['company']} Situation")
    st.info(research.get("SUMMARY", "No summary available."))

    # Sources — clickable links from grounding metadata
    sources = research.get("SOURCES", [])
    links = _render_sources(sources)
    if links:
        st.caption("🔗 **Sources:** " + " · ".join(links))

    # Signals in order: RC, SCD, MP, SG
    codes = [
        ("RC", "🟡 Resource Constraints"),
        ("SCD", "🔵 Supply Chain Disruption"),
        ("MP", "🔴 Margin Pressure"),
        ("SG", "🟢 Significant Growth"),
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
                st.markdown(signal)

    st.divider()
    st.header("📝 Outreach Proposals")
    st.write(res["situations"])

    st.divider()
    st.header("🏢 XIMPAX Positioning")
    st.write(res["positioning"])

    # Data for export
    data = {
        "known_function": [res["function"]],
        "company": [res["company"]],
        "situation_notes": [res["situations"]],
        "positioning_notes": [res["positioning"]],
        "RC_score": [research.get("RC_score", 0)],
        "RC_signal": [research.get("RC_signal", "")],
        "RC_status": [research.get("RC_status", "")],
        "SCD_score": [research.get("SCD_score", 0)],
        "SCD_signal": [research.get("SCD_signal", "")],
        "SCD_status": [research.get("SCD_status", "")],
        "MP_score": [research.get("MP_score", 0)],
        "MP_signal": [research.get("MP_signal", "")],
        "MP_status": [research.get("MP_status", "")],
        "SG_score": [research.get("SG_score", 0)],
        "SG_signal": [research.get("SG_signal", "")],
        "SG_status": [research.get("SG_status", "")],
        "summary": [research.get("SUMMARY", "")],
        "sources": [research.get("SOURCES", [])],
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
    uploaded_file = st.file_uploader("Upload CSV (known_company, known_function, closeness_level)", type="csv")
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
