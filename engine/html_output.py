import pandas as pd
import html as hl
import re

CSS = "\n".join([
    "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.5; color: #333; max-width: 900px; margin: 40px auto; background: #f9f9f9; padding: 20px; }",
    "h1 { color: #0a66c2; font-size: 28px; margin-bottom: 5px; }",
    ".sub { color: #666; font-size: 14px; margin-bottom: 30px; }",
    "table { width: 100%; border-collapse: collapse; margin-bottom: 40px; background: #fff; border-radius: 8px; overflow: hidden; }",
    "th { background: #0a66c2; color: #fff; text-align: left; padding: 12px 15px; font-size: 13px; text-transform: uppercase; }",
    "td { padding: 12px 15px; border-bottom: 1px solid #eee; vertical-align: top; }",
    ".card { background: #fff; padding: 25px; margin-bottom: 25px; border-radius: 8px; border: 1px solid #e0e0e0; }",
    ".name { font-size: 20px; font-weight: 700; color: #000; margin-bottom: 4px; }",
    ".meta { font-size: 14px; color: #0a66c2; font-weight: 600; margin-bottom: 15px; }",
    ".summary-box { background: #f0f7ff; border-left: 4px solid #0a66c2; padding: 15px; margin: 15px 0; font-size: 14px; font-style: italic; }",
    ".signal-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-right: 5px; color: #fff; }",
    ".sig-RC { background: #f5c518; color: #333; }",
    ".sig-MP { background: #d93025; }",
    ".sig-SG { background: #1e8e3e; }",
    ".sig-SCD { background: #1a73e8; }",
    ".sig-block { margin: 12px 0; padding: 12px 15px; background: #fafafa; border-radius: 6px; border: 1px solid #e8e8e8; }",
    ".sig-block ul { margin: 6px 0 0 0; padding-left: 18px; }",
    ".sig-block ul li { font-size: 13px; color: #444; margin-bottom: 4px; }",
    ".sig-status { font-size: 11px; color: #888; margin-left: 6px; }",
    ".option-block { background: #f8f9fa; border-left: 4px solid #e0e0e0; padding: 15px; margin-top: 10px; font-size: 14px; border-radius: 0 4px 4px 0; }",
    ".option-num { font-size: 11px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }",
    ".positioning { background: #f0f7ff; border-left: 4px solid #0a66c2; padding: 15px; margin-top: 10px; font-size: 14px; }",
    ".pos-option { margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #dce8f5; }",
    ".pos-option:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }",
])


def _split_numbered(text):
    """Split numbered list 1. / 2. / 3. Ignores year-like numbers e.g. 2025."""
    if not text or not isinstance(text, str):
        return []
    text = text.strip()
    # Only split on 1-2 digit numbers at line start — prevents splitting on years like 2025
    parts = re.split(r'(?m)(?:^|\n)\s*(?=\d{1,2}\.)', text)
    items = []
    for p in parts:
        if not p.strip():
            continue
        m = re.match(r'^(\d{1,2})\.\s*(.*)', p.strip(), re.DOTALL)
        if m:
            items.append((m.group(1), m.group(2).strip()))
        elif items:
            last_num, last_body = items[-1]
            items[-1] = (last_num, last_body + " " + p.strip())
        else:
            items.append(("", p.strip()))
    return items[:3]


def _signal_bullets_html(signal_text):
    """Render newline-separated signal sentences as HTML bullet list."""
    if not signal_text or not isinstance(signal_text, str):
        return ""
    bullets = [b.strip() for b in signal_text.split("\n") if b.strip()]
    if not bullets:
        return "<p style='font-size:13px'>" + hl.escape(signal_text.strip()) + "</p>"
    items = "".join("<li>" + hl.escape(b) + "</li>" for b in bullets)
    return "<ul>" + items + "</ul>"


def generate_html(df):
    SIGNAL_ORDER = [
        ("RC",  "Resource Constraints",    "sig-RC"),
        ("SCD", "Supply Chain Disruption", "sig-SCD"),
        ("MP",  "Margin Pressure",         "sig-MP"),
        ("SG",  "Significant Growth",      "sig-SG"),
    ]

    table_header = "<thead><tr><th>Target</th><th>RC</th><th>SCD</th><th>MP</th><th>SG</th></tr></thead>"
    table_rows = []
    rows_html = []

    for _, row in df.iterrows():
        tr = "<tr><td><b>" + hl.escape(str(row.get('name', ''))) + "</b><br><small>" + hl.escape(str(row.get('company', ''))) + "</small></td>"
        for code, label, css_class in SIGNAL_ORDER:
            val = str(row.get(code + "_score", ""))
            if val != "":
                val = code + ": " + val + "/10"
            tr += "<td><div style='font-size:11px'>" + hl.escape(val) + "</div></td>"
        tr += "</tr>"
        table_rows.append(tr)

        card = "<div class='card'>"
        card += "<div class='name'>" + hl.escape(str(row.get('name', ''))) + "</div>"
        card += "<div class='meta'>" + hl.escape(str(row.get('known_function', ''))) + " @ " + hl.escape(str(row.get('company', ''))) + "</div>"

        summary = str(row.get("summary", ""))
        if summary and summary.strip():
            card += "<div class='summary-box'>" + hl.escape(summary) + "</div>"

        for code, label, css_class in SIGNAL_ORDER:
            score  = row.get(code + "_score", 0)
            status = str(row.get(code + "_status", "UNCLEAR"))
            signal = str(row.get(code + "_signal", ""))
            if not signal or not signal.strip():
                continue
            card += "<div class='sig-block'>"
            card += "<span class='signal-tag " + css_class + "'>" + code + "</span>"
            card += "<b style='font-size:13px'>" + hl.escape(label) + "</b>"
            card += "<span class='sig-status'>" + hl.escape(status) + " (" + str(score) + "/10)</span>"
            card += _signal_bullets_html(signal)
            card += "</div>"

        situations = str(row.get("situation_notes", ""))
        if situations.strip():
            card += "<h3 style='margin:20px 0 8px'>&#128221; Outreach Proposals</h3>"
            opts = _split_numbered(situations)
            if opts:
                for num, body in opts:
                    label_txt = "Option " + num if num else "Option"
                    card += "<div class='option-block'><div class='option-num'>" + label_txt + "</div>" + hl.escape(body) + "</div>"
            else:
                card += "<div class='option-block'>" + hl.escape(situations) + "</div>"

        positioning = str(row.get("positioning_notes", ""))
        if positioning.strip():
            card += "<h3 style='margin:20px 0 8px'>&#127970; XIMPAX Positioning</h3>"
            card += "<div class='positioning'>"
            pos_opts = _split_numbered(positioning)
            if pos_opts:
                for num, body in pos_opts:
                    card += "<div class='pos-option'>" + hl.escape(body) + "</div>"
            else:
                card += hl.escape(positioning)
            card += "</div>"

        card += "</div>"
        rows_html.append(card)

    return (
        "<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
        "<meta charset='UTF-8'>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        "<title>XIMPAX Outreach Report</title>\n"
        "<style>" + CSS + "</style>\n"
        "</head>\n<body>\n"
        "<h1>&#9889; XIMPAX Outreach Report</h1>\n"
        "<p class='sub'>Generated by XIMPAX Outreach Engine</p>\n"
        "<table>" + table_header + "<tbody>" + "".join(table_rows) + "</tbody></table>\n"
        + "".join(rows_html) +
        "\n</body>\n</html>"
    )
