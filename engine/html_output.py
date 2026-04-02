import re

def generate_html(df):
    """Generates a clean HTML report for outreach messages and research."""
    
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
                --rc: #ef4444;
                --mp: #f97316;
                --sg: #22c55e;
                --scd: #3b82f6;
            }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                background-color: var(--bg); 
                color: var(--text);
                margin: 0;
                padding: 20px;
                line-height: 1.5;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 { color: var(--text); border-bottom: 2px solid var(--primary); padding-bottom: 10px; }
            .card { 
                background: var(--card); 
                border-radius: 8px; 
                box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
                margin-bottom: 24px; 
                overflow: hidden;
                border: 1px solid var(--border);
            }
            .card-header { 
                padding: 16px 20px; 
                background: #f1f5f9; 
                border-bottom: 1px solid var(--border);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .card-header h2 { margin: 0; font-size: 1.25rem; }
            .card-body { padding: 20px; }
            
            .outreach-options { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 20px; 
                margin-bottom: 24px;
            }
            .option { 
                border: 1px solid var(--border); 
                border-radius: 6px; 
                padding: 16px; 
                background: #fff;
                cursor: pointer;
                transition: transform 0.1s, box-shadow 0.1s;
                position: relative;
            }
            .option:hover { transform: translateY(-2px); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
            .option:active { transform: translateY(0); }
            .option-label { 
                font-size: 0.75rem; 
                text-transform: uppercase; 
                font-weight: bold; 
                color: var(--primary); 
                margin-bottom: 8px;
                display: block;
            }
            .copy-hint { 
                position: absolute; top: 12px; right: 12px; font-size: 0.7rem; color: #94a3b8;
            }
            
            .signals-grid { 
                display: grid; 
                grid-template-columns: repeat(4, 1fr); 
                gap: 12px; 
                margin-top: 16px;
            }
            .signal-box { 
                padding: 12px; 
                border-radius: 6px; 
                font-size: 0.85rem;
                min-height: 80px;
            }
            .signal-rc { background: #fee2e2; border-left: 4px solid var(--rc); }
            .signal-mp { background: #ffedd5; border-left: 4px solid var(--mp); }
            .signal-sg { background: #dcfce7; border-left: 4px solid var(--sg); }
            .signal-scd { background: #dbeafe; border-left: 4px solid var(--scd); }
            .signal-title { font-weight: bold; display: block; margin-bottom: 4px; }
            
            .summary { 
                background: #f8fafc; 
                padding: 16px; 
                border-radius: 6px; 
                font-style: italic; 
                margin-top: 20px;
                border-left: 4px solid #94a3b8;
            }
            
            .toast {
                position: fixed; bottom: 20px; right: 20px; background: #1e293b; color: #fff;
                padding: 12px 24px; border-radius: 4px; opacity: 0; transition: opacity 0.3s;
                pointer-events: none;
            }
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
                <div class="card-header">
                    <h2>{name} — {func} at {comp}</h2>
                </div>
                <div class="card-body">
                    <h3>Proposed Outreach Notes</h3>
                    <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 16px;">Click an option to copy it to your clipboard.</p>
                    <div class="outreach-options">
        """)
        
        notes_text = row.get('situation_notes', '')
        proposals = []
        if notes_text:
            parts = re.split(r'\\n?\\d+\\.\\s', notes_text)
            proposals = [p.strip() for p in parts if p.strip()]
        
        if not proposals:
            html.append('<p>No proposals generated for this contact.</p>')
        else:
            for i, p in enumerate(proposals[:3]):
                p_disp = p.replace('\\n', '<br>')
                html.append(f"""
                        <div class="option" onclick="copyToClipboard(this)">
                            <span class="option-label">Proposal {i+1}</span>
                            <span class="copy-hint">Click to copy</span>
                            <div class="content">{p_disp}</div>
                        </div>
                """)
        
        html.append("""
                    </div>
                    <h3>Research Signals</h3>
                    <div class="signals-grid">
        """)
        
        for code, label in [("RC", "Resource Constraints"), ("MP", "Margin Pressure"), ("SG", "Significant Growth"), ("SCD", "Supply Chain Disruption")]:
            status = row.get(f"{code}_status", "UNCLEAR")
            signal = row.get(f"{code}_signal", "No specific signal found.")
            html.append(f"""
                        <div class="signal-box signal-{code.lower()}">
                            <span class="signal-title">{label} ({status})</span>
                            {signal}
                        </div>
            """)
            
        html.append(f"""
                    </div>
                    <div class="summary">
                        <strong>Strategic Summary:</strong> {row.get('company_summary', 'N/A')}
                    </div>
                </div>
            </div>
        """)
        
    html.append("""
        </div>
        <div id="toast" class="toast">Copied to clipboard!</div>
        <script>
            function copyToClipboard(el) {
                const text = el.querySelector('.content').innerText;
                const temp = document.createElement('textarea');
                temp.value = text;
                document.body.appendChild(temp);
                temp.select();
                document.execCommand('copy');
                document.body.removeChild(temp);
                
                const toast = document.getElementById('toast');
                toast.style.opacity = '1';
                setTimeout(() => { toast.style.opacity = '0'; }, 2000);
            }
        </script>
    </body>
    </html>
    """)
    
    return "\\n".join(html)
