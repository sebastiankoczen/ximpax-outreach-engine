import time
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"
PAUSE = 2

ROLE_AFFINITY = {
    "procurement": ["MP", "RC", "SG", "SCD"],
    "sourcing": ["MP", "SCD", "RC", "SG"],
    "category": ["MP", "RC", "SG", "SCD"],
    "purchasing": ["MP", "RC", "SCD", "SG"],
    "buyer": ["MP", "SCD", "RC", "SG"],
    "planning": ["SCD", "SG", "RC", "MP"],
    "supply": ["SCD", "RC", "SG", "MP"],
    "logistics": ["SCD", "MP", "RC", "SG"],
    "operations": ["RC", "SCD", "SG", "MP"],
    "manufacturing": ["RC", "SCD", "MP", "SG"],
    "demand": ["SCD", "SG", "MP", "RC"],
    "inventory": ["SCD", "MP", "RC", "SG"],
    "s&op": ["SG", "SCD", "RC", "MP"],
    "network": ["SCD", "SG", "RC", "MP"],
    "transformation": ["RC", "SG", "SCD", "MP"],
    "excellence": ["RC", "MP", "SCD", "SG"],
    "director": ["MP", "RC", "SG", "SCD"],
    "vp": ["MP", "SG", "RC", "SCD"],
    "cpo": ["MP", "RC", "SG", "SCD"],
    "coo": ["RC", "MP", "SCD", "SG"],
    "head": ["RC", "MP", "SG", "SCD"],
    "material": ["SCD", "MP", "RC", "SG"],
    "metal": ["MP", "SCD", "RC", "SG"],
    "indirect": ["MP", "RC", "SG", "SCD"],
}

SITUATION_NOTES_SYSTEM = """You write situation-specific outreach proposals for Sebastian Koczen. These are 3 alternative options Sebastian can use for a LinkedIn InMail.

STRICT FORMAT — output exactly this structure, nothing else:
1. [option text here]

2. [option text here]

3. [option text here]

Rules for each option:
- Exactly 3 options, numbered 1. / 2. / 3.
- Each references a DIFFERENT active signal (RC, MP, SG or SCD) from the research.
- Tailor to the function: Procurement reacts to margin pressure; Planning/Supply Chain reacts to disruption.
- Each paragraph is 50-70 words. Specific, direct and professional.
- Open DIRECTLY with the named fact — no soft introductions, no "I noticed", no "it seems".
- Use plain, everyday language — like one senior colleague talking to another.
- Reference real, specific evidence: named programmes, numbers, events, or divisions.
- Show you understand what the situation means for someone in the contact's specific role.
- Each MUST end with a simple, direct request for a brief meeting.
- NEVER mention XIMPAX, AI, automation, consulting, consultancy, or consultants.
- NEVER use: resilience, optimise, leverage, synergies, value proposition, holistic, solutions.
- NEVER use hedging phrases: "it seems", "I imagine", "I would assume", "presumably", "likely", "perhaps", "I noticed".
- Write ONLY the 3 numbered options. No headers, no commentary, nothing else."""

POSITIONING_SYSTEM = """You write short positioning sentences for XIMPAX — a small Swiss team of senior supply chain and procurement experts.
Generate exactly 3 short options (numbered 1. / 2. / 3.) that Sebastian can use to describe XIMPAX.
Angle 1: External taskforce — hands-on, embedded, not advisory.
Angle 2: Industry experts — deep functional knowledge, real operator experience.
Angle 3: NOT a consultancy — direct contrast to typical consulting firms."""


def _call_with_retry(client, model, contents, config, retries=2, wait=30):
    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            if "429" in str(e) and attempt < retries:
                time.sleep(wait)
                continue
            raise


def generate_situation_notes(company, function, active_situations, gemini_api_key) -> str:
    if not active_situations:
        return "No specific signals found - re-run Stage 1 or check research data."
    client = genai.Client(api_key=gemini_api_key)

    sig_lines = ""
    for s in active_situations[:3]:
        sig_lines += f"- {s['label']} ({s['status']}, score {s['score']}/10): {s['signal']}" + chr(10)

    prompt = f"""Write exactly 3 outreach options for Sebastian Koczen to send to: {function} at {company}

Active signals from research — cite specific facts directly:
{sig_lines}
Format — output ONLY this, no other text:
1. [50-70 word message opening directly with a named fact, ending with a meeting request]

2. [50-70 word message on a DIFFERENT signal, opening directly with a named fact, ending with a meeting request]

3. [50-70 word message on a DIFFERENT signal, opening directly with a named fact, ending with a meeting request]

Do NOT use: "I noticed", "it seems", "I imagine", "I would assume", "presumably". Open cold with the fact."""

    try:
        resp = _call_with_retry(
            client, MODEL, prompt,
            types.GenerateContentConfig(system_instruction=SITUATION_NOTES_SYSTEM, temperature=0.7)
        )
        time.sleep(PAUSE)
        return resp.text.strip()
    except Exception as e:
        time.sleep(PAUSE)
        if "429" in str(e):
            return "Rate limit reached - please wait 60 seconds and try again."
        return f"[Error: {str(e)}]"


def generate_positioning_notes(company, function, gemini_api_key) -> str:
    client = genai.Client(api_key=gemini_api_key)
    prompt = f"Generate 3 positioning options for XIMPAX for a contact at {company} in the {function} function."
    try:
        resp = _call_with_retry(
            client, MODEL, prompt,
            types.GenerateContentConfig(system_instruction=POSITIONING_SYSTEM, temperature=0.85)
        )
        time.sleep(PAUSE)
        return resp.text.strip()
    except Exception as e:
        time.sleep(PAUSE)
        if "429" in str(e):
            return "Rate limit reached - please wait 60 seconds and try again."
        return f"[Error: {str(e)}]"
