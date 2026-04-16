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

POSITIONING_SYSTEM = """You write short, company-specific positioning sentences for XIMPAX — a small Swiss team of senior supply chain and procurement experts who embed directly inside client teams.

You will be given:
- The contact's company name and job function
- The 2-3 most important business signals found for that company (e.g. margin pressure, restructuring, growth)
- A one-sentence summary of the company's situation

Generate exactly 3 options (numbered 1. / 2. / 3.) that Sebastian can use verbally or in writing to position XIMPAX.

Rules:
- Each option must reference the SPECIFIC company situation — name the programme, the challenge, or the pressure the contact is facing
- Each option uses a DIFFERENT angle:
    Angle 1: External taskforce — hands-on, embedded, not advisory. Tie to a specific operational challenge at this company.
    Angle 2: Industry experts with real operator experience. Tie to the functional domain of this contact.
    Angle 3: NOT a consultancy — direct contrast to typical consulting firms. Tie to what this company actually needs right now.
- 1-2 sentences per option. Plain language. No jargon.
- NEVER use: resilience, optimise, leverage, synergies, value proposition, holistic, solutions, consultants, consulting.
- Output ONLY the 3 numbered options. No headers, no commentary."""


def _call_with_retry(client, model, contents, config, retries=2, wait=30):
    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            if "429" in str(e) and attempt < retries:
                time.sleep(wait)
                continue
            raise


def generate_situation_notes(company, function, active_situations, gemini_api_key, closeness="") -> str:
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


def generate_positioning_notes(company, function, gemini_api_key, closeness="",
                                active_situations=None, summary="") -> str:
    client = genai.Client(api_key=gemini_api_key)

    # Build a compact signals block so the model knows what this company is actually facing
    sig_lines = ""
    if active_situations:
        for s in (active_situations or [])[:3]:
            # One-line summary per signal: label, status, first bullet only
            first_bullet = s["signal"].split("\n")[0].lstrip("- ").strip()
            sig_lines += f"- {s['label']} ({s['status']}): {first_bullet}\n"

    prompt = f"""Generate 3 XIMPAX positioning options for Sebastian to use with:
Contact role: {function}
Company: {company}
Company situation summary: {summary or 'Not available'}
Key signals:
{sig_lines or '- No specific signals available'}

Each option must reference this specific company situation, not generic language.
Output ONLY the 3 numbered options."""

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
