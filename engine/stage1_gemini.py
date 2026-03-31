import re, time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 15

LABELS = {
    "RC":  "Resource Constraints",
    "MP":  "Margin Pressure",
    "SG":  "Significant Growth",
    "SCD": "Supply Chain Disruption",
}

PROMPT = """You are a strategic business analyst. Use Google Search to research the company "{company}" right now.

Assess current signals across 4 categories:
- RC (Resource Constraints): staffing shortages, hiring freezes, restructuring, capability gaps
- MP (Margin Pressure): cost reduction programs, profitability challenges, price pressure, margin decline
- SG (Significant Growth): M&A, market expansion, new product launches, capacity investments, scaling
- SCD (Supply Chain Disruption): supplier issues, nearshoring moves, logistics challenges, sourcing risk

Scoring: STRONG public evidence = +2 | Indirect/implied = +1 | None = 0 (max 10 per category)

Reply in this EXACT format — no deviations:
RC: [score 0-10] | [CONFIRMED/LIKELY/UNCLEAR] | [3-4 sentence summary with specific facts, numbers, and named programmes]
MP: [score 0-10] | [CONFIRMED/LIKELY/UNCLEAR] | [3-4 sentence summary with specific facts, numbers, and named programmes]
SG: [score 0-10] | [CONFIRMED/LIKELY/UNCLEAR] | [3-4 sentence summary with specific facts, numbers, and named programmes]
SCD: [score 0-10] | [CONFIRMED/LIKELY/UNCLEAR] | [3-4 sentence summary with specific facts, numbers, and named programmes]
SUMMARY: [3 sentence executive summary covering the 2-3 most important developments]
SOURCES: [key source names or URLs]

Important:
- Use CONFIRMED only when score is 7 or higher with strong direct evidence
- Use LIKELY for score 4-6 with indirect or secondary evidence
- Use UNCLEAR for score 0-3 or when no real evidence found
- Each signal summary must contain specific named facts — no vague generalities

Company: {company}
Industry hint: {industry_hint}"""


def parse_result(text: str) -> dict:
    out = {}
    for code in ["RC", "MP", "SG", "SCD"]:
        m = re.search(
            rf"{code}:\s*(\d+)\s*\|\s*(CONFIRMED|LIKELY|UNCLEAR)\s*\|\s*(.+?)(?=\n(?:RC|MP|SG|SCD|SUMMARY|SOURCES):|$)",
            text, re.DOTALL)
        score  = min(int(m.group(1)), 10) if m else 0
        status = m.group(2).strip() if m else "UNCLEAR"
        signal = m.group(3).strip() if m else ""
        # Enforce score-status consistency
        if score >= 7:
            status = "CONFIRMED"
        elif score >= 4:
            if status == "CONFIRMED":
                status = "LIKELY"
        else:
            status = "UNCLEAR"
        out[f"{code}_score"]  = score
        out[f"{code}_status"] = status
        out[f"{code}_signal"] = signal
    sm  = re.search(r"SUMMARY:\s*(.+?)(?=SOURCES:|$)", text, re.DOTALL)
    out["SUMMARY"]    = sm.group(1).strip() if sm else ""
    out["raw_output"] = text
    return out


def get_active(parsed: dict) -> list:
    active = []
    for code in ["RC", "MP", "SG", "SCD"]:
        if parsed.get(f"{code}_status") in ("CONFIRMED", "LIKELY"):
            active.append({
                "code":   code,
                "label":  LABELS[code],
                "score":  parsed[f"{code}_score"],
                "status": parsed[f"{code}_status"],
                "signal": parsed[f"{code}_signal"],
            })
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
                temperature=0.2,
            )
        )
        parsed = parse_result(resp.text)
    except Exception as e:
        parsed = parse_result("")
        parsed["SUMMARY"] = f"Error scanning {company}: {e}"
        parsed["error"]   = str(e)
    finally:
        time.sleep(PAUSE)
    parsed["company"]           = company
    parsed["active_situations"] = get_active(parsed)
    return parsed
