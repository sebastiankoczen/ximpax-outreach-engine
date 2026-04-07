import re
import time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 8

LABELS = {
    "RC": "Resource Constraints",
    "MP": "Margin Pressure",
    "SG": "Significant Growth",
    "SCD": "Supply Chain Disruption",
}

PROMPT = (
    "You are a strategic business analyst. "
    "Search the web for the most recent developments regarding \"{company}\". "
    "\n\n"
    "Identify specific evidence from the last 18 months for these 4 signals:\n"
    "RC (Resource Constraints): staffing shortages, hiring freezes, restructuring, layoffs, capability gaps\n"
    "MP (Margin Pressure): cost reduction programmes, profitability challenges, price pressure, margin warnings\n"
    "SG (Significant Growth): M&A, market expansion, new plant/capacity, major product launches, IPO, scaling\n"
    "SCD (Supply Chain Disruption): supply disruptions, nearshoring, logistics challenges, supplier issues\n"
    "\n"
    "For each signal, write 4-5 sentences including named programmes, real numbers, and specific dates if known.\n"
    "If no specific information is found for a category, state that clearly and score it low.\n"
    "\n"
    "Scoring:\n"
    "- STRONG evidence (named programme, specific number, known announcement) = score 7-10\n"
    "- MEDIUM/implied evidence = score 4-6\n"
    "- No evidence = score 0-3\n"
    "\n"
    "Reply in this EXACT format (no markdown, no bold, no asterisks):\n"
    "RC: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [4-5 sentence signal text]\n"
    "MP: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [4-5 sentence signal text]\n"
    "SG: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [4-5 sentence signal text]\n"
    "SCD: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [4-5 sentence signal text]\n"
    "SUMMARY: [2-3 sentence executive summary of the most important findings]\n"
    "SOURCES: [mention key known sources]\n"
    "\n"
    "Company: {company}\n"
    "Industry: {industry_hint}\n"
)

def _enforce(score):
    if score >= 7: return "CONFIRMED"
    if score >= 4: return "LIKELY"
    return "UNCLEAR"

def parse_result(text):
    # Strip markdown artifacts
    clean = re.sub(r"[*`#_~]+", "", text)
    clean = re.sub(r"<[^>]+>", "", clean)
    clean = clean.strip()
    clean = re.sub(r"^[ \t]+", "", clean, flags=re.MULTILINE)  # strip leading spaces per line
    
    out = {}
    for code in ["RC", "MP", "SG", "SCD"]:
        score, signal = 0, ""
        # Improved regex: more flexible with whitespace and lookahead
        pat = rf"(?mi)^{code}[^|\n:]*:\s*(\d+)\s*\|\s*(CONFIRMED|LIKELY|UNCLEAR)\s*\|\s*(.+?)(?=\n(?:RC|MP|SG|SCD|SUMMARY|SOURCES)|$)"
        
        m = re.search(pat, clean, re.DOTALL)
        if m:
            score = min(int(m.group(1)), 10)
            signal = re.sub(r"\s+", " ", m.group(3)).strip()
        else:
            # Fallback: look for code + score
            fallback = rf"(?i){code}\s*:[^\d]*(\d+)"
            mf = re.search(fallback, clean)
            if mf:
                score = min(int(mf.group(1)), 10)
                txt_pat = rf"(?i){code}\s*:[^|]*?\d+.*?\|?.*?\|?\s*(.+?)(?=\n(?:RC|MP|SG|SCD|SUMMARY|SOURCES)|$)"
                mt = re.search(txt_pat, clean, re.DOTALL)
                if mt: signal = re.sub(r"\s+", " ", mt.group(1)).strip()

        out[code + "_score"] = score
        out[code + "_status"] = _enforce(score)
        out[code + "_signal"] = signal

    sm = re.search(r"(?i)SUMMARY\s*:\s*(.+?)(?=SOURCES\s*:|$)", clean, re.DOTALL)
    out["SUMMARY"] = re.sub(r"\s+", " ", sm.group(1)).strip() if sm else ""
    
    out["raw_output"] = text
    return out

def get_active(parsed):
    active = []
    for code in ["RC", "MP", "SG", "SCD"]:
        if parsed[code + "_status"] in ("CONFIRMED", "LIKELY") and parsed[code + "_signal"]:
            active.append({
                "code": code,
                "label": LABELS[code],
                "score": parsed[code + "_score"],
                "status": parsed[code + "_status"],
                "signal": parsed[code + "_signal"],
            })
    return sorted(active, key=lambda x: -x["score"])

def _call_with_retry(client, model, contents, config, retries=2, wait=30):
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
        parsed["SUMMARY"] = f"Stage1 error for {company}: {str(e)}"
        parsed["error"] = str(e)
    finally:
        time.sleep(PAUSE)
    
    parsed["company"] = company
    parsed["active_situations"] = get_active(parsed)
    return parsed
