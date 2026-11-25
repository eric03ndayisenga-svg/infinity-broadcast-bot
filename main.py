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

flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "INFINITY BOT V9 LIVE - OK"
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
                            await tg_app.bot.send_message(chat_id=int(gid), text=txt)
                            await asyncio.sleep(0.3)
                        except: pass
                    job["next_run"]=(now+timedelta(minutes=job["interval_minutes"])).isoformat()
                    save_sched(jobs)
        except: pass
        await asyncio.sleep(30)

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📢 BROADCAST ALL {len(groups)}",callback_data="broadcast_all")],
        [InlineKeyboardButton("⏰ AUTO MSG - YEMEZA",callback_data="auto_start")],
        [InlineKeyboardButton(f"👥 G:{len(groups)}",callback_data="list_groups"),InlineKeyboardButton(f"⏳ P:{len(pending)}",callback_data="list_pending")],
        [InlineKeyboardButton("⏰ JOBS - HINDURA IGIHE",callback_data="sched_list"),InlineKeyboardButton("📊 STATS",callback_data="stats")],
        [InlineKeyboardButton("⚙️ SET",callback_data="set"),InlineKeyboardButton("🤖 AI",callback_data="ai")],
    ])

async def start(update,context):
    chat=update.effective_chat
    gid=str(chat.id)
    if chat.type in [ChatType.GROUP,ChatType.SUPERGROUP]:
        if gid not in groups and gid not in pending:
            pending[gid]={"title":chat.title,"added_at":datetime.now().isoformat()}
            save_data(groups,pending,banned,logs,keywords,settings)
        st="EMEWE ✅" if gid in groups else "TEGEREJE ⏳"
        await update.message.reply_text(f"V9\n{chat.title}\n{st}\nNdi MEMBER gusa.")
        return
    if not await is_admin(update):
        await update.message.reply_text("Muraho V9! 👋")
        return
    txt=f"👑 INFINITY V9 PANEL 👑\n\nG:{len(groups)} | P:{len(pending)} | J:{len(jobs)}\nLIVE 🟢\n\n⏰ AUTO MSG: Wemeza, Yiyohereza\n✏️ Wowe uhindura IGIHE igihe ushaka\n✅ NTIBISABA ADMIN"
    await update.message.reply_text(txt,reply_markup=main_kb(),parse_mode="Markdown")

async def broad_cmd(update,context):
    if not await is_admin(update): return
    await update.message.reply_text("✍️ Send msg to broadcast / /cancel")
    context.user_data["broad"]=True

async def auto_cmd(update,context):
    if not await is_admin(update): return
    context.user_data["auto_step"]="wait_msg"
    await update.message.reply_text("✍️ Ohereza message ushaka ko yiyohereza AUTOMATIC:\n\n/cancel kwanga")

async def handle_msg(update,context):
    chat=update.effective_chat
    text=update.message.text or ""
    if await is_admin(update) and chat.type==ChatType.PRIVATE:
        # --- HINDURA IGIHE ---
        if context.user_data.get("edit_job_id"):
            if text=="/cancel":
                context.user_data["edit_job_id"]=None
                await update.message.reply_text("❌ Byanze guhindura igihe")
                return
            try:
                new_mins=int(text.strip())
            except:
                await update.message.reply_text("Andika numero gusa. Urugero: 30")
                return
            if new_mins < 1:
                await update.message.reply_text("Shyiramo numero > 0")
                return
            jid=context.user_data.get("edit_job_id")
            found=False
            for j in jobs:
                if j["id"]==jid:
                    j["interval_minutes"]=new_mins
                    j["next_run"]=(datetime.now()+timedelta(minutes=new_mins)).isoformat()
                    found=True
                    break
            if found:
                save_sched(jobs)
                await update.message.reply_text(f"✅ IGIHE CYAHINDUTSE!\n\nUbu izajya yoherezwa buri {new_mins} min.\nIzohereza ubutaha: {new_mins} min uhereye ubu.")
            else:
                await update.message.reply_text("❌ Job ntiyabonetse")
            context.user_data["edit_job_id"]=None
            return
        # --- AUTO MSG FLOW ---
        if context.user_data.get("auto_step")=="wait_msg":
            if text=="/cancel":
                context.user_data["auto_step"]=None
                await update.message.reply_text("❌ Byanze")
                return
            context.user_data["auto_msg"]=text
            context.user_data["auto_step"]="wait_interval"
            await update.message.reply_text("⏰ Ni buri minota ingahe yoherezwa?\n\n30 = buri 30 min\n60 = buri saha\n1440 = buri munsi")
            return
        if context.user_data.get("auto_step")=="wait_interval":
            try:
                mins=int(text.strip())
            except:
                await update.message.reply_text("Andika numero gusa. Urugero: 60")
                return
            context.user_data["auto_interval"]=mins
            context.user_data["auto_step"]=None
            msg=context.user_data.get("auto_msg","")
            kb=[[InlineKeyboardButton("✅ YEMEZA - YOHEREZA",callback_data="auto_yes")],[InlineKeyboardButton("❌ OYA",callback_data="auto_no")]]
            await update.message.reply_text(f"Uremeza iyi message yoherezwa buri {mins} min?\n\n---\n{msg}\n---",reply_markup=InlineKeyboardMarkup(kb))
            return
        if context.user_data.get("broad"):
            if text=="/cancel":
                context.user_data["broad"]=False
                await update.message.reply_text("❌ Stopped")
                return
            c=0
            for gid in list(groups.keys()):
                try:
                    await context.bot.copy_message(chat_id=int(gid),from_chat_id=chat.id,message_id=update.message.message_id)
                    c+=1
                except:
                    try:
                        await context.bot.send_message(chat_id=int(gid), text=text)
                        c+=1
                    except: pass
                await asyncio.sleep(0.3)
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
                await update.message.reply_text("✅ V9 Added! Ndi MEMBER gusa, sinshaka ADMIN.")

