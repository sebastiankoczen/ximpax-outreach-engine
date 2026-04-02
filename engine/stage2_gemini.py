import time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 0.5

ROLE_AFFINITY = {
    "procurement":    ["MP", "RC", "SG", "SCD"],
    "sourcing":       ["MP", "SCD", "RC", "SG"],
    "category":       ["MP", "RC", "SG", "SCD"],
    "purchasing":     ["MP", "RC", "SCD", "SG"],
    "buyer":          ["MP", "SCD", "RC", "SG"],
    "planning":       ["SCD", "SG", "RC", "MP"],
    "supply":         ["SCD", "RC", "SG", "MP"],
    "logistics":      ["SCD", "MP", "RC", "SG"],
    "operations":     ["RC", "SCD", "SG", "MP"],
    "manufacturing":  ["RC", "SCD", "MP", "SG"],
    "demand":         ["SCD", "SG", "MP", "RC"],
    "inventory":      ["SCD", "MP", "RC", "SG"],
    "s&op":           ["SG", "SCD", "RC", "MP"],
    "network":        ["SCD", "SG", "RC", "MP"],
    "transformation": ["RC", "SG", "SCD", "MP"],
    "excellence":     ["RC", "MP", "SCD", "SG"],
    "director":       ["MP", "RC", "SG", "SCD"],
    "vp":             ["MP", "SG", "RC", "SCD"],
    "cpo":            ["MP", "RC", "SG", "SCD"],
    "coo":            ["RC", "MP", "SCD", "SG"],
    "head":           ["RC", "MP", "SG", "SCD"],
    "material":       ["SCD", "MP", "RC", "SG"],
    "metal":          ["MP", "SCD", "RC", "SG"],
    "indirect":       ["MP", "RC", "SG", "SCD"],
}

SIGNAL_ANGLES = {
    "RC":  "we bring in experienced people quickly to cover gaps without a long ramp-up",
    "MP":  "we have helped similar companies cut costs through sharper category management and supplier negotiations",
    "SG":  "we help build the procurement and planning structure needed to grow without losing control",
    "SCD": "we help reduce supply risk by rethinking sourcing strategies and building backup options",
}

CLOSENESS = {
    1: "Very close - write like a text to a good colleague. Casual, warm, straight to the point.",
    2: "Know each other professionally - friendly and direct, like a former colleague.",
    3: "Barely know each other - professional, respectful, no over-familiarity.",
}

MSG_SYSTEM = """You write short LinkedIn InMail messages for Sebastian Koczen.

THE MESSAGE IS ONLY A HOOK - it must:
1. Reference something specific and real about the company situation (a named programme, a number, a known event)
2. Show you understand what that means for someone in their role
3. End with a simple, direct meeting request

THAT IS ALL. The message contains NO description of XIMPAX, NO company pitch, NO services listed.
Sebastian will add his own positioning separately after sending.

STRICT RULES:
- MAX 60 words. Count them.
- Plain everyday language - like a smart colleague talking to another
- NEVER mention XIMPAX, consultancy, consultants, experts, or any company description
- NEVER start with "I wanted to reach out", "I hope this finds you well", "I noticed your role"
- NEVER use: resilience, optimise, leverage, synergies, stakeholders, holistic, landscape, solutions
- NEVER mention AI or automation
- No subject line, no "Dear X", no sign-off
- Write ONLY the message. Nothing else."""

POSITIONING_SYSTEM = """You write short positioning sentences for XIMPAX - a small Swiss team of senior supply chain and procurement experts.

Generate exactly 3 short sentences (numbered 1/2/3) that Sebastian can use to describe XIMPAX.
Angle 1: External taskforce - hands-on, embedded, not advisory.
Angle 2: Industry experts - deep functional knowledge, real operator experience.
Angle 3: NOT a consultancy - direct contrast to typical consulting firms.

Rules:
- Max 20 words per sentence
- Plain language - no jargon
- NEVER use: consultants, consulting, consultancy, solutions, leverage, stakeholders, resilience
- Each sentence must feel distinct
- Write ONLY the 3 numbered sentences. Nothing else."""

