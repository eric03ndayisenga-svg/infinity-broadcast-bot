import os
from threading import Thread
from flask import Flask
import json, asyncio
from datetime import datetime, timedelta, time as dtime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.constants import ChatType

START_TIME = datetime.now()

# --- WEB SERVER - KUGIRANGO RENDER ITARYAMA ---
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "INFINITY V14 LIVE - OK"
@flask_app.route('/health')
def health(): return f"OK - Uptime:{datetime.now()-START_TIME} - G:{len(groups)} - J:{len(jobs)}"
def run_web():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID","0"))
DATABASE_URL = os.getenv("DATABASE_URL","")
DATA="bot_data.json"; SCHED="schedule.json"

# --- DATABASE - JOBS NTIZISIBAMA ---
try:
    import psycopg2
    HAS_PG = bool(DATABASE_URL)
except:
    HAS_PG = False

def pg_conn():
    import psycopg2
    return psycopg2.connect(DATABASE_URL, sslmode='require')
def pg_init():
    if not HAS_PG: return
    try:
        c=pg_conn(); cur=c.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS store (k TEXT PRIMARY KEY, v TEXT)")
        c.commit(); c.close(); print("✅ Postgres OK - Jobs ntizisibama!")
    except Exception as e: print(f"Postgres fail: {e}")
def pg_save(k,v):
    if not HAS_PG: return
    try:
        c=pg_conn(); cur=c.cursor()
        cur.execute("INSERT INTO store(k,v) VALUES(%s,%s) ON CONFLICT(k) DO UPDATE SET v=EXCLUDED.v",(k,json.dumps(v)))
        c.commit(); c.close()
    except Exception as e: print(e)
def pg_load(k,default):
    if not HAS_PG: return default
    try:
        c=pg_conn(); cur=c.cursor(); cur.execute("SELECT v FROM store WHERE k=%s",(k,)); r=cur.fetchone(); c.close()
        return json.loads(r[0]) if r else default
    except: return default

def load_data():
    if HAS_PG:
        return pg_load("groups",{}),{},{},[],pg_load("keywords",{}),pg_load("settings",{"welcome":True,"anti_link":False})
    try:
        with open(DATA,"r") as f:
            d=json.load(f); return d.get("groups",{}),d.get("pending",{}),d.get("banned",[]),d.get("logs",[]),d.get("keywords",{}),d.get("settings",{"welcome":True,"anti_link":False})
    except: return {},{},{},[],{},{"welcome":True,"anti_link":False}
def save_data(g,p,b,l,k,s):
    if HAS_PG: pg_save("groups",g); pg_save("keywords",k); pg_save("settings",s); return
    with open(DATA,"w") as f: json.dump({"groups":g,"pending":p,"banned":b,"logs":l,"keywords":k,"settings":s},f,indent=2)
def load_sched():
    if HAS_PG: return pg_load("jobs",[])
    try:
        with open(SCHED,"r") as f: return json.load(f)
    except: return []
def save_sched(s):
    if HAS_PG: pg_save("jobs",s); return
    with open(SCHED,"w") as f: json.dump(s,f,indent=2)

pg_init()
groups,pending,banned,logs,keywords,settings=load_data()
jobs=load_sched()
print(f"🚀 V14 YatangiYe - G:{len(groups)} J:{len(jobs)} DB:{HAS_PG}")

async def is_admin(u): return u.effective_user.id==ADMIN

