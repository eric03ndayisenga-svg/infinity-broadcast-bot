import os
from threading import Thread
from flask import Flask
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatType

# --- WEB KEEP ALIVE ---
flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "INFINITY BOT V11 LIVE - OK"
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

# --- AUTO JOB LOOP ---
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
                            # BOT UBWAYO YOHEREZA
                            await tg_app.bot.send_message(chat_id=int(gid), text=txt)
                            await asyncio.sleep(0.3)
                        except Exception as e:
                            print(f"Auto fail {gid}: {e}")
                    job["next_run"]=(now+timedelta(minutes=job["interval_minutes"])).isoformat()
                    save_sched(jobs)
        except Exception as e:
            print(f"loop error: {e}")
        await asyncio.sleep(30)

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 OHEREZA BISANZWE - UBU",callback_data="send_now")],
        [InlineKeyboardButton("⏰ AUTO MSG - YEMEZA",callback_data="auto_start")],
        [InlineKeyboardButton(f"👥 G:{len(groups)}",callback_data="list_groups"),InlineKeyboardButton(f"⏰ JOBS:{len(jobs)}",callback_data="sched_list")],
        [InlineKeyboardButton("📊 STATS",callback_data="stats"),InlineKeyboardButton("⚙️ SET",callback_data="set")],
    ])

async def start(update,context):
    chat=update.effective_chat
    gid=str(chat.id)
    if chat.type in [ChatType.GROUP,ChatType.SUPERGROUP]:
        # AUTO APPROVE - NTA PENDING, NTA ADMIN
        if gid not in groups:
            groups[gid]={"title":chat.title,"added_at":datetime.now().isoformat()}
            save_data(groups,pending,banned,logs,keywords,settings)
        await update.message.reply_text(f"V11 ✅\n{chat.title}\nEMEWE - AUTO YEMEJWE\nNdi MEMBER gusa.")
        return
    if not await is_admin(update):
        await update.message.reply_text("Muraho V11! 👋")
        return
    txt=f"👑 INFINITY V11 PANEL 👑\n\nG:{len(groups)} | J:{len(jobs)}\nLIVE 🟢\n\n📤 BISANZWE: Bot yohereza ubu\n⏰ AUTO: Bot yohereza buri gihe\n✅ NTIBISABA ADMIN - MEMBER gusa"
    await update.message.reply_text(txt,reply_markup=main_kb(),parse_mode="Markdown")

async def handle_msg(update,context):
    chat=update.effective_chat
    text=update.message.text or ""
    if await is_admin(update) and chat.type==ChatType.PRIVATE:
        # --- HINDURA IGIHE ---
        if context.user_data.get("edit_job_id"):
            if text=="/cancel":
                context.user_data["edit_job_id"]=None
                await update.message.reply_text("❌ Byanze")
                return
            try:
                new_mins=int(text.strip())
            except:
                await update.message.reply_text("Andika numero gusa. Urugero: 30")
                return
            jid=context.user_data.get("edit_job_id")
            for j in jobs:
                if j["id"]==jid:
                    j["interval_minutes"]=new_mins
                    j["next_run"]=(datetime.now()+timedelta(minutes=new_mins)).isoformat()
                    break
            save_sched(jobs)
            context.user_data["edit_job_id"]=None
            await update.message.reply_text(f"✅ IGIHE CYAHINDUTSE! Ubu buri {new_mins} min.")
            return
        # --- AUTO STEP 1: MESSAGE ---
        if context.user_data.get("auto_step")=="wait_msg":
            if text=="/cancel":
                context.user_data["auto_step"]=None
                await update.message.reply_text("❌ Byanze")
                return
            context.user_data["auto_msg"]=text
            context.user_data["auto_step"]="wait_interval"
            await update.message.reply_text("⏰ Ni buri minota ingahe?\n30 = buri 30 min\n60 = buri saha\n1440 = buri munsi")
            return
        # --- AUTO STEP 2: INTERVAL ---
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
        # --- OHEREZA BISANZWE - BOT UBWAYO ---
        if context.user_data.get("broad"):
            if text=="/cancel":
                context.user_data["broad"]=False
                await update.message.reply_text("❌ Stopped")
                return
            c=0; fail=0
            for gid in list(groups.keys()):
                try:
                    if update.message.photo:
                        await context.bot.send_photo(chat_id=int(gid), photo=update.message.photo[-1].file_id, caption=update.message.caption or "")
                    elif update.message.video:
                        await context.bot.send_video(chat_id=int(gid), video=update.message.video.file_id, caption=update.message.caption or "")
                    else:
                        await context.bot.send_message(chat_id=int(gid), text=text)
                    c+=1
                except Exception as e:
                    print(f"Send fail {gid}: {e}")
                    fail+=1
                await asyncio.sleep(0.3)
            context.user_data["broad"]=False
            if c>0:
                await update.message.reply_text(f"✅ BOT YOHEREJE NKA BOT UBWAYO!\n📤 {c}/{len(groups)} groups\n❌ Yananiwe: {fail}")
            else:
                await update.message.reply_text(f"❌ NTIGEZE! G:{len(groups)} - Kuramo bot uyisubizemo, muri groupe andika /start")
            return
    # --- GROUP KEYWORDS ---
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
            if gid not in groups:
                groups[gid]={"title":chat.title,"added_at":datetime.now().isoformat()}
                save_data(groups,pending,banned,logs,keywords,settings)
                await update.message.reply_text("✅ V11 Added! Ndi MEMBER gusa. AUTO YEMEJWE.")

