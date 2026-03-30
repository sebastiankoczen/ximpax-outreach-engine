import re, time, requests

SERPER_URL = "https://google.serper.dev/search"
STOPWORDS = {"of","the","and","in","at","for","a","an","to","with","is","are","by","as"}

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
    # Guard: skip if name is empty or too short
    name = (name or "").strip()
    if not name or len(name) < 2:
        return {"company": None, "confidence": 0.0, "strategy": "empty_name",
                "title_found": "", "snippet": ""}

    parts = name.split()
    first = parts[0] if parts else name
    kw = _kw(function or "")

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
                if company and len(company) > 1:
                    return {"company": company, "confidence": conf,
                            "strategy": label, "title_found": title, "snippet": snippet}
            time.sleep(0.3)
        except Exception:
            continue

    return {"company": None, "confidence": 0.0, "strategy": "failed",
            "title_found": "", "snippet": ""}