# --- AUTO LOOP - IKORA NEZA BYOSE ---
async def loop_job(tg_app):
    print("🔄 LOOP V14 YATANGIYE")
    await asyncio.sleep(10)
    while True:
        try:
            now=datetime.now()
            for job in jobs[:]:
                if job.get("type")=="daily":
                    target=dtime(job.get("hour",8),job.get("minute",0))
                    today=datetime.combine(now.date(),target)
                    if now>=today and job.get("last_sent","")!=now.date().isoformat():
                        for gid in list(groups.keys()):
                            try: await tg_app.bot.send_message(chat_id=int(gid), text=job["text"]); await asyncio.sleep(0.3)
                            except Exception as e: print(f"Daily fail {gid}: {e}")
                        job["last_sent"]=now.date().isoformat(); save_sched(jobs)
                else:
                    nxt=datetime.fromisoformat(job["next_run"])
                    if now>=nxt:
                        print(f"📤 AUTO YOHEREZA: {job['text'][:30]}")
                        for gid in list(groups.keys()):
                            try: await tg_app.bot.send_message(chat_id=int(gid), text=job["text"]); print(f"✅ {gid}"); await asyncio.sleep(0.3)
                            except Exception as e: print(f"❌ {gid}: {e}")
                        job["next_run"]=(now+timedelta(minutes=job["interval_minutes"])).isoformat(); save_sched(jobs)
        except Exception as e: print(f"Loop error: {e}")
        await asyncio.sleep(30)

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 OHEREZA UBU - BOT UBWAYO",callback_data="send_now")],
        [InlineKeyboardButton("🎯 OHEREZA MURI GROUPE 1",callback_data="send_one")],
        [InlineKeyboardButton("⏰ AUTO BURI MINOTA",callback_data="auto_start")],
        [InlineKeyboardButton("🕗 AUTO KU ISHAHA (08:00)",callback_data="auto_daily")],
        [InlineKeyboardButton(f"👥 G:{len(groups)}",callback_data="list_groups"),InlineKeyboardButton(f"⏰ J:{len(jobs)}",callback_data="sched_list")],
        [InlineKeyboardButton("💬 KEYWORDS",callback_data="kw_list"),InlineKeyboardButton("🛡️ ANTI-LINK",callback_data="anti_link")],
        [InlineKeyboardButton("📊 STATS",callback_data="stats"),InlineKeyboardButton("🔍 DEBUG",callback_data="debug_btn")],
        [InlineKeyboardButton("⏱️ UPTIME",callback_data="uptime_btn"),InlineKeyboardButton("⚙️ SET",callback_data="set")],
    ])

async def start(update,context):
    chat=update.effective_chat; gid=str(chat.id)
    if chat.type in [ChatType.GROUP,ChatType.SUPERGROUP]:
        if gid not in groups:
            groups[gid]={"title":chat.title,"added_at":datetime.now().isoformat()}; save_data(groups,pending,banned,logs,keywords,settings)
        await update.message.reply_text(f"V14 ✅\n{chat.title}\nEMEWE - AUTO YEMEJWE - Ndi MEMBER gusa")
        return
    if not await is_admin(update):
        await update.message.reply_text("Muraho! V14 👋"); return
    db="Postgres ✅ ntisibama" if HAS_PG else "JSON ⚠️ Shyiramo DATABASE_URL"
    txt=f"👑 INFINITY V14 FINAL 👑\n\nG:{len(groups)} | J:{len(jobs)}\nDB: {db}\nLIVE 🟢\n\nByose bikora neza!"
    await update.message.reply_text(txt,reply_markup=main_kb())

async def uptime_cmd(update,context):
    if not await is_admin(update): return
    await update.message.reply_text(f"⏱️ UPTIME\n{datetime.now()-START_TIME}\nG:{len(groups)} | J:{len(jobs)}\nLIVE 🟢")
async def debug_cmd(update,context):
    if not await is_admin(update): return
    txt=f"🔍 DEBUG\nG:{len(groups)} | J:{len(jobs)} | DB:{HAS_PG}\n\n"
    for j in jobs: txt+=f"• {j.get('type','interval')} - {j['text'][:25]}\n"
    await update.message.reply_text(txt or "Nta job")

