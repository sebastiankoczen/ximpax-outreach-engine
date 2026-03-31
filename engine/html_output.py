import html as hl, re

SIGNAL_META = {
    "RC":  ("#fff3cd", "#856404", "🔴", "Resource Constraints"),
    "MP":  ("#f8d7da", "#842029", "🟠", "Margin Pressure"),
    "SG":  ("#d1e7dd", "#0f5132", "🟢", "Significant Growth"),
    "SCD": ("#cfe2ff", "#084298", "🔵", "Supply Chain Disruption"),
}

def _score_badge(score):
    s = int(score or 0)
    if s >= 7:   bg, fg = "#f8d7da","#842029"
    elif s >= 4: bg, fg = "#fff3cd","#856404"
    else:        bg, fg = "#e9ecef","#6c757d"
    return f'<span class="sig-score" style="background:{bg};color:{fg};">score {s}/10</span>'


def _all_signal_bullets(row):
    """Show every active (non-UNCLEAR) signal as a bullet."""
    items = []
    for code in ["MP", "RC", "SG", "SCD"]:
        score  = int(row.get(f"{code}_score", 0) or 0)
        status = str(row.get(f"{code}_status", "UNCLEAR"))
        signal = str(row.get(f"{code}_signal", "")).strip()
        if status == "UNCLEAR" or not signal or signal == "nan":
            continue
        bg, fg, icon, label = SIGNAL_META[code]
        badge = _score_badge(score)
        txt   = hl.escape(signal[:200]) + ("…" if len(signal) > 200 else "")
        items.append(f"""
        <li class="sig-bullet" style="border-left:3px solid {fg};background:{bg}18;">
            <div class="sig-header">
                <span class="sig-label" style="color:{fg};">{icon} {label}</span>
                {badge}
                <span class="sig-status" style="background:{fg};color:#fff;">{status}</span>
            </div>
            <p class="sig-text">{txt}</p>
        </li>""")
    if not items:
        return ""
    return '<ul class="sig-list">' + "".join(items) + "</ul>"


def _note_cards(raw, section_id, label, hint):
    """Render numbered lines from Gemini as click-to-copy cards."""
    if not raw or str(raw).strip() in ("", "nan"):
        return ""
    lines = [l.strip() for l in str(raw).splitlines() if l.strip()]
    cards = []
    for line in lines[:3]:
        text = re.sub(r"^[1-3][.)\s]+", "", line).strip()
        if not text:
            continue
        text_esc = hl.escape(text)
        cards.append(
            f'<div class="note-card" onclick="copyNote(this)" title="Click to copy">{text_esc}</div>'
        )
    if not cards:
        return ""
    return (f'<div class="notes-section" id="{section_id}">' 
            f'<div class="section-label">{label} <span class="hint">{hint}</span></div>' 
            + "".join(cards) + '</div>')


def generate_html(df) -> str:
    cards = []
    for _, row in df.iterrows():
        name     = hl.escape(str(row.get("name", "")))
        func     = hl.escape(str(row.get("known_function", "")))
        company  = hl.escape(str(row.get("company", "")))
        message  = hl.escape(str(row.get("linkedin_message", ""))).replace("\n", "<br>")
        pos_notes = str(row.get("positioning_notes", ""))
        sit_notes = str(row.get("situation_notes", ""))
        notes    = str(row.get("notes", ""))
        skipped  = "no company" in notes.lower() or "skipped" in notes.lower()

        signal_bullets = _all_signal_bullets(row) if not skipped else ""

        situation_block = ""
        if signal_bullets and not skipped:
            situation_block = f"""
            <div class="summary-block">
                <div class="section-label">📋 Company Situation</div>
                {signal_bullets}
            </div>"""

        pos_section = _note_cards(
            pos_notes, "pos", "✏️ XIMPAX Positioning Options", "(click to copy)"
        ) if not skipped else ""

        sit_section = _note_cards(
            sit_notes, "sit", "💡 Situation Note Options", "(click to append to message)"
        ) if not skipped else ""

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
            {situation_block}
            {pos_section}
            {sit_section}
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
  .summary-block,.notes-section,.message-section{{margin-bottom:16px}}
  /* Signal list */
  .sig-list{{list-style:none;display:flex;flex-direction:column;gap:7px}}
  .sig-bullet{{border-radius:8px;padding:9px 12px}}
  .sig-header{{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:4px}}
  .sig-label{{font-size:12px;font-weight:700;flex:1;min-width:130px}}
  .sig-score{{font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px}}
  .sig-status{{font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px}}
  .sig-text{{font-size:12px;color:#444;line-height:1.55}}
  /* Note cards — positioning + situation */
  .note-card{{background:#f0f7ff;border:1.5px solid #b8d4f8;border-radius:8px;
              padding:10px 14px;font-size:13px;color:#1a1a2e;cursor:pointer;
              margin-bottom:6px;transition:background .15s;line-height:1.5}}
  .note-card:hover{{background:#dbeafe}}
  /* Situation note cards — slightly different colour */
  #sit .note-card{{background:#f0fff4;border-color:#86efac}}
  #sit .note-card:hover{{background:#dcfce7}}
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
<p class="subtitle">Click any message, positioning note, or situation note to copy it to clipboard.</p>
<div class="stats">
  <div class="stat"><strong>{total}</strong><span>Contacts</span></div>
  <div class="stat"><strong>{ready}</strong><span>Messages ready</span></div>
  <div class="stat"><strong>{skipped_n}</strong><span>Skipped</span></div>
</div>
{"".join(cards)}
<div class="toast" id="toast">✅ Copied!</div>
<script>
function copyMsg(el){{navigator.clipboard.writeText(el.innerText).then(showToast);}}
function copyNote(el){{navigator.clipboard.writeText(el.innerText).then(showToast);}}
function showToast(){{
  const t=document.getElementById("toast");
  t.classList.add("show");setTimeout(()=>t.classList.remove("show"),2000);
}}
</script>
</body>
</html>"""
