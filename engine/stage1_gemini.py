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
    "Always respond with ONLY the exact structured output requested. "
    "Never write a preamble, introduction, or explanation. "
    "Start your response immediately with RC: on the very first line. "
    "Never use code blocks, backticks, or markdown."
)

PROMPT = (
    "Search the web for the most recent news about \"{company}\" from the last 12 months.\n\n"
    "Find specific evidence for these 4 signals:\n"
    "RC (Resource Constraints): layoffs, restructuring, hiring freezes, capability gaps\n"
    "MP (Margin Pressure): cost cuts, profitability warnings, price pressure, margin decline\n"
    "SG (Significant Growth): M&A, new factories, major launches, market expansion, IPO\n"
    "SCD (Supply Chain Disruption): supply issues, logistics problems, nearshoring, supplier failures\n\n"
    "Score each signal:\n"
    "7-10 = CONFIRMED: named programme, specific number, or announced date found\n"
    "4-6  = LIKELY: implied or reported without specifics\n"
    "0-3  = UNCLEAR: no evidence found\n\n"
    "START YOUR RESPONSE WITH RC: — no introduction, no preamble, no code blocks.\n"
    "Use this exact format:\n"
    "RC: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [evidence sentence 1]. [sentence 2]. [sentence 3].\n"
    "MP: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [evidence sentence 1]. [sentence 2]. [sentence 3].\n"
    "SG: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [evidence sentence 1]. [sentence 2]. [sentence 3].\n"
    "SCD: [score] | [CONFIRMED or LIKELY or UNCLEAR] | [evidence sentence 1]. [sentence 2]. [sentence 3].\n"
    "SUMMARY: [single sentence: the most critical business situation for this company right now]\n\n"
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


def _call_with_retry(client, model, contents, config, retries=3, wait=15):
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
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.1,
    )
    sources = []
    full_text = ""
    last_resp = None

    try:
        # Try up to 3 times with grounding until structured data appears
        for attempt in range(3):
            resp = _call_with_retry(client, MODEL, prompt, config)
            last_resp = resp
            full_text = _get_full_text(resp)
            sources = _extract_grounding_sources(resp)
            if _has_structured_data(full_text):
                break
            time.sleep(5)

        parsed = parse_result(full_text)
        parsed["SOURCES"] = sources

        if not _has_structured_data(full_text):
            parsed["SUMMARY"] = "Research completed but structured output not returned by Gemini — please retry."

    except Exception as e:
        parsed = parse_result("")
        parsed["SUMMARY"] = f"Stage1 error for {company}: {str(e)}"
        parsed["error"] = str(e)
    finally:
        time.sleep(PAUSE)

    parsed["company"] = company
    parsed["active_situations"] = get_active(parsed)
    return parsed
