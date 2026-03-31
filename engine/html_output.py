import html as hl
import re

SIGNAL_META = {
    "RC":  ("#fff3cd", "#856404", "🔴", "Resource Constraints"),
    "MP":  ("#f8d7da", "#842029", "🟠", "Margin Pressure"),
    "SG":  ("#d1e7dd", "#0f5132", "🟢", "Significant Growth"),
    "SCD": ("#cfe2ff", "#084298", "🔵", "Supply Chain Disruption"),
}


def _status(score):
    s = int(score or 0)
    if s >= 7:
        return "CONFIRMED"
    if s >= 4:
        return "LIKELY"
    return "UNCLEAR"


def _style(score):
    s = int(score or 0)
    if s >= 7:
        return "#f8d7da", "#842029"
    if s >= 4:
        return "#fff3cd", "#856404"
    return "#e9ecef", "#6c757d"


def _bullets(text):
    if not text or str(text).strip() in ("", "nan"):
        return ""
    raw = re.sub(r"[*]+", "", str(text)).strip()
    parts = re.split(r"(?<=[.!?]) +", raw)
    parts = [p.strip() for p in parts if len(p.strip()) > 15][:5]
    if not parts:
        return "<p class='st'>" + hl.escape(raw[:400]) + "</p>"
    inner = "".join("<li>" + hl.escape(p) + "</li>" for p in parts)
    return "<ul class='el'>" + inner + "</ul>"


def _sig_html(row):
    out = []
    for code in ["MP", "RC", "SG", "SCD"]:
        score  = int(row.get(code + "_score", 0) or 0)
        signal = str(row.get(code + "_signal", "")).strip()
        st     = _status(score)
        if st == "UNCLEAR" or not signal or signal == "nan":
            continue
        bg, fg       = _style(score)
        _, _, ic, lb = SIGNAL_META[code]
        bl           = _bullets(signal)
        item = (
            "<li class='sb' style='border-left:3px solid %(fg)s;background:%(bg)s18;'>"
            "<div class='sh'>"
            "<span class='sl' style='color:%(fg)s;'>%(ic)s %(lb)s</span>"
            "<span class='ss' style='background:%(bg)s;color:%(fg)s;'>score %(sc)s/10</span>"
            "<span class='sv' style='background:%(fg)s;color:#fff;'>%(st)s</span>"
            "</div>%(bl)s</li>"
        ) % {"fg": fg, "bg": bg, "ic": ic, "lb": lb, "sc": score, "st": st, "bl": bl}
        out.append(item)
    if not out:
        return ""
    return "<ul class='sg'>" + "".join(out) + "</ul>"


def _note_cards(raw, label, hint, bg, border):
    if not raw or str(raw).strip() in ("", "nan"):
        return ""
    rows = [re.sub(r"^[1-3][.) ]+", "", ln).strip()
            for ln in str(raw).splitlines() if ln.strip()]
    rows = [r for r in rows if r][:3]
    if not rows:
        return ""
    cards = ""
    for r in rows:
        cards += (
            "<div class='nc' onclick='cp(this)' title='Click to copy'"
            " style='background:%(bg)s;border:1.5px solid %(bd)s;'>"
            "%(txt)s</div>"
        ) % {"bg": bg, "bd": border, "txt": hl.escape(r)}
    return (
        "<div class='ns'>"
        "<div class='hl'>%(lb)s <span class='ht'>%(ht)s</span></div>"
        "%(cards)s</div>"
    ) % {"lb": label, "ht": hint, "cards": cards}


CSS = (
    "* {box-sizing:border-box;margin:0;padding:0}"
    "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
    "background:#f0f2f5;color:#1a1a2e;padding:28px 20px}"
    "h1{font-size:22px;font-weight:700;color:#0a66c2;margin-bottom:3px}"
    ".sub{font-size:13px;color:#888;margin-bottom:20px}"
    ".stats{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}"
    ".stat{background:#fff;border-radius:10px;padding:12px 20px;"
    "box-shadow:0 1px 4px rgba(0,0,0,.08);text-align:center;min-width:90px}"
    ".stat strong{display:block;font-size:26px;font-weight:700;color:#0a66c2}"
    ".stat span{font-size:11px;color:#999}"
    ".card{background:#fff;border-radius:14px;padding:22px 24px;margin-bottom:18px;"
    "box-shadow:0 1px 6px rgba(0,0,0,.08);border-left:4px solid #0a66c2}"
    ".card.sk{border-left-color:#ccc;opacity:.65}"
    ".ch{display:flex;justify-content:space-between;align-items:flex-start;"
    "margin-bottom:16px;gap:12px;flex-wrap:wrap}"
    ".cn{font-size:16px;font-weight:700;display:block}"
    ".cm{font-size:12px;color:#666;margin-top:2px;display:block}"
    ".ct{background:#e8f0fe;color:#0a66c2;font-size:12px;font-weight:600;"
    "padding:5px 12px;border-radius:20px;white-space:nowrap;flex-shrink:0}"
    ".hl{font-size:11px;font-weight:700;color:#495057;text-transform:uppercase;"
    "letter-spacing:.5px;margin-bottom:8px}"
    ".ht{font-weight:400;font-size:10px;color:#aaa;text-transform:none;letter-spacing:0}"
    ".ns{margin-bottom:16px}"
    ".nc{border-radius:8px;padding:11px 14px;font-size:13px;color:#1a1a2e;"
    "cursor:pointer;margin-bottom:6px;line-height:1.6;transition:filter .15s}"
    ".nc:hover{filter:brightness(.95)}"
    ".sg{list-style:none;padding:0;margin:0 0 16px 0;display:flex;flex-direction:column;gap:8px}"
    ".sb{border-radius:8px;padding:10px 14px;list-style:none}"
    ".sh{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:5px}"
    ".sl{font-size:12px;font-weight:700;flex:1;min-width:130px}"
    ".ss{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px}"
    ".sv{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px}"
    ".el{list-style:disc;padding-left:16px;margin:0;display:flex;flex-direction:column;gap:3px}"
    ".el li{font-size:12px;color:#444;line-height:1.55}"
    ".st{font-size:12px;color:#444;line-height:1.55}"
    ".mb{background:#f0f7ff;border:1.5px solid #b8d4f8;border-radius:8px;"
    "padding:14px 16px;font-size:14px;line-height:1.7;cursor:pointer;"
    "white-space:pre-wrap;color:#1a1a2e;transition:filter .15s}"
    ".mb:hover{filter:brightness(.96)}"
    ".sk-n{color:#aaa;font-size:13px;font-style:italic;padding:8px 0}"
    ".toast{position:fixed;bottom:24px;right:24px;background:#1a1a2e;color:#fff;"
    "padding:10px 18px;border-radius:8px;font-size:13px;opacity:0;"
    "transition:opacity .3s;pointer-events:none;z-index:999}"
    ".toast.show{opacity:1}"
)

