import pandas as pd
import html as hl
import re

CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.5; color: #333; max-width: 900px; margin: 40px auto; background: #f9f9f9; padding: 20px; }
h1 { color: #0a66c2; font-size: 28px; margin-bottom: 5px; }
.sub { color: #666; font-size: 14px; margin-bottom: 30px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 40px; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }
th { background: #0a66c2; color: #fff; text-align: left; padding: 12px 15px; font-size: 13px; text-transform: uppercase; }
td { padding: 12px 15px; border-bottom: 1px solid #eee; vertical-align: top; }
.card { background: #fff; padding: 25px; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; }
.name { font-size: 20px; font-weight: 700; color: #000; margin-bottom: 4px; }
.meta { font-size: 14px; color: #0a66c2; font-weight: 600; margin-bottom: 15px; }
.summary-box { background: #f0f7ff; border-left: 4px solid #0a66c2; padding: 15px; margin: 15px 0; font-size: 14px; font-style: italic; }
.signal-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-right: 5px; color: #fff; }
.sig-RC { background: #d93025; }
.sig-MP { background: #f29900; }
.sig-SG { background: #1e8e3e; }
.sig-SCD { background: #1a73e8; }
.proposal { background: #f8f9fa; border-left: 4px solid #e0e0e0; padding: 15px; margin-top: 10px; font-size: 14px; white-space: pre-wrap; }
"""


def _split_numbered(text):
    if not text or not isinstance(text, str):
        return []
    items = []
    parts = re.split(r' (?=\d+\.)|^(?=\d+\.)', text.strip(), flags=re.MULTILINE)
    for p in parts:
        if not p.strip():
            continue
        m = re.match(r'^(\d+)\.\s*(.*)', p.strip(), re.DOTALL)
        if m:
            items.append((m.group(1), m.group(2).strip()))
        else:
            items.append(("", p.strip()))
    return items


def generate_html(df):
    table_header = "<thead><tr><th>Target</th><th>RC</th><th>MP</th><th>SG</th><th>SCD</th></tr></thead>"
    table_rows = []
    rows_html = []

    for _, row in df.iterrows():
        # Row for overview table
        tr = f"<tr><td><b>{hl.escape(str(row.get('name', '')))}</b><br><small>{hl.escape(str(row.get('company', '')))}</small></td>"
        for code in ["RC", "MP", "SG", "SCD"]:
            val = str(row.get(f"{code}_score", ""))
            if val != '':
                val = f"{code}: {val}/10"
            tr += f"<td><div style='font-size:11px'>{hl.escape(val)}</div></td>"
        tr += "</tr>"
        table_rows.append(tr)

        # Detail Card
        card = "<div class='card'>"
        card += f"<div class='name'>{hl.escape(str(row.get('name', '')))}</div>"
        card += f"<div class='meta'>{hl.escape(str(row.get('known_function', '')))} @ {hl.escape(str(row.get('company', '')))}</div>"

        # Summary Box
        summary = row.get('company_summary') or row.get('summary', '')
        if summary and str(summary).strip() not in ("", "nan"):
            card += f"<div class='summary-box'><strong>Strategic Summary:</strong><br><br>{hl.escape(str(summary))}</div>"

        signals = []
        for code in ["RC", "MP", "SG", "SCD"]:
            sig_text = str(row.get(f'{code}_signal', ''))
            if sig_text and sig_text.strip() not in ("", "nan"):
                signals.append(f"<div style='margin-bottom:8px'><span class='signal-tag sig-{code}'>{code}</span> <span style='font-size:12px'>{hl.escape(sig_text)}</span></div>")
        card += "".join(signals)

        # Outreach Options
        card += "<div style='margin-top:20px;padding-top:10px;border-top:2px solid #eee;font-weight:700;color:#0a66c2'>OUTREACH PROPOSALS</div>"
        options = _split_numbered(row.get('situation_notes', ''))
        for num, body in options:
            card += f"<div style='margin-top:15px;font-weight:600;font-size:12px;color:#666'>Option {num}</div>"
            card += f"<div class='proposal'>{hl.escape(body)}</div>"

        # Positioning Options
        pos_notes = row.get('positioning_notes', '')
        if pos_notes and str(pos_notes).strip() not in ("", "nan"):
            card += "<div style='margin-top:25px;padding-top:10px;border-top:2px solid #eee;font-weight:700;color:#0a66c2'>XIMPAX POSITIONING</div>"
            p_options = _split_numbered(pos_notes)
            for num, body in p_options:
                card += f"<div style='margin-top:15px;font-weight:600;font-size:12px;color:#666'>Angle {num}</div>"
                card += f"<div class='proposal' style='background:#f0f7ff;border-left-color:#0a66c2'>{hl.escape(body)}</div>"

        card += "</div>"
        rows_html.append(card)

    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        + CSS
        + "</style></head><body>"
        + "<h1>XIMPAX Outreach Report</h1>"
        + "<div class='sub'>Generated for Sebastian Koczen</div>"
        + "<table>" + table_header + "<tbody>" + "".join(table_rows) + "</tbody></table>"
        + "".join(rows_html)
        + "</body></html>"
    )
    return html
