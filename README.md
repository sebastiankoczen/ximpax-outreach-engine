# ⚡ XIMPAX LinkedIn Outreach Engine

A 3-stage automated pipeline that turns a CSV of LinkedIn contacts into
**tailored, research-backed LinkedIn messages** — powered by Serper, Gemini 2.0 Flash,
and OpenAI GPT-4o.

---

## How It Works

```
contacts.csv  (name + function + closeness)
      │
      ▼  Stage 0 — Serper
      │  site:linkedin.com/in "Name" + function keywords
      │  → resolves current company + confidence score
      │
      ▼  Stage 1 — Gemini 2.0 Flash (Google Search grounding)
      │  → RC / MP / SG / SCD scores, signals, SUMMARY
      │
      ▼  Stage 2 — OpenAI GPT-4o
         Signals + XIMPAX capability match + closeness level
         → tailored 80–120 word LinkedIn message
```

## Input CSV — Minimal (3 columns)

| Column | Required | Notes |
|--------|----------|-------|
| `name` | ✅ | Full name |
| `known_function` | ✅ | e.g. "Head of Supply Chain" |
| `closeness_level` | ✅ | 1=Acquaintance, 2=Professional, 3=Close |
| `known_company` | Optional | Skip Serper lookup if already known |
| `company_situation` | Optional | Override Gemini summary for this contact |

---

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/ximpax-outreach-engine.git
cd ximpax-outreach-engine
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set API keys
```bash
cp .env.example .env
# Edit .env and fill in your keys
```

### 4a. Run the Streamlit UI
```bash
streamlit run app.py
```
Upload your CSV, watch per-contact progress, preview all messages, download Excel.

### 4b. Run headless (CLI)
```bash
export SERPER_API_KEY="..."
export GEMINI_API_KEY="..."
export OPENAI_API_KEY="..."
python run.py --input contacts_sample.csv
```

---

## Deploy on Streamlit Cloud (Recommended)

1. Push this repo to GitHub (private is fine)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → point to `app.py`
3. In **App Settings → Secrets**, paste:
```toml
SERPER_API_KEY = "your_serper_key"
GEMINI_API_KEY = "your_gemini_key"
OPENAI_API_KEY = "your_openai_key"
```
4. Deploy — you get a private URL only you can access

---

## Output Excel — 3 Sheets

| Sheet | Contents |
|-------|----------|
| **All Contacts** | Full enriched data + LinkedIn message per contact |
| **Needs Review** | Contacts with confidence < 50% on company lookup |
| **Stage1 Raw** | Raw Gemini output for audit trail |

---

## Situation Scoring

| Code | Label | XIMPAX Angle |
|------|-------|--------------|
| RC | Resource Constraints | Embedded experts, task-force staffing, day-one deployment |
| MP | Margin Pressure | Category management, Source-to-Pay, margin improvement |
| SG | Significant Growth | IBP/S&OP, demand planning, M&A integration |
| SCD | Supply Chain Disruption | Network resilience, nearshoring, make-vs-buy |

Only **CONFIRMED** and **LIKELY** signals feed the message.

---

## Customisation

- **Update XIMPAX positioning**: edit `config/ximpax_profile.txt` — every future message reflects it automatically
- **Swap the LLM**: change `MODEL = "gpt-4o"` in `engine/stage2_openai.py`
- **Adjust tone per closeness**: edit the `CLOSENESS` dict in `engine/stage2_openai.py`
- **Change Gemini pause**: edit `PAUSE = 15` in `engine/stage1_gemini.py`

---

## Project Structure

```
ximpax_outreach_engine/
├── app.py                  ← Streamlit web UI
├── run.py                  ← CLI runner
├── requirements.txt
├── .env.example            ← copy to .env, fill in keys
├── .gitignore
├── contacts_sample.csv
├── config/
│   └── ximpax_profile.txt  ← edit your positioning here
└── engine/
    ├── __init__.py
    ├── stage0_serper.py    ← company lookup (4-strategy cascade)
    ├── stage1_gemini.py    ← situation signal scan
    ├── stage2_openai.py    ← message generation + XIMPAX matching
    └── pipeline.py         ← orchestrates all 3 stages
```
