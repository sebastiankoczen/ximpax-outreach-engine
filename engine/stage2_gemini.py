import time
import google.generativeai as genai

MODEL = "gemini-2.0-flash"
PAUSE = 0.5

CAPABILITIES = {
    "RC":  "Embedded experts, task-force staffing, day-one deployment — senior SC/procurement talent that integrates without onboarding overhead.",
    "MP":  "Category management, Source-to-Pay optimisation, indirect spend programmes — delivering measurable savings within the engagement.",
    "SG":  "IBP/S&OP design, demand planning, network design, M&A integration — building operating models that sustain growth.",
    "SCD": "Network resilience, nearshoring strategy, make-vs-buy analysis, logistics re-routing — SC design built for volatility.",
}

CLOSENESS = {
    1: ("Acquaintance",      "Professional and respectful. Brief context reminder. Formal but warm."),
    2: ("Professional",      "Collegial and direct. Reference shared professional ground. Moderate warmth."),
    3: ("Close Contact",     "Warm, direct, candid — skip formal pleasantries, they know you."),
}

SYSTEM_INSTRUCTION = """You are a senior business development writer for XIMPAX, a boutique supply chain and procurement consultancy in Switzerland.

Rules for the LinkedIn message:
- 80-120 words maximum
- Do NOT start with "Hi [Name]," — lead with a relevant insight or observation
- Reference specific company situation signals
- Position XIMPAX naturally — never pushy
- End with ONE soft CTA (e.g. "Would a brief call make sense?")
- Match tone precisely to closeness level
- Sound human and specific — never templated
- Write ONLY the message body — no labels, no subject line"""


def _situation_block(active: list) -> str:
    if not active:
        return "No strong signals — use general SC/procurement angle."
    lines = []
    for s in active:
        lines.append(
            f"• {s['label']} ({s['status']}, score {s['score']}): {s['signal']}\n"
            f"  XIMPAX angle: {CAPABILITIES.get(s['code'], '')}"
        )
    return "\n".join(lines)


def generate_message(name, company, function, closeness_level,
                     active_situations, company_summary,
                     ximpax_profile, gemini_api_key) -> str:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=SYSTEM_INSTRUCTION + f"\n\nXIMPAX PROFILE:\n{ximpax_profile}",
    )
    cl_label, cl_tone = CLOSENESS.get(closeness_level, CLOSENESS[1])
    prompt = f"""Contact: {name} | {function} @ {company}
Closeness: {closeness_level} — {cl_label} | Tone: {cl_tone}

Company situation (from research):
{company_summary}

Active signals:
{_situation_block(active_situations)}

Write only the message body."""

    try:
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        return f"[Error generating message: {e}]"
    finally:
        time.sleep(PAUSE)
