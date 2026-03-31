import html as hl

SIGNAL_META = {
    "RC":  ("#fff3cd", "#856404", "🔴", "Resource Constraints"),
    "MP":  ("#f8d7da", "#842029", "🟠", "Margin Pressure"),
    "SG":  ("#d1e7dd", "#0f5132", "🟢", "Significant Growth"),
    "SCD": ("#cfe2ff", "#084298", "🔵", "Supply Chain Disruption"),
}


def _signal_row(code, status, signal_text):
    """Full signal row with label, status and evidence text."""
    if status == "UNCLEAR" or not signal_text or str(signal_text).strip() in ("", "nan"):
        return ""
    bg, fg, icon, label = SIGNAL_META[code]
    text = hl.escape(str(signal_text).strip())
    return f"""
    <div class="signal-row" style="border-left:3px solid {fg}; background:{bg}20;">
        <span class="signal-label" style="color:{fg};">{icon} {label}</span>
        <span class="signal-status" style="background:{bg};color:{fg};">{status}</span>
        <p class="signal-text">{text}</p>
    </div>"""


def _signal_badge(code, status):
    if status == "UNCLEAR":
        return ""
    bg, fg, icon, label = SIGNAL_META[code]
    return (f'<span class="badge" style="background:{bg};color:{fg};border:1px solid {fg}40;">' 
            f'{icon} {label} — {status}</span>')


