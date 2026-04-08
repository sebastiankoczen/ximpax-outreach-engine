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

SYSTEM_INSTRUCTION = (
    "You are a strategic business analyst. "
    "You always respond with ONLY the structured data requested — no preamble, no explanation, "
    "no code blocks, no backticks, no markdown formatting. "
    "Output plain text only, starting immediately with RC: on the first line."
)

PROMPT = (
    "Search the web for the most recent developments regarding \"{company}\". "
    "\n\n"
    "Identify specific evidence from the last 12 months for these 4 signals:\n"
    "RC (Resource Constraints): staffing shortages, hiring freezes, restructuring, layoffs, capability gaps\n"
    "MP (Margin Pressure): cost reduction programmes, profitability challenges, price pressure, margin warnings\n"
    "SG (Significant Growth): M&A, market expansion, new plant/capacity, major product launches, IPO, scaling\n"
    "SCD (Supply Chain Disruption): supply disruptions, nearshoring, logistics challenges, supplier issues\n"
    "\n"
    "For each signal provide 3 distinct evidence points. Each point must be a single sentence containing a named programme, real number, or specific date.\n"
    "If no specific information is found for a signal, state that clearly and score it low.\n"
    "\n"
    "Scoring:\n"
    "- STRONG evidence (named programme, specific number, known announcement) = score 7-10\n"
    "- MEDIUM/implied evidence = score 4-6\n"
    "- No evidence = score 0-3\n"
    "\n"
    "Reply in this EXACT format, starting with RC: on line 1, nothing before it:\n"
    "RC: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [sentence 1]. [sentence 2]. [sentence 3].\n"
    "MP: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [sentence 1]. [sentence 2]. [sentence 3].\n"
    "SG: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [sentence 1]. [sentence 2]. [sentence 3].\n"
    "SCD: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [sentence 1]. [sentence 2]. [sentence 3].\n"
    "SUMMARY: [1 sentence: the single most critical business situation for this company right now]\n"
    "\n"
    "Company: {company}\n"
    "Industry: {industry_hint}\n"
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
    """Concatenate ALL text parts from ALL candidates."""
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


def _has_structured_data(text):
    """Check if text contains the expected RC/MP/SG/SCD structure."""
    return bool(re.search(r'RC\s*:\s*\d+', text))


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
    clean = re.sub(r"```[a-z]*", "", text)
    clean = re.sub(r"[\*\`#~]+", "", clean)
    clean = clean.strip()

    out = {}
    for code in ["RC", "MP", "SG", "SCD"]:
        score, signal = 0, ""
        pat = rf"(?mi)^{code}[^|\n:]*:\s*(\d+)\s*\|\s*(CONFIRMED|LIKELY|UNCLEAR)\s*\|(.+?)(?=\n(?:RC|MP|SG|SCD|SUMMARY|SOURCES)|$)"
        m = re.search(pat, clean, re.DOTALL)
        if m:
            score = min(int(m.group(1)), 10)
            raw_signal = m.group(3).strip()
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
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            )
        )
        full_text = _get_full_text(resp)

        # If only preamble came back, retry once without grounding to force formatting
        if not _has_structured_data(full_text):
            retry_prompt = (
                f"Based on your knowledge of {company}, provide ONLY this exact structured output "
                f"with no preamble:\n"
                f"RC: [score] | [CONFIRMED or LIKELY or UNCLEAR] | evidence sentences.\n"
                f"MP: [score] | [CONFIRMED or LIKELY or UNCLEAR] | evidence sentences.\n"
                f"SG: [score] | [CONFIRMED or LIKELY or UNCLEAR] | evidence sentences.\n"
                f"SCD: [score] | [CONFIRMED or LIKELY or UNCLEAR] | evidence sentences.\n"
                f"SUMMARY: one sentence summary.\n"
            )
            resp2 = _call_with_retry(
                client, MODEL, retry_prompt,
                types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1,
                )
            )
            full_text = _get_full_text(resp2)

        parsed = parse_result(full_text)
        parsed["SOURCES"] = _extract_grounding_sources(resp)
    except Exception as e:
        parsed = parse_result("")
        parsed["SUMMARY"] = f"Stage1 error for {company}: {str(e)}"
        parsed["error"] = str(e)
    finally:
        time.sleep(PAUSE)
    parsed["company"] = company
    parsed["active_situations"] = get_active(parsed)
    return parsed
