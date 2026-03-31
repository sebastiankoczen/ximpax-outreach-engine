import html as hl

SIGNAL_META = {
    "RC":  ("#fff3cd", "#856404", "🔴", "Resource Constraints"),
    "MP":  ("#f8d7da", "#842029", "🟠", "Margin Pressure"),
    "SG":  ("#d1e7dd", "#0f5132", "🟢", "Significant Growth"),
    "SCD": ("#cfe2ff", "#084298", "🔵", "Supply Chain Disruption"),
}

SCORE_COLOR = {
    (0,3):  ("#e9ecef","#6c757d"),
    (4,6):  ("#fff3cd","#856404"),
    (7,10): ("#f8d7da","#842029"),
}

def _score_color(score):
    s = int(score or 0)
    for (lo,hi),(bg,fg) in SCORE_COLOR.items():
        if lo <= s <= hi:
            return bg, fg
    return "#e9ecef","#6c757d"


def _top3_bullets(row):
    """Return top 3 signals sorted by score as HTML bullet items."""
    signals = []
    for code in ["RC","MP","SG","SCD"]:
        score  = int(row.get(f"{code}_score", 0) or 0)
        status = str(row.get(f"{code}_status","UNCLEAR"))
        signal = str(row.get(f"{code}_signal","")).strip()
        if status != "UNCLEAR" and signal and signal != "nan":
            _, _, icon, label = SIGNAL_META[code]
            signals.append((score, code, label, icon, status, signal))
    signals.sort(key=lambda x: -x[0])
    top3 = signals[:3]
    if not top3:
        return ""

    items = []
    for score, code, label, icon, status, signal in top3:
        bg, fg = _score_color(score)
        txt    = hl.escape(signal[:160]) + ("…" if len(signal) > 160 else "")
        items.append(f"""
        <li class="sig-bullet">
            <div class="sig-bullet-header">
                <span class="sig-icon-label" style="color:{fg};">{icon} {label}</span>
                <span class="sig-score" style="background:{bg};color:{fg};">score {score}/10</span>
                <span class="sig-status" style="background:{fg};color:#fff;">{status}</span>
            </div>
            <p class="sig-evidence">{txt}</p>
        </li>""")
    return "<ul class=\"sig-list\">" + "".join(items) + "</ul>"


def _notes_block(notes_raw):
    """Render the 3 positioning options as selectable cards."""
    if not notes_raw or str(notes_raw).strip() in ("","nan"):
        return ""
    lines = [l.strip() for l in str(notes_raw).splitlines() if l.strip()]
    cards = []
    for line in lines[:3]:
        # Strip leading "1." "2." "3." numbering
        import re
        text = re.sub(r"^[1-3][.)\s]+", "", line).strip()
        text = hl.escape(text)
        cards.append(
            f'<div class="note-card" onclick="copyNote(this)" title="Click to copy">' 
            f'{text}</div>'
        )
    if not cards:
        return ""
    return ('<div class="notes-section">' 
            '<div class="section-label">✏️ XIMPAX Positioning Options <span class="hint">(click to copy)</span></div>' 
            + "".join(cards) + '</div>')


