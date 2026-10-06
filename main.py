import os
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

web = Flask(__name__)

@web.route('/')
def home():
    return "Bot is LIVE! ✅"

def run_flask():
    web.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Bot ikora neza! ID yawe: {update.effective_user.id}")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print("Bot started...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
