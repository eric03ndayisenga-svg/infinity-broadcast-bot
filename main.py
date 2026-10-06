import os, json, asyncio, logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ChatMemberHandler
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8607653512"))
DATA_FILE = "data.json"

# SECURITY CONFIG
BLOCK_BOTS = True # Hagarika izindi Bots zikoresha iyi bot
ONLY_ADMIN_BROADCAST = True
LOG_ALL_ACTIONS = True

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                d = json.load(f)
                d.setdefault("users", {})
                d.setdefault("groups", {})
                d.setdefault("pending_groups", {})
                d.setdefault("banned_users", [])
                d.setdefault("logs", [])
                return d
        except: pass
    return {"users": {}, "groups": {}, "pending_groups": {}, "banned_users": [], "logs": []}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def add_log(action, details):
    if LOG_ALL_ACTIONS:
        data["logs"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "action": action, "details": details})
        # Keep only last 100 logs
        if len(data["logs"]) > 100:
            data["logs"] = data["logs"][-100:]
        save_data()

data = load_data()
users = data["users"]
groups = data["groups"]
pending_groups = data["pending_groups"]
banned_users = data["banned_users"]
waiting = {}
contact_waiting = {}

web = Flask(__name__)
@web.route('/')
def home():
    return f"INFINITY V4 SECURE LIVE! U:{len(users)} G:{len(groups)} SECURE:ON 🛡️"

def run_flask():
    web.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def security_check(update: Update):
    """SECURITY CHECK - Hagarika Bots n'abantu babi"""
    user = update.effective_user
    if not user:
        return False
    # 1. Hagarika Bots zindi
    if BLOCK_BOTS and user.is_bot:
        return False
    # 2. Hagarika abantu ba Banned
    if str(user.id) in banned_users:
        return False
    return True

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    await update.message.reply_text(
        "🛡️ **INFINITY V4 SECURE BOT**\n\n"
        "🔒 Private Owner - Secure Mode ON\n\n"
        "📋 Commands:\n"
        "/start - Kwiyandikisha\n"
        "/help - Ubufasha\n"
        "/owner - Contact Owner (Private)\n\n"
        "👥 **Groups:**\n"
        "Bot ifite Security - Ntawuyikura, nta Bot yindi iyihagarika!\n"
        "Ongeza bot muri Group -> /start -> Tegereza approval\n\n"
        "🛡️ Security: ANTI-KICK, ANTI-BOT, OWNER ONLY"
    )

