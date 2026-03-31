import time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 0.5

ROLE_AFFINITY = {
    "procurement":   ["MP", "RC", "SG", "SCD"],
    "sourcing":      ["MP", "SCD", "RC", "SG"],
    "category":      ["MP", "RC", "SG", "SCD"],
    "purchasing":    ["MP", "RC", "SCD", "SG"],
    "buyer":         ["MP", "SCD", "RC", "SG"],
    "planning":      ["SCD", "SG", "RC", "MP"],
    "supply":        ["SCD", "RC", "SG", "MP"],
    "logistics":     ["SCD", "MP", "RC", "SG"],
    "operations":    ["RC", "SCD", "SG", "MP"],
    "manufacturing": ["RC", "SCD", "MP", "SG"],
    "demand":        ["SCD", "SG", "MP", "RC"],
    "inventory":     ["SCD", "MP", "RC", "SG"],
    "s&op":          ["SG", "SCD", "RC", "MP"],
    "network":       ["SCD", "SG", "RC", "MP"],
    "transformation":["RC", "SG", "SCD", "MP"],
    "excellence":    ["RC", "MP", "SCD", "SG"],
    "director":      ["MP", "RC", "SG", "SCD"],
    "vp":            ["MP", "SG", "RC", "SCD"],
    "cpo":           ["MP", "RC", "SG", "SCD"],
    "coo":           ["RC", "MP", "SCD", "SG"],
    "head":          ["RC", "MP", "SG", "SCD"],
    "material":      ["SCD", "MP", "RC", "SG"],
    "metal":         ["MP", "SCD", "RC", "SG"],
    "indirect":      ["MP", "RC", "SG", "SCD"],
}

SIGNAL_ANGLES = {
    "RC":  "we bring in experienced people quickly to support the team without a long ramp-up",
    "MP":  "we have helped similar companies cut costs through better category management and supplier deals",
    "SG":  "we help build the procurement and planning structure needed to grow without losing control",
    "SCD": "we help reduce supply risk by rethinking sourcing strategies and building backup options",
}

CLOSENESS = {
    1: "Very close — write like a text to a good colleague. Casual, warm, straight to the point.",
    2: "Know each other professionally — friendly and direct, like a former colleague.",
    3: "Barely know each other — professional, respectful, no over-familiarity.",
}

MSG_SYSTEM = """You write short LinkedIn InMail messages for Sebastian Koczen, who runs XIMPAX — a small Swiss team of senior supply chain and procurement experts.

TONE AND STYLE — follow all without exception:
- Plain everyday language. No jargon, no complex words.
- Sound like a real person writing to a colleague — not a sales pitch.
- Go straight to the point. Reference something specific about the company situation.
- MAX 80 words. Count them.
- End with a simple, direct ask for a short meeting: e.g. "Would you be open to a quick call?" or "Could we find 20 minutes?"
- NEVER start with "I wanted to reach out", "I hope this finds you well" or similar.
- NEVER mention AI, automation, or that this was generated.
- NEVER call XIMPAX a consultancy or the team consultants.
- NEVER use: resilience, optimise, leverage, synergies, value proposition, stakeholders, holistic, landscape, solutions.
- One mention of XIMPAX max — just the name, no long description.
- LinkedIn InMail format — no subject line, no "Dear X", no sign-off.
- Write ONLY the message. Nothing else.

XIMPAX context (one sentence max in message):
{ximpax_profile}"""

NOTES_SYSTEM = """You write short positioning sentences for XIMPAX — a small Swiss team of senior supply chain and procurement experts.

Generate exactly 3 short sentences (one per line, numbered 1/2/3) that Sebastian can use to describe XIMPAX in outreach. Each should be a different angle:
1. Framing as an external taskforce — hands-on, embedded, not advisory
2. Framing as industry experts — deep functional knowledge, real operator experience
3. Framing around NOT being a consultancy — direct, honest, different from typical consulting firms

Rules:
- Max 20 words per sentence
- Plain language — no jargon
- Must NOT use: consultants, consulting, consultancy, solutions, leverage, stakeholders, resilience
- Each sentence should feel distinct — not variations of the same thing
- These are building blocks Sebastian picks from, not a paragraph
- Write ONLY the 3 numbered sentences. Nothing else."""


def _role_priority(function: str) -> list:
    fl = function.lower()
    for kw, p in ROLE_AFFINITY.items():
        if kw in fl:
            return p
    return ["MP", "RC", "SCD", "SG"]


def _signals_block(active: list, role_priority: list) -> str:
    if not active:
        return "No specific signals found. Base message on a realistic challenge for their role and industry."
    order  = {c: i for i, c in enumerate(role_priority)}
    ranked = sorted(active, key=lambda s: order.get(s["code"], 99))
    primary = ranked[0]
    lines = [
        f"LEAD WITH THIS (most relevant for their role):",
        f"  Signal: {primary['label']} ({primary['status']})",
        f"  Evidence: {primary['signal']}",
        f"  Angle: {SIGNAL_ANGLES.get(primary['code'], '')}",
        "",
        "Other signals (use only if space allows):",
    ]
    for s in ranked[1:]:
        lines.append(f"  • {s['label']} ({s['status']}): {s['signal']}")
    return "\n".join(lines)


def generate_message(name, company, function, closeness_level,
                     active_situations, company_summary,
                     ximpax_profile, gemini_api_key) -> str:
    client   = genai.Client(api_key=gemini_api_key)
    system   = MSG_SYSTEM.format(ximpax_profile=ximpax_profile)
    tone     = CLOSENESS.get(closeness_level, CLOSENESS[3])
    priority = _role_priority(function)
    signals  = _signals_block(active_situations, priority)

    prompt = f"""Write a LinkedIn InMail from Sebastian to:

Name: {name}
Title: {function}
Company: {company}
Tone: {tone}

What we know about {company}:
{company_summary or "No specific research — use what you know about this company and industry."}

{signals}

MAX 80 words. Plain language. End with meeting request. No jargon. No AI mention."""

    try:
        resp = client.models.generate_content(
            model=MODEL, contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=0.75))
        return resp.text.strip()
    except Exception as e:
        return f"[Error: {e}]"
    finally:
        time.sleep(PAUSE)


def generate_notes(company, function, gemini_api_key) -> str:
    """Generate 3 alternative XIMPAX positioning sentences for this context."""
    client = genai.Client(api_key=gemini_api_key)
    prompt = f"""Generate 3 short positioning sentences for XIMPAX for someone in this role:
Function: {function}
Company: {company}

Each sentence = one way Sebastian can describe XIMPAX.
Angle 1: External taskforce — hands-on, embedded, not advisory.
Angle 2: Industry experts — deep functional knowledge, real operator background.
Angle 3: NOT a consultancy — direct and honest contrast to typical consulting firms."""

    try:
        resp = client.models.generate_content(
            model=MODEL, contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=NOTES_SYSTEM, temperature=0.9))
        return resp.text.strip()
    except Exception as e:
        return f"[Notes error: {e}]"
    finally:
        time.sleep(PAUSE)
