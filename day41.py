import os
import json
import httpx
import psycopg2
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
N8N_WEBHOOK = "https://maritime-circulate-majestic.ngrok-free.dev/webhook/397fb073-1c9d-4d4f-a227-0da3b3d66b29"

SCORE_RANK = {"COLD": 0, "WARM": 1, "HOT": 2}

BASE_PRICES = {
    "airport_sedan": 150,
    "airport_suv": 200,
    "hourly_sedan": 100,
    "hourly_suv": 150
}

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            score TEXT DEFAULT 'COLD',
            max_score TEXT DEFAULT 'COLD',
            interactions INTEGER DEFAULT 0,
            history JSONB DEFAULT '[]',
            quotes JSONB DEFAULT '[]',
            score_history JSONB DEFAULT '[]',
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def load_lead(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM leads WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {
            "user_id": row[0], "name": row[1], "score": row[2],
            "max_score": row[3], "interactions": row[4],
            "history": row[5], "quotes": row[6], "score_history": row[7]
        }
    return None

def save_lead(lead):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO leads (user_id, name, score, max_score, interactions, history, quotes, score_history, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            name = EXCLUDED.name, score = EXCLUDED.score,
            max_score = EXCLUDED.max_score, interactions = EXCLUDED.interactions,
            history = EXCLUDED.history, quotes = EXCLUDED.quotes,
            score_history = EXCLUDED.score_history, updated_at = NOW()
    """, (
        lead["user_id"], lead["name"], lead["score"], lead["max_score"],
        lead["interactions"], json.dumps(lead["history"]),
        json.dumps(lead["quotes"]), json.dumps(lead["score_history"])
    ))
    conn.commit()
    cur.close()
    conn.close()

def load_all_leads():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, name, score, interactions, quotes, score_history FROM leads")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def update_score(lead, new_score):
    current_max = lead.get("max_score", "COLD")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if SCORE_RANK.get(new_score, 0) > SCORE_RANK.get(current_max, 0):
        lead["score_history"].append({"from": current_max, "to": new_score, "at": timestamp})
        lead["max_score"] = new_score
    lead["score"] = lead["max_score"]
    return lead["score"]

def calculate_price(service, client_type, hour, day_of_week, hours=1):
    price = BASE_PRICES.get(service, 150)
    adjustments = []
    if hour >= 22 or hour < 6:
        price *= 1.25
        adjustments.append("Night +25%")
    if day_of_week >= 5:
        price *= 1.15
        adjustments.append("Weekend +15%")
    if "hourly" in service:
        price *= hours
    if client_type == "VIP":
        price *= 0.9
        adjustments.append("VIP -10%")
    return round(price), adjustments

async def notify_hot_lead(name, score):
    async with httpx.AsyncClient() as client:
        await client.post(N8N_WEBHOOK, json={"name": name, "score": score})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚗 Welcome to Elite Transportation LA!\n\nTell me about your transportation needs."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    lead = load_lead(user_id) or {
        "user_id": user_id, "name": update.effective_user.first_name,
        "score": "COLD", "max_score": "COLD", "interactions": 0,
        "history": [], "quotes": [], "score_history": []
    }

    user_message = update.message.text
    lead["history"].append({"role": "user", "content": user_message})
    lead["interactions"] += 1

    analysis = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """Analyze this transportation request. Return ONLY JSON:
{"score": "HOT or WARM or COLD", "service": "airport_sedan or airport_suv or hourly_sedan or hourly_suv or unknown", "client_type": "VIP or Standard", "pickup_hour": 12, "hours": 1, "ready_for_quote": true or false}"""},
            *lead["history"][-6:]
        ]
    )

    try:
        details = json.loads(analysis.choices[0].message.content)
    except:
        details = {"score": "COLD", "service": "unknown", "client_type": "Standard", "pickup_hour": 12, "hours": 1, "ready_for_quote": False}

    current_score = update_score(lead, details["score"])

    if current_score == "HOT":
        await notify_hot_lead(lead["name"], current_score)

    price_context = ""
    if details["ready_for_quote"] and details["service"] != "unknown":
        price, adjustments = calculate_price(details["service"], details["client_type"], details["pickup_hour"], datetime.now().weekday(), details.get("hours", 1))
        lead["quotes"].append({"service": details["service"], "price": price, "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
        price_context = f"\nQUOTE READY: {details['service']} = ${price}. Adjustments: {', '.join(adjustments) if adjustments else 'none'}"

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are an elegant VIP transportation concierge for Elite Transportation LA.{price_context} Be professional and concise."},
            *lead["history"]
        ]
    )

    reply = response.choices[0].message.content
    lead["history"].append({"role": "assistant", "content": reply})
    if len(lead["history"]) > 20:
        lead["history"] = lead["history"][-20:]

    save_lead(lead)
    await update.message.reply_text(reply)

async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = load_all_leads()
    if not rows:
        await update.message.reply_text("No leads yet.")
        return
    text = "📊 LEADS DASHBOARD\n\n"
    for row in rows:
        uid, name, score, interactions, quotes, score_history = row
        emoji = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}.get(score, "❓")
        text += f"{emoji} {name} | {score} | {interactions} msgs"
        if quotes:
            text += f" | Last quote: ${quotes[-1]['price']}"
        text += "\n"
    await update.message.reply_text(text)

def main():
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leads", leads_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚗 Elite Transportation Bot (day41) with PostgreSQL is running!")
    app.run_polling()

if __name__ == "__main__":
    main()