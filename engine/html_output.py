import re
import html as hl

def _split_numbered(text):
    """Split '1. text
2. text
3. text' into list of (num, text) tuples."""
    if not text or str(text).strip() in ("", "nan"):
        return []
    
    clean = re.sub(r"[*`]+", "", str(text)).strip()
    
    # Split on numbered list markers: 1. / 1) / Option 1: etc.
    parts = re.split(r"(?m)^\s*(?:Option\s*)?(\d+)[.):]\s*", clean)
    results = []
    
    if len(parts) >= 3:
        i = 1
        while i + 1 < len(parts):
            num = parts[i].strip()
            body = parts[i + 1].strip()
            if body:
                results.append((num, body))
            i += 2
            
    if not results:
        # Fallback: split on double newlines or similar
        chunks = [c.strip() for c in re.split(r"\\s*[\\r\
]{2,}\\s*", clean) if c.strip()]
        results = [(str(i + 1), c) for i, c in enumerate(chunks[:5])]
        
    return results[:5]

CSS = """
* {box-sizing:border-box;margin:0;padding:0}
body {font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1a1a2e;padding:28px 20px}
h1 {font-size:24px;font-weight:700;color:#0a66c2;margin-bottom:5px}
.sub {font-size:14px;color:#666;margin-bottom:25px}
table {width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.08);margin-bottom:30px}
th, td {padding:15px;text-align:left;border-bottom:1px solid #eee;font-size:14px}
th {background:#0a66c2;color:#fff;font-weight:600;text-transform:uppercase;font-size:12px;letter-spacing:0.5px}
tr:hover {background:#f8fafc}
.card {background:#fff;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 1px 6px rgba(0,0,0,.08);border-left:5px solid #0a66c2}
.name {font-size:18px;font-weight:700;color:#0a66c2;margin-bottom:4px}
.meta {font-size:13px;color:#888;margin-bottom:15px;border-bottom:1px solid #f0f0f0;padding-bottom:10px}
.summary-box {background:#fff9e6;padding:12px;border-radius:6px;margin-bottom:15px;font-size:13px;border:1px solid #ffeeba}
.signal-tag {display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;margin-right:5px;background:#eee}
.sig-RC {background:#ffebee;color:#c62828}
.sig-MP {background:#fff3e0;color:#ef6c00}
.sig-SG {background:#e8f5e9;color:#2e7d32}
.sig-SCD {background:#e3f2fd;color:#1565c0}
.proposal {background:#f9f9f9;padding:12px;border-radius:8px;margin-top:10px;font-size:14px;white-space:pre-wrap;border-left:3px solid #ddd}
"""

def generate_html(df) -> str:
    rows_html = []
    
    # Table header
    table_header = (
        "<thead><tr>"
        "<th>Name</th><th>Company</th><th>Function</th>"
        "<th>Outreach Message (Options)</th>"
        "<th>RC</th><th>SCD</th><th>MP</th><th>SG</th>"
        "</tr></thead>"
    )
    
    table_rows = []
    
    for _, row in df.iterrows():
        # Table Row
        tr = "<tr>"
        tr += f"<td>{hl.escape(str(row.get('name', '')))}</td>"
        tr += f"<td>{hl.escape(str(row.get('company', '')))}</td>"
        tr += f"<td>{hl.escape(str(row.get('known_function', '')))}</td>"
        
        # Outreach Message
        msg = str(row.get('situation_notes', ''))
        tr += f"<td><div style='max-height:150px;overflow:auto;white-space:pre-wrap;font-size:12px'>{hl.escape(msg)}</div></td>"
        
        # Signals
        for code in ["RC", "SCD", "MP", "SG"]:
            val = str(row.get(code + '_score', ''))
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
            card += f"<div class='summary-box'><strong>Strategic Summary:</strong><br>{hl.escape(str(summary))}</div>"
        
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
        
    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<h1>XIMPAX Outreach Report</h1>
<div class='sub'>Generated for Sebastian Koczen</div>
<table>{table_header}<tbody>{''.join(table_rows)}</tbody></table>
{''.join(rows_html)}
</body></html>"""
    
    return html
