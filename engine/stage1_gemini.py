import re, time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 15

LABELS = {"RC": "Resource Constraints", "MP": "Margin Pressure",
          "SG": "Significant Growth", "SCD": "Supply Chain Disruption"}

PROMPT = """You are a strategic business analyst with access to Google Search.
Search the web right now for the latest news, reports and announcements about the company "{company}".

Assess current signals for these 4 categories:
- RC (Resource Constraints): staffing shortages, hiring freezes, restructuring, layoffs, capability gaps
- MP (Margin Pressure): cost reduction programmes, profitability challenges, price pressure, margin warnings
- SG (Significant Growth): M&A, market expansion, new product launches, IPO, scaling, new markets
- SCD (Supply Chain Disruption): supply disruptions, nearshoring, logistics challenges, supplier issues

Scoring: STRONG evidence (named programme, number, announcement) = +2 | MEDIUM/implied = +1 | None = 0 (cap at 10)

For each category, write 4-5 specific sentences using:
- Named programmes (e.g. "Tailor Made cost programme", "Project Phoenix")
- Real numbers (e.g. "EUR 400M savings target", "2,000 job cuts")
- Specific events (e.g. "Q3 2025 earnings call", "January 2026 press release")
- Named executives or divisions where relevant

Reply in this EXACT format (no markdown, no bold, no asterisks):
RC: [score] | [CONFIRMED/LIKELY/UNCLEAR] | [4-5 sentence signal summary with specific facts]
MP: [score] | [CONFIRMED/LIKELY/UNCLEAR] | [4-5 sentence signal summary with specific facts]
SG: [score] | [CONFIRMED/LIKELY/UNCLEAR] | [4-5 sentence signal summary with specific facts]
SCD: [score] | [CONFIRMED/LIKELY/UNCLEAR] | [4-5 sentence signal summary with specific facts]
SUMMARY: [2-3 sentence executive summary of the most important challenges and opportunities]
SOURCES: [key source names or URLs]

Company: {company}
Industry hint: {industry_hint}"""


def parse_result(text: str) -> dict:
    # Strip markdown bold/italic formatting
    text = re.sub(r'\*+', '', text)
    out = {}
    for code in ["RC", "MP", "SG", "SCD"]:
        m = re.search(
            rf"{code}:\s*(\d+)\s*\|\s*(CONFIRMED|LIKELY|UNCLEAR)\s*\|\s*(.+?)(?=\n[A-Z]{{2,}}:|$)",
            text, re.DOTALL)
        raw_score = min(int(m.group(1)), 10) if m else 0
        # Enforce status strictly from score
        if raw_score >= 7:
            status = "CONFIRMED"
        elif raw_score >= 4:
            status = "LIKELY"
        else:
            status = "UNCLEAR"
        out[f"{code}_score"] = raw_score
        out[f"{code}_status"] = status
        out[f"{code}_signal"] = m.group(3).strip() if m else ""
    sm = re.search(r"SUMMARY:\s*(.+?)(?=SOURCES:|$)", text, re.DOTALL)
    out["SUMMARY"] = sm.group(1).strip() if sm else ""
    srm = re.search(r"SOURCES:\s*(.+?)$", text, re.DOTALL)
    out["SOURCES"] = srm.group(1).strip() if srm else ""
    out["raw_output"] = text
    return out


def get_active(parsed: dict) -> list:
    active = []
    for code in ["RC", "MP", "SG", "SCD"]:
        if parsed.get(f"{code}_status") in ("CONFIRMED", "LIKELY"):
            active.append({"code": code, "label": LABELS[code],
                           "score": parsed[f"{code}_score"],
                           "status": parsed[f"{code}_status"],
                           "signal": parsed[f"{code}_signal"]})
    return sorted(active, key=lambda x: -x["score"])


def scan_company(company: str, api_key: str, industry_hint: str = "") -> dict:
    client = genai.Client(api_key=api_key)
    prompt = PROMPT.format(company=company, industry_hint=industry_hint or "not specified")
    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2
            )
        )
        parsed = parse_result(resp.text)
    except Exception as e:
        parsed = parse_result("")
        parsed["SUMMARY"] = f"Error scanning {company}: {e}"
        parsed["error"] = str(e)
    finally:
        time.sleep(PAUSE)
    parsed["company"] = company
    parsed["active_situations"] = get_active(parsed)
    return parsed
