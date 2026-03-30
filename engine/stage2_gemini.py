import time
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

# 1 = closest contact, 3 = barely know them
CLOSENESS = {
    1: ("Close", "Write like you're texting a friend you respect. Skip all formalities. Get straight to it. Short sentences."),
    2: ("Professional", "Collegial. Like catching up with a former colleague. Warm but not overfamiliar. Direct."),
    3: ("Acquaintance", "You barely know this person. Be human and credible, not salesy. No buzzwords. No corporate speak. Don't over-explain XIMPAX. One simple idea, one question."),
}

SYSTEM_INSTRUCTION = """You write short LinkedIn messages for Sebastian Koczen, founder of XIMPAX, a small Swiss consultancy that helps companies with supply chain and procurement.

YOUR WRITING RULES — follow every single one:
- MAX 80 words. Count them.
- Sound like a real person, not a consultant writing a brochure
- NO buzzwords: no "resilience", "optimise", "leverage", "solutions", "differentiator", "value proposition", "stakeholders"
- NO phrases like "I wanted to reach out", "I hope this finds you well", "observing the current landscape"
- Start with something specific and real about THEIR company or role — not a generic industry observation
- XIMPAX gets ONE mention, max. Don't describe what we do in detail — one short sentence is enough
- End with a single low-pressure question like "Worth a quick chat?" or "Keen to hear your take."
- Match tone exactly to closeness level — a level 3 must feel like a cold message from someone credible, not a sales pitch
- Write ONLY the message. No labels, no subject line, nothing else.

XIMPAX context (use sparingly):
{ximpax_profile}"""


def _situation_block(active: list) -> str:
    if not active:
        return "No signals found — base the message on what is likely relevant for their role and industry."
    lines = []
    for s in active:
        lines.append(f"• {s['label']} ({s['status']}): {s['signal']}\n  Use this angle: {CAPABILITIES.get(s['code'], '')}")
    return "\n".join(lines)


def generate_message(name, company, function, closeness_level,
                     active_situations, company_summary,
                     ximpax_profile, gemini_api_key) -> str:
    client = genai.Client(api_key=gemini_api_key)
    cl_label, cl_tone = CLOSENESS.get(closeness_level, CLOSENESS[3])
    system = SYSTEM_INSTRUCTION.format(ximpax_profile=ximpax_profile)

    prompt = f"""Write a LinkedIn message from Sebastian to:

Name: {name}
Title: {function}
Company: {company}
Closeness level: {closeness_level} ({cl_label}) — {cl_tone}

What we know about {company}:
{company_summary if company_summary else "No research available — use what you know about the company/industry."}

Signals to potentially reference:
{_situation_block(active_situations)}

Remember: MAX 80 words. Real and human. No buzzwords. One mention of XIMPAX max."""

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
