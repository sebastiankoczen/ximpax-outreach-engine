import re

def generate_html(df):
    """Generates a clean HTML report for outreach proposals and research."""
    
    html = ["""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>XIMPAX Outreach Engine - Results</title>
        <style>
            :root {
                --primary: #2563eb;
                --bg: #f8fafc;
                --card: #ffffff;
                --text: #1e293b;
                --border: #e2e8f0;
                --rc: #ef4444; --mp: #f97316; --sg: #22c55e; --scd: #3b82f6;
            }
            body { font-family: sans-serif; background-color: var(--bg); color: var(--text); margin: 0; padding: 20px; line-height: 1.5; }
            .container { max-width: 900px; margin: 0 auto; }
            .card { background: var(--card); border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; padding: 24px; border: 1px solid var(--border); }
            h1, h2, h3 { color: var(--text); margin-top: 0; }
            .section { margin-bottom: 30px; }
            .outreach-grid { display: grid; grid-template-columns: 1fr; gap: 15px; }
            .option { border: 1px solid var(--border); border-radius: 6px; padding: 16px; background: #fff; cursor: pointer; position: relative; }
            .option:hover { background: #f1f5f9; }
            .option-label { font-size: 0.7rem; text-transform: uppercase; font-weight: bold; color: var(--primary); display: block; margin-bottom: 5px; }
            .signals { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }
            .sig { padding: 12px; border-radius: 6px; font-size: 0.8rem; }
            .sig-rc { background: #fee2e2; } .sig-mp { background: #ffedd5; } .sig-sg { background: #dcfce7; } .sig-scd { background: #dbeafe; }
            .toast { position: fixed; bottom: 20px; right: 20px; background: #333; color: #fff; padding: 10px 20px; border-radius: 4px; opacity: 0; transition: opacity 0.3s; pointer-events: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>XIMPAX Outreach Report</h1>
    """]
    
    for _, row in df.iterrows():
        name = row.get('name', 'N/A')
        comp = row.get('company', 'N/A')
        func = row.get('known_function', 'N/A')
        
        html.append(f"""
            <div class="card">
                <h2>{name} — {func} at {comp}</h2>
                
                <div class="section">
                    <h3>📊 Situation Overview</h3>
                    <p><i>{row.get('company_summary', 'N/A')}</i></p>
                    <div class="signals">
                        <div class="sig sig-rc"><strong>Resource:</strong> {row.get('RC_status', 'N/A')}<br>{row.get('RC_signal', '')}</div>
                        <div class="sig sig-mp"><strong>Margin:</strong> {row.get('MP_status', 'N/A')}<br>{row.get('MP_signal', '')}</div>
                        <div class="sig sig-sg"><strong>Growth:</strong> {row.get('SG_status', 'N/A')}<br>{row.get('SG_signal', '')}</div>
                        <div class="sig sig-scd"><strong>Supply Chain:</strong> {row.get('SCD_status', 'N/A')}<br>{row.get('SCD_signal', '')}</div>
                    </div>
                </div>

                <div class="section">
                    <h3>🎯 Situational Notes (Click to Copy)</h3>
                    <div class="outreach-grid">
        """)
        
        notes = row.get('situation_notes', '')
        parts = re.split(r'\n?\d+\.\s', notes)
        for i, p in enumerate([pt for pt in parts if pt.strip()][:3]):
            html.append(f"""
                        <div class="option" onclick="copyText(this)">
                            <span class="option-label">Option {i+1}</span>
                            <div class="content">{p.strip().replace('\n', '<br>')}</div>
                        </div>
            """)

        html.append("""
                    </div>
                </div>

                <div class="section">
                    <h3>🏢 Positioning Options (Click to Copy)</h3>
                    <div class="outreach-grid">
        """)

        pos_notes = row.get('positioning_notes', '')
        pos_parts = re.split(r'\n?\d+\.\s', pos_notes)
        for i, p in enumerate([pt for pt in pos_parts if pt.strip()][:3]):
             html.append(f"""
                        <div class="option" onclick="copyText(this)">
                            <span class="option-label">Option {i+1}</span>
                            <div class="content">{p.strip()}</div>
                        </div>
            """)

        html.append("</div></div></div>")

    html.append("""
        </div>
        <div id="toast" class="toast">Copied!</div>
        <script>
            function copyText(el) {
                const text = el.querySelector('.content').innerText;
                navigator.clipboard.writeText(text).then(() => {
                    const toast = document.getElementById('toast');
                    toast.style.opacity = '1';
                    setTimeout(() => { toast.style.opacity = '0'; }, 2000);
                });
            }
        </script>
    </body>
    </html>
    """)
    
    return "".join(html)
