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
LEADS_FILE = "day38_leads.json"

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
    """Advance score only if new_score is higher; log every change in score_history."""
    current_max = lead.get("max_score", "COLD")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    if SCORE_RANK.get(new_score, 0) > SCORE_RANK.get(current_max, 0):
        lead["score_history"].append({
            "from": current_max,
            "to": new_score,
            "at": timestamp
        })
        lead["max_score"] = new_score

    # current display score is always the maximum ever reached
    lead["score"] = lead["max_score"]
    return lead["score"]

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

    # Migrate old records that lack the new fields
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

    # FIX: never downgrade — only advance to a higher score
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

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leads", leads_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚗 Elite Transportation Bot (day38) is running!")
    print("Commands: /leads")
    app.run_polling()

if __name__ == "__main__":
    main()
