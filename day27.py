from openai import OpenAI
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MEMORY_FILE = "day27_leads.json"

# ─────────────────────────────────────────
# CLIENT MEMORY
# ─────────────────────────────────────────

def load_leads():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {}

def save_leads(leads):
    with open(MEMORY_FILE, "w") as f:
        json.dump(leads, f, indent=2)

def get_lead(leads, name):
    return leads.get(name.lower())

def upsert_lead(leads, name, updates):
    key = name.lower()
    if key not in leads:
        leads[key] = {
            "name": name,
            "score": "COLD",
            "budget": None,
            "pain_points": [],
            "interactions": 0,
            "created": datetime.now().isoformat(),
        }
    leads[key].update(updates)
    leads[key]["interactions"] += 1
    leads[key]["last_seen"] = datetime.now().isoformat()
    save_leads(leads)
    return leads[key]

# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

stats = {"calls": 0, "tokens": 0, "cost": 0.0, "qualified": 0, "objections": 0, "closes": 0}

def track(tokens, stage):
    cost = (tokens * 0.00015) / 1000
    stats["calls"] += 1
    stats["tokens"] += tokens
    stats["cost"] += cost
    if stage == "qualifier":
        stats["qualified"] += 1
    elif stage == "objection":
        stats["objections"] += 1
    elif stage == "closer":
        stats["closes"] += 1

def show_dashboard():
    print("\n" + "=" * 44)
    print("  SALES PIPELINE DASHBOARD")
    print("=" * 44)
    print(f"  AI calls:        {stats['calls']}")
    print(f"  Leads qualified: {stats['qualified']}")
    print(f"  Objections handled: {stats['objections']}")
    print(f"  Close attempts:  {stats['closes']}")
    print(f"  Total tokens:    {stats['tokens']}")
    print(f"  Total cost:      ${stats['cost']:.5f}")
    print("=" * 44 + "\n")

def show_leads(leads):
    if not leads:
        print("  No leads yet.\n")
        return
    print("\n" + "=" * 44)
    print("  LEAD MEMORY")
    print("=" * 44)
    for lead in leads.values():
        badge = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}.get(lead["score"], "?")
        print(f"  {badge} {lead['name']} | {lead['score']} | interactions: {lead['interactions']}")
        if lead.get("budget"):
            print(f"     Budget: {lead['budget']}")
        if lead.get("pain_points"):
            print(f"     Pain points: {', '.join(lead['pain_points'])}")
    print("=" * 44 + "\n")

# ─────────────────────────────────────────
# AGENTS
# ─────────────────────────────────────────

def ai(system_prompt, user_message, stage):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )
    reply = response.choices[0].message.content
    track(response.usage.total_tokens, stage)
    return reply


def qualifier_agent(user_input, lead_context):
    system = f"""You are a B2B sales lead qualifier for a SaaS CRM product priced at $299/mo.

Lead history: {lead_context}

Analyze the prospect's message and return ONLY valid JSON:
{{
  "score": "HOT" | "WARM" | "COLD",
  "budget_mentioned": "<budget string or null>",
  "pain_points": ["<pain point>"],
  "intent": "<one sentence summary>",
  "has_objection": true | false,
  "objection_type": "price" | "timing" | "competitor" | "need" | null
}}

HOT = clear need + budget + urgency. WARM = interested but unclear. COLD = not a fit or just browsing."""

    raw = ai(system, user_input, "qualifier")
    try:
        # strip markdown code fences if present
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        return {"score": "COLD", "budget_mentioned": None, "pain_points": [],
                "intent": user_input, "has_objection": False, "objection_type": None}