async def handle_msg(update,context):
    chat=update.effective_chat; text=update.message.text or ""
    if chat.type in [ChatType.GROUP,ChatType.SUPERGROUP] and settings.get("anti_link"):
        if "http://" in text or "https://" in text or "t.me/" in text:
            try: await update.message.delete(); await update.message.reply_text("❌ Link ntayemerewe!"); return
            except: pass
    if await is_admin(update) and chat.type==ChatType.PRIVATE:
        if context.user_data.get("kw_add"):
            if text=="/cancel": context.user_data["kw_add"]=False; await update.message.reply_text("❌ Byanze"); return
            if "|" in text:
                k,v=text.split("|",1); keywords[k.strip().lower()]=v.strip(); save_data(groups,pending,banned,logs,keywords,settings); context.user_data["kw_add"]=False
                await update.message.reply_text(f"✅ Keyword yongewe!\n'{k.strip()}' -> '{v.strip()}'"); return
            await update.message.reply_text("Andika nka: hello | Muraho!"); return
        if context.user_data.get("auto_daily_step")=="wait_msg":
            context.user_data["auto_daily_msg"]=text; context.user_data["auto_daily_step"]="wait_time"
            await update.message.reply_text("🕗 Ni saa ingahe? Andika nka: 08:00"); return
        if context.user_data.get("auto_daily_step")=="wait_time":
            try: h,m=map(int,text.strip().split(":")); context.user_data["auto_daily_step"]=None
            except: await update.message.reply_text("Andika nka 08:00"); return
            msg=context.user_data.get("auto_daily_msg","")
            jobs.append({"id":f"daily_{int(datetime.now().timestamp())}","type":"daily","hour":h,"minute":m,"text":msg,"last_sent":""}); save_sched(jobs)
            await update.message.reply_text(f"✅ AUTO KU ISHAHA!\nBuri munsi saa {h:02d}:{m:02d}\n{msg}"); return
        if context.user_data.get("send_one_gid"):
            gid=context.user_data["send_one_gid"]
            try: await context.bot.send_message(chat_id=int(gid), text=text); await update.message.reply_text(f"✅ Yoherejwe muri {groups.get(gid,{}).get('title',gid)}")
            except Exception as e: await update.message.reply_text(f"❌ {e}")
            context.user_data["send_one_gid"]=None; return
        if context.user_data.get("edit_job_id"):
            if text=="/cancel": context.user_data["edit_job_id"]=None; await update.message.reply_text("❌ Byanze"); return
            try: new_mins=int(text.strip())
            except: await update.message.reply_text("Andika numero gusa"); return
            for j in jobs:
                if j["id"]==context.user_data["edit_job_id"]: j["interval_minutes"]=new_mins; j["next_run"]=(datetime.now()+timedelta(minutes=new_mins)).isoformat(); break
            save_sched(jobs); context.user_data["edit_job_id"]=None; await update.message.reply_text(f"✅ Buri {new_mins} min"); return
        if context.user_data.get("auto_step")=="wait_msg":
            if text=="/cancel": context.user_data["auto_step"]=None; await update.message.reply_text("❌ Byanze"); return
            context.user_data["auto_msg"]=text; context.user_data["auto_step"]="wait_interval"; await update.message.reply_text("⏰ Buri minota ingahe? 30 / 60 / 1440"); return
        if context.user_data.get("auto_step")=="wait_interval":
            try: mins=int(text.strip())
            except: await update.message.reply_text("Andika numero gusa"); return
            context.user_data["auto_interval"]=mins; context.user_data["auto_step"]=None
            kb=[[InlineKeyboardButton("✅ YEMEZA - YOHEREZA UBU",callback_data="auto_yes")],[InlineKeyboardButton("❌ OYA",callback_data="auto_no")]]
            await update.message.reply_text(f"Uremeza buri {mins} min?\n\n{context.user_data.get('auto_msg','')}",reply_markup=InlineKeyboardMarkup(kb)); return
        if context.user_data.get("broad"):
            if text=="/cancel": context.user_data["broad"]=False; await update.message.reply_text("❌ Stopped"); return
            c=0; fail=0
            for gid in list(groups.keys()):
                try:
                    if update.message.photo: await context.bot.send_photo(chat_id=int(gid), photo=update.message.photo[-1].file_id, caption=update.message.caption or "")
                    elif update.message.video: await context.bot.send_video(chat_id=int(gid), video=update.message.video.file_id, caption=update.message.caption or "")
                    else: await context.bot.send_message(chat_id=int(gid), text=text)
                    c+=1
                except: fail+=1
                await asyncio.sleep(0.3)
            context.user_data["broad"]=False; await update.message.reply_text(f"✅ BOT YOHEREJE NKA BOT UBWAYO!\n📤 {c}/{len(groups)} | ❌ {fail}"); return
    if chat.type in [ChatType.GROUP,ChatType.SUPERGROUP]:
        gid=str(chat.id)
        if gid in groups:
            low=text.lower()
            for k,v in keywords.items():
                if k in low: await update.message.reply_text(v); break