SITUATION_NOTES_SYSTEM = """You write situation-specific add-on notes for LinkedIn InMail outreach from Sebastian Koczen at XIMPAX.

These are 3 optional paragraphs - one per active company signal - that Sebastian can choose to append to his main message.

Rules:
- Exactly 3 paragraphs, numbered 1/2/3
- Each references a DIFFERENT active signal (RC, MP, SG or SCD)
- Each paragraph is 60-80 words. Specific, personal and useful.
- Plain, direct language - like one senior colleague talking to another
- Each must reference real, specific evidence: named programmes, numbers, events, divisions
- Write as a natural, warm observation - like a knowledgeable colleague sharing what they noticed
- Show understanding of what the situation means for someone in the contact's specific role
- NEVER mention AI, automation, consulting, consultancy, consultants, XIMPAX
- NEVER use: resilience, optimise, leverage, synergies, value proposition, holistic, landscape
- Write ONLY the 3 numbered paragraphs. Nothing else."""


def _role_priority(function: str) -> list:
    fl = function.lower()
    for kw, p in ROLE_AFFINITY.items():
        if kw in fl:
            return p
    return ["MP", "RC", "SCD", "SG"]


def _signals_block(active: list, role_priority: list) -> str:
    if not active:
        return "No specific signals confirmed. Write a short, direct message based on a realistic challenge typical for their role and industry. Keep it credible - do not invent specifics."
    order = {c: i for i, c in enumerate(role_priority)}
    ranked = sorted(active, key=lambda s: order.get(s["code"], 99))
    primary = ranked[0]
    lines = [
        "LEAD WITH THIS signal (most relevant for their role):",
        f"  Signal type: {primary['label']} ({primary['status']})",
        f"  Evidence: {primary['signal']}",
        "",
        "Other signals (do NOT mention in message - use as context only):",
    ]
    for s in ranked[1:]:
        lines.append(f"  - {s['label']}: {s['signal'][:120]}")
    return "\n".join(lines)


def generate_message(name, company, function, closeness_level, active_situations, company_summary, ximpax_profile, gemini_api_key) -> str:
    client = genai.Client(api_key=gemini_api_key)
    tone = CLOSENESS.get(closeness_level, CLOSENESS[3])
    priority = _role_priority(function)
    signals = _signals_block(active_situations, priority)
    prompt = f"""Write a LinkedIn InMail hook from Sebastian to:
Name: {name}
Title: {function}
Company: {company}
Tone: {tone}

Company context:
{company_summary or "No specific research available."}

{signals}

REMEMBER: MAX 60 words. NO mention of XIMPAX or any company. Pure hook - specific situation reference + meeting ask."""
    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=MSG_SYSTEM,
                temperature=0.75))
        return resp.text.strip()
    except Exception as e:
        return f"[Error: {e}]"
    finally:
        time.sleep(PAUSE)


def generate_positioning_notes(company, function, gemini_api_key) -> str:
    """3 alternative XIMPAX positioning sentences."""
    client = genai.Client(api_key=gemini_api_key)
    prompt = f"""Generate 3 short positioning sentences for XIMPAX for someone in this role:
Function: {function}
Company: {company}
Angle 1: External taskforce - hands-on, embedded, not advisory.
Angle 2: Industry experts - deep functional knowledge, real operator background.
Angle 3: NOT a consultancy - direct and honest contrast to typical consulting firms."""
    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=POSITIONING_SYSTEM,
                temperature=0.9))
        return resp.text.strip()
    except Exception as e:
        return f"[Error: {e}]"
    finally:
        time.sleep(PAUSE)


def generate_situation_notes(company, function, active_situations, gemini_api_key) -> str:
    """3 situation-specific add-on paragraphs - one per active signal."""
    if not active_situations:
        return ""
    client = genai.Client(api_key=gemini_api_key)
    signal_lines = "\n".join(
        f"- {s['label']} ({s['status']}): {s['signal']}"
        for s in active_situations[:3]
    )
    prompt = f"""Write 3 situation-specific add-on paragraphs for a LinkedIn InMail from Sebastian.

Contact: {function} at {company}

Active company signals (use the specific facts - named programmes, numbers, events):
{signal_lines}

Each paragraph references a DIFFERENT signal above.
Each is 60-80 words - specific, warm, like a knowledgeable colleague sharing a relevant observation.
Reference the actual evidence by name. Show you understand what it means for someone in their role.
Plain language. No jargon. No mention of XIMPAX or consulting."""
    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SITUATION_NOTES_SYSTEM,
                temperature=0.9))
        return resp.text.strip()
    except Exception as e:
        return f"[Error: {e}]"
    finally:
        time.sleep(PAUSE)
