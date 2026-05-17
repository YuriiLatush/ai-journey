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
LEADS_FILE = "day37_leads.json"

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
            "interactions": 0,
            "quotes": []
        }
    
    user_message = update.message.text
    leads[user_id]["history"].append({"role": "user", "content": user_message})
    leads[user_id]["interactions"] += 1
    
    # Qualify and extract details
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
            *leads[user_id]["history"][-6:]
        ]
    )
    
    try:
        details = json.loads(analysis.choices[0].message.content)
    except:
        details = {"score": "COLD", "service": "unknown", "client_type": "Standard", 
                   "pickup_hour": 12, "hours": 1, "ready_for_quote": False}
    
    leads[user_id]["score"] = details["score"]
    
    # Generate response
    if details["ready_for_quote"] and details["service"] != "unknown":
        price, adjustments = calculate_price(
            details["service"],
            details["client_type"],
            details["pickup_hour"],
            datetime.now().weekday(),
            details.get("hours", 1)
        )
        
        leads[user_id]["quotes"].append({
            "service": details["service"],
            "price": price,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        
        price_context = f"\nQUOTE READY: {details['service']} = ${price}. Adjustments: {', '.join(adjustments) if adjustments else 'none'}"
    else:
        price_context = ""
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are an elegant VIP transportation concierge for Elite Transportation LA.
{price_context}
If quote is ready, present it elegantly with the exact price calculated.
If not ready, ask natural qualifying questions. Be professional and concise."""},
            *leads[user_id]["history"]
        ]
    )
    
    reply = response.choices[0].message.content
    leads[user_id]["history"].append({"role": "assistant", "content": reply})
    
    if len(leads[user_id]["history"]) > 20:
        leads[user_id]["history"] = leads[user_id]["history"][-20:]
    
    save_leads(leads)
    
    score_emoji = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}.get(details["score"], "❓")
    print(f"Lead: {leads[user_id]['name']} | {score_emoji} {details['score']} | Service: {details['service']}")
    
    await update.message.reply_text(reply)

async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leads = load_leads()
    if not leads:
        await update.message.reply_text("No leads yet.")
        return
    
    text = "📊 LEADS DASHBOARD\n\n"
    for uid, data in leads.items():
        score_emoji = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}.get(data.get("score", "COLD"), "❓")
        text += f"{score_emoji} {data['name']} | {data['score']} | {data['interactions']} msgs"
        if data.get("quotes"):
            last_quote = data["quotes"][-1]
            text += f" | Last quote: ${last_quote['price']}"
        text += "\n"
    
    await update.message.reply_text(text)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leads", leads_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚗 Elite Transportation Bot is running!")
    print("Commands: /leads")
    app.run_polling()

if __name__ == "__main__":
    main()