import time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 0.5

ROLE_AFFINITY = {
    "procurement": ["MP", "RC", "SG", "SCD"], "sourcing":  ["MP", "SCD", "RC", "SG"],
    "category":    ["MP", "RC", "SG", "SCD"], "purchasing": ["MP", "RC", "SCD", "SG"],
    "buyer":       ["MP", "SCD", "RC", "SG"], "planning":  ["SCD", "SG", "RC", "MP"],
    "supply":      ["SCD", "RC", "SG", "MP"], "logistics": ["SCD", "MP", "RC", "SG"],
    "operations":  ["RC", "SCD", "SG", "MP"], "manufacturing": ["RC", "SCD", "MP", "SG"],
    "demand":      ["SCD", "SG", "MP", "RC"], "inventory": ["SCD", "MP", "RC", "SG"],
    "director":    ["MP", "RC", "SG", "SCD"], "vp":        ["MP", "SG", "RC", "SCD"],
    "cpo":         ["MP", "RC", "SG", "SCD"], "coo":       ["RC", "MP", "SCD", "SG"],
    "head":        ["RC", "MP", "SG", "SCD"], "material":  ["SCD", "MP", "RC", "SG"],
    "indirect":    ["MP", "RC", "SG", "SCD"],
}

CLOSENESS_TONE = {
    "cold":         "The opening must reference a specific named public fact (programme name, number, announcement). Formal but direct. No familiarity.",
    "professional": "Slightly warmer. Reference shared professional context or a visible company challenge. Brief, collegial.",
    "regular":      "Skip formal introductions entirely. Be direct and personal. Assume they know who Sebastian is.",
}

SITUATION_NOTES_SYSTEM = """You write situation-specific outreach proposals for Sebastian Koczen. These are 3 alternative options Sebastian can use for a LinkedIn InMail.
Rules for each option:
- Exactly 3 options, numbered 1. / 2. / 3.
- Each references a DIFFERENT active signal (RC, MP, SG or SCD) from the research.
- Each paragraph is 50-70 words. Specific, direct and professional.
- Use plain, everyday language — like one senior colleague talking to another.
- Reference real, specific evidence from the research: named programmes, numbers, events, or divisions.
- Show you understand what the situation means for someone in the contact's specific role.
- Each MUST end with a simple, direct request for a brief meeting (e.g., "Are you free for a short call next week?").
- NEVER mention XIMPAX, AI, automation, consulting, consultancy, or consultants.
- NEVER use: resilience, optimise, leverage, synergies, value proposition, holistic, landscape, solutions.
- Write ONLY the 3 numbered options. Nothing else."""

POSITIONING_SYSTEM = """You write short positioning sentences for XIMPAX — a small Swiss team of senior supply chain and procurement experts. Generate exactly 3 short options (numbered 1. / 2. / 3.) that Sebastian can use to describe XIMPAX.
Angle 1: External taskforce — hands-on, embedded, not advisory.
Angle 2: Industry experts — deep functional knowledge, real operator experience.
Angle 3: NOT a consultancy — direct contrast to typical consulting firms.
Rules:
- Max 20 words per option.
- Plain language — no jargon.
- NEVER use: consultants, consulting, consultancy, solutions, leverage, stakeholders, resilience, optimise.
- Each option must feel distinct.
- Write ONLY the 3 numbered options. Nothing else."""


def _closeness_tag(closeness: str) -> str:
    c = closeness.lower()
    if "cold" in c or "never" in c:      return "cold"
    if "professional" in c or "once" in c: return "professional"
    return "regular"


def generate_situation_notes(company, function, active_situations,
                              gemini_api_key, closeness="") -> str:
    if not active_situations:
        return "No specific signals found — re-run Stage 1 or check API key."
    client     = genai.Client(api_key=gemini_api_key)
    tone_hint  = CLOSENESS_TONE.get(_closeness_tag(closeness), CLOSENESS_TONE["cold"])
    sig_lines  = "\n".join(
        f"- {s['label']} ({s['status']}, score {s['score']}/10): {s['signal']}"
        for s in active_situations[:3]
    )
    prompt = (
        f"Write 3 outreach proposals for Sebastian to:\n"
        f"Contact: {function} at {company}\n"
        f"Active company signals (use specific facts):\n{sig_lines}\n\n"
        f"Tone instruction: {tone_hint}\n"
        f"Each option references a DIFFERENT signal. End each with a meeting request. Plain language."
    )
    try:
        resp = client.models.generate_content(
            model=MODEL, contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SITUATION_NOTES_SYSTEM, temperature=0.85))
        return resp.text.strip()
    except Exception as e:
        return f"[Error: {e}]"
    finally:
        time.sleep(PAUSE)


def generate_positioning_notes(company, function, gemini_api_key, closeness="") -> str:
    client    = genai.Client(api_key=gemini_api_key)
    tone_hint = CLOSENESS_TONE.get(_closeness_tag(closeness), CLOSENESS_TONE["cold"])
    prompt    = (
        f"Generate 3 positioning options for XIMPAX for a contact at {company} "
        f"in the {function} function.\nTone: {tone_hint}"
    )
    try:
        resp = client.models.generate_content(
            model=MODEL, contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=POSITIONING_SYSTEM, temperature=0.9))
        return resp.text.strip()
    except Exception as e:
        return f"[Error: {e}]"
    finally:
        time.sleep(PAUSE)
