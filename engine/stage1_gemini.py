import re, time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 2

LABELS = {"RC": "Resource Constraints", "MP": "Margin Pressure",
          "SG": "Significant Growth", "SCD": "Supply Chain Disruption"}

PROMPT = """You are a strategic business analyst with deep knowledge of global companies.
Using everything you know about the company "{company}", assess their current business situation.

Assess signals for these 4 categories based on what you know:
- RC (Resource Constraints): staffing shortages, hiring freezes, restructuring, layoffs, capability gaps
- MP (Margin Pressure): cost reduction programmes, profitability challenges, price pressure, margin warnings
- SG (Significant Growth): M&A, market expansion, new product launches, IPO, scaling, new markets
- SCD (Supply Chain Disruption): supply disruptions, nearshoring, logistics challenges, supplier issues

Scoring per category:
- STRONG evidence (named programme, specific number, known announcement) = score 7-10
- MEDIUM/implied evidence = score 4-6
- No evidence = score 0-3

For each category write 4-5 specific sentences using:
- Named programmes (e.g. "Tailor Made cost programme", "Project Phoenix")
- Real numbers where known (e.g. "EUR 400M savings target", "2,000 job cuts")
- Specific events or announcements
- Named divisions or business units where relevant
- If you don't have specific information, say so honestly and score low

Reply in this EXACT format (no markdown, no bold, no asterisks, no bullet points in the signal text):
RC: [score 0-10] | [CONFIRMED/LIKELY/UNCLEAR] | [4-5 sentence signal summary]
MP: [score 0-10] | [CONFIRMED/LIKELY/UNCLEAR] | [4-5 sentence signal summary]
SG: [score 0-10] | [CONFIRMED/LIKELY/UNCLEAR] | [4-5 sentence signal summary]
SCD: [score 0-10] | [CONFIRMED/LIKELY/UNCLEAR] | [4-5 sentence signal summary]
SUMMARY: [2-3 sentence executive summary of the most important challenges and opportunities]
SOURCES: [mention key known sources e.g. annual reports, press releases, news]

Company: {company}
Industry hint: {industry_hint}"""


def parse_result(text: str) -> dict:
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    out = {}
    for code in ["RC", "MP", "SG", "SCD"]:
        m = re.search(
            rf"{code}:\s*(\d+)\s*\|\s*(CONFIRMED|LIKELY|UNCLEAR)\s*\|\s*(.+?)(?=\n(?:RC|MP|SG|SCD|SUMMARY|SOURCES):|$)",
            text, re.DOTALL)
        raw_score = min(int(m.group(1)), 10) if m else 0
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
                temperature=0.3
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
