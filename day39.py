from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LEADS_FILE = "day39_leads.json"

SCORE_RANK = {"COLD": 0, "WARM": 1, "HOT": 2}

BASE_PRICES = {
    "airport_sedan": 150,
    "airport_suv": 200,
    "hourly_sedan": 100,
    "hourly_suv": 150
}

def calculate_price(service, client_type, hour, day_of_week, hours=1):
    price = BASE_PRICES.get(service, 150)
    adjustments = []

    if hour >= 22 or hour < 6:
        price *= 1.25
        adjustments.append("Night surcharge +25%")

    if day_of_week >= 5:
        price *= 1.15
        adjustments.append("Weekend surcharge +15%")

    if "hourly" in service:
        price *= hours

    if client_type == "VIP":
        price *= 0.9
        adjustments.append("VIP discount -10%")

    return round(price), adjustments

def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_leads(leads):
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

def update_score(lead: dict, new_score: str) -> str:
    current_max = lead.get("max_score", "COLD")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    if SCORE_RANK.get(new_score, 0) > SCORE_RANK.get(current_max, 0):
        lead["score_history"].append({
            "from": current_max,
            "to": new_score,
            "at": timestamp
        })
        lead["max_score"] = new_score

    lead["score"] = lead["max_score"]
    return lead["score"]

