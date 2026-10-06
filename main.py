import os, json
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8607653512"))
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"users": {}, "groups": {}}
    return {"users": {}, "groups": {}}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

data = load_data()
users = data.get("users", {})
groups = data.get("groups", {})
waiting = {}

web = Flask(__name__)
@web.route('/')
def home():
    return f"INFINITY ULTIMATE + GROUPS LIVE! Users: {len(users)} Groups: {len(groups)} 🚀"

def run_flask():
    web.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    uid = update.effective_user.id
    name = update.effective_user.first_name

    # Niba ari Group
    if chat.type in ['group', 'supergroup']:
        groups[str(chat.id)] = {"title": chat.title, "added": datetime.now().strftime("%Y-%m-%d")}
        save_data()
        await update.message.reply_text(f"✅ Nongewe muri {chat.title}!\n\n👥 Groups zose: {len(groups)}\n👤 Users: {len(users)}\n\nIyi Group izajya yakira BROADCAST zose! 🚀")
        try:
            await context.bot.send_message(ADMIN_ID, f"🆕 Group nshya!\n📛 {chat.title}\n🆔 {chat.id}\n👥 Groups: {len(groups)}")
        except:
            pass
        return

    # Niba ari Private User
    if str(uid) not in users:
        users[str(uid)] = {"name": name, "username": update.effective_user.username, "joined": datetime.now().strftime("%Y-%m-%d")}
        save_data()

    if uid == ADMIN_ID:
        kb = [[InlineKeyboardButton("📢 BROADCAST (Bose)", callback_data='bc_all')],
              [InlineKeyboardButton("👤 Users gusa", callback_data='bc_users'), InlineKeyboardButton("👥 Groups gusa", callback_data='bc_groups')],
              [InlineKeyboardButton("📊 STATS", callback_data='stats'), InlineKeyboardButton("📋 LIST", callback_data='list')]]
        await update.message.reply_text(f"👑 INFINITY GROUPS BOT\n\nBoss {name}! 👋\n👤 Users: {len(users)}\n👥 Groups: {len(groups)}\n\nHitamo:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(f"🌟 Murakaza neza {name}!\nWamaze kwiyandikisha! Uzakira amakuru yose! 🚀")

async def btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        return
    if q.data.startswith('bc_'):
        waiting[q.from_user.id] = q.data
        target = {"bc_all": f"{len(users)} users + {len(groups)} groups", "bc_users": f"{len(users)} users", "bc_groups": f"{len(groups)} groups"}[q.data]
        await q.edit_message_text(f"✍️ Ohereza icyo ushaka kohereza kuri {target}:\n\n✔️ Text\n✔️ Photo\n✔️ Video\n✔️ Link\n✔️ File\n✔️ Voice\n\nOhereza ubu:")
    elif q.data == 'stats':
        await q.edit_message_text(f"📊 STATS\n\n👤 Users: {len(users)}\n👥 Groups: {len(groups)}\n📅 {datetime.now()}\n\n🟢 LIVE", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ SUBIRA", callback_data='back')]]))
    elif q.data == 'list':
        txt = f"📋 LIST\n\n👥 GROUPS ({len(groups)}):\n"
        for gid, g in list(groups.items())[:10]:
            txt += f"• {g['title']} - {gid}\n"
        txt += f"\n👤 USERS ({len(users)}):\n"
        for uid, u in list(users.items())[:10]:
            txt += f"• {u['name']} - {uid}\n"
        await q.edit_message_text(txt[:4000], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ SUBIRA", callback_data='back')]]))
    elif q.data == 'back':
        kb = [[InlineKeyboardButton("📢 BROADCAST (Bose)", callback_data='bc_all')], [InlineKeyboardButton("👤 Users gusa", callback_data='bc_users'), InlineKeyboardButton("👥 Groups gusa", callback_data='bc_groups')], [InlineKeyboardButton("📊 STATS", callback_data='stats'), InlineKeyboardButton("📋 LIST", callback_data='list')]]
        await q.edit_message_text(f"👑 INFINITY\n👤 {len(users)} | 👥 {len(groups)}\nHitamo:", reply_markup=InlineKeyboardMarkup(kb))

async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID or uid not in waiting:
        return
    mode = waiting.pop(uid)
    total_targets = []
    if mode in ['bc_all', 'bc_users']:
        total_targets += list(users.keys())
    if mode in ['bc_all', 'bc_groups']:
        total_targets += list(groups.keys())

    await update.message.reply_text(f"🚀 Ndohereza kuri {len(total_targets)}... ⏳")

    sent = 0
    for tid in total_targets:
        try:
            await context.bot.copy_message(chat_id=int(tid), from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            sent += 1
        except Exception as e:
            print(f"Fail {tid}: {e}")

    await update.message.reply_text(f"✅ BYARANGIYE!\n\n✔️ Byageze: {sent}/{len(total_targets)}\n❌ Bitarageze: {len(total_targets)-sent}\n\nMode: {mode}")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print(f"BOT GROUPS STARTED Users:{len(users)} Groups:{len(groups)}")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(btn_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_handler))
    app.run_polling()
