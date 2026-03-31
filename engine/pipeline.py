import time
import pandas as pd
from typing import Optional, Callable
from .stage1_gemini import scan_company
from .stage2_gemini import generate_message

OUTPUT_COLS = [
    "name", "known_function", "company", "linkedin_message",
    "closeness_level", "active_situations", "company_summary",
    "RC_score", "RC_status", "RC_signal",
    "MP_score", "MP_status", "MP_signal",
    "SG_score", "SG_status", "SG_signal",
    "SCD_score", "SCD_status", "SCD_signal",
    "notes",
]


def _load_profile(path="config/ximpax_profile.txt") -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "XIMPAX is a small Swiss team of senior supply chain and procurement experts."


def run_pipeline(
    df: pd.DataFrame,
    gemini_key: str,
    config_path: str = "config/ximpax_profile.txt",
    progress_cb: Optional[Callable] = None,
) -> tuple:
    profile = _load_profile(config_path)
    df = df.dropna(how="all")
    df = df[df["name"].astype(str).str.strip().str.len() > 1].reset_index(drop=True)

    results, raw_stage1 = [], []
    total = len(df)

    for idx, row in df.iterrows():
        name         = str(row.get("name", "")).strip()
        function     = str(row.get("known_function", "")).strip()
        closeness    = int(row.get("closeness_level", 3))
        company      = str(row.get("known_company", "")).strip()
        sit_override = str(row.get("company_situation", "")).strip()

        if company.lower() in ("nan", ""):
            company = ""

        rec = {col: "" for col in OUTPUT_COLS}
        rec.update(name=name, known_function=function, closeness_level=closeness,
                   company=company, RC_score=0, MP_score=0, SG_score=0, SCD_score=0,
                   RC_status="UNCLEAR", MP_status="UNCLEAR",
                   SG_status="UNCLEAR", SCD_status="UNCLEAR",
                   notes="")

        if not company:
            rec["notes"] = "No company provided — skipped. Add known_company column to your CSV."
            results.append(rec)
            if progress_cb: progress_cb(idx + 1, total, f"⚠️ Skipped {name} — no company")
            continue

        # Stage 1 — Gemini research
        if progress_cb: progress_cb(idx, total, f"Stage 1 — researching {company}...")
        active_situations = []
        try:
            scan = scan_company(company, gemini_key)
            for code in ["RC", "MP", "SG", "SCD"]:
                rec[f"{code}_score"]  = scan.get(f"{code}_score", 0)
                rec[f"{code}_status"] = scan.get(f"{code}_status", "UNCLEAR")
                rec[f"{code}_signal"] = scan.get(f"{code}_signal", "")
            rec["company_summary"]   = scan.get("SUMMARY", "")
            active_situations        = scan.get("active_situations", [])
            rec["active_situations"] = "; ".join(
                f"{s['code']}:{s['status']}" for s in active_situations)
            raw_stage1.append({"name": name, "company": company,
                                "raw_output": scan.get("raw_output", "")})
        except Exception as e:
            rec["notes"] += f"Stage1 error: {e} | "

        summary = sit_override if sit_override and sit_override.lower() != "nan"                   else rec["company_summary"]

        # Stage 2 — Message
        if progress_cb: progress_cb(idx, total, f"Stage 2 — writing message for {name}...")
        try:
            rec["linkedin_message"] = generate_message(
                name=name, company=company, function=function,
                closeness_level=closeness, active_situations=active_situations,
                company_summary=summary, ximpax_profile=profile,
                gemini_api_key=gemini_key,
            )
        except Exception as e:
            rec["notes"] += f"Stage2 error: {e}"

        results.append(rec)
        if progress_cb: progress_cb(idx + 1, total, f"✅ Done: {name}")

    all_df = pd.DataFrame(results)
    ordered = [c for c in OUTPUT_COLS if c in all_df.columns]
    all_df  = all_df[ordered]
    raw_df  = pd.DataFrame(raw_stage1) if raw_stage1 else pd.DataFrame()
    return all_df, raw_df
