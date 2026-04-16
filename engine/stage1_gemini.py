import re
import time
import urllib.request
import urllib.error
from google import genai
from google.genai import types


def _fetch_article_date(uri, timeout=6):
    """
    Follow the full redirect chain (Gemini returns proxy URLs) to the real
    article, then extract a publication date from meta tags or JSON-LD.
    Returns 'YYYY-MM-DD' string or None.
    """
    DATE_PATTERNS = [
        r"""<meta[^>]+property=['"]article:published_time['"][^>]+content=['"]([^'"\\s]+)""",
        r"""<meta[^>]+content=['"]([^'"\\s]+)['"][^>]+property=['"]article:published_time['"]""",
        r"""<meta[^>]+name=['"](?:date|pubdate|publish[_-]?date|publication[_-]?date|dc\.date)['"][^>]+content=['"]([^'"\\s]+)""",
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'"publishedAt"\s*:\s*"([^"]+)"',
        r'"dateCreated"\s*:\s*"([^"]+)"',
        r"""<time[^>]+datetime=['"]([^'"\\s]+)""",
    ]

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def _resolve(url, hops=6):
        """Follow redirects manually, return (final_url, html_text)."""
        for _ in range(hops):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return r.url, r.read(20_000).decode("utf-8", errors="ignore")
            except urllib.error.HTTPError as exc:
                loc = exc.headers.get("Location", "")
                if loc and loc != url:
                    url = loc
                    continue
                return url, ""
            except Exception:
                return url, ""
        return url, ""

    try:
        _, html = _resolve(uri)
        if not html:
            return None
        for pat in DATE_PATTERNS:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                raw = m.group(1)[:10]
                if re.match(r"\d{4}-\d{2}-\d{2}", raw):
                    return raw
    except Exception:
        pass
    return None


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
    "Reply in this EXACT format:\n"
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
    if score >= 7: return "CONFIRMED"
    if score >= 4: return "LIKELY"
    return "UNCLEAR"


def _prose_to_bullets(text, n=3):
    """
    Split prose into up to n bullet points by sentence boundaries.
    Handles abbreviations (U.S., e.g., Dr., etc.) to avoid false splits.
    """
    # Temporarily mask known abbreviations so their periods don't trigger splits
    ABBREVS = r"\b(?:U\.S|U\.K|e\.g|i\.e|Dr|Mr|Mrs|Ms|St|vs|approx|est|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec|CHF|EUR|USD)\.(?=\s)"
    masked = re.sub(ABBREVS, lambda m: m.group(0).replace(".", "\x00"), text.strip())
    # Split on sentence-ending punctuation followed by whitespace
    parts = re.split(r'(?<=[.!?])\s+', masked)
    # Restore masked periods
    sentences = [p.replace("\x00", ".").strip() for p in parts if len(p.strip()) > 15]
    if not sentences:
        return text
    if len(sentences) <= n:
        bullets = sentences
    else:
        bullets = sentences[:n-1] + [" ".join(sentences[n-1:])]
    return "\n".join(f"- {s}" for s in bullets)


