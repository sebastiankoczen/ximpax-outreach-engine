import html

SIGNAL_COLORS = {
    "RC":  ("#fff3cd", "#856404", "Resource Constraints"),
    "MP":  ("#f8d7da", "#842029", "Margin Pressure"),
    "SG":  ("#d1e7dd", "#0f5132", "Significant Growth"),
    "SCD": ("#cfe2ff", "#084298", "Supply Chain Disruption"),
}

STATUS_ICON = {"CONFIRMED": "🔴", "LIKELY": "🟡", "UNCLEAR": "⚪"}


def _signal_badge(code, status, signal_text):
    if status == "UNCLEAR":
        return ""
    bg, fg, label = SIGNAL_COLORS.get(code, ("#eee", "#333", code))
    icon = STATUS_ICON.get(status, "")
    tip = html.escape(signal_text[:120]) if signal_text else ""
    return (f'<span class="badge" style="background:{bg};color:{fg};border:1px solid {fg}20;" ' 
            f'title="{tip}">{icon} {label} — {status}</span>')


def generate_html(df) -> str:
    cards = []
    for _, row in df.iterrows():
        name    = html.escape(str(row.get("name", "")))
        func    = html.escape(str(row.get("known_function", "")))
        company = html.escape(str(row.get("company", "")))
        message = html.escape(str(row.get("linkedin_message", ""))).replace("\n", "<br>")
        summary = html.escape(str(row.get("company_summary", "")))
        notes   = str(row.get("notes", ""))

        badges = ""
        for code in ["MP", "RC", "SG", "SCD"]:
            badges += _signal_badge(
                code,
                str(row.get(f"{code}_status", "UNCLEAR")),
                str(row.get(f"{code}_signal", "")),
            )

        skipped = "no company" in notes.lower() or "skipped" in notes.lower()
        card_class = "card skipped" if skipped else "card"

        msg_block = (
            '<p class="skipped-note">⚠️ Skipped — no company provided</p>'
            if skipped else
            f'<div class="message-box" onclick="copyMsg(this)" title="Click to copy">{message}</div>'
            f'<p class="copy-hint">👆 Click message to copy</p>'
        )

        summary_block = (
            f'<details><summary>Company research summary</summary><p class="summary">{summary}</p></details>'
            if summary and not skipped else ""
        )

        cards.append(f"""
        <div class="{card_class}">
            <div class="card-header">
                <div>
                    <span class="contact-name">{name}</span>
                    <span class="contact-meta">{func}</span>
                </div>
                <span class="company-tag">{company}</span>
            </div>
            <div class="badges">{badges}</div>
            {msg_block}
            {summary_block}
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>XIMPAX Outreach Messages</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #f4f6f9; color: #1a1a2e; padding: 24px; }}
  h1   {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; color: #0a66c2; }}
  .subtitle {{ font-size: 13px; color: #666; margin-bottom: 24px; }}
  .stats {{ display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap; }}
  .stat {{ background:#fff; border-radius:8px; padding:12px 20px;
           box-shadow:0 1px 4px rgba(0,0,0,.08); text-align:center; }}
  .stat strong {{ display:block; font-size:24px; color:#0a66c2; }}
  .stat span   {{ font-size:12px; color:#888; }}
  .card {{ background:#fff; border-radius:12px; padding:20px 24px;
           margin-bottom:16px; box-shadow:0 1px 6px rgba(0,0,0,.08);
           border-left: 4px solid #0a66c2; }}
  .card.skipped {{ border-left-color:#ccc; opacity:.7; }}
  .card-header {{ display:flex; justify-content:space-between;
                  align-items:flex-start; margin-bottom:10px; gap:12px; flex-wrap:wrap; }}
  .contact-name {{ font-size:16px; font-weight:600; display:block; }}
  .contact-meta {{ font-size:12px; color:#666; display:block; margin-top:2px; }}
  .company-tag  {{ background:#e8f0fe; color:#0a66c2; font-size:12px; font-weight:600;
                   padding:4px 10px; border-radius:20px; white-space:nowrap; }}
  .badges {{ display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; }}
  .badge  {{ font-size:11px; font-weight:600; padding:3px 8px; border-radius:20px;
             cursor:help; }}
  .message-box {{ background:#f8faff; border:1px solid #d0e4ff; border-radius:8px;
                  padding:14px 16px; font-size:14px; line-height:1.6;
                  cursor:pointer; transition:background .15s; white-space:pre-wrap; }}
  .message-box:hover {{ background:#e8f0fe; }}
  .copy-hint {{ font-size:11px; color:#999; margin-top:5px; text-align:right; }}
  .skipped-note {{ color:#999; font-size:13px; font-style:italic; padding:10px 0; }}
  details {{ margin-top:10px; }}
  summary  {{ font-size:12px; color:#0a66c2; cursor:pointer; user-select:none; }}
  .summary {{ font-size:12px; color:#555; line-height:1.6; margin-top:6px;
              background:#f9f9f9; padding:10px; border-radius:6px; }}
  .toast {{ position:fixed; bottom:24px; right:24px; background:#1a1a2e; color:#fff;
            padding:10px 18px; border-radius:8px; font-size:13px; opacity:0;
            transition:opacity .3s; pointer-events:none; z-index:999; }}
  .toast.show {{ opacity:1; }}
  @media(max-width:600px) {{ body {{ padding:12px; }} }}
</style>
</head>
<body>
<h1>⚡ XIMPAX Outreach Messages</h1>
<p class="subtitle">Click any message to copy it to clipboard.</p>

<div class="stats">
  <div class="stat"><strong>{len(df)}</strong><span>Total contacts</span></div>
  <div class="stat"><strong>{len(df[df["linkedin_message"].astype(str).str.len() > 10])}</strong><span>Messages ready</span></div>
  <div class="stat"><strong>{len(df[df["notes"].astype(str).str.contains("skipped|error", case=False, na=False)])}</strong><span>Skipped / errors</span></div>
</div>

{"".join(cards)}

<div class="toast" id="toast">✅ Copied to clipboard!</div>

<script>
function copyMsg(el) {{
  const text = el.innerText;
  navigator.clipboard.writeText(text).then(() => {{
    const t = document.getElementById("toast");
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 2000);
  }});
}}
</script>
</body>
</html>"""