async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    kb = [[InlineKeyboardButton("📩 Contact Secure Owner 🔒", callback_data='contact_owner')]]
    await update.message.reply_text("👑 **Secure Private Owner 🔒🛡️**\n\nOwner ni Private & Secure.\nKanda hasi umwandikire - Ubutumwa bugera kuri Owner gusa!", reply_markup=InlineKeyboardMarkup(kb))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    chat = update.effective_chat
    uid = update.effective_user.id
    name = update.effective_user.first_name

    if chat.type in ['group', 'supergroup']:
        gid = str(chat.id)
        title = chat.title

        # SECURITY: Reba niba group iri muri banned?
        if gid in banned_users:
            await update.message.reply_text("🚫 Iyi Group yahagaritswe!")
            add_log("BANNED_GROUP_TRY", f"{title} {gid}")
            return

        if gid in groups:
            await update.message.reply_text(f"✅ **{title}** Secure & Active! 🛡️")
            return

        # Anti-spam: Niba group isanzwe muri pending, ntuyongere
        if gid not in pending_groups:
            pending_groups[gid] = {"title": title, "added_by": uid, "added": datetime.now().strftime("%Y-%m-%d %H:%M"), "username": update.effective_user.username, "name": name}
            save_data()
            add_log("GROUP_REQUEST", f"{title} by {name} {uid}")

        kb = [[InlineKeyboardButton("📩 Saba Approval (Secure)", callback_data='contact_owner')]]
        await update.message.reply_text(
            f"🛡️ **{title} - SECURE MODE**\n\n"
            f"🤖 Bot yongewe na {name}\n"
            f"🔒 Private Owner - Secure\n"
            f"🛡️ Anti-Kick: ON\n"
            f"🤖 Anti-Bot: ON\n"
            f"⏳ Tegereje approval!\n\n"
            f"**Ntawushobora kuyikura! Security ON!**",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        try:
            kb_admin = [
                [InlineKeyboardButton(f"✅ EMERA {title[:15]}", callback_data=f'approve_{gid}')],
                [InlineKeyboardButton(f"❌ HAKANA", callback_data=f'reject_{gid}'), InlineKeyboardButton(f"🚫 BANA GROUP", callback_data=f'ban_group_{gid}')]
            ]
            await context.bot.send_message(ADMIN_ID, f"🆕 **SECURE REQUEST 🛡️**\n\n📛 {title}\n🆔 {gid}\n👤 {name} (@{update.effective_user.username}) {uid}\n\n🛡️ Secure Mode - Nta Bot yindi ishobora kuyikoresha!", reply_markup=InlineKeyboardMarkup(kb_admin))
        except: pass
        return

    # PRIVATE
    if str(uid) not in users:
        users[str(uid)] = {"name": name, "username": update.effective_user.username, "joined": datetime.now().strftime("%Y-%m-%d")}
        save_data()
        add_log("NEW_USER", f"{name} {uid}")

    if uid == ADMIN_ID:
        kb = [
            [InlineKeyboardButton(f"📢 ALL ({len(users)+len(groups)})", callback_data='bc_all')],
            [InlineKeyboardButton(f"👤 {len(users)}", callback_data='bc_users'), InlineKeyboardButton(f"👥 {len(groups)}", callback_data='bc_groups')],
            [InlineKeyboardButton(f"⏳ Pending {len(pending_groups)}", callback_data='pending'), InlineKeyboardButton("📊 STATS", callback_data='stats')],
            [InlineKeyboardButton("🛡️ SECURITY LOG", callback_data='seclog'), InlineKeyboardButton("🚫 BANNED", callback_data='banned')],
            [InlineKeyboardButton("📋 LIST", callback_data='list')]
        ]
        await update.message.reply_text(f"👑 **SECURE OWNER PANEL 🛡️🔒**\n\nBoss {name}!\n👤 {len(users)} | 👥 {len(groups)} | ⏳ {len(pending_groups)}\n\n🛡️ Anti-Kick: ON\n🤖 Anti-Bot: ON\n🔒 Private: ON\n📝 Logging: ON", reply_markup=InlineKeyboardMarkup(kb))
    else:
        kb = [[InlineKeyboardButton("📩 Contact Secure Owner", callback_data='contact_owner')]]
        await update.message.reply_text(f"🌟 Murakaza neza {name}! 🛡️\n\n🔒 Secure Bot - Anti-Kick ON\n✅ Wiyandikishije!\n\nOngeza bot muri Group yawe - Ntizakurwa!", reply_markup=InlineKeyboardMarkup(kb))

# SECURITY: Iyo bot ikuwe muri Group - Menya ninde wabikoze!
async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return
    # Niba bot ariyo yavuye / yakuwe
    if result.new_chat_member.user.id == context.bot.id:
        chat = update.effective_chat
        gid = str(chat.id)
        old_status = result.old_chat_member.status
        new_status = result.new_chat_member.status

        # Niba yakuwe (kicked/left)
        if new_status in ['left', 'kicked', 'banned']:
            # Ninde wabikoze?
            actor = update.effective_user
            actor_info = f"{actor.first_name} ({actor.id}) @{actor.username}" if actor else "Unknown"

            add_log("BOT_REMOVED", f"Group {chat.title} {gid} removed by {actor_info}")

            # Siba muri groups/pending
            if gid in groups:
                groups.pop(gid)
            if gid in pending_groups:
                pending_groups.pop(gid)
            save_data()

            # Oherereza Owner alert
            try:
                await context.bot.send_message(ADMIN_ID, f"🚨 **ALERT! BOT YAKUWE MURI GROUP! 🛡️**\n\n📛 Group: {chat.title}\n🆔 ID: {gid}\n👤 Yakuwe na: {actor_info}\n📅 {datetime.now()}\n\n⚠️ Action: Yakuwe muri database. Ongera uyongeze niba ubishaka!")
            except: pass

async def btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == 'contact_owner':
        contact_waiting[uid] = True
        await q.edit_message_text("✍️ **Andika ubutumwa kuri Secure Private Owner 🛡️🔒:**\n\nAndika hano...")
        return
    if q.data == 'seclog':
        if uid!= ADMIN_ID: return
        logs = data.get("logs", [])[-10:]
        txt = "🛡️ **SECURITY LOG (Last 10):**\n\n"
        for l in logs:
            txt+= f"• {l['time']} - {l['action']}: {l['details'][:40]}\n"
        await q.edit_message_text(txt[:4000], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ SUBIRA", callback_data='back')]]))
        return
    if q.data == 'banned':
        if uid!= ADMIN_ID: return
        txt = f"🚫 Banned: {len(banned_users)}\n" + "\n".join(banned_users[:20])
        await q.edit_message_text(txt[:4000], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ SUBIRA", callback_data='back')]]))
        return
    if q.data.startswith('approve_'):
        if uid!= ADMIN_ID: return
        gid = q.data.replace('approve_', '')
        if gid in pending_groups:
            g = pending_groups.pop(gid)
            groups[gid] = g
            save_data()
            add_log("APPROVED", f"{g['title']} {gid}")
            await q.edit_message_text(f"✅ **Yemerewe Secure! 🛡️** {g['title']}")
            try: await context.bot.send_message(int(gid), f"🎉 **BYEMEWE 🛡️**\n\n✅ {g['title']} yemerewe!\n🔒 Secure Mode ON - Ntawuyikura!")
            except: pass
        return
    if q.data.startswith('reject_'):
        if uid!= ADMIN_ID: return
        gid = q.data.replace('reject_', '')
        if gid in pending_groups:
            g = pending_groups.pop(gid)
            save_data()
            add_log("REJECTED", f"{g['title']} {gid}")
            await q.edit_message_text(f"❌ {g['title']} yahakanywe")
        return
    if q.data.startswith('ban_group_'):
        if uid!= ADMIN_ID: return
        gid = q.data.replace('ban_group_', '')
        banned_users.append(gid)
        if gid in pending_groups: pending_groups.pop(gid)
        if gid in groups: groups.pop(gid)
        save_data()
        add_log("BANNED_GROUP", gid)
        await q.edit_message_text(f"🚫 Group {gid} ibanye!")
        return

    if uid!= ADMIN_ID: return
    if q.data.startswith('bc_'):
        waiting[uid] = q.data
        await q.edit_message_text(f"✍️ Ohereza kuri {q.data} - Secure Fast ⚡🛡️")
    elif q.data == 'stats':
        await q.edit_message_text(f"📊 SECURE STATS 🛡️\n👤 {len(users)}\n👥 {len(groups)}\n⏳ {len(pending_groups)}\n🚫 Banned: {len(banned_users)}\n🛡️ Security: MAX", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ SUBIRA", callback_data='back')]]))
    elif q.data == 'pending':
        txt = f"⏳ {len(pending_groups)} pending\n" + "\n".join([f"{g['title']} {gid}" for gid,g in pending_groups.items()][:10])
        kb = [[InlineKeyboardButton(f"✅ {g['title'][:15]}", callback_data=f'approve_{gid}')] for gid,g in list(pending_groups.items())[:5]]
        kb.append([InlineKeyboardButton("⬅️ SUBIRA", callback_data='back')])
        await q.edit_message_text(txt[:4000] or "Nta pending", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data == 'list':
        await q.edit_message_text(f"Groups: {len(groups)} Users: {len(users)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ SUBIRA", callback_data='back')]]))
    elif q.data == 'back':
        kb = [[InlineKeyboardButton(f"📢 ALL", callback_data='bc_all')], [InlineKeyboardButton(f"👤 {len(users)}", callback_data='bc_users'), InlineKeyboardButton(f"👥 {len(groups)}", callback_data='bc_groups')], [InlineKeyboardButton(f"⏳ {len(pending_groups)}", callback_data='pending'), InlineKeyboardButton("📊 STATS", callback_data='stats')], [InlineKeyboardButton("🛡️ LOG", callback_data='seclog'), InlineKeyboardButton("📋 LIST", callback_data='list')]]
        await q.edit_message_text(f"👑 SECURE PANEL 🛡️\n👤 {len(users)} | 👥 {len(groups)}", reply_markup=InlineKeyboardMarkup(kb))

async def fast_send(context, tid, from_chat_id, message_id):
    try:
        await context.bot.copy_message(chat_id=int(tid), from_chat_id=from_chat_id, message_id=message_id)
        return True
    except: return False

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    uid = update.effective_user.id

    if uid in contact_waiting:
        contact_waiting.pop(uid)
        try:
            await context.bot.send_message(ADMIN_ID, f"📩 **Secure Message 🔒**\n\n👤 {update.effective_user.first_name} @{update.effective_user.username}\n🆔 {uid}\n\n💬 {update.message.text or 'Media'}")
            if not update.message.text:
                await context.bot.copy_message(ADMIN_ID, update.effective_chat.id, update.message.message_id)
            await update.message.reply_text("✅ Bwoherejwe kuri Secure Owner! 🔒🛡️")
        except: pass
        return

    if uid == ADMIN_ID and uid in waiting:
        mode = waiting.pop(uid)
        targets = []
        if mode in ['bc_all', 'bc_users']: targets += list(users.keys())
        if mode in ['bc_all', 'bc_groups']: targets += list(groups.keys())
        await update.message.reply_text(f"🚀 Secure Fast kuri {len(targets)}... 🛡️⚡")
        tasks = [fast_send(context, tid, update.effective_chat.id, update.message.message_id) for tid in targets]
        results = await asyncio.gather(*tasks)
        sent = sum(results)
        add_log("BROADCAST", f"Mode {mode} Sent {sent}/{len(targets)}")
        await update.message.reply_text(f"✅ BYARANGIYE SECURE! {sent}/{len(targets)} 🛡️🚀")
        return

    if uid == ADMIN_ID and update.message.reply_to_message and "🆔" in (update.message.reply_to_message.text or ""):
        import re
        m = re.search(r'🆔 (\d+)', update.message.reply_to_message.text)
        if m:
            target_uid = int(m.group(1))
            try:
                await context.bot.send_message(target_uid, f"👑 **Secure Owner Reply 🛡️🔒:**\n\n{update.message.text}")
                await update.message.reply_text(f"✅ Byoherejwe")
            except: pass

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print("BOT V4 SECURE STARTED 🛡️")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(CallbackQueryHandler(btn_handler))
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))
    app.run_polling()
