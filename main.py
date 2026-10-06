
            
import os,json,asyncio,re
from datetime import datetime,timedelta
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ContextTypes,filters
from telegram.constants import ChatType
import aiohttp

TOKEN=os.getenv("BOT_TOKEN")
ADMIN=int(os.getenv("ADMIN_ID","0"))
DATA="bot_data.json"
SCHED="schedule.json"

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

def add_log(a,d=""):
    t=datetime.now().strftime("%m-%d %H:%M")
    logs.append(f"[{t}] {a}:{d}")
    if len(logs)>100:
        logs.pop(0)
    save_data(groups,pending,banned,logs,keywords,settings)

async def ask_ai(q):
    try:
        k=os.getenv("OPENAI_API_KEY")
        if k:
            async with aiohttp.ClientSession() as s:
                async with s.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":"gpt-3.5-turbo","messages":[{"role":"user","content":q}],"max_tokens":200}) as r:
                    d=await r.json()
                    return d["choices"][0]["message"]["content"]
        return f"AI V6: {q[:100]}"
    except Exception as e:
        return f"Err {str(e)[:50]}"

async def is_admin(u):
    return u.effective_user.id==ADMIN

async def loop_job(app):
    while True:
        try:
            now=datetime.now()
            for job in jobs[:]:
                nxt=datetime.fromisoformat(job["next_run"])
                if now>=nxt:
                    txt=job["text"]
                    sent=0
                    for gid in list(groups.keys()):
                        try:
                            await app.bot.send_message(chat_id=int(gid),text=txt)
                            sent+=1
                            await asyncio.sleep(0.3)
                        except:
                            pass
                    job["next_run"]=(now+timedelta(minutes=job["interval_minutes"])).isoformat()
                    save_sched(jobs)
        except:
            pass
        await asyncio.sleep(30)

async def start(update,context):
    chat=update.effective_chat
    gid=str(chat.id)
    if chat.type in [ChatType.GROUP,ChatType.SUPERGROUP]:
        if gid not in groups and gid not in pending:
            pending[gid]={"title":chat.title,"added_at":datetime.now().isoformat()}
            save_data(groups,pending,banned,logs,keywords,settings)
        st="EMEWE" if gid in groups else "TEGEREJE"
        await update.message.reply_text(f"V6\n{chat.title}\n{st}")
        return
    if not await is_admin(update):
        await update.message.reply_text("Muraho V6!")
        return
    kb=[
        [InlineKeyboardButton(f"ALL {len(groups)}",callback_data="broadcast_all")],
        [InlineKeyboardButton(f"G:{len(groups)}",callback_data="list_groups"),InlineKeyboardButton(f"P:{len(pending)}",callback_data="list_pending")],
        [InlineKeyboardButton("JOBS",callback_data="sched_list"),InlineKeyboardButton("STATS",callback_data="stats")],
        [InlineKeyboardButton("SET",callback_data="set"),InlineKeyboardButton("AI",callback_data="ai")],
    ]
    txt=f"PANEL G:{len(groups)} P:{len(pending)} J:{len(jobs)}"
    await update.message.reply_text(txt,reply_markup=InlineKeyboardMarkup(kb))

async def ai_cmd(update,context):
    if not context.args:
        await update.message.reply_text("/ai question")
        return
    q=" ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id,action="typing")
    ans=await ask_ai(q)
    await update.message.reply_text(ans)

async def sched_cmd(update,context):
    if not await is_admin(update):
        return
    if len(context.args)<2:
        await update.message.reply_text("/schedule 30 text")
        return
    try:
        mins=int(context.args[0])
        msg=" ".join(context.args[1:])
        jid=f"j{len(jobs)+1}"
        job={"id":jid,"text":msg,"interval_minutes":mins,"next_run":(datetime.now()+timedelta(minutes=mins)).isoformat()}
        jobs.append(job)
        save_sched(jobs)
        await update.message.reply_text(f"OK {jid}")
    except Exception as e:
        await update.message.reply_text(f"Err {e}")

async def sched_list(update,context):
    if not await is_admin(update):
        return
    if not jobs:
        await update.message.reply_text("Nta job")
        return
    t=""
    for j in jobs:
        t+=f"{j['id']} {j['interval_minutes']}m\n"
    await update.message.reply_text(t[:3000])

async def sched_clear(update,context):
    if not await is_admin(update):
        return
    jobs.clear()
    save_sched(jobs)
    await update.message.reply_text("Cleared")

