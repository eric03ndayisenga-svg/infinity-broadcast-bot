import os
import json
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8607653512"))
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                data = json.load(f)
                # support old format
                if isinstance(data, dict):
                    return data
                return {int(uid): {"joined": "2026"} for uid in data}
        except:
            return {}
    return {}

def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

users = load_users()
waiting = {}

web = Flask(__name__)
@web.route('/')
def home():
    return f"Infinity Bot ULTIMATE LIVE! 👑 Users: {len(users)}"

def run_flask():
    web.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    if uid not in users:
        users[uid] = {"name": name, "joined": datetime.now().strftime("%Y-%m-%d"), "username": update.effective_user.username}
        save_users()

    if uid == ADMIN_ID:
        kb = [
            [InlineKeyboardButton("📢 BROADCAST", callback_data='bc')],
            [InlineKeyboardButton("📊 STATS", callback_data='stats'), InlineKeyboardButton("👥 USERS", callback_data='users')]
        ]
        await update.message.reply_text(f"👑 INFINITY ULTIMATE BOT\n\nMuraho Boss {name}! 👋\n🆔 ID: {uid}\n👥 Abakoresha: {len(users)}\n\nHitamo:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(f"🌟 Murakaza neza {name} muri Infinity Bot!\n\n🆔 ID yawe: {uid}\n✅ Wamaze kwiyandikisha!\n\nUzakira amakuru agezweho hano! 🚀")
        # Notify admin
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🆕 Umukoresha mushya!\n👤 {name}\n🆔 {uid}\n👥 Bose: {len(users)}")
        except:
            pass

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        return
    await update.message.reply_text(f"📊 STATS\n\n👥 Abakoresha bose: {len(users)}\n🕒 Bot yatangiye: {datetime.now()}\n🟢 Status: LIVE\n\nFayili: {USERS_FILE}")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id!= ADMIN_ID:
        await q.edit_message_text("❌ Ntabwo wemerewe")
        return

    if q.data == 'bc':
        waiting[q.from_user.id] = True
        await q.edit_message_text(f"✍️ Ohereza icyo ushaka kohereza kuri {len(users)} bantu:\n\n• Text\n• Photo\n• Video\n• Voice\n• File\n\nOhereza ubu:")

    elif q.data == 'stats':
        await q.edit_message_text(f"📊 STATS\n\n👥 Bose: {len(users)}\n📅 Uyu munsi: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ SUBIRA", callback_data='back')]]))

    elif q.data == 'users':
        txt = f"👥 USERS ({len(users)}):\n\n"
        for uid, info in list(users.items())[:20]:
            txt += f"• {info.get('name','?')} - {uid}\n"
        if len(users) > 20:
            txt += f"\n...na {len(users)-20} bandi"
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ SUBIRA", callback_data='back')]]))

    elif q.data == 'back':
        kb = [[InlineKeyboardButton("📢 BROADCAST", callback_data='bc')], [InlineKeyboardButton("📊 STATS", callback_data='stats'), InlineKeyboardButton("👥 USERS", callback_data='users')]]
        await q.edit_message_text(f"👑 INFINITY BOT\n👥 {len(users)} users\nHitamo:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid!= ADMIN_ID or not waiting.get(uid):
        return
    waiting[uid] = False
    total = len(users)
    await update.message.reply_text(f"🚀 Ndohereza kuri {total} bantu... Tegereza ⏳")

    sent = 0
    for user_id in list(users.keys()):
        try:
            await context.bot.copy_message(chat_id=user_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ BYARANGIYE Boss!\n\n✔️ Byoherejwe: {sent}/{total}\n❌ Bitarabashije: {total-sent}\n\n👑 Infinity Ultimate!")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print(f"ULTIMATE Bot started! Users: {len(users)}")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msg))
    app.run_polling()
