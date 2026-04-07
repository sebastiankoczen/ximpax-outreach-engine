import pandas as pd
from engine.stage1_gemini import scan_company
from engine.stage2_gemini import generate_situation_notes, generate_positioning_notes


def run_pipeline(df, gemini_key, progress_callback=None):
    total = len(df)
    results = []

    for i, row in df.iterrows():
        company = str(row.get('known_company', row.get('company', '')))
        function = str(row.get('known_function', row.get('function', '')))
        closeness = str(row.get('closeness_level', row.get('closeness', '')))

        if progress_callback:
            progress_callback(i, total, f"Researching {company}...")

        # Stage 1
        research = scan_company(company, gemini_key, function)

        # Stage 2
        situations = generate_situation_notes(
            company, function, research["active_situations"], gemini_key, closeness
        )
        positioning = generate_positioning_notes(
            company, function, gemini_key, closeness
        )

        # Combine
        res = {
            "company": company,
            "known_function": function,
            "closeness": closeness,
            "situation_notes": situations,
            "positioning_notes": positioning,
            "summary": research.get("SUMMARY", ""),
            "sources": research.get("SOURCES", []),
        }

        # Add individual scores and signals
        for code in ["RC", "MP", "SG", "SCD"]:
            res[f"{code}_score"] = research.get(f"{code}_score", 0)
            res[f"{code}_signal"] = research.get(f"{code}_signal", "")
            res[f"{code}_status"] = research.get(f"{code}_status", "")

        results.append(res)

    return pd.DataFrame(results), results