def objection_handler_agent(user_input, objection_type, lead_data):
    objection_scripts = {
        "price":      "Acknowledge cost, emphasize ROI, offer a 14-day free trial.",
        "timing":     "Understand their timeline, offer a future demo slot, keep warm.",
        "competitor": "Ask what they like about the competitor, highlight unique differentiators.",
        "need":       "Uncover the real pain point with open-ended questions.",
    }
    script = objection_scripts.get(objection_type, "Acknowledge and explore further.")

    system = f"""You are an expert sales objection handler.
Lead: {lead_data['name']}, score: {lead_data['score']}, pain points: {lead_data.get('pain_points', [])}.
Objection type: {objection_type}. Strategy: {script}
Reply in 2-3 sentences. Be empathetic and consultative, never pushy."""

    return ai(system, user_input, "objection")


def closer_agent(user_input, lead_data, conversation_summary):
    score = lead_data["score"]
    closes = {
        "HOT":  "Propose a specific next step: book a 30-min demo or start a trial today.",
        "WARM": "Offer value first (case study, free audit), then a soft call-to-action.",
        "COLD": "Educate and nurture. Do not push for a close.",
    }
    strategy = closes.get(score, closes["COLD"])

    system = f"""You are a senior sales closer.
Lead: {lead_data['name']}, score: {score}, budget: {lead_data.get('budget')}.
Conversation so far: {conversation_summary}
Strategy: {strategy}
Respond in 3-4 sentences. End with a clear, single next-step ask."""

    return ai(system, user_input, "closer")

# ─────────────────────────────────────────
# PIPELINE ORCHESTRATOR
# ─────────────────────────────────────────

def run_pipeline(user_input, lead_name, leads, history):
    lead_data = get_lead(leads, lead_name) or {"name": lead_name, "score": "COLD",
                                                "budget": None, "pain_points": []}

    # Stage 1 — Qualify
    lead_context = json.dumps(lead_data)
    qual = qualifier_agent(user_input, lead_context)

    # Update memory
    updates = {"score": qual["score"]}
    if qual["budget_mentioned"]:
        updates["budget"] = qual["budget_mentioned"]
    if qual["pain_points"]:
        existing = lead_data.get("pain_points", [])
        updates["pain_points"] = list(set(existing + qual["pain_points"]))
    lead_data = upsert_lead(leads, lead_name, updates)

    stage_log = [f"Qualifier → {qual['score']} | intent: {qual['intent']}"]
    response = ""

    # Stage 2 — Handle objection if present
    if qual["has_objection"] and qual["objection_type"]:
        response = objection_handler_agent(user_input, qual["objection_type"], lead_data)
        stage_log.append(f"Objection handler → {qual['objection_type']}")
    else:
        # Stage 3 — Closer
        summary = " | ".join([m["content"][:60] for m in history[-4:]])
        response = closer_agent(user_input, lead_data, summary)
        stage_log.append(f"Closer → {lead_data['score']} strategy")

    return response, stage_log, lead_data

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

print("\nAI Sales System — Lead Qualification + Memory + Multi-Agent Pipeline")
print("=" * 60)
print("Commands: 'leads' — view all leads | 'stats' — dashboard | 'quit'\n")

leads = load_leads()

lead_name = input("Prospect name: ").strip()
if not lead_name:
    lead_name = "Unknown"

existing = get_lead(leads, lead_name)
if existing:
    print(f"\nWelcome back, {existing['name']}! (Score: {existing['score']}, "
          f"Interactions: {existing['interactions']})\n")
else:
    print(f"\nNew lead: {lead_name}\n")

history = []

while True:
    user_input = input(f"{lead_name}: ").strip()

    if user_input.lower() == "quit":
        break
    if user_input.lower() == "stats":
        show_dashboard()
        continue
    if user_input.lower() == "leads":
        show_leads(loads := load_leads())
        continue
    if not user_input:
        continue

    response, stages, lead_data = run_pipeline(user_input, lead_name, leads, history)

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response})

    badge = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}.get(lead_data["score"], "")
    print(f"\n  Pipeline: {' → '.join(stages)}")
    print(f"  Lead score: {badge} {lead_data['score']}")
    print(f"\nSales AI: {response}\n")

show_dashboard()
print(f"Lead data saved to {MEMORY_FILE}")
print("Goodbye!")
