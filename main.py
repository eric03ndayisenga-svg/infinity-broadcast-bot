import json, os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8525709744:AAHpcEgh-4C4bqnGGTesz0JAuaTTC7dvRI8"
OWNER_ID = 8607653512
GROUPS_FILE = "groups.json"

def load_groups():
    if os.path.exists(GROUPS_FILE):
        try:
            with open(GROUPS_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_groups(groups):
    with open(GROUPS_FILE, 'w') as f:
        json.dump(list(groups), f)

groups = load_groups()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global groups
    chat = update.effective_chat
    user = update.effective_user
    if user.id != OWNER_ID and chat.type == 'private':
        await update.message.reply_text("❌ Private bot.")
        return
    if chat.type in ['group', 'supergroup']:
        groups.add(chat.id)
        save_groups(groups)
        await update.message.reply_text(f"✅ Yongewe muri: {chat.title}\nMuhe admin!")
    else:
        await update.message.reply_text(f"🚀 INFINITY BOT ONLINE 24/7!\n📋 Groups: {len(groups)}\n\n/broadcast Ubutumwa\n/groups")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not context.args:
        await update.message.reply_text("Koresha: /broadcast Muraho!")
        return
    msg = " ".join(context.args)
    await update.message.reply_text(f"⏳ Kohereza mu {len(groups)}...")
    sent=failed=0
    for gid in list(groups):
        try:
            await context.bot.send_message(chat_id=gid, text=f"📢 INFINITY UPDATE:\n\n{msg}")
            sent+=1
        except: failed+=1
    await update.message.reply_text(f"✅ Byoherejwe: {sent} | ❌ Byanze: {failed}")

async def groups_cmd(update, context):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text(str(list(groups)) if groups else "Nta group")

async def id_cmd(update, context):
    await update.message.reply_text(f"User: {update.effective_user.id}\nChat: {update.effective_chat.id}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("groups", groups_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, start))
    app.run_polling()

if __name__ == "__main__":
    main()
