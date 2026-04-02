import re
import time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 8

LABELS = {
    "RC":  "Resource Constraints",
    "MP":  "Margin Pressure",
    "SG":  "Significant Growth",
    "SCD": "Supply Chain Disruption",
}

PROMPT = (
    "You are a business intelligence analyst. "
    "Search the web RIGHT NOW for recent news about \"{company}\"."
    "\n\n"
    "Find SPECIFIC evidence (last 18 months) for these 4 signals:\n"
    "RC - Resource Constraints: layoffs, hiring freezes, restructuring, named cost programmes, capability gaps\n"
    "MP - Margin Pressure: cost-cut targets, margin warnings, profitability decline, named efficiency programmes\n"
    "SG - Significant Growth: M&A, new plant/capacity, market entry, major product launch, named expansion plans\n"
    "SCD - Supply Chain Disruption: force majeure, supplier failures, nearshoring moves, logistics problems\n"
    "\n"
    "For each signal write 4-5 sentences using named programmes, real numbers, specific events and dates.\n"
    "If nothing found for a category, say so and score low.\n"
    "\n"
    "Scoring: named programme + number + date = 8-10 | indirect = 4-6 | nothing = 0-3\n"
    "Status: CONFIRMED if >= 7 | LIKELY if 4-6 | UNCLEAR if <= 3\n"
    "\n"
    "Reply in EXACT format — no markdown, no asterisks:\n"
    "RC: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [4-5 sentence signal]\n"
    "MP: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [4-5 sentence signal]\n"
    "SG: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [4-5 sentence signal]\n"
    "SCD: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [4-5 sentence signal]\n"
    "SUMMARY: [2-3 sentence executive summary]\n"
    "SOURCES: [key source names]\n"
    "\n"
    "Company: {company}\n"
    "Industry: {industry_hint}\n"
)


def _enforce(score):
    if score >= 7:   return "CONFIRMED"
    if score >= 4:   return "LIKELY"
    return "UNCLEAR"


def parse_result(text):
    clean = re.sub(r"[*`#]+", "", text).strip()
    out = {}
    for code in ["RC", "MP", "SG", "SCD"]:
        pat = (
            r"(?m)^" + code + r"\s*:\s*(\d+)\s*\|\s*(CONFIRMED|LIKELY|UNCLEAR)\s*\|"
            r"\s*(.+?)(?=\n\s*(?:RC|MP|SG|SCD|SUMMARY|SOURCES)\s*:|\Z)"
        )
        m = re.search(pat, clean, re.DOTALL | re.IGNORECASE)
        if m:
            score  = min(int(m.group(1)), 10)
            signal = re.sub(r"\s+", " ", m.group(3)).strip()
        else:
            score, signal = 0, ""
        out[code + "_score"]  = score
        out[code + "_status"] = _enforce(score)
        out[code + "_signal"] = signal
    sm = re.search(r"SUMMARY\s*:\s*(.+?)(?=SOURCES\s*:|\Z)", clean, re.DOTALL)
    out["SUMMARY"]    = re.sub(r"\s+", " ", sm.group(1)).strip() if sm else ""
    out["raw_output"] = text
    return out


def get_active(parsed):
    active = []
    for code in ["RC", "MP", "SG", "SCD"]:
        if parsed[code + "_status"] in ("CONFIRMED", "LIKELY") and parsed[code + "_signal"]:
            active.append({
                "code":   code,
                "label":  LABELS[code],
                "score":  parsed[code + "_score"],
                "status": parsed[code + "_status"],
                "signal": parsed[code + "_signal"],
            })
    return sorted(active, key=lambda x: -x["score"])


def _call_with_retry(client, model, contents, config, retries=2, wait=30):
    """Call Gemini with automatic retry on 429 rate-limit errors."""
    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=config)
        except Exception as e:
            if "429" in str(e) and attempt < retries:
                time.sleep(wait)
                continue
            raise


def scan_company(company, api_key, industry_hint=""):
    client = genai.Client(api_key=api_key)
    prompt = PROMPT.format(
        company=company,
        industry_hint=industry_hint or "not specified"
    )
    try:
        resp = _call_with_retry(
            client, MODEL, prompt,
            types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            )
        )
        parsed = parse_result(resp.text)
    except Exception as e:
        parsed = parse_result("")
        parsed["SUMMARY"] = "Stage1 error for " + company + ": " + str(e)
        parsed["error"]   = str(e)
    finally:
        time.sleep(PAUSE)
    parsed["company"]           = company
    parsed["active_situations"] = get_active(parsed)
    return parsed
