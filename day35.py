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
LEADS_FILE = "day35_leads.json"

def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_leads(leads):
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

def qualify_lead(message, history):
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """You are a lead qualification AI for a VIP transportation company.
Analyze the conversation and return ONLY JSON:
{
  "score": "HOT or WARM or COLD",
  "intent": "brief description",
  "needs_followup": true or false,
  "suggested_service": "airport_suv or airport_sedan or hourly or unknown"
}"""},
            *history,
            {"role": "user", "content": message}
        ]
    )
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {"score": "COLD", "intent": "unknown", "needs_followup": False, "suggested_service": "unknown"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚗 Welcome to Elite Transportation!\n\n"
        "How can I help you today? Tell me about your transportation needs."
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
            "created": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    
    user_message = update.message.text
    leads[user_id]["history"].append({"role": "user", "content": user_message})
    leads[user_id]["interactions"] += 1
    
    qualification = qualify_lead(user_message, leads[user_id]["history"][-10:])
    leads[user_id]["score"] = qualification["score"]
    leads[user_id]["intent"] = qualification.get("intent", "")
    leads[user_id]["service"] = qualification.get("suggested_service", "")
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """You are an elegant VIP transportation concierge.
Pricing: airport sedan $150, airport SUV $200, hourly sedan $100/hr, hourly SUV $150/hr.
Be professional and helpful. Ask qualifying questions naturally."""},
            *leads[user_id]["history"]
        ]
    )
    
    reply = response.choices[0].message.content
    leads[user_id]["history"].append({"role": "assistant", "content": reply})
    
    if len(leads[user_id]["history"]) > 20:
        leads[user_id]["history"] = leads[user_id]["history"][-20:]
    
    save_leads(leads)
    
    score_emoji = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}.get(qualification["score"], "❓")
    print(f"Lead: {leads[user_id]['name']} | {score_emoji} {qualification['score']} | {qualification.get('intent', '')}")
    
    await update.message.reply_text(reply)

async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leads = load_leads()
    if not leads:
        await update.message.reply_text("No leads yet.")
        return
    
    text = "📊 LEADS DASHBOARD\n\n"
    for uid, data in leads.items():
        score_emoji = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}.get(data.get("score", "COLD"), "❓")
        text += f"{score_emoji} {data['name']} | {data.get('score', 'COLD')} | {data.get('interactions', 0)} msgs\n"
        if data.get("intent"):
            text += f"   Intent: {data['intent']}\n"
    
    await update.message.reply_text(text)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leads", leads_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚗 Lead Generation Bot is running...")
    print("Commands: /leads to see all leads")
    app.run_polling()

if __name__ == "__main__":
    main()