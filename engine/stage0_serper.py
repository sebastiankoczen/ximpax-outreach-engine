import re, time, requests

SERPER_URL = "https://google.serper.dev/search"
STOPWORDS = {"of","the","and","in","at","for","a","an","to","with","is","are","by","as","bei","van","de"}

# Words that indicate education, not a company — skip these in headline extraction
EDU_BLACKLIST = {
    "university","université","universität","hochschule","fachhochschule","fhnw","eth",
    "epfl","hsg","uzh","masters","master","bachelor","mba","phd","studies","school",
    "college","institute","academy","alumni","student","graduating",
}

def _is_edu(name: str) -> bool:
    words = set(name.lower().split())
    return bool(words & EDU_BLACKLIST) or any(k in name.lower() for k in EDU_BLACKLIST)


def _extract_from_headline(headline: str):
    """
    Extract (clean_function, company) from a LinkedIn headline.
    Handles: "Head of SC at Nestle | ...", "Director bei Lonza | ...", "Title - Company"
    Skips educational institutions.
    """
    # Split on | and process segments
    segments = [s.strip() for s in headline.split("|")]

    for seg in segments:
        # Try "Title at/bei/chez/@ Company"
        m = re.search(
            r"^(.+?)\s+(?:at|bei|chez|@)\s+([A-Z][^|\-–]{2,50}?)\s*$",
            seg.strip(), re.I
        )
        if m:
            company_candidate = m.group(2).strip().rstrip(".,")
            if not _is_edu(company_candidate) and len(company_candidate) > 1:
                func_part = m.group(1).strip()
                return func_part, company_candidate

        # Try "Title - Company" (dash, company is Title Case or all caps)
        m2 = re.search(r"^(.+?)\s*[-–]\s*([A-Z][A-Za-z0-9\s&\.]{2,40}?)\s*$", seg)
        if m2:
            company_candidate = m2.group(2).strip()
            if not _is_edu(company_candidate) and len(company_candidate) > 1:
                return m2.group(1).strip(), company_candidate

    # No company found in headline
    clean_func = segments[0] if segments else headline
    return clean_func, None


def _kw(func: str, n: int = 3) -> str:
    words = [w for w in func.split() if w.lower() not in STOPWORDS]
    return " ".join(words[:n])

def _company_from_title(text: str):
    m = re.search(r"\bat\s+([A-Z][^|\u2013\-]{2,40}?)(?:\s*[|\u2013]|\s*$)", text)
    return m.group(1).strip() if m else None

def _company_from_snippet(text: str):
    m = re.search(r"\bat\s+([A-Z][A-Za-z0-9\s&\-\.]{2,40}?)(?:\s*[\.,|]|\s+(?:since|from|\u2013|-|linkedin))", text, re.I)
    return m.group(1).strip() if m else None


def lookup_company(name: str, function: str, api_key: str) -> dict:
    name = (name or "").strip()
    if not name or len(name) < 2:
        return {"company": None, "confidence": 0.0, "strategy": "empty_name",
                "title_found": "", "snippet": ""}

    # Try extracting company directly from LinkedIn headline first
    clean_func, inline_company = _extract_from_headline(function or "")
    if inline_company and len(inline_company) > 1:
        return {"company": inline_company, "confidence": 0.95,
                "strategy": "headline_parse", "title_found": function, "snippet": ""}

    parts = name.split()
    first = parts[0] if parts else name
    kw = _kw(clean_func)
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    strategies = [
        (f'site:linkedin.com/in "{name}" {kw}'.strip(), 0.9, "precise"),
        (f'site:linkedin.com/in "{name}"', 0.7, "name_only"),
        (f'"{name}" linkedin {kw}'.strip(), 0.5, "broad"),
        (f'"{first}" linkedin {kw} site:linkedin.com'.strip(), 0.3, "firstname"),
    ]

    for query, conf, label in strategies:
        try:
            r = requests.post(SERPER_URL, json={"q": query, "num": 3},
                              headers=headers, timeout=10)
            r.raise_for_status()
            for hit in r.json().get("organic", []):
                title   = hit.get("title", "")
                snippet = hit.get("snippet", "")
                company = (_company_from_title(title)
                           or _company_from_snippet(snippet)
                           or _company_from_snippet(title))
                if company and len(company) > 1 and not _is_edu(company):
                    return {"company": company, "confidence": conf,
                            "strategy": label, "title_found": title, "snippet": snippet}
            time.sleep(0.3)
        except Exception:
            continue

    return {"company": None, "confidence": 0.0, "strategy": "failed",
            "title_found": "", "snippet": ""}