def build_report_data(leads: dict) -> dict:
    """Aggregate lead data into a structured dict for the AI to summarize."""
    breakdown = {"HOT": [], "WARM": [], "COLD": []}
    total_revenue = 0

    for uid, data in leads.items():
        score = data.get("score", "COLD")
        quotes = data.get("quotes", [])
        best_quote = max((q["price"] for q in quotes), default=0)
        total_revenue += best_quote

        breakdown[score].append({
            "name": data.get("name", "Unknown"),
            "interactions": data.get("interactions", 0),
            "quotes": quotes,
            "best_quote": best_quote,
            "score_journey": data.get("score_history", []),
        })

    # Sort each tier by best quote descending so top opportunities surface first
    for tier in breakdown:
        breakdown[tier].sort(key=lambda x: x["best_quote"], reverse=True)

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_leads": len(leads),
        "hot_count": len(breakdown["HOT"]),
        "warm_count": len(breakdown["WARM"]),
        "cold_count": len(breakdown["COLD"]),
        "potential_revenue": total_revenue,
        "breakdown": breakdown,
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚗 Welcome to Elite Transportation LA!\n\n"
        "Tell me about your transportation needs and I'll provide an instant quote."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leads = load_leads()
    user_id = str(update.effective_user.id)

    if user_id not in leads:
        leads[user_id] = {
            "name": update.effective_user.first_name,
            "history": [],
            "score": "COLD",
            "max_score": "COLD",
            "score_history": [],
            "interactions": 0,
            "quotes": []
        }

    lead = leads[user_id]
    if "max_score" not in lead:
        lead["max_score"] = lead.get("score", "COLD")
    if "score_history" not in lead:
        lead["score_history"] = []

    user_message = update.message.text
    lead["history"].append({"role": "user", "content": user_message})
    lead["interactions"] += 1

    analysis = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """Analyze this transportation request. Return ONLY JSON:
{
  "score": "HOT or WARM or COLD",
  "service": "airport_sedan or airport_suv or hourly_sedan or hourly_suv or unknown",
  "client_type": "VIP or Standard",
  "pickup_hour": 12,
  "hours": 1,
  "ready_for_quote": true or false
}"""},
            *lead["history"][-6:]
        ]
    )

    try:
        details = json.loads(analysis.choices[0].message.content)
    except Exception:
        details = {"score": "COLD", "service": "unknown", "client_type": "Standard",
                   "pickup_hour": 12, "hours": 1, "ready_for_quote": False}

    current_score = update_score(lead, details["score"])

    if details["ready_for_quote"] and details["service"] != "unknown":
        price, adjustments = calculate_price(
            details["service"],
            details["client_type"],
            details["pickup_hour"],
            datetime.now().weekday(),
            details.get("hours", 1)
        )

        lead["quotes"].append({
            "service": details["service"],
            "price": price,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

        price_context = (
            f"\nQUOTE READY: {details['service']} = ${price}. "
            f"Adjustments: {', '.join(adjustments) if adjustments else 'none'}"
        )
    else:
        price_context = ""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are an elegant VIP transportation concierge for Elite Transportation LA.
{price_context}
If quote is ready, present it elegantly with the exact price calculated.
If not ready, ask natural qualifying questions. Be professional and concise."""},
            *lead["history"]
        ]
    )

    reply = response.choices[0].message.content
    lead["history"].append({"role": "assistant", "content": reply})

    if len(lead["history"]) > 20:
        lead["history"] = lead["history"][-20:]

    save_leads(leads)

    score_emoji = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}.get(current_score, "❓")
    print(f"Lead: {lead['name']} | {score_emoji} {current_score} | Service: {details['service']}")

    await update.message.reply_text(reply)

async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leads = load_leads()
    if not leads:
        await update.message.reply_text("No leads yet.")
        return

    text = "📊 LEADS DASHBOARD\n\n"
    for uid, data in leads.items():
        score = data.get("score", "COLD")
        score_emoji = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}.get(score, "❓")
        text += f"{score_emoji} {data['name']} | {score} | {data['interactions']} msgs"
        if data.get("quotes"):
            last_quote = data["quotes"][-1]
            text += f" | Last quote: ${last_quote['price']}"
        history = data.get("score_history", [])
        if history:
            progression = " → ".join(
                [history[0]["from"]] + [h["to"] for h in history]
            )
            text += f" | Journey: {progression}"
        text += "\n"

    await update.message.reply_text(text)

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leads = load_leads()
    if not leads:
        await update.message.reply_text("No leads yet — nothing to report.")
        return

    await update.message.reply_text("Generating AI summary report...")

    data = build_report_data(leads)

    # Format top opportunities for the prompt (max 5 per tier to keep prompt tight)
    def fmt_leads(tier_list):
        if not tier_list:
            return "none"
        lines = []
        for l in tier_list[:5]:
            quote_str = f"${l['best_quote']}" if l["best_quote"] else "no quote yet"
            lines.append(f"  - {l['name']}: {l['interactions']} interactions, best quote {quote_str}")
        return "\n".join(lines)

    prompt = f"""You are a sales manager at Elite Transportation LA. Generate a concise daily summary report based on this data.

DATE: {data['date']}
TOTAL LEADS: {data['total_leads']}
HOT (🔥): {data['hot_count']}
WARM (🌤): {data['warm_count']}
COLD (❄️): {data['cold_count']}
POTENTIAL REVENUE (sum of best quotes): ${data['potential_revenue']}

HOT LEADS:
{fmt_leads(data['breakdown']['HOT'])}

WARM LEADS:
{fmt_leads(data['breakdown']['WARM'])}

COLD LEADS:
{fmt_leads(data['breakdown']['COLD'])}

Write a structured report with these sections:
1. Executive Summary (2-3 sentences)
2. Lead Breakdown (HOT/WARM/COLD counts and what they mean for the pipeline)
3. Potential Revenue (total and what's realistic to close today)
4. Top Opportunities (name the most promising leads and recommended next actions)
5. Action Items (3 bullet points for the sales team)

Keep it professional, specific, and actionable. Use the actual names and numbers."""

    summary = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    report_text = summary.choices[0].message.content
    header = f"📋 DAILY REPORT — {data['date']}\n{'─' * 30}\n\n"

    # Telegram has a 4096 char limit; split if needed
    full_message = header + report_text
    if len(full_message) <= 4096:
        await update.message.reply_text(full_message)
    else:
        await update.message.reply_text(header + report_text[:4000] + "\n\n[continued...]")
        await update.message.reply_text(report_text[4000:])

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leads", leads_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚗 Elite Transportation Bot (day39) is running!")
    print("Commands: /leads  /report")
    app.run_polling()

if __name__ == "__main__":
    main()