def generate_html(df) -> str:
    cards = []
    for _, row in df.iterrows():
        name    = hl.escape(str(row.get("name", "")))
        func    = hl.escape(str(row.get("known_function", "")))
        company = hl.escape(str(row.get("company", "")))
        message = hl.escape(str(row.get("linkedin_message", ""))).replace("\n", "<br>")
        summary = hl.escape(str(row.get("company_summary", ""))).strip()
        notes   = str(row.get("notes", ""))
        skipped = "no company" in notes.lower() or "skipped" in notes.lower()

        # Signal rows
        signal_rows = ""
        has_signals = False
        for code in ["MP", "RC", "SG", "SCD"]:
            status = str(row.get(f"{code}_status", "UNCLEAR"))
            signal = str(row.get(f"{code}_signal", ""))
            if status != "UNCLEAR":
                has_signals = True
            signal_rows += _signal_row(code, status, signal)

        # Summary block
        summary_block = ""
        if summary and summary not in ("", "nan") and not skipped:
            summary_block = f"""
            <div class="summary-block">
                <div class="summary-label">📋 Company Situation Summary</div>
                <p class="summary-text">{summary}</p>
            </div>"""

        # Signals section
        signals_section = ""
        if has_signals and not skipped:
            signals_section = f"""
            <div class="signals-section">
                <div class="section-label">📊 Situation Signals</div>
                {signal_rows}
            </div>"""

        # Message block
        if skipped:
            msg_block = '<p class="skipped-note">⚠️ Skipped — no company provided</p>'
        else:
            msg_block = f"""
            <div class="section-label">💬 LinkedIn InMail</div>
            <div class="message-box" onclick="copyMsg(this)" title="Click to copy">{message}</div>
            <p class="copy-hint">👆 Click message to copy to clipboard</p>"""

        card_cls = "card skipped" if skipped else "card"
        cards.append(f"""
        <div class="{card_cls}">
            <div class="card-header">
                <div>
                    <span class="contact-name">{name}</span>
                    <span class="contact-meta">{func}</span>
                </div>
                <span class="company-tag">{company}</span>
            </div>
            {summary_block}
            {signals_section}
            <div class="message-section">
                {msg_block}
            </div>
        </div>""")

    total   = len(df)
    ready   = len(df[df["linkedin_message"].astype(str).str.len() > 10])
    skipped_n = len(df[df["notes"].astype(str).str.contains("skipped|error", case=False, na=False)])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>XIMPAX Outreach Messages</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
       background:#f0f2f5;color:#1a1a2e;padding:28px 20px}}
  h1{{font-size:22px;font-weight:700;color:#0a66c2;margin-bottom:3px}}
  .subtitle{{font-size:13px;color:#888;margin-bottom:20px}}
  .stats{{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}}
  .stat{{background:#fff;border-radius:10px;padding:12px 20px;
         box-shadow:0 1px 4px rgba(0,0,0,.08);text-align:center;min-width:100px}}
  .stat strong{{display:block;font-size:26px;font-weight:700;color:#0a66c2}}
  .stat span{{font-size:11px;color:#999}}
  .card{{background:#fff;border-radius:14px;padding:22px 24px;
         margin-bottom:18px;box-shadow:0 1px 6px rgba(0,0,0,.08);
         border-left:4px solid #0a66c2}}
  .card.skipped{{border-left-color:#ccc;opacity:.65}}
  .card-header{{display:flex;justify-content:space-between;align-items:flex-start;
                margin-bottom:14px;gap:12px;flex-wrap:wrap}}
  .contact-name{{font-size:16px;font-weight:700;display:block}}
  .contact-meta{{font-size:12px;color:#666;margin-top:2px;display:block}}
  .company-tag{{background:#e8f0fe;color:#0a66c2;font-size:12px;font-weight:600;
                padding:5px 12px;border-radius:20px;white-space:nowrap;flex-shrink:0}}
  .summary-block{{background:#f8f9fa;border-radius:8px;padding:12px 14px;
                  margin-bottom:14px;border:1px solid #e9ecef}}
  .summary-label{{font-size:11px;font-weight:700;color:#495057;
                  text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}}
  .summary-text{{font-size:13px;color:#444;line-height:1.6}}
  .signals-section{{margin-bottom:14px}}
  .section-label{{font-size:11px;font-weight:700;color:#495057;
                  text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
  .signal-row{{border-radius:6px;padding:8px 12px;margin-bottom:6px}}
  .signal-label{{font-size:12px;font-weight:700;margin-right:8px}}
  .signal-status{{font-size:10px;font-weight:700;padding:2px 7px;
                  border-radius:10px;margin-right:8px;vertical-align:middle}}
  .signal-text{{font-size:12px;color:#444;margin-top:4px;line-height:1.5}}
  .message-section{{margin-top:4px}}
  .message-box{{background:#f0f7ff;border:1.5px solid #b8d4f8;border-radius:8px;
                padding:14px 16px;font-size:14px;line-height:1.7;cursor:pointer;
                transition:background .15s;white-space:pre-wrap;color:#1a1a2e}}
  .message-box:hover{{background:#dbeafe}}
  .copy-hint{{font-size:11px;color:#aaa;margin-top:5px;text-align:right}}
  .skipped-note{{color:#aaa;font-size:13px;font-style:italic;padding:8px 0}}
  .badge{{font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px;
          display:inline-block;margin:2px 3px 2px 0}}
  .toast{{position:fixed;bottom:24px;right:24px;background:#1a1a2e;color:#fff;
          padding:10px 18px;border-radius:8px;font-size:13px;opacity:0;
          transition:opacity .3s;pointer-events:none;z-index:999}}
  .toast.show{{opacity:1}}
  @media(max-width:600px){{body{{padding:12px}}.card{{padding:16px}}}}
</style>
</head>
<body>
<h1>⚡ XIMPAX Outreach Messages</h1>
<p class="subtitle">Click any message to copy it directly to clipboard.</p>
<div class="stats">
  <div class="stat"><strong>{total}</strong><span>Contacts</span></div>
  <div class="stat"><strong>{ready}</strong><span>Messages ready</span></div>
  <div class="stat"><strong>{skipped_n}</strong><span>Skipped</span></div>
</div>
{"".join(cards)}
<div class="toast" id="toast">✅ Copied!</div>
<script>
function copyMsg(el){{
  navigator.clipboard.writeText(el.innerText).then(()=>{{
    const t=document.getElementById("toast");
    t.classList.add("show");
    setTimeout(()=>t.classList.remove("show"),2000);
  }});
}}
</script>
</body>
</html>"""