async def key_cmd(update,context):
    if not await is_admin(update):
        return
    if len(context.args)<2:
        return
    k=context.args[0].lower()
    v=" ".join(context.args[1:])
    keywords[k]=v
    save_data(groups,pending,banned,logs,keywords,settings)
    await update.message.reply_text("OK")

async def broad_cmd(update,context):
    if not await is_admin(update):
        return
    if update.effective_chat.type!=ChatType.PRIVATE:
        return
    await update.message.reply_text("Send msg")
    context.user_data["broad"]=True

async def handle_msg(update,context):
    chat=update.effective_chat
    text=update.message.text or ""
    if context.user_data.get("broad") and await is_admin(update) and chat.type==ChatType.PRIVATE:
        if text=="/cancel":
            context.user_data["broad"]=False
            await update.message.reply_text("Stopped")
            return
        c=0
        for gid in list(groups.keys()):
            try:
                await context.bot.copy_message(chat_id=int(gid),from_chat_id=chat.id,message_id=update.message.message_id)
                c+=1
                await asyncio.sleep(0.3)
            except:
                pass
        context.user_data["broad"]=False
        await update.message.reply_text(f"Sent {c}")
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
                await update.message.reply_text("V6 Added!")
        else:
            if gid not in groups and gid not in pending:
                pending[gid]={"title":chat.title,"added_at":datetime.now().isoformat()}
                save_data(groups,pending,banned,logs,keywords,settings)
            if settings.get("welcome") and gid in groups:
                await update.message.reply_text(f"Muraho {m.first_name}!")

async def btn(update,context):
    q=update.callback_query
    await q.answer()
    d=q.data
    if not await is_admin(update):
        return
    if d=="list_groups":
        t=""
        for gid,info in groups.items():
            t+=f"{info.get('title','G')} {gid}\n"
        await q.edit_message_text(t[:3000] or "Nta group")
    elif d=="list_pending":
        if not pending:
            await q.edit_message_text("Nta pending")
            return
        kb=[]
        for gid,info in list(pending.items())[:10]:
            kb.append([InlineKeyboardButton(f"YES {info.get('title','G')[:10]}",callback_data=f"ap_{gid}"),InlineKeyboardButton("NO",callback_data=f"rj_{gid}")])
        await q.edit_message_text(f"P:{len(pending)}",reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("ap_"):
        gid=d.split("ap_")[1]
        if gid in pending:
            groups[gid]=pending.pop(gid)
            save_data(groups,pending,banned,logs,keywords,settings)
            await q.edit_message_text("Approved")
    elif d.startswith("rj_"):
        gid=d.split("rj_")[1]
        if gid in pending:
            pending.pop(gid)
            save_data(groups,pending,banned,logs,keywords,settings)
            await q.edit_message_text("Rejected")
    elif d=="broadcast_all":
        await q.edit_message_text("Send msg /cancel")
        context.user_data["broad"]=True
    elif d=="stats":
        await q.edit_message_text(f"G:{len(groups)} P:{len(pending)} J:{len(jobs)}")
    elif d=="sched_list":
        t=""
        for j in jobs:
            t+=f"{j['id']} {j['text'][:20]}\n"
        await q.edit_message_text(t[:2000] or "Nta job")
    elif d=="set":
        kb=[[InlineKeyboardButton(f"W:{settings.get('welcome')}",callback_data="tw")],[InlineKeyboardButton(f"L:{settings.get('anti_link')}",callback_data="tl")]]
        await q.edit_message_text("Set",reply_markup=InlineKeyboardMarkup(kb))
    elif d=="tw":
        settings["welcome"]=not settings.get("welcome",True)
        save_data(groups,pending,banned,logs,keywords,settings)
        await q.edit_message_text(f"W:{settings.get('welcome')}")
    elif d=="tl":
        settings["anti_link"]=not settings.get("anti_link",False)
        save_data(groups,pending,banned,logs,keywords,settings)
        await q.edit_message_text(f"L:{settings.get('anti_link')}")

async def post_init(app):
    asyncio.create_task(loop_job(app))

def main():
    app=Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("ai",ai_cmd))
    app.add_handler(CommandHandler("ask",ai_cmd))
    app.add_handler(CommandHandler("schedule",sched_cmd))
    app.add_handler(CommandHandler("schedule_list",sched_list))
    app.add_handler(CommandHandler("schedule_clear",sched_clear))
    app.add_handler(CommandHandler("keyword",key_cmd))
    app.add_handler(CommandHandler("broadcast",broad_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS,new_mem))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND,handle_msg))
    print("BOT V6 STARTED")
    app.run_polling()

if __name__=="__main__":
    main()
