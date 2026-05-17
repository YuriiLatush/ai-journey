from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm your AI assistant. Ask me anything about AI automation and business!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant specializing in business automation and AI systems."},
            {"role": "user", "content": user_message}
        ]
    )
    
    reply = response.choices[0].message.content
    await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()