JS = (
    "function cp(el){navigator.clipboard.writeText(el.innerText).then(t);}"
    "function t(){var x=document.getElementById('ts');"
    "x.classList.add('show');setTimeout(function(){x.classList.remove('show');},2000);}"
)


def generate_html(df):
    cards = []
    for _, row in df.iterrows():
        name    = hl.escape(str(row.get("name", "")))
        func    = hl.escape(str(row.get("known_function", "")))
        company = hl.escape(str(row.get("company", "")))
        message = hl.escape(str(row.get("linkedin_message", ""))).replace("\n", "<br>")
        pos     = str(row.get("positioning_notes", ""))
        sit     = str(row.get("situation_notes", ""))
        notes   = str(row.get("notes", ""))
        skip    = "no company" in notes.lower() or "skipped" in notes.lower()

        sig_sec = ""
        if not skip:
            sh = _sig_html(row)
            if sh:
                sig_sec = (
                    "<div style='margin-bottom:16px;'>"
                    "<div class='hl'>\U0001f4cb Company Situation</div>"
                    + sh + "</div>"
                )

        pos_sec = ""
        sit_sec = ""
        if not skip:
            pos_sec = _note_cards(
                pos,
                "\u270f\ufe0f XIMPAX Positioning Options", "(click to copy)",
                "#f0f7ff", "#b8d4f8"
            )
            sit_sec = _note_cards(
                sit,
                "\U0001f4a1 Situation Note Options", "(click to append to message)",
                "#f0fff4", "#86efac"
            )

        if skip:
            msg = "<p class='sk-n'>\u26a0\ufe0f Skipped \u2014 no company provided</p>"
        else:
            msg = (
                "<div class='hl'>\U0001f4ac LinkedIn InMail "
                "<span class='ht'>(click to copy)</span></div>"
                "<div class='mb' onclick='cp(this)'>" + message + "</div>"
            )

        cards.append(
            "<div class='card%(sk)s'>"
            "<div class='ch'>"
            "<div><span class='cn'>%(nm)s</span><span class='cm'>%(fn)s</span></div>"
            "<span class='ct'>%(co)s</span>"
            "</div>"
            "%(sig)s%(pos)s%(sit)s"
            "<div>%(msg)s</div>"
            "</div>" % {
                "sk": " sk" if skip else "",
                "nm": name, "fn": func, "co": company,
                "sig": sig_sec, "pos": pos_sec, "sit": sit_sec,
                "msg": msg,
            }
        )

    total = len(df)
    ready = len(df[df["linkedin_message"].astype(str).str.len() > 10])
    skpd  = len(df[df["notes"].astype(str).str.contains("skipped|error", case=False, na=False)])

    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>XIMPAX Outreach Messages</title>"
        "<style>%(css)s</style>"
        "</head><body>"
        "<h1>\u26a1 XIMPAX Outreach Messages</h1>"
        "<p class='sub'>Click any message, positioning note, or situation note to copy it.</p>"
        "<div class='stats'>"
        "<div class='stat'><strong>%(tot)s</strong><span>Contacts</span></div>"
        "<div class='stat'><strong>%(rdy)s</strong><span>Messages ready</span></div>"
        "<div class='stat'><strong>%(skp)s</strong><span>Skipped</span></div>"
        "</div>"
        "%(cards)s"
        "<div class='toast' id='ts'>\u2705 Copied!</div>"
        "<script>%(js)s</script>"
        "</body></html>"
    ) % {
        "css": CSS, "js": JS,
        "tot": total, "rdy": ready, "skp": skpd,
        "cards": "".join(cards),
    }
