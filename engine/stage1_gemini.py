import re, time
import google.generativeai as genai
from google.generativeai import protos

MODEL = "gemini-2.0-flash"
PAUSE = 15

LABELS = {"RC": "Resource Constraints", "MP": "Margin Pressure",
          "SG": "Significant Growth", "SCD": "Supply Chain Disruption"}

PROMPT = """You are a strategic business analyst. Use Google Search to research the company "{company}" right now.

Assess current signals for these 4 categories:
- RC (Resource Constraints): staffing shortages, hiring freezes, restructuring, capability gaps
- MP (Margin Pressure): cost reduction, profitability challenges, price pressure
- SG (Significant Growth): M&A, market expansion, new launches, scaling
- SCD (Supply Chain Disruption): supply disruptions, nearshoring, logistics challenges

Score: STRONG evidence = +2 | MEDIUM/implied = +1 | None = 0 (cap each at 10)

Reply in this EXACT format:
RC: [score] | [CONFIRMED/LIKELY/UNCLEAR] | [1-2 sentence signal summary]
MP: [score] | [CONFIRMED/LIKELY/UNCLEAR] | [1-2 sentence signal summary]
SG: [score] | [CONFIRMED/LIKELY/UNCLEAR] | [1-2 sentence signal summary]
SCD: [score] | [CONFIRMED/LIKELY/UNCLEAR] | [1-2 sentence signal summary]
SUMMARY: [2-3 sentence executive summary of main challenges/opportunities]
SOURCES: [key source URLs or publication names]

Company: {company}
Industry hint: {industry_hint}"""


def parse_result(text: str) -> dict:
    out = {}
    for code in ["RC", "MP", "SG", "SCD"]:
        m = re.search(
            rf"{code}:\s*(\d+)\s*\|\s*(CONFIRMED|LIKELY|UNCLEAR)\s*\|\s*(.+?)(?=\n[A-Z]{{2,}}:|$)",
            text, re.DOTALL)
        out[f"{code}_score"]  = min(int(m.group(1)), 10) if m else 0
        out[f"{code}_status"] = m.group(2).strip() if m else "UNCLEAR"
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
    genai.configure(api_key=api_key)
    # Use the correct google_search tool (not google_search_retrieval)
    tool = protos.Tool(google_search=protos.GoogleSearch())
    model = genai.GenerativeModel(MODEL, tools=[tool])
    prompt = PROMPT.format(company=company, industry_hint=industry_hint or "not specified")
    try:
        resp = model.generate_content(prompt)
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