def _extract_grounding_sources(resp):
    """
    Extract source titles and URIs from Gemini grounding metadata.

    Tries four strategies in order:
      1. grounding_chunks  (most common in google-genai SDK)
      2. grounding_supports -> grounding_chunk_indices (some SDK versions)
      3. search_entry_point rendered HTML -- parses anchor tags
      4. Regex scan of the raw response text for https:// URLs
    """
    sources = []
    debug_info = {}

    try:
        candidates = list(resp.candidates or [])
        debug_info["candidates_count"] = len(candidates)

        for candidate in candidates:
            gm = getattr(candidate, "grounding_metadata", None)
            debug_info["has_grounding_metadata"] = gm is not None
            if not gm:
                continue

            # Strategy 1: grounding_chunks
            chunks = getattr(gm, "grounding_chunks", None) or []
            debug_info["grounding_chunks_count"] = len(chunks)
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if web:
                    title = getattr(web, "title", "") or ""
                    uri   = getattr(web, "uri",   "") or ""
                    if uri:
                        sources.append({"title": title or uri, "uri": uri})

            # Strategy 2: grounding_supports
            if not sources:
                supports = getattr(gm, "grounding_supports", None) or []
                debug_info["grounding_supports_count"] = len(supports)
                for sup in supports:
                    indices = getattr(sup, "grounding_chunk_indices", []) or []
                    for idx in indices:
                        if idx < len(chunks):
                            web = getattr(chunks[idx], "web", None)
                            if web:
                                uri   = getattr(web, "uri",   "") or ""
                                title = getattr(web, "title", "") or uri
                                if uri:
                                    sources.append({"title": title, "uri": uri})

            # Strategy 3: search_entry_point HTML anchors
            if not sources:
                sep = getattr(gm, "search_entry_point", None)
                if sep:
                    html_snip = getattr(sep, "rendered_content", "") or ""
                    for m in re.finditer(r'href=["\'](http[^"\' ]+)["\'][^>]*>([^<]+)<', html_snip):
                        uri, title = m.group(1), m.group(2).strip()
                        sources.append({"title": title or uri, "uri": uri})
                debug_info["search_entry_point"] = bool(sep)

    except Exception as exc:
        debug_info["extraction_error"] = str(exc)

    # Strategy 4: regex scan of raw response text
    if not sources:
        try:
            raw = getattr(resp, "text", "") or ""
            for uri in re.findall(r'https?://[^\s\)\]>"\']+', raw):
                uri = uri.rstrip(".,;)")
                sources.append({"title": uri, "uri": uri})
            debug_info["text_url_fallback"] = True
        except Exception:
            pass

    # Deduplicate by URI
    seen, unique = set(), []
    for s in sources:
        if s["uri"] not in seen:
            seen.add(s["uri"])
            unique.append(s)

    debug_info["final_sources_count"] = len(unique)

    # Enrich with publication dates (best-effort, never blocks pipeline)
    for s in unique:
        s["date"] = _fetch_article_date(s["uri"])

    return unique, debug_info


def parse_result(text):
    clean = re.sub(r"[\*\`#~]+", "", text)
    clean = re.sub(r"<[^>]+>", "", clean)
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
            # Fallback: only accept a score if we can also extract real signal text.
            # This prevents "10/no signal" results when Gemini uses a non-standard format.
            fallback = rf"(?i){code}\s*:[^\d]*(\d+)"
            mf = re.search(fallback, clean)
            if mf:
                candidate_score = min(int(mf.group(1)), 10)
                txt_pat = rf"(?i){code}\s*:[^|]*?\d+.*?\|?.*?\|?\s*(.+?)(?=\n(?:RC|MP|SG|SCD|SUMMARY|SOURCES)|$)"
                mt = re.search(txt_pat, clean, re.DOTALL)
                if mt:
                    raw_signal = mt.group(1).strip()
                    if len(raw_signal) > 20:   # only accept if there's real text
                        score = candidate_score
                        bullet_lines = re.findall(r"^\s*[-\u2022]\s*(.+)", raw_signal, re.MULTILINE)
                        if len(bullet_lines) >= 2:
                            signal = "\n".join(f"- {b.strip()}" for b in bullet_lines[:3])
                        else:
                            signal = _prose_to_bullets(raw_signal, n=3)
                    # else: leave score=0, signal="" — better than 10/blank
        out[code + "_score"] = score
        out[code + "_status"] = _enforce(score)
        out[code + "_signal"] = signal

    sm = re.search(r"(?i)SUMMARY\s*:\s*(.+?)(?=SOURCES\s*:|$)", clean, re.DOTALL)
    out["SUMMARY"] = re.sub(r"\s+", " ", sm.group(1)).strip() if sm else ""
    out["SOURCES"] = []  # Will be populated from grounding metadata
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
        # Extract all sources from grounding metadata (returns sources + debug dict)
        sources, source_debug = _extract_grounding_sources(resp)
        parsed["SOURCES"] = sources
        parsed["SOURCES_DEBUG"] = source_debug
    except Exception as e:
        parsed = parse_result("")
        parsed["SUMMARY"] = f"Stage1 error for {company}: {str(e)}"
        parsed["error"] = str(e)
    finally:
        time.sleep(PAUSE)
    parsed["company"] = company
    parsed["active_situations"] = get_active(parsed)
    return parsed
