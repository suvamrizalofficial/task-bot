import json
import os
from datetime import time

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

TOKEN = "8494060018:AAGxAtWLVRbiTfDpbll703_bAtWIG5OjCDE"

TASK, PRIORITY = range(2)

user_data = {}
FILE = "tasks.json"

# ---------- LOAD / SAVE ----------
def load_tasks():
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            data = json.load(f)

        # auto-fix old data
        for user_id in data:
            for task in data[user_id]:
                if "status" not in task:
                    task["status"] = "pending"

        return data
    return {}

def save_tasks(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)

tasks_db = load_tasks()

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Task Bot Active\n\n"
        "/addtask - Add task\n"
        "/tasks - View tasks\n"
        "/done <num> - Complete task"
    )

# ---------- ADD TASK ----------
async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✍️ Enter task:")
    return TASK

async def get_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    task_text = update.message.text

    user_data[user_id] = {"task": task_text}

    keyboard = [
        ["1 - Urgent & Important"],
        ["2 - Urgent & Not Important"],
        ["3 - Not Urgent & Important"],
        ["4 - Not Urgent & Not Important"]
    ]

    await update.message.reply_text(
        "📊 Choose priority:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )

    return PRIORITY

async def set_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    priority = update.message.text
    task = user_data[user_id]["task"]

    if user_id not in tasks_db:
        tasks_db[user_id] = []

    tasks_db[user_id].append({
        "task": task,
        "priority": priority,
        "status": "pending"
    })

    save_tasks(tasks_db)

    await update.message.reply_text(
        f"✅ Saved!\n\n📝 {task}\n📊 {priority}"
    )

    return ConversationHandler.END

# ---------- SHOW TASKS ----------
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)

    user_tasks = tasks_db.get(user_id, [])
    pending = [t for t in user_tasks if t.get("status") == "pending"]

    if not pending:
        await update.message.reply_text("🎉 No pending tasks!")
        return

    msg = "📌 Pending Tasks:\n\n"
    for i, t in enumerate(pending, start=1):
        msg += f"{i}. {t['task']} ({t['priority']})\n"

    await update.message.reply_text(msg)

# ---------- DONE ----------
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)

    if user_id not in tasks_db:
        await update.message.reply_text("No tasks found.")
        return

    try:
        index = int(context.args[0]) - 1
    except:
        await update.message.reply_text("Usage: /done 1")
        return

    user_tasks = tasks_db[user_id]
    pending = [t for t in user_tasks if t.get("status") == "pending"]

    if index < 0 or index >= len(pending):
        await update.message.reply_text("Invalid task number.")
        return

    target = pending[index]

    for t in user_tasks:
        if t["task"] == target["task"] and t.get("status") == "pending":
            t["status"] = "done"
            break

    save_tasks(tasks_db)

    await update.message.reply_text(f"🎯 Done:\n{target['task']}")

# ---------- DAILY REMINDER ----------
async def remind(context: ContextTypes.DEFAULT_TYPE):
    for user_id, tasks in tasks_db.items():
        pending = [t for t in tasks if t.get("status") == "pending"]

        if pending:
            msg = "⏰ Reminder: You have pending tasks:\n\n"
            for i, t in enumerate(pending, start=1):
                msg += f"{i}. {t['task']} ({t['priority']})\n"

            await context.bot.send_message(chat_id=user_id, text=msg)

# ---------- CANCEL ----------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled")
    return ConversationHandler.END

# ---------- BOT SETUP ----------
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("addtask", addtask)],
    states={
        TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task)],
        PRIORITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_priority)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("tasks", show_tasks))
app.add_handler(CommandHandler("done", done))
app.add_handler(conv_handler)

# 🔥 SCHEDULE REMINDER (every 60 minutes)
job_queue = app.job_queue
job_queue.run_repeating(remind, interval=3600, first=10)

print("🤖 Bot running with reminders...")
app.run_polling()