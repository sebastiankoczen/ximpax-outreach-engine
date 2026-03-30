import time, re
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 0.5

CAPABILITIES = {
    "RC":  "We place experienced SC/procurement people directly inside teams — no ramp-up, no lengthy briefings.",
    "MP":  "We run category reviews, supplier negotiations and spend programmes that deliver real savings fast.",
    "SG":  "We help build the planning and procurement muscle to scale — S&OP design, network strategy, M&A integration.",
    "SCD": "We help redesign for resilience — nearshoring, alternative sourcing, make-vs-buy.",
}

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
    "material":      ["SCD", "MP", "RC", "SG"],
    "metal":         ["MP", "SCD", "RC", "SG"],
    "indirect":      ["MP", "RC", "SG", "SCD"],
}

SIGNAL_CONTEXT = {
    "RC":  ("resource constraints or capability gaps",
            "We place experienced SC/procurement experts directly inside teams — no ramp-up needed."),
    "MP":  ("margin pressure or cost reduction",
            "We run category reviews, supplier negotiations and spend programmes that deliver real savings fast."),
    "SG":  ("growth or transformation",
            "We help build the procurement and planning muscle to scale — S&OP, network, M&A integration."),
    "SCD": ("supply chain disruption or sourcing risk",
            "We help redesign for resilience — nearshoring, alternative sourcing, make-vs-buy."),
}

CLOSENESS = {
    1: ("Close", "Write like you're texting a close colleague. Skip all formalities. Short, direct sentences."),
    2: ("Professional", "Collegial. Like catching up with a former colleague. Warm but not overfamiliar. Direct."),
    3: ("Acquaintance", "You barely know this person. Be credible and human, not salesy. One clear idea, one question."),
}

SYSTEM_INSTRUCTION = """You write short LinkedIn messages for Sebastian Koczen, co-founder of XIMPAX.

XIMPAX is a small Swiss firm of senior supply chain and procurement experts — NOT a consultancy. Never call XIMPAX a "consultancy" or call the team "consultants". Use words like: experts, practitioners, industry experts, external expertise, experienced practitioners, or simply "we".

RULES — all apply without exception:
- MAX 80 words. Hard limit. Count them.
- Sound like a real person texting, not a marketing email
- BANNED words: "consultancy", "consultant", "consulting", "resilience", "optimise", "leverage", "solutions", "differentiator", "value proposition", "stakeholders", "landscape", "holistic", "synergy"
- BANNED openers: "I wanted to reach out", "I hope this finds you well", "observing the current...", "In today's..."
- Start with something SPECIFIC to this person's company or a real challenge for their exact function
- Lead with the PRIMARY SIGNAL for their role — the thing they personally feel, not just company news
- XIMPAX gets ONE mention, max. One short sentence. Do not explain what XIMPAX does in detail.
- End with a single low-pressure question: "Worth a quick chat?" / "Happy to share what we're seeing." / "Keen to hear your take."
- NO generic phrases about industry trends unless tied to a specific, real signal
- Match tone exactly to closeness level
- Write ONLY the message body. Nothing else.

XIMPAX context (use sparingly — one sentence max in message):
{ximpax_profile}"""


def _infer_role_priorities(function: str) -> list:
    func_lower = function.lower()
    for keyword, priority in ROLE_AFFINITY.items():
        if keyword in func_lower:
            return priority
    return ["MP", "RC", "SCD", "SG"]


def _build_situation_block(active: list, role_priority: list) -> str:
    if not active:
        return "No signals found — base message on what is most relevant for their exact role and industry."
    code_order = {code: i for i, code in enumerate(role_priority)}
    sorted_active = sorted(active, key=lambda s: code_order.get(s["code"], 99))
    primary = sorted_active[0]
    ctx = SIGNAL_CONTEXT.get(primary["code"], ("challenges", ""))

    block = (
        f"PRIMARY SIGNAL for this role: {primary['label']} ({primary['status']}\n"
        f"Evidence: {primary['signal']}\n"
        f"Frame as: {ctx[0]}\n"
        f"XIMPAX angle (ONE sentence only if used): {ctx[1]}\n\n"
        "ALL ACTIVE SIGNALS:\n" +
        "\n".join(f"• {s['label']} ({s['status']}, score {s['score']}): {s['signal']}"
                   for s in sorted_active)
    )
    return block


def generate_message(name, company, function, closeness_level,
                     active_situations, company_summary,
                     ximpax_profile, gemini_api_key) -> str:
    client = genai.Client(api_key=gemini_api_key)
    cl_label, cl_tone = CLOSENESS.get(closeness_level, CLOSENESS[3])
    system = SYSTEM_INSTRUCTION.format(ximpax_profile=ximpax_profile)
    role_priority = _infer_role_priorities(function)
    situation_block = _build_situation_block(active_situations, role_priority)

    prompt = f"""Write a LinkedIn message from Sebastian to:

Name: {name}
Title: {function}
Company: {company}
Closeness: {closeness_level} ({cl_label}) — {cl_tone}
Role signal priority: {" > ".join(role_priority)}

Company research summary:
{company_summary if company_summary else "No research data — use what you know about this company/industry."}

{situation_block}

MAX 80 words. Real language. No buzzwords. Never say consultancy or consultant. One XIMPAX mention max. Specific to {name}'s role."""

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