async def btn(update,context):
    q=update.callback_query
    await q.answer()
    d=q.data
    if not await is_admin(update): return
    if d=="auto_start":
        context.user_data["auto_step"]="wait_msg"
        await q.edit_message_text("✍️ Ohereza message ushaka ko yiyohereza AUTOMATIC:\n\n/cancel kwanga")
        return
    if d=="auto_yes":
        msg=context.user_data.get("auto_msg","")
        interval=context.user_data.get("auto_interval",60)
        new_job={"id":f"auto_{len(jobs)+1}_{int(datetime.now().timestamp())}","text":msg,"interval_minutes":interval,"next_run":(datetime.now()+timedelta(minutes=interval)).isoformat()}
        jobs.append(new_job)
        save_sched(jobs)
        await q.edit_message_text(f"✅ YEMEJWE!\n\nBuri {interval} min.\nKuyihindura igihe: JOBS -> HINDURA",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
        return
    if d=="auto_no":
        context.user_data["auto_step"]=None
        await q.edit_message_text("❌ Byanze.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
        return
    # --- HINDURA IGIHE BUTTON ---
    if d.startswith("edit_"):
        jid=d.replace("edit_","")
        context.user_data["edit_job_id"]=jid
        # Shaka job
        cur="?"
        for j in jobs:
            if j["id"]==jid:
                cur=j["interval_minutes"]
                break
        await q.edit_message_text(f"✏️ HINDURA IGIHE\n\nIgihe cya kera: buri {cur} min\n\nAndika igihe GISHYA mu minota.\nUrugero:\n30 = buri 30 min\n60 = buri saha\n120 = buri 2h\n\n/cancel kwanga")
        return
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
        if not jobs:
            await q.edit_message_text("Nta job", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
            return
        kb=[]
        txt="⏰ AUTO MSG ZOSE - HINDURA IGIHE:\n\n"
        for j in jobs:
            txt+=f"• Buri {j['interval_minutes']} min: {j['text'][:30]}\n"
            kb.append([InlineKeyboardButton(f"✏️ HINDURA - Buri {j['interval_minutes']}m: {j['text'][:15]}",callback_data=f"edit_{j['id']}")])
        kb.append([InlineKeyboardButton("🗑️ Clear Zose",callback_data="clear_jobs")])
        kb.append([InlineKeyboardButton("⬅️ Back",callback_data="back")])
        await q.edit_message_text(txt[:2000], reply_markup=InlineKeyboardMarkup(kb))
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
        txt=f"👑 INFINITY V9 PANEL 👑\n\nG:{len(groups)} | P:{len(pending)} | J:{len(jobs)}\nLIVE 🟢"
        await q.edit_message_text(txt,reply_markup=main_kb(),parse_mode="Markdown")
    elif d=="ai":
        await q.edit_message_text("🤖 /ai question")

async def post_init(tg_app):
    asyncio.create_task(loop_job(tg_app))

def main():
    tg_app=Application.builder().token(TOKEN).post_init(post_init).build()
    tg_app.add_handler(CommandHandler("start",start))
    tg_app.add_handler(CommandHandler("broadcast",broad_cmd))
    tg_app.add_handler(CommandHandler("auto",auto_cmd))
    tg_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS,new_mem))
    tg_app.add_handler(CallbackQueryHandler(btn))
    tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND,handle_msg))
    print("BOT V9 STARTED")
    tg_app.run_polling()

if __name__=="__main__":
    main()
