
import os
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Infinity Broadcast Bot is Live! 🚀"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📢 Broadcast", callback_data='broadcast')]]
    await update.message.reply_text("Murakaza neza!", reply_markup=InlineKeyboardMarkup(keyboard))

async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("Ntabwo wemerewe.")
        return
    await query.edit_message_text("Ohereza message:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"Yakiriwe: {update.message.text}")

async def main_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(broadcast_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot started...")
    await application.run_polling()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main_bot())
