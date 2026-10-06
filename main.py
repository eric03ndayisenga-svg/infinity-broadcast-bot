     
import os
from threading import Thread
from flask import Flask
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatType
import aiohttp

# === FLASK KEEP-ALIVE FOR RENDER FREE (NTIBYISHYUZA) ===
flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "INFINITY BOT V6 LIVE - OK"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)
Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID", "0"))
DATA = "bot_data.json"
SCHED = "schedule.json"

def load_data():
    try:
        with open(DATA,"r") as f:
            d=json.load(f)
            return d.get("groups",{}),d.get("pending",{}),d.get("banned",[]),d.get("logs",[]),d.get("keywords",{}),d.get("settings",{"welcome":True,"anti_link":False,"auto_ai":False})
    except:
        return {},{},{},[],{},{"welcome":True,"anti_link":False,"auto_ai":False}

def save_data(g,p,b,l,k,s):
    with open(DATA,"w") as f:
        json.dump({"groups":g,"pending":p,"banned":b,"logs":l,"keywords":k,"settings":s},f,indent=2)

def load_sched():
    try:
        with open(SCHED,"r") as f:
            return json.load(f)
    except:
        return []
def save_sched(s):
    with open(SCHED,"w") as f:
        json.dump(s,f,indent=2)

groups,pending,banned,logs,keywords,settings=load_data()
jobs=load_sched()

async def is_admin(u):
    return u.effective_user.id==ADMIN

async def loop_job(tg_app):
    while True:
        try:
            now=datetime.now()
            for job in jobs[:]:
                nxt=datetime.fromisoformat(job["next_run"])
                if now>=nxt:
                    txt=job["text"]
                    for gid in list(groups.keys()):
                        try:
                            await tg_app.bot.send_message(chat_id=int(gid),text=txt)
                            await asyncio.sleep(0.3)
                        except: pass
                    job["next_run"]=(now+timedelta(minutes=job["interval_minutes"])).isoformat()
                    save_sched(jobs)
        except: pass
        await asyncio.sleep(30)

