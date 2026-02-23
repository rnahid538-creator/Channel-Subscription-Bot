import os
import sqlite3
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# =======================
# Environment Variable
# =======================
TOKEN = os.getenv("BOT_TOKEN")  # Render Dashboard এ BOT_TOKEN দিতে হবে
if not TOKEN:
    raise ValueError("⚠️ BOT_TOKEN set করা হয়নি। Environment Variables এ দিন।")

ADMIN_ID = 8534308595  # তোমার Telegram ID বসাও
GROUP_LINK = "https://t.me/+eiFGZcO3yRk5MjVl"

# =======================
# SQLite Database
# =======================
DB_PATH = "/tmp/database.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    expiry TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    user_id INTEGER,
    plan_days INTEGER,
    status TEXT,
    requested_at TEXT
)
""")
conn.commit()

# =======================
# Subscription Plans
# =======================
plans = {
    "3": 3,
    "7": 7,
    "30": 30
}

# =======================
# Start Command
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("৩ দিন - 30 টাকা", callback_data="3")],
        [InlineKeyboardButton("৭ দিন - 70 টাকা", callback_data="7")],
        [InlineKeyboardButton("৩০ দিন - 90 টাকা", callback_data="30")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 সাবস্ক্রিপশন প্ল্যান নির্বাচন করুন:", reply_markup=reply_markup)

# =======================
# Plan Selection
# =======================
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
        f"💰 বিকাশ নাম্বার: 01741374715\n\n"
        f"{plan_days} দিনের সাবস্ক্রিপশন পেতে উপরের নাম্বারে টাকা পাঠিয়ে নিচের বাটনে চাপুন।",
        reply_markup=reply_markup
    )

# =======================
# Payment Done
# =======================
async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    plan_days = context.user_data.get("selected_plan")
    requested_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Payment record
    cursor.execute(
        "INSERT INTO payments(user_id, plan_days, status, requested_at) VALUES (?, ?, ?, ?)",
        (user_id, plan_days, "pending", requested_at)
    )
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("Approve ✅", callback_data=f"approve_{user_id}_{plan_days}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("⏳ আপনার পেমেন্ট যাচাই হচ্ছে।")
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"User {user_id} payment request করেছে।\nPlan: {plan_days} দিন",
        reply_markup=reply_markup
    )

# =======================
# Admin Approve
# =======================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    user_id = int(data[1])
    plan_days = int(data[2])

    expiry_date = datetime.now(timezone.utc) + timedelta(days=plan_days)
    expiry_str = expiry_date.strftime("%Y-%m-%d")

    # Update users table
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET expiry=? WHERE user_id=?", (expiry_str, user_id))
    else:
        cursor.execute("INSERT INTO users(user_id, expiry) VALUES (?, ?)", (user_id, expiry_str))

    # Update payments table
    cursor.execute(
        "UPDATE payments SET status='approved' WHERE user_id=? AND plan_days=? AND status='pending'",
        (user_id, plan_days)
    )
    conn.commit()

    # Notify user
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ আপনার সাবস্ক্রিপশন চালু হয়েছে!\n\nগ্রুপ লিংক:\n{GROUP_LINK}\nসাবস্ক্রিপশন শেষ হবে: {expiry_str}"
    )

    await query.message.edit_text("Approved ✅")

# =======================
# Handlers
# =======================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(plan_selected, pattern="^(3|7|30)$"))
app.add_handler(CallbackQueryHandler(payment_done, pattern="^paid$"))
app.add_handler(CallbackQueryHandler(approve, pattern="^approve_"))

# =======================
# Run Bot
# =======================
app.run_polling()
