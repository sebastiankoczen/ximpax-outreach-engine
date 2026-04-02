import re
import html as hl


def _split_numbered(text):
    """Split '1. text\n2. text\n3. text' into list of (num, text) tuples."""
    if not text or str(text).strip() in ("", "nan"):
        return []
    clean = re.sub(r"[*`]+", "", str(text)).strip()
    # Split on numbered list markers: 1. / 1) / Option 1: etc.
    parts = re.split(r"(?m)^\s*(?:Option\s*)?([123])[.):]\s*", clean)
    # re.split with capture groups: [pre, num, text, num, text, ...]
    results = []
    if len(parts) >= 3:
        i = 1
        while i + 1 < len(parts):
            num  = parts[i].strip()
            body = parts[i + 1].strip()
            if body:
                results.append((num, body))
            i += 2
    if not results:
        # Fallback: split on double newlines or single newlines between chunks
        chunks = [c.strip() for c in re.split(r"\n{2,}", clean) if c.strip()]
        results = [(str(i + 1), c) for i, c in enumerate(chunks[:3])]
    return results[:3]


CSS = (
    "* {box-sizing:border-box;margin:0;padding:0}"
    "body {font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
    "background:#f0f2f5;color:#1a1a2e;padding:28px 20px}"
    "h1 {font-size:22px;font-weight:700;color:#0a66c2;margin-bottom:3px}"
    ".sub {font-size:13px;color:#888;margin-bottom:20px}"
    ".card {background:#fff;border-radius:14px;padding:22px 24px;margin-bottom:18px;"
    "box-shadow:0 1px 6px rgba(0,0,0,.08);border-left:4px solid #0a66c2}"
    ".ch {display:flex;justify-content:space-between;align-items:flex-start;"
    "margin-bottom:16px;gap:12px;flex-wrap:wrap}"
    ".cn {font-size:16px;font-weight:700}"
    ".cm {font-size:12px;color:#666;margin-top:2px}"
    ".ct {background:#e8f0fe;color:#0a66c2;font-size:12px;font-weight:600;"
    "padding:5px 12px;border-radius:20px;white-space:nowrap}"
    ".sec {margin-bottom:16px}"
    ".hl {font-size:11px;font-weight:700;color:#495057;text-transform:uppercase;"
    "letter-spacing:.5px;margin-bottom:8px}"
    ".ht {font-weight:400;font-size:10px;color:#aaa;text-transform:none;letter-spacing:0}"
    ".sig-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin-bottom:16px}"
    ".sig {padding:12px;border-radius:8px;font-size:12px}"
    ".sig-rc {background:#fee2e2} .sig-mp {background:#ffedd5}"
    ".sig-sg {background:#dcfce7} .sig-scd {background:#dbeafe}"
    ".sig-score {font-size:10px;font-weight:700;padding:1px 6px;border-radius:8px;"
    "background:rgba(0,0,0,.08);margin-left:4px}"
    ".opt {background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:10px;"
    "padding:14px 16px;margin-bottom:10px;cursor:pointer;transition:background .15s;position:relative}"
    ".opt:hover {background:#eef2ff;border-color:#c7d2fe}"
    ".opt-num {display:inline-flex;align-items:center;justify-content:center;"
    "width:22px;height:22px;background:#0a66c2;color:#fff;border-radius:50%;"
    "font-size:11px;font-weight:700;margin-right:8px;flex-shrink:0;vertical-align:middle}"
    ".opt-body {font-size:13px;line-height:1.65;color:#1a1a2e;white-space:pre-wrap}"
    ".toast {position:fixed;bottom:24px;right:24px;background:#1a1a2e;color:#fff;"
    "padding:10px 18px;border-radius:8px;font-size:13px;opacity:0;"
    "transition:opacity .3s;pointer-events:none;z-index:999}"
    ".toast.show {opacity:1}"
)

JS = (
    "function cp(el){"
    "var t=el.querySelector('.opt-body');"
    "navigator.clipboard.writeText(t.innerText).then(function(){"
    "var x=document.getElementById('ts');"
    "x.classList.add('show');"
    "setTimeout(function(){x.classList.remove('show');},2000);});}"
)


def _sig_block(row):
    parts = []
    meta = [
        ("RC",  "Resource Constraints", "sig-rc"),
        ("MP",  "Margin Pressure",       "sig-mp"),
        ("SG",  "Significant Growth",    "sig-sg"),
        ("SCD", "Supply Chain Disruption", "sig-scd"),
    ]
    for code, label, cls in meta:
        status = str(row.get(code + "_status", "UNCLEAR"))
        score  = int(row.get(code + "_score", 0) or 0)
        signal = str(row.get(code + "_signal", "")).strip()
        if status == "UNCLEAR" or not signal or signal == "nan":
            continue
        parts.append(
            "<div class='sig " + cls + "'>"
            "<strong>" + hl.escape(label) + "</strong>"
            "<span class='sig-score'>" + status + " " + str(score) + "/10</span>"
            "<br><span style='color:#555;'>" + hl.escape(signal[:200]) + "</span>"
            "</div>"
        )
    if not parts:
        return ""
    return (
        "<div class='sec'>"
        "<div class='hl'>📋 Company Situation</div>"
        "<div class='sig-grid'>" + "".join(parts) + "</div>"
        "</div>"
    )


def _option_cards(raw, section_label, hint):
    items = _split_numbered(raw)
    if not items:
        return ""
    cards = ""
    for num, body in items:
        cards += (
            "<div class='opt' onclick='cp(this)'>"
            "<span class='opt-num'>" + num + "</span>"
            "<span class='opt-body'>" + hl.escape(body) + "</span>"
            "</div>"
        )
    return (
        "<div class='sec'>"
        "<div class='hl'>" + section_label + " <span class='ht'>" + hint + "</span></div>"
        + cards +
        "</div>"
    )


def generate_html(df):
    cards = []
    for _, row in df.iterrows():
        name    = hl.escape(str(row.get("name", "")))
        func    = hl.escape(str(row.get("known_function", "")))
        company = hl.escape(str(row.get("company", "")))
        sit_raw = str(row.get("situation_notes", ""))
        pos_raw = str(row.get("positioning_notes", ""))

        sig_sec = _sig_block(row)
        sit_sec = _option_cards(sit_raw, "💡 Situation Notes", "(click to copy)")
        pos_sec = _option_cards(pos_raw, "✏️ XIMPAX Positioning", "(click to copy)")

        cards.append(
            "<div class='card'>"
            "<div class='ch'>"
            "<div><div class='cn'>" + name + "</div><div class='cm'>" + func + "</div></div>"
            "<span class='ct'>" + company + "</span>"
            "</div>"
            + sig_sec + sit_sec + pos_sec +
            "</div>"
        )

    total = len(df)
    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>XIMPAX Outreach Report</title>"
        "<style>" + CSS + "</style>"
        "</head><body>"
        "<h1>⚡ XIMPAX Outreach Report</h1>"
        "<p class='sub'>" + str(total) + " contact" + ("s" if total != 1 else "") +
        " — click any card to copy text</p>"
        + "".join(cards)
        + "<div class='toast' id='ts'>✅ Copied!</div>"
        "<script>" + JS + "</script>"
        "</body></html>"
    )
