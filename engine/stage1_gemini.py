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

RESEARCH_PROMPT = (
    "Search the web for the most recent news and developments about \"{company}\" "
    "from the last 12 months.\n\n"
    "Find specific facts, announcements, programmes, and numbers related to:\n"
    "1. Layoffs, restructuring, hiring freezes, or capability gaps\n"
    "2. Cost reduction, margin pressure, profitability warnings, price cuts\n"
    "3. Acquisitions, new factories, major product launches, market expansion\n"
    "4. Supply chain disruptions, logistics issues, supplier problems, nearshoring\n\n"
    "Write a factual research summary of what you found. Include specific names, "
    "numbers, dates, and programme names wherever possible. "
    "Be direct and factual. No opinions, no speculation.\n\n"
    "Company: {company}\n"
    "Industry context: {industry_hint}\n"
)

FORMAT_PROMPT = (
    "Based on this research about {company}, score and format the 4 signals below.\n\n"
    "RESEARCH:\n{research_text}\n\n"
    "Scoring rules:\n"
    "7-10 = CONFIRMED: named programme, specific number, or announced date in the research\n"
    "4-6  = LIKELY: implied or reported without hard specifics\n"
    "0-3  = UNCLEAR: no evidence found\n\n"
    "Output ONLY these 5 lines. Use bare numbers and words — no square brackets:\n"
    "RC: 7 | CONFIRMED | sentence one. sentence two. sentence three.\n"
    "MP: 5 | LIKELY | sentence one. sentence two. sentence three.\n"
    "SG: 3 | UNCLEAR | sentence one. sentence two. sentence three.\n"
    "SCD: 8 | CONFIRMED | sentence one. sentence two. sentence three.\n"
    "SUMMARY: single sentence summary.\n\n"
    "Now do the same for {company}:\n"
    "RC: [your score] | [CONFIRMED or LIKELY or UNCLEAR] | [evidence from the research]\n"
    "MP: [your score] | [CONFIRMED or LIKELY or UNCLEAR] | [evidence from the research]\n"
    "SG: [your score] | [CONFIRMED or LIKELY or UNCLEAR] | [evidence from the research]\n"
    "SCD: [your score] | [CONFIRMED or LIKELY or UNCLEAR] | [evidence from the research]\n"
    "SUMMARY: [most critical business situation for {company} right now]\n"
)


def _enforce(score):
    if score >= 7:
        return "CONFIRMED"
    if score >= 4:
        return "LIKELY"
    return "UNCLEAR"


def _prose_to_bullets(text, n=3):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
    if not sentences:
        return text
    if len(sentences) <= n:
        bullets = sentences
    else:
        bullets = sentences[:n-1] + [" ".join(sentences[n-1:])]
    return "\n".join(f"- {s}" for s in bullets)


def _get_full_text(resp):
    parts_text = []
    try:
        for candidate in (resp.candidates or []):
            content = getattr(candidate, "content", None)
            if not content:
                continue
            for part in (getattr(content, "parts", None) or []):
                t = getattr(part, "text", None)
                if t and t.strip():
                    parts_text.append(t.strip())
    except Exception:
        pass
    if parts_text:
        return "\n".join(parts_text)
    try:
        return resp.text or ""
    except Exception:
        return ""


def _extract_grounding_sources(resp):
    sources = []
    try:
        for candidate in (resp.candidates or []):
            gm = getattr(candidate, "grounding_metadata", None)
            if not gm:
                continue
            for chunk in (getattr(gm, "grounding_chunks", []) or []):
                web = getattr(chunk, "web", None)
                if web:
                    title = getattr(web, "title", "") or ""
                    uri = getattr(web, "uri", "") or ""
                    if uri and title:
                        sources.append({"title": title, "uri": uri})
                    elif uri:
                        sources.append({"title": uri, "uri": uri})
    except Exception:
        pass
    seen = set()
    unique = []
    for s in sources:
        if s["uri"] not in seen:
            seen.add(s["uri"])
            unique.append(s)
    return unique