async def start(update,context):
    chat=update.effective_chat
    gid=str(chat.id)
    if chat.type in [ChatType.GROUP,ChatType.SUPERGROUP]:
        if gid not in groups and gid not in pending:
            pending[gid]={"title":chat.title,"added_at":datetime.now().isoformat()}
            save_data(groups,pending,banned,logs,keywords,settings)
        st="EMEWE ✅" if gid in groups else "TEGEREJE ⏳"
        await update.message.reply_text(f"V6\n{chat.title}\n{st}")
        return
    if not await is_admin(update):
        await update.message.reply_text("Muraho V6! 👋")
        return
    kb=[
        [InlineKeyboardButton(f"📢 BROADCAST ALL {len(groups)}",callback_data="broadcast_all")],
        [InlineKeyboardButton(f"👥 G:{len(groups)}",callback_data="list_groups"),InlineKeyboardButton(f"⏳ P:{len(pending)}",callback_data="list_pending")],
        [InlineKeyboardButton("⏰ JOBS",callback_data="sched_list"),InlineKeyboardButton("📊 STATS",callback_data="stats")],
        [InlineKeyboardButton("⚙️ SET",callback_data="set"),InlineKeyboardButton("🤖 AI",callback_data="ai")],
    ]
    txt=f"👑 INFINITY V6 PANEL 👑\n\nG:{len(groups)} | P:{len(pending)} | J:{len(jobs)}\nLIVE 🟢"
    await update.message.reply_text(txt,reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")

async def broad_cmd(update,context):
    if not await is_admin(update): return
    await update.message.reply_text("✍️ Send msg to broadcast / /cancel")
    context.user_data["broad"]=True

async def handle_msg(update,context):
    chat=update.effective_chat
    text=update.message.text or ""
    if context.user_data.get("broad") and await is_admin(update) and chat.type==ChatType.PRIVATE:
        if text=="/cancel":
            context.user_data["broad"]=False
            await update.message.reply_text("❌ Stopped")
            return
        c=0
        for gid in list(groups.keys()):
            try:
                await context.bot.copy_message(chat_id=int(gid),from_chat_id=chat.id,message_id=update.message.message_id)
                c+=1
                await asyncio.sleep(0.3)
            except: pass
        context.user_data["broad"]=False
        await update.message.reply_text(f"✅ Sent {c}/{len(groups)}")
        return
    if chat.type in [ChatType.GROUP,ChatType.SUPERGROUP]:
        gid=str(chat.id)
        if gid in groups:
            low=text.lower()
            for k,v in keywords.items():
                if k in low:
                    await update.message.reply_text(v)
                    break

async def new_mem(update,context):
    chat=update.effective_chat
    gid=str(chat.id)
    for m in update.message.new_chat_members:
        if m.id==context.bot.id:
            if gid not in groups and gid not in pending:
                pending[gid]={"title":chat.title,"added_at":datetime.now().isoformat()}
                save_data(groups,pending,banned,logs,keywords,settings)
                await update.message.reply_text("✅ V6 Added! Waiting approval.")

async def btn(update,context):
    q=update.callback_query
    await q.answer()
    d=q.data
    if not await is_admin(update): return
    if d=="list_groups":
        t=""
        for gid,info in groups.items():
            t+=f"{info.get('title','G')} | {gid}\n"
        await q.edit_message_text(t[:3000] or "Nta group", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
    elif d=="list_pending":
        if not pending:
            await q.edit_message_text("Nta pending", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
            return
        kb=[]
        for gid,info in list(pending.items())[:10]:
            kb.append([InlineKeyboardButton(f"✅ YES {info.get('title','G')[:15]}",callback_data=f"ap_{gid}"),InlineKeyboardButton("❌ NO",callback_data=f"rj_{gid}")])
        kb.append([InlineKeyboardButton("⬅️ Back",callback_data="back")])
        await q.edit_message_text(f"⏳ P:{len(pending)}",reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("ap_"):
        gid=d.split("ap_")[1]
        if gid in pending:
            groups[gid]=pending.pop(gid)
            save_data(groups,pending,banned,logs,keywords,settings)
            await q.edit_message_text("✅ Approved")
    elif d.startswith("rj_"):
        gid=d.split("rj_")[1]
        if gid in pending:
            pending.pop(gid)
            save_data(groups,pending,banned,logs,keywords,settings)
            await q.edit_message_text("❌ Rejected")
    elif d=="broadcast_all":
        await q.edit_message_text("✍️ Send msg / /cancel")
        context.user_data["broad"]=True
    elif d=="stats":
        await q.edit_message_text(f"📊 STATS\nG:{len(groups)}\nP:{len(pending)}\nJ:{len(jobs)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
    elif d=="sched_list":
        t=""
        for j in jobs:
            t+=f"{j['id']} {j['interval_minutes']}m: {j['text'][:25]}\n"
        await q.edit_message_text(t[:2000] or "Nta job", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Clear",callback_data="clear_jobs")],[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
    elif d=="clear_jobs":
        jobs.clear()
        save_sched(jobs)
        await q.edit_message_text("✅ Cleared")
    elif d=="set":
        kb=[[InlineKeyboardButton(f"Welcome:{settings.get('welcome')}",callback_data="tw")],[InlineKeyboardButton(f"AntiLink:{settings.get('anti_link')}",callback_data="tl")],[InlineKeyboardButton("⬅️ Back",callback_data="back")]]
        await q.edit_message_text("⚙️ Settings",reply_markup=InlineKeyboardMarkup(kb))
    elif d=="tw":
        settings["welcome"]=not settings.get("welcome",True)
        save_data(groups,pending,banned,logs,keywords,settings)
        await q.edit_message_text(f"Welcome:{settings.get('welcome')}")
    elif d=="tl":
        settings["anti_link"]=not settings.get("anti_link",False)
        save_data(groups,pending,banned,logs,keywords,settings)
        await q.edit_message_text(f"AntiLink:{settings.get('anti_link')}")
    elif d=="back":
        kb=[
            [InlineKeyboardButton(f"📢 BROADCAST ALL {len(groups)}",callback_data="broadcast_all")],
            [InlineKeyboardButton(f"👥 G:{len(groups)}",callback_data="list_groups"),InlineKeyboardButton(f"⏳ P:{len(pending)}",callback_data="list_pending")],
            [InlineKeyboardButton("⏰ JOBS",callback_data="sched_list"),InlineKeyboardButton("📊 STATS",callback_data="stats")],
            [InlineKeyboardButton("⚙️ SET",callback_data="set"),InlineKeyboardButton("🤖 AI",callback_data="ai")],
        ]
        txt=f"👑 INFINITY V6 PANEL 👑\n\nG:{len(groups)} | P:{len(pending)} | J:{len(jobs)}\nLIVE 🟢"
        await q.edit_message_text(txt,reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")
    elif d=="ai":
        await q.edit_message_text("🤖 /ai question")

async def post_init(tg_app):
    asyncio.create_task(loop_job(tg_app))

def main():
    tg_app=Application.builder().token(TOKEN).post_init(post_init).build()
    tg_app.add_handler(CommandHandler("start",start))
    tg_app.add_handler(CommandHandler("broadcast",broad_cmd))
    tg_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS,new_mem))
    tg_app.add_handler(CallbackQueryHandler(btn))
    tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND,handle_msg))
    print("BOT V6 STARTED")
    tg_app.run_polling()

if __name__=="__main__":
    main()            
