import time, re
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 0.5

CAPABILITIES = {
    "RC":  "We place experienced SC/procurement people directly inside teams — they hit the ground running, no handholding needed.",
    "MP":  "We run category reviews, supplier negotiations and spend analysis that deliver real savings, fast.",
    "SG":  "We help companies build the planning and procurement muscle to scale — S&OP design, network strategy, M&A integration.",
    "SCD": "We help redesign supply chains for resilience — nearshoring, alternative sourcing, make-vs-buy.",
}

# What each role actually cares about most — ordered by relevance
# Format: list of signal codes, highest priority first
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
    "operational":   ["RC", "SCD", "SG", "MP"],
    "manufacturing": ["RC", "SCD", "MP", "SG"],
    "demand":        ["SCD", "SG", "MP", "RC"],
    "inventory":     ["SCD", "MP", "RC", "SG"],
    "s&op":          ["SG", "SCD", "RC", "MP"],
    "ibp":           ["SG", "SCD", "RC", "MP"],
    "network":       ["SCD", "SG", "RC", "MP"],
    "transformation":["RC", "SG", "SCD", "MP"],
    "excellence":    ["RC", "MP", "SCD", "SG"],
    "director":      ["MP", "RC", "SG", "SCD"],
    "vp":            ["MP", "SG", "RC", "SCD"],
    "cpo":           ["MP", "RC", "SG", "SCD"],
    "coo":           ["RC", "MP", "SCD", "SG"],
    "head":          ["RC", "MP", "SG", "SCD"],
}

# Human label + what angle XIMPAX takes per signal
SIGNAL_CONTEXT = {
    "RC":  ("resource constraints or capability gaps",
            "We place experienced SC/procurement people directly inside teams — no ramp-up."),
    "MP":  ("margin pressure or cost reduction",
            "We run category reviews, negotiations and spend programmes that deliver real savings fast."),
    "SG":  ("growth or transformation",
            "We help build the planning and procurement muscle to scale — S&OP, network, M&A integration."),
    "SCD": ("supply chain disruption or sourcing risk",
            "We help redesign for resilience — nearshoring, alternative sourcing, make-vs-buy."),
}

CLOSENESS = {
    1: ("Close", "Write like you're texting a friend you respect. Skip all formalities. Short sentences."),
    2: ("Professional", "Collegial. Like catching up with a former colleague. Warm but not overfamiliar."),
    3: ("Acquaintance", "You barely know this person. Be human and credible, not salesy. One idea, one question."),
}

SYSTEM_INSTRUCTION = """You write short LinkedIn messages for Sebastian Koczen, founder of XIMPAX, a small Swiss supply chain and procurement consultancy.

RULES — every single one applies:
- MAX 80 words. Hard limit.
- Sound like a real person, not a consultant writing a brochure
- NO buzzwords: no "resilience", "optimise", "leverage", "solutions", "differentiator", "value proposition", "stakeholders", "landscape"
- NO openers like "I wanted to reach out", "I hope this finds you well", "observing the current..."
- Start with something SPECIFIC to their company or a real challenge for their exact function
- Lead with the PRIMARY SIGNAL for their role — this is the one they will personally feel, not just their company
- XIMPAX gets ONE mention, max. One short sentence. No description of what we do beyond that.
- End with a single low-pressure question: "Worth a quick chat?" / "Happy to share what we're seeing." / "Keen to hear your take."
- Match tone exactly to closeness level
- Write ONLY the message. Nothing else.

XIMPAX context (use sparingly):
{ximpax_profile}"""


def _infer_role_priorities(function: str) -> list:
    """Return signal priority order based on function keywords."""
    func_lower = function.lower()
    for keyword, priority in ROLE_AFFINITY.items():
        if keyword in func_lower:
            return priority
    return ["MP", "RC", "SCD", "SG"]  # default


def _build_situation_block(active: list, role_priority: list) -> tuple:
    """
    Returns (primary_signal_text, full_block_text).
    Primary signal = highest-priority signal that is CONFIRMED or LIKELY for this role.
    """
    if not active:
        return None, "No signals found — base message on what is most relevant for their exact role."

    # Sort active signals by role priority
    code_order = {code: i for i, code in enumerate(role_priority)}
    sorted_active = sorted(active, key=lambda s: code_order.get(s["code"], 99))

    primary = sorted_active[0]
    ctx = SIGNAL_CONTEXT.get(primary["code"], ("challenges", ""))
    primary_text = (
        f"PRIMARY SIGNAL for this role: {primary['label']} ({primary['status']})\n"
        f"Evidence: {primary['signal']}\n"
        f"Frame as: {ctx[0]}\n"
        f"XIMPAX angle if mentioned: {ctx[1]}"
    )

    all_lines = []
    for s in sorted_active:
        c = SIGNAL_CONTEXT.get(s["code"], ("", ""))
        all_lines.append(f"• {s['label']} ({s['status']}, score {s['score']}): {s['signal']}")
    full_block = primary_text + "\n\nALL ACTIVE SIGNALS:\n" + "\n".join(all_lines)

    return primary, full_block


def generate_message(name, company, function, closeness_level,
                     active_situations, company_summary,
                     ximpax_profile, gemini_api_key) -> str:
    client = genai.Client(api_key=gemini_api_key)
    cl_label, cl_tone = CLOSENESS.get(closeness_level, CLOSENESS[3])
    system = SYSTEM_INSTRUCTION.format(ximpax_profile=ximpax_profile)

    role_priority = _infer_role_priorities(function)
    primary_signal, situation_block = _build_situation_block(active_situations, role_priority)

    prompt = f"""Write a LinkedIn message from Sebastian to:

Name: {name}
Title: {function}
Company: {company}
Closeness: {closeness_level} ({cl_label}) — {cl_tone}

Role signal priority for this function: {" > ".join(role_priority)}
(Lead the message with the highest-priority signal that has evidence.)

Company research summary:
{company_summary if company_summary else "No research — use what you know about this company/industry."}

{situation_block}

Remember: MAX 80 words. Real language. No buzzwords. One XIMPAX mention max. Specific to {name}'s role as {function}."""

    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.8,
            )
        )
        return resp.text.strip()
    except Exception as e:
        return f"[Error: {e}]"
    finally:
        time.sleep(PAUSE)