def parse_result(text):
    # Strip markdown fences and formatting
    clean = re.sub(r"```[a-z]*", "", text)
    clean = re.sub(r"[\*\`#~]+", "", clean)
    # Remove square brackets around scores and statuses e.g. [7] -> 7, [CONFIRMED] -> CONFIRMED
    clean = re.sub(r"\[(\d+)\]", r"\1", clean)
    clean = re.sub(r"\[(CONFIRMED|LIKELY|UNCLEAR)\]", r"\1", clean)
    clean = clean.strip()

    out = {}
    for code in ["RC", "MP", "SG", "SCD"]:
        score, signal = 0, ""
        pat = rf"(?mi)^{code}[^|\n:]*:\s*(\d+)\s*\|\s*(CONFIRMED|LIKELY|UNCLEAR)\s*\|(.+?)(?=\n(?:RC|MP|SG|SCD|SUMMARY|SOURCES)|$)"
        m = re.search(pat, clean, re.DOTALL)
        if m:
            score = min(int(m.group(1)), 10)
            raw_signal = m.group(3).strip()
            # Remove any leftover bracket wrappers around the signal text
            raw_signal = re.sub(r"^\[|\]$", "", raw_signal).strip()
            bullet_lines = re.findall(r"^\s*[-\u2022]\s*(.+)", raw_signal, re.MULTILINE)
            if len(bullet_lines) >= 2:
                signal = "\n".join(f"- {b.strip()}" for b in bullet_lines[:3])
            else:
                signal = _prose_to_bullets(raw_signal, n=3)
        else:
            fallback = rf"(?i){code}\s*:[^\d]*(\d+)"
            mf = re.search(fallback, clean)
            if mf:
                score = min(int(mf.group(1)), 10)
                txt_pat = rf"(?i){code}\s*:[^|]*?\d+.*?\|?.*?\|?\s*(.+?)(?=\n(?:RC|MP|SG|SCD|SUMMARY|SOURCES)|$)"
                mt = re.search(txt_pat, clean, re.DOTALL)
                if mt:
                    raw_signal = mt.group(1).strip()
                    raw_signal = re.sub(r"^\[|\]$", "", raw_signal).strip()
                    bullet_lines = re.findall(r"^\s*[-\u2022]\s*(.+)", raw_signal, re.MULTILINE)
                    if len(bullet_lines) >= 2:
                        signal = "\n".join(f"- {b.strip()}" for b in bullet_lines[:3])
                    else:
                        signal = _prose_to_bullets(raw_signal, n=3)
        out[code + "_score"] = score
        out[code + "_status"] = _enforce(score)
        out[code + "_signal"] = signal

    sm = re.search(r"(?i)SUMMARY\s*:\s*(.+?)(?=SOURCES\s*:|$)", clean, re.DOTALL)
    out["SUMMARY"] = re.sub(r"\s+", " ", sm.group(1)).strip() if sm else ""
    out["SOURCES"] = []
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


def _call_with_retry(client, model, contents, config, retries=2, wait=20):
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

    # STEP 1: Grounded research — collect real facts, no format pressure
    research_prompt = RESEARCH_PROMPT.format(
        company=company,
        industry_hint=industry_hint or "not specified"
    )
    try:
        resp1 = _call_with_retry(
            client, MODEL, research_prompt,
            types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            )
        )
        research_text = _get_full_text(resp1)
        sources = _extract_grounding_sources(resp1)
        time.sleep(3)
    except Exception as e:
        parsed = parse_result("")
        parsed["SUMMARY"] = f"Research error for {company}: {str(e)}"
        parsed["error"] = str(e)
        parsed["company"] = company
        parsed["active_situations"] = []
        time.sleep(PAUSE)
        return parsed

    # STEP 2: Format the research into RC/MP/SG/SCD — no grounding needed
    format_prompt = FORMAT_PROMPT.format(
        company=company,
        research_text=research_text[:4000]
    )
    try:
        resp2 = _call_with_retry(
            client, MODEL, format_prompt,
            types.GenerateContentConfig(
                temperature=0.1,
            )
        )
        formatted_text = _get_full_text(resp2)
    except Exception as e:
        parsed = parse_result("")
        parsed["SUMMARY"] = f"Formatting error for {company}: {str(e)}"
        parsed["error"] = str(e)
        parsed["company"] = company
        parsed["active_situations"] = []
        time.sleep(PAUSE)
        return parsed

    parsed = parse_result(formatted_text)
    parsed["SOURCES"] = sources
    parsed["raw_output"] = formatted_text
    time.sleep(PAUSE)
    parsed["company"] = company
    parsed["active_situations"] = get_active(parsed)
    return parsed
