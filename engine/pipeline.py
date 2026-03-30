import time
import pandas as pd
from typing import Optional, Callable
from .stage0_serper import lookup_company
from .stage1_gemini import scan_company
from .stage2_gemini import generate_message

SERPER_PAUSE = 1.5
LOW_CONF = 0.5


def _load_profile(path="config/ximpax_profile.txt") -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ("XIMPAX is a boutique supply chain and procurement consultancy based in "
                "Switzerland, specialising in embedded expert deployment, category management, "
                "and operational excellence for FMCG and Life Sciences clients.")


def run_pipeline(
    df: pd.DataFrame,
    serper_key: str,
    gemini_key: str,
    config_path: str = "config/ximpax_profile.txt",
    progress_cb: Optional[Callable] = None,
) -> tuple:
    profile = _load_profile(config_path)
    results, raw_stage1 = [], []
    total = len(df)

    for idx, row in df.iterrows():
        name         = str(row.get("name", "")).strip()
        function     = str(row.get("known_function", "")).strip()
        closeness    = int(row.get("closeness_level", 1))
        sit_override = str(row.get("company_situation", "")).strip()

        rec = dict(name=name, known_function=function, closeness_level=closeness,
                   company="", company_confidence=0.0, lookup_strategy="",
                   review_flag="", RC_score=0, RC_status="UNCLEAR", RC_signal="",
                   MP_score=0, MP_status="UNCLEAR", MP_signal="",
                   SG_score=0, SG_status="UNCLEAR", SG_signal="",
                   SCD_score=0, SCD_status="UNCLEAR", SCD_signal="",
                   company_summary="", active_situations="",
                   linkedin_message="", notes="")

        # Stage 0 — Company lookup
        if progress_cb: progress_cb(idx, total, f"Stage 0 — company lookup: {name}")
        known_co = str(row.get("known_company", "")).strip()
        if known_co and known_co.lower() != "nan":
            company, conf, strategy = known_co, 1.0, "provided"
        else:
            lk = lookup_company(name, function, serper_key)
            company  = lk.get("company") or ""
            conf     = lk.get("confidence", 0.0)
            strategy = lk.get("strategy", "")
            time.sleep(SERPER_PAUSE)

        rec.update(company=company, company_confidence=conf, lookup_strategy=strategy)
        if conf < LOW_CONF:
            rec["review_flag"] = "⚠️ Low confidence"

        if not company:
            rec["notes"] = "Company not found — skipped Stage 1 & 2"
            results.append(rec)
            if progress_cb: progress_cb(idx + 1, total, f"⚠️ Skipped {name}")
            continue

        # Stage 1 — Gemini situation scan
        if progress_cb: progress_cb(idx, total, f"Stage 1 — scanning {company}...")
        active_situations = []
        try:
            scan = scan_company(company, gemini_key)
            for code in ["RC", "MP", "SG", "SCD"]:
                rec[f"{code}_score"]  = scan.get(f"{code}_score", 0)
                rec[f"{code}_status"] = scan.get(f"{code}_status", "UNCLEAR")
                rec[f"{code}_signal"] = scan.get(f"{code}_signal", "")
            rec["company_summary"]   = scan.get("SUMMARY", "")
            active_situations = scan.get("active_situations", [])
            rec["active_situations"] = "; ".join(f"{s['code']}:{s['status']}" for s in active_situations)
            raw_stage1.append({"name": name, "company": company,
                                "raw_output": scan.get("raw_output", "")})
        except Exception as e:
            rec["notes"] += f"Stage1 error: {e} | "

        summary = (sit_override if sit_override and sit_override.lower() != "nan"
                   else rec["company_summary"])

        # Stage 2 — Message generation (Gemini)
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

    all_df    = pd.DataFrame(results)
    review_df = all_df[all_df["review_flag"] != ""].copy() if not all_df.empty else pd.DataFrame()
    raw_df    = pd.DataFrame(raw_stage1) if raw_stage1 else pd.DataFrame()
    return all_df, review_df, raw_df