async def new_mem(update,context):
    chat=update.effective_chat; gid=str(chat.id)
    for m in update.message.new_chat_members:
        if m.id==context.bot.id:
            if gid not in groups: groups[gid]={"title":chat.title,"added_at":datetime.now().isoformat()}; save_data(groups,pending,banned,logs,keywords,settings)
            await update.message.reply_text("✅ V14 Added! AUTO YEMEJWE.")
        elif settings.get("welcome"):
            await update.message.reply_text(f"👋 Murakaza neza {m.first_name} muri {chat.title}!")

async def btn(update,context):
    q=update.callback_query; await q.answer(); d=q.data
    if not await is_admin(update): return
    if d=="send_now": context.user_data["broad"]=True; await q.edit_message_text("✍️ Ohereza message BOT yohereza ubu:\n/cancel kwanga"); return
    if d=="send_one":
        kb=[]
        for gid,info in groups.items(): kb.append([InlineKeyboardButton(f"📤 {info.get('title','G')}",callback_data=f"one_{gid}")])
        kb.append([InlineKeyboardButton("⬅️ Back",callback_data="back")])
        await q.edit_message_text("Hitamo groupe:",reply_markup=InlineKeyboardMarkup(kb)); return
    if d.startswith("one_"):
        gid=d.replace("one_",""); context.user_data["send_one_gid"]=gid; await q.edit_message_text(f"✍️ Andika message yo kohereza muri {groups.get(gid,{}).get('title','')} gusa:"); return
    if d=="auto_start": context.user_data["auto_step"]="wait_msg"; await q.edit_message_text("✍️ Ohereza message ya AUTO:\n/cancel kwanga"); return
    if d=="auto_daily": context.user_data["auto_daily_step"]="wait_msg"; await q.edit_message_text("✍️ Ohereza message ya AUTO KU ISHAHA:\n/cancel kwanga"); return
    if d=="auto_yes":
        msg=context.user_data.get("auto_msg",""); interval=context.user_data.get("auto_interval",60)
        jobs.append({"id":f"auto_{len(jobs)+1}_{int(datetime.now().timestamp())}","text":msg,"interval_minutes":interval,"next_run":(datetime.now()+timedelta(minutes=interval)).isoformat()}); save_sched(jobs)
        c=0
        for gid in list(groups.keys()):
            try: await context.bot.send_message(chat_id=int(gid), text=msg); c+=1
            except: pass
            await asyncio.sleep(0.3)
        await q.edit_message_text(f"✅ AUTO IKORA NEZA BYOSE!\n\n📤 Yoherejwe ubu: {c}/{len(groups)}\n⏰ Izongera buri {interval} min.\nDB: {'Postgres ✅' if HAS_PG else 'JSON'}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]])); return
    if d=="auto_no": context.user_data["auto_step"]=None; await q.edit_message_text("❌ Byanze",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]])); return
    if d.startswith("edit_"):
        jid=d.replace("edit_",""); context.user_data["edit_job_id"]=jid; await q.edit_message_text("✏️ Andika igihe GISHYA mu minota. 30 / 60\n/cancel kwanga"); return
    if d=="kw_list":
        txt="💬 KEYWORDS:\n\n" + "\n".join([f"• {k} -> {v}" for k,v in keywords.items()]) if keywords else "Nta keyword"
        kb=[[InlineKeyboardButton("➕ Yongeramo",callback_data="kw_add")],[InlineKeyboardButton("🗑️ Siba Zose",callback_data="kw_clear")],[InlineKeyboardButton("⬅️ Back",callback_data="back")]]
        await q.edit_message_text(txt[:2000],reply_markup=InlineKeyboardMarkup(kb)); return
    if d=="kw_add": context.user_data["kw_add"]=True; await q.edit_message_text("✍️ Andika nka:\nhello | Muraho!"); return
    if d=="kw_clear": keywords.clear(); save_data(groups,pending,banned,logs,keywords,settings); await q.edit_message_text("✅ Zasibwe"); return
    if d=="anti_link":
        settings["anti_link"]=not settings.get("anti_link",False); save_data(groups,pending,banned,logs,keywords,settings)
        await q.edit_message_text(f"🛡️ ANTI-LINK: {'ON ✅' if settings['anti_link'] else 'OFF ❌'}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]])); return
    if d=="list_groups":
        t="\n".join([f"{info.get('title','G')} | {gid}" for gid,info in groups.items()])
        await q.edit_message_text(t[:3000] or "Nta group",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
    elif d=="stats": await q.edit_message_text(f"📊 STATS\nG:{len(groups)} J:{len(jobs)} Keywords:{len(keywords)}\nAnti-Link:{settings.get('anti_link')}\nDB:{'Postgres ✅' if HAS_PG else 'JSON'}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
    elif d=="debug_btn": await q.edit_message_text(f"🔍 DEBUG\nG:{len(groups)} J:{len(jobs)} DB:{HAS_PG}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
    elif d=="uptime_btn":
        await q.edit_message_text(f"⏱️ UPTIME\n{datetime.now()-START_TIME}\nG:{len(groups)} J:{len(jobs)}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]]))
    elif d=="sched_list":
        if not jobs: await q.edit_message_text("Nta job",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="back")]])); return
        kb=[]; txt="⏰ JOBS:\n\n"
        for j in jobs:
            if j.get("type")=="daily": txt+=f"• Buri munsi {j['hour']:02d}:{j['minute']:02d}: {j['text'][:20]}\n"
            else: txt+=f"• Buri {j['interval_minutes']} min: {j['text'][:20]}\n"; kb.append([InlineKeyboardButton(f"✏️ {j['text'][:15]}",callback_data=f"edit_{j['id']}")])
        kb.append([InlineKeyboardButton("🗑️ Clear Zose",callback_data="clear_jobs")]); kb.append([InlineKeyboardButton("⬅️ Back",callback_data="back")])
        await q.edit_message_text(txt[:2000],reply_markup=InlineKeyboardMarkup(kb))
    elif d=="clear_jobs": jobs.clear(); save_sched(jobs); await q.edit_message_text("✅ Cleared")
    elif d=="set":
        kb=[[InlineKeyboardButton(f"Welcome:{settings.get('welcome')}",callback_data="tw")],[InlineKeyboardButton(f"Anti-Link:{settings.get('anti_link')}",callback_data="anti_link")],[InlineKeyboardButton("⬅️ Back",callback_data="back")]]
        await q.edit_message_text("⚙️ Settings",reply_markup=InlineKeyboardMarkup(kb))
    elif d=="tw": settings["welcome"]=not settings.get("welcome",True); save_data(groups,pending,banned,logs,keywords,settings); await q.edit_message_text(f"Welcome:{settings.get('welcome')}")
    elif d=="back": await q.edit_message_text(f"👑 INFINITY V14 👑\n\nG:{len(groups)} | J:{len(jobs)}\nLIVE 🟢",reply_markup=main_kb())

async def post_init(tg_app): asyncio.create_task(loop_job(tg_app))
async def run_bot(tg_app):
    await tg_app.initialize(); await tg_app.start(); await tg_app.updater.start_polling()
    while True: await asyncio.sleep(3600)
def main():
    tg_app = Application.builder().token(TOKEN).post_init(post_init).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("uptime", uptime_cmd))
    tg_app.add_handler(CommandHandler("debug", debug_cmd))
    tg_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_mem))
    tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msg))
    tg_app.add_handler(CallbackQueryHandler(btn))
    asyncio.run(run_bot(tg_app))
if __name__ == '__main__': main()