async def btn(update,context):
    q=update.callback_query
    await q.answer()
    d=q.data
    if not await is_admin(update): return

    if d=="send_now":
        context.user_data["broad"]=True
        await q.edit_message_text("✍️ Ohereza message BOT yohereza BISANZWE ubu:\n\nAndika message ubu, bot ubwayo iyohereze.\n\n/cancel kwanga")
        return

    if d=="auto_start":
        context.user_data["auto_step"]="wait_msg"
        await q.edit_message_text("✍️ Ohereza message ushaka ko BOT yiyohereza AUTOMATIC:\n\n/cancel kwanga")
        return

    if d=="auto_yes":
        msg=context.user_data.get("auto_msg","")
        interval=context.user_data.get("auto_interval",60)
        new_job={"id":f"auto_{len(jobs)+1}_{int(datetime.now().timestamp())}","text":msg,"interval_minutes":interval,"next_run":(datetime.now()+timedelta(minutes=interval)).isoformat()}
        jobs.append(new_job)
        save_sched(jobs)
        # TEST UB - OHEREZA UBU
        c=0; fail=0
        for gid in list(groups.keys()):
            try:
                await context.bot.send_message(chat_id=int(gid), text=msg)
                c+=1
            except:
                fail+=1
            await asyncio.sleep(0.3)
        if c>0:
            await q.edit_message_text(f"✅ AUTOMATIC IKORA NEZA!\n\n📤 Yoherejwe ubu: {c}/{len(groups)}\n⏰ Izongera buri {interval} min.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
        else:
            await q.edit_message_text(f"❌ NTIGEZE! G:{len(groups)}\nKuramo bot uyisubizemo, muri groupe andika /start", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
        return

    if d=="auto_no":
        context.user_data["auto_step"]=None
        await q.edit_message_text("❌ Byanze.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
        return

    if d.startswith("edit_"):
        jid=d.replace("edit_","")
        context.user_data["edit_job_id"]=jid
        cur="?"
        for j in jobs:
            if j["id"]==jid:
                cur=j["interval_minutes"]
                break
        await q.edit_message_text(f"✏️ HINDURA IGIHE\nIgihe cya kera: buri {cur} min\nAndika igihe GISHYA mu minota.\n30 / 60 / 120\n/cancel kwanga")
        return

    if d=="list_groups":
        t=""
        for gid,info in groups.items():
            t+=f"{info.get('title','G')} | {gid}\n"
        await q.edit_message_text(t[:3000] or "Nta group", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
    elif d=="stats":
        await q.edit_message_text(f"📊 STATS\nG:{len(groups)}\nJ:{len(jobs)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
    elif d=="sched_list":
        if not jobs:
            await q.edit_message_text("Nta job", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
            return
        kb=[]; txt="⏰ AUTO MSG ZOSE:\n\n"
        for j in jobs:
            txt+=f"• Buri {j['interval_minutes']} min: {j['text'][:30]}\n"
            kb.append([InlineKeyboardButton(f"✏️ HINDURA - Buri {j['interval_minutes']}m: {j['text'][:15]}",callback_data=f"edit_{j['id']}")])
        kb.append([InlineKeyboardButton("🗑️ Clear Zose",callback_data="clear_jobs")])
        kb.append([InlineKeyboardButton("⬅️ Back",callback_data="back")])
        await q.edit_message_text(txt[:2000], reply_markup=InlineKeyboardMarkup(kb))
    elif d=="clear_jobs":
        jobs.clear(); save_sched(jobs)
        await q.edit_message_text("✅ Cleared")
    elif d=="set":
        kb=[[InlineKeyboardButton(f"Welcome:{settings.get('welcome')}",callback_data="tw")],[InlineKeyboardButton("⬅️ Back",callback_data="back")]]
        await q.edit_message_text("⚙️ Settings",reply_markup=InlineKeyboardMarkup(kb))
    elif d=="tw":
        settings["welcome"]=not settings.get("welcome",True)
        save_data(groups,pending,banned,logs,keywords,settings)
        await q.edit_message_text(f"Welcome:{settings.get('welcome')}")
    elif d=="back":
        txt=f"👑 INFINITY V11 PANEL 👑\n\nG:{len(groups)} | J:{len(jobs)}\nLIVE 🟢"
        await q.edit_message_text(txt,reply_markup=main_kb(),parse_mode="Markdown")

async def post_init(tg_app):
    asyncio.create_task(loop_job(tg_app))

async def run_bot(tg_app):
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)

def main():
    tg_app = Application.builder().token(TOKEN).post_init(post_init).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_mem))
    tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msg))
    tg_app.add_handler(CallbackQueryHandler(btn))
    asyncio.run(run_bot(tg_app))

if __name__ == '__main__':
    main()
