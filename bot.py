import os
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 123456789  # এখানে তোমার Telegram user ID বসাও
GROUP_LINK = "https://t.me/your_private_group_link"

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    expiry TEXT
)
""")
conn.commit()

plans = {
    "3": 3,
    "7": 7,
    "30": 30
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("৩ দিন - ১০০ টাকা", callback_data="3")],
        [InlineKeyboardButton("৭ দিন - ২০০ টাকা", callback_data="7")],
        [InlineKeyboardButton("৩০ দিন - ৫০০ টাকা", callback_data="30")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 সাবস্ক্রিপশন প্ল্যান নির্বাচন করুন:", reply_markup=reply_markup)

async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_days = plans[query.data]
    context.user_data["selected_plan"] = plan_days

    keyboard = [
        [InlineKeyboardButton("আমি পেমেন্ট করেছি ✅", callback_data="paid")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "💰 বিকাশ নাম্বার: 01XXXXXXXXX\n\n"
        "উপরের নাম্বারে টাকা পাঠিয়ে নিচের বাটনে চাপুন।",
        reply_markup=reply_markup
    )

async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    plan_days = context.user_data.get("selected_plan")

    keyboard = [
        [InlineKeyboardButton("Approve ✅", callback_data=f"approve_{user_id}_{plan_days}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("⏳ আপনার পেমেন্ট যাচাই হচ্ছে।")

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"User {user_id} payment request করেছে।",
        reply_markup=reply_markup
    )

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    user_id = int(data[1])
    plan_days = int(data[2])

    expiry_date = datetime.now() + timedelta(days=plan_days)

    cursor.execute("INSERT INTO users VALUES (?, ?)", (user_id, expiry_date.strftime("%Y-%m-%d")))
    conn.commit()

    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ আপনার সাবস্ক্রিপশন চালু হয়েছে!\n\nগ্রুপ লিংক:\n{GROUP_LINK}"
    )

    await query.message.edit_text("Approved ✅")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(plan_selected, pattern="^(3|7|30)$"))
app.add_handler(CallbackQueryHandler(payment_done, pattern="^paid$"))
app.add_handler(CallbackQueryHandler(approve, pattern="^approve_"))

app.run_polling()
