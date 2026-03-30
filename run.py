#!/usr/bin/env python3
"""CLI runner — python run.py --input contacts.csv [--output result.xlsx]"""
import argparse, os, sys
import pandas as pd
from engine.pipeline import run_pipeline

def main():
    p = argparse.ArgumentParser(description="XIMPAX Outreach Engine — CLI")
    p.add_argument("--input",   required=True, help="Path to contacts CSV")
    p.add_argument("--output",  default="output/outreach_output.xlsx")
    p.add_argument("--config",  default="config/ximpax_profile.txt")
    args = p.parse_args()

    serper = os.environ.get("SERPER_API_KEY")  or sys.exit("SERPER_API_KEY not set")
    gemini = os.environ.get("GEMINI_API_KEY")  or sys.exit("GEMINI_API_KEY not set")
    openai = os.environ.get("OPENAI_API_KEY")  or sys.exit("OPENAI_API_KEY not set")

    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} contacts from {args.input}")

    def cb(done, total, msg):
        print(f"  [{done}/{total}] {msg}")

    all_df, review_df, raw_df = run_pipeline(
        df=df, serper_key=serper, gemini_key=gemini, openai_key=openai,
        config_path=args.config, progress_cb=cb,
    )

    os.makedirs("output", exist_ok=True)
    with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
        all_df.to_excel(writer,    sheet_name="All Contacts", index=False)
        if not review_df.empty:
            review_df.to_excel(writer, sheet_name="Needs Review",  index=False)
        if not raw_df.empty:
            raw_df.to_excel(writer,    sheet_name="Stage1 Raw",    index=False)

    print(f"\n✅ Done — output saved to {args.output}")
    print(f"   {len(all_df)} contacts processed | {len(review_df)} flagged for review")

if __name__ == "__main__":
    main()