def generate_html(df) -> str:
    cards = []
    for _, row in df.iterrows():
        name    = hl.escape(str(row.get("name", "")))
        func    = hl.escape(str(row.get("known_function", "")))
        company = hl.escape(str(row.get("company", "")))
        message = hl.escape(str(row.get("linkedin_message", ""))).replace("\n", "<br>")
        summary = hl.escape(str(row.get("company_summary", ""))).strip()
        pos_notes = str(row.get("positioning_notes", ""))
        notes   = str(row.get("notes", ""))
        skipped = "no company" in notes.lower() or "skipped" in notes.lower()

        bullets       = _top3_bullets(row) if not skipped else ""
        notes_section = _notes_block(pos_notes) if not skipped else ""

        summary_block = ""
        if summary and summary not in ("","nan") and not skipped:
            summary_block = f"""
            <div class="summary-block">
                <div class="section-label">📋 Company Situation</div>
                {bullets if bullets else f'<p class="summary-text">{summary[:300]}…</p>'}
            </div>"""

        if skipped:
            msg_block = '<p class="skipped-note">⚠️ Skipped — no company provided</p>'
        else:
            msg_block = f"""
            <div class="section-label">💬 LinkedIn InMail <span class="hint">(click to copy)</span></div>
            <div class="message-box" onclick="copyMsg(this)">{message}</div>"""

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
            {notes_section}
            <div class="message-section">{msg_block}</div>
        </div>""")

    total     = len(df)
    ready     = len(df[df["linkedin_message"].astype(str).str.len() > 10])
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
         box-shadow:0 1px 4px rgba(0,0,0,.08);text-align:center;min-width:90px}}
  .stat strong{{display:block;font-size:26px;font-weight:700;color:#0a66c2}}
  .stat span{{font-size:11px;color:#999}}
  .card{{background:#fff;border-radius:14px;padding:22px 24px;
         margin-bottom:18px;box-shadow:0 1px 6px rgba(0,0,0,.08);
         border-left:4px solid #0a66c2}}
  .card.skipped{{border-left-color:#ccc;opacity:.65}}
  .card-header{{display:flex;justify-content:space-between;align-items:flex-start;
                margin-bottom:16px;gap:12px;flex-wrap:wrap}}
  .contact-name{{font-size:16px;font-weight:700;display:block}}
  .contact-meta{{font-size:12px;color:#666;margin-top:2px;display:block}}
  .company-tag{{background:#e8f0fe;color:#0a66c2;font-size:12px;font-weight:600;
                padding:5px 12px;border-radius:20px;white-space:nowrap;flex-shrink:0}}
  .section-label{{font-size:11px;font-weight:700;color:#495057;
                  text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
  .hint{{font-weight:400;font-size:10px;color:#aaa;text-transform:none;letter-spacing:0}}
  .summary-block,.notes-section,.message-section{{margin-bottom:14px}}
  /* Signal bullets */
  .sig-list{{list-style:none;display:flex;flex-direction:column;gap:8px}}
  .sig-bullet{{border-radius:8px;padding:10px 12px;background:#f8f9fa;
               border:1px solid #e9ecef}}
  .sig-bullet-header{{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:4px}}
  .sig-icon-label{{font-size:12px;font-weight:700;flex:1;min-width:140px}}
  .sig-score{{font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px}}
  .sig-status{{font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px}}
  .sig-evidence{{font-size:12px;color:#555;line-height:1.5}}
  /* Positioning note cards */
  .note-card{{background:#f0f7ff;border:1.5px solid #b8d4f8;border-radius:8px;
              padding:10px 14px;font-size:13px;color:#1a1a2e;cursor:pointer;
              margin-bottom:6px;transition:background .15s;line-height:1.5}}
  .note-card:hover{{background:#dbeafe}}
  /* Message */
  .message-box{{background:#f0f7ff;border:1.5px solid #b8d4f8;border-radius:8px;
                padding:14px 16px;font-size:14px;line-height:1.7;cursor:pointer;
                transition:background .15s;white-space:pre-wrap;color:#1a1a2e}}
  .message-box:hover{{background:#dbeafe}}
  .skipped-note{{color:#aaa;font-size:13px;font-style:italic;padding:8px 0}}
  .toast{{position:fixed;bottom:24px;right:24px;background:#1a1a2e;color:#fff;
          padding:10px 18px;border-radius:8px;font-size:13px;opacity:0;
          transition:opacity .3s;pointer-events:none;z-index:999}}
  .toast.show{{opacity:1}}
  @media(max-width:600px){{body{{padding:12px}}.card{{padding:16px}}}}
</style>
</head>
<body>
<h1>⚡ XIMPAX Outreach Messages</h1>
<p class="subtitle">Click any message or positioning note to copy it to clipboard.</p>
<div class="stats">
  <div class="stat"><strong>{total}</strong><span>Contacts</span></div>
  <div class="stat"><strong>{ready}</strong><span>Messages ready</span></div>
  <div class="stat"><strong>{skipped_n}</strong><span>Skipped</span></div>
</div>
{"".join(cards)}
<div class="toast" id="toast">✅ Copied!</div>
<script>
function copyMsg(el){{
  navigator.clipboard.writeText(el.innerText).then(()=>showToast());
}}
function copyNote(el){{
  navigator.clipboard.writeText(el.innerText).then(()=>showToast());
}}
function showToast(){{
  const t=document.getElementById("toast");
  t.classList.add("show");
  setTimeout(()=>t.classList.remove("show"),2000);
}}
</script>
</body>
</html>"""
