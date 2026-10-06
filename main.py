import os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
waiting = {}

web = Flask(__name__)
@web.route('/')
def home():
    return "Infinity Bot LIVE! 🚀"
def run_flask():
    web.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("📢 BROADCAST", callback_data='bc')]]
    await update.message.reply_text(f"🌟 INFINITY BOT\nID: {update.effective_user.id}", reply_markup=InlineKeyboardMarkup(kb))

async def bc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.edit_message_text("❌ Ntabwo wemerewe")
        return
    waiting[q.from_user.id]=True
    await q.edit_message_text("✍️ Ohereza message:")

async def msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID or not waiting.get(update.effective_user.id):
        return
    waiting[update.effective_user.id]=False
    await update.message.reply_text(f"✅ Yakiriwe: {update.message.text}")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print("Bot started...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(bc, pattern='bc'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    app.run_polling()
