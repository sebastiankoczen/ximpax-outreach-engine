import time
import pandas as pd
from typing import Optional, Callable
from .stage1_gemini import scan_company
from .stage2_gemini import generate_situation_notes

OUTPUT_COLS = [
    "name", "known_function", "company", "situation_notes",
    "closeness_level", "active_situations", "company_summary",
    "RC_score", "RC_status", "RC_signal",
    "MP_score", "MP_status", "MP_signal",
    "SG_score", "SG_status", "SG_signal",
    "SCD_score", "SCD_status", "SCD_signal",
    "notes",
]

def run_pipeline(df, gemini_key, progress_cb=None):
    df = df.dropna(how="all")
    df = df[df["name"].astype(str).str.strip().str.len() > 1].reset_index(drop=True)
    
    results, raw_stage1 = [], []
    total = len(df)
    
    for idx, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        function = str(row.get("known_function", "")).strip()
        closeness = int(row.get("closeness_level", 3))
        company = str(row.get("known_company", "")).strip()
        sit_override = str(row.get("company_situation", "")).strip()
        
        if company.lower() in ("nan", ""):
            company = ""
            
        rec = {col: "" for col in OUTPUT_COLS}
        rec.update(name=name, known_function=function, closeness_level=closeness, company=company)
        
        if not company:
            rec["notes"] = "No company provided — skipped."
            results.append(rec)
            if progress_cb: progress_cb(idx + 1, total, f"⚠️ Skipped {name}")
            continue

        # Stage 1: Research
        if progress_cb: progress_cb(idx, total, f"[{idx+1}/{total}] Researching {company}...")
        active_situations = []
        try:
            scan = scan_company(company, gemini_key)
            for code in ["RC", "MP", "SG", "SCD"]:
                rec[f"{code}_score"] = scan.get(f"{code}_score", 0)
                rec[f"{code}_status"] = scan.get(f"{code}_status", "UNCLEAR")
                rec[f"{code}_signal"] = scan.get(f"{code}_signal", "")
            
            rec["company_summary"] = scan.get("SUMMARY", "")
            active_situations = scan.get("active_situations", [])
            rec["active_situations"] = "; ".join(f"{s['code']}:{s['status']}" for s in active_situations)
            raw_stage1.append({"name": name, "company": company, "raw_output": scan.get("raw_output", "")})
        except Exception as e:
            rec["notes"] += f"Research error: {e} | "

        # Stage 2: Outreach Options
        if progress_cb: progress_cb(idx, total, f"[{idx+1}/{total}] Generating proposals for {name}...")
        try:
            rec["situation_notes"] = generate_situation_notes(
                company=company,
                function=function,
                active_situations=active_situations,
                gemini_api_key=gemini_key
            )
        except Exception as e:
            rec["notes"] += f"Proposal error: {e}"

        results.append(rec)
        if progress_cb: progress_cb(idx + 1, total, f"✅ Done: {name}")

    all_df = pd.DataFrame(results)
    raw_df = pd.DataFrame(raw_stage1) if raw_stage1 else pd.DataFrame()
    return all_df, raw_df
