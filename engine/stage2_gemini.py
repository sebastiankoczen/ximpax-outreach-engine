import time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 2

CLOSENESS_TONE = {
    "cold":         "The opening must reference a specific named public fact (programme name, number, announcement). Formal but direct. No familiarity.",
    "professional": "Slightly warmer. Reference shared professional context or a visible company challenge. Brief, collegial.",
    "regular":      "Skip formal introductions entirely. Be direct and personal. Assume they know who Sebastian is.",
}

SITUATION_NOTES_SYSTEM = (
    "You write situation-specific outreach proposals for Sebastian Koczen. "
    "These are 3 alternative options Sebastian can use for a LinkedIn InMail.\n"
    "Rules for each option:\n"
    "- Exactly 3 options, numbered 1. / 2. / 3.\n"
    "- Each references a DIFFERENT active signal (RC, MP, SG or SCD) from the research.\n"
    "- Each paragraph is 50-70 words. Specific, direct and professional.\n"
    "- Use plain, everyday language — like one senior colleague talking to another.\n"
    "- Reference real, specific evidence: named programmes, numbers, events, or divisions.\n"
    "- Show you understand what the situation means for someone in the contact\'s specific role.\n"
    "- Each MUST end with a simple, direct request for a brief meeting.\n"
    "- NEVER mention XIMPAX, AI, automation, consulting, consultancy, or consultants.\n"
    "- NEVER use: resilience, optimise, leverage, synergies, value proposition, holistic, solutions.\n"
    "- Write ONLY the 3 numbered options. Nothing else."
)

POSITIONING_SYSTEM = (
    "You write short positioning sentences for XIMPAX — a small Swiss team of senior supply chain "
    "and procurement experts. Generate exactly 3 short options (numbered 1. / 2. / 3.) that Sebastian "
    "can use to describe XIMPAX.\n"
    "Angle 1: External taskforce — hands-on, embedded, not advisory.\n"
    "Angle 2: Industry experts — deep functional knowledge, real operator experience.\n"
    "Angle 3: NOT a consultancy — direct contrast to typical consulting firms.\n"
    "Rules:\n"
    "- Max 20 words per option.\n"
    "- Plain language — no jargon.\n"
    "- NEVER use: consultants, consulting, consultancy, solutions, leverage, stakeholders, resilience, optimise.\n"
    "- Each option must feel distinct.\n"
    "- Write ONLY the 3 numbered options. Nothing else."
)


def _closeness_tag(closeness):
    c = str(closeness).lower()
    if "cold" in c or "never" in c:        return "cold"
    if "professional" in c or "once" in c: return "professional"
    return "regular"


def _call_with_retry(client, model, contents, config, retries=2, wait=30):
    """Retry on 429 rate-limit errors with a configurable wait."""
    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=config)
        except Exception as e:
            if "429" in str(e) and attempt < retries:
                time.sleep(wait)
                continue
            raise


def generate_situation_notes(company, function, active_situations,
                              gemini_api_key, closeness="") -> str:
    if not active_situations:
        return "No specific signals found — re-run Stage 1 or check API key."
    client    = genai.Client(api_key=gemini_api_key)
    tone_hint = CLOSENESS_TONE.get(_closeness_tag(closeness), CLOSENESS_TONE["cold"])
    sig_lines = "\n".join(
        "- " + s["label"] + " (" + s["status"] + ", score " + str(s["score"]) + "/10): " + s["signal"]
        for s in active_situations[:3]
    )
    prompt = (
        "Write 3 outreach proposals for Sebastian to:\n"
        "Contact: " + function + " at " + company + "\n"
        "Active company signals (use specific facts):\n" + sig_lines + "\n\n"
        "Tone instruction: " + tone_hint + "\n"
        "Each option references a DIFFERENT signal. End each with a meeting request. Plain language."
    )
    try:
        resp = _call_with_retry(
            client, MODEL, prompt,
            types.GenerateContentConfig(
                system_instruction=SITUATION_NOTES_SYSTEM,
                temperature=0.85))
        time.sleep(PAUSE)
        return resp.text.strip()
    except Exception as e:
        time.sleep(PAUSE)
        if "429" in str(e):
            return "Rate limit reached — please wait 60 seconds and try again."
        return "[Error: " + str(e) + "]"


def generate_positioning_notes(company, function, gemini_api_key, closeness="") -> str:
    client    = genai.Client(api_key=gemini_api_key)
    tone_hint = CLOSENESS_TONE.get(_closeness_tag(closeness), CLOSENESS_TONE["cold"])
    prompt    = (
        "Generate 3 positioning options for XIMPAX for a contact at " + company +
        " in the " + function + " function.\nTone: " + tone_hint
    )
    try:
        resp = _call_with_retry(
            client, MODEL, prompt,
            types.GenerateContentConfig(
                system_instruction=POSITIONING_SYSTEM,
                temperature=0.9))
        time.sleep(PAUSE)
        return resp.text.strip()
    except Exception as e:
        time.sleep(PAUSE)
        if "429" in str(e):
            return "Rate limit reached — please wait 60 seconds and try again."
        return "[Error: " + str(e) + "]"
