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

MEMORY_FILE = "telegram_memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def get_user_context(memory, user_id):
    user_id = str(user_id)
    if user_id not in memory:
        memory[user_id] = {
            "name": "",
            "interactions": 0,
            "history": [],
            "first_seen": datetime.now().strftime("%Y-%m-%d")
        }
    return memory[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    user_id = update.effective_user.id
    user_data = get_user_context(memory, user_id)
    user_data["name"] = update.effective_user.first_name
    save_memory(memory)
    
    if user_data["interactions"] > 0:
        await update.message.reply_text(
            f"Welcome back, {user_data['name']}! You've chatted with me {user_data['interactions']} times before."
        )
    else:
        await update.message.reply_text(
            f"Hi {user_data['name']}! I'm your AI assistant. I'll remember our conversations!"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    user_id = update.effective_user.id
    user_data = get_user_context(memory, user_id)
    user_data["name"] = update.effective_user.first_name
    user_data["interactions"] += 1
    
    user_message = update.message.text
    user_data["history"].append({"role": "user", "content": user_message})
    
    if len(user_data["history"]) > 20:
        user_data["history"] = user_data["history"][-20:]
    
    messages = [
        {"role": "system", "content": f"You are a helpful AI assistant. The user's name is {user_data['name']}. They have chatted with you {user_data['interactions']} times. Use their name occasionally."}
    ] + user_data["history"]
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    reply = response.choices[0].message.content
    user_data["history"].append({"role": "assistant", "content": reply})
    save_memory(memory)
    
    await update.message.reply_text(reply)

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    user_id = update.effective_user.id
    user_data = get_user_context(memory, user_id)
    
    await update.message.reply_text(
        f"📊 Your stats:\n"
        f"Name: {user_data['name']}\n"
        f"Interactions: {user_data['interactions']}\n"
        f"First seen: {user_data['first_seen']}\n"
        f"Messages in memory: {len(user_data['history'])}"
    )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Memory Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()