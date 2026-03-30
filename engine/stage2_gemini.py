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

# Scale: 1 = closest (warm/direct), 3 = least known (formal/careful)
CLOSENESS = {
    1: ("Close Contact",      "Warm, direct, candid — skip formal pleasantries, they know you well."),
    2: ("Professional",       "Collegial and direct. Reference shared professional ground. Moderate warmth."),
    3: ("Acquaintance",       "Professional and respectful. Be thoughtful — they barely know you. No familiarity. Formal but human."),
}

SYSTEM_INSTRUCTION = """You are a senior business development writer for XIMPAX, a boutique supply chain and procurement consultancy in Switzerland.

Rules for the LinkedIn message:
- 80-120 words maximum
- Do NOT start with "Hi [Name]," — lead with a relevant business insight or observation about their company
- Reference specific company situation signals if available
- Position XIMPAX naturally — never pushy, never salesy
- End with ONE soft CTA (e.g. "Would a brief call make sense?" or "Happy to share what we're seeing if useful.")
- Match tone precisely to the closeness level — a level 3 (acquaintance) must feel measured and credible, not overfamiliar
- Sound human and specific — never templated or generic
- Write ONLY the message body — no subject line, no labels, no "Message:" prefix"""


def _situation_block(active: list) -> str:
    if not active:
        return "No strong signals found — use a general SC/procurement observation relevant to their industry."
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
    cl_label, cl_tone = CLOSENESS.get(closeness_level, CLOSENESS[3])
    prompt = f"""Contact: {name} | {function} @ {company}
Closeness: {closeness_level} — {cl_label}
Tone guidance: {cl_tone}

Company situation (from research):
{company_summary if company_summary else "No research data — use general industry angle."}

Active signals to reference:
{_situation_block(active_situations)}

Write only the message body. Be specific to this person and company."""

    try:
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        return f"[Error generating message: {e}]"
    finally:
        time.sleep(PAUSE)
