import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from datetime import datetime
import re, csv

BOT_TOKEN = os.environ['BOT_TOKEN']
ADMIN_ID = 7495372506

queue_counter_file = "queue_counter.txt"
user_data_file = "user_data.csv"

districts = [
    "Qon'irat", "Moynaq", "Qanliko'l", "Shomanay", "Beruniy", "To'rtko'l",
    "Ellikqala", "Amudarya", "Taxiyatash", "Xojeli", "No'kis", "No'kis rayon",
    "Bozataw", "Kegeyli", "Shimbay", "Qarao'zek", "Taxtako'pir"
]

def get_next_queue_number():
    if not os.path.exists(queue_counter_file):
        with open(queue_counter_file, "w") as f:
            f.write("1")
        return 1
    with open(queue_counter_file, "r") as f:
        current = int(f.read())
    next_number = current + 1
    with open(queue_counter_file, "w") as f:
        f.write(str(next_number))
    return next_number

def save_user_data(user_id, data):
    file_exists = os.path.exists(user_data_file)
    with open(user_data_file, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["UserID", "Name", "Phone", "District", "Passport", "Queue"])
        writer.writerow([
            user_id, data.get("name"), data.get("phone"),
            data.get("district"), data.get("passport"), data.get("queue_number")
        ])

def is_valid_name(name): return bool(re.match("^[A-Za-zА-Яа-яЁё' ]+$", name))
def is_valid_phone_number(phone): return bool(re.match(r"^\+?[0-9]{10,15}$", phone))
def is_valid_passport(passport): return bool(re.match(r"^[A-Z]{2}\d{7}$", passport))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Assalawma aleykum.\n"
        "Aydawshılıq guwalıǵın alıw ushın test imtixanına elektron náwbet alıw botına xosh keldińiz!\n"
        "Ati familiyan'izni jiberin'"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    if "name" not in context.user_data:
        if is_valid_name(text):
            context.user_data["name"] = text
            button = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
            await update.message.reply_text("Telefon nomeringizni jiberin'", reply_markup=ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True))
        else:
            await update.message.reply_text("Ismingizda faqat harflar bo'lishi kerak.")
    elif text == "📝 Náwbetke jazıluw" and "phone" in context.user_data:
        buttons = [[KeyboardButton(d)] for d in districts]
        await update.message.reply_text("Tumaningizni tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True))
    elif text in districts and "district" not in context.user_data:
        context.user_data["district"] = text
        await update.message.reply_text("Pasport seriyasi hám nomerin'izdi jiberin' (AA1234567)", reply_markup=ReplyKeyboardRemove())
    elif "district" in context.user_data and "passport" not in context.user_data:
        if is_valid_passport(text):
            context.user_data["passport"] = text.upper()
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton("💳 To'lov qilish", callback_data="pay")]])
            await update.message.reply_text("To‘lov kvitansiyasini yuboring yoki tugmani bosing.", reply_markup=buttons)
        else:
            await update.message.reply_text("Xato format! Masalan: AA1234567")
    elif text == "🔍 Náwbetti tekseriw":
        if "queue_number" in context.user_data:
            await update.message.reply_text(f"Sizning navbat raqamingiz: {context.user_data['queue_number']}")
        else:
            await update.message.reply_text("Siz hali navbatga yozilmadingiz.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if "passport" in context.user_data:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "pending_users" not in context.chat_data:
            context.chat_data["pending_users"] = {}
        context.chat_data["pending_users"][user_id] = context.user_data.copy()
        photo_file_id = update.message.photo[-1].file_id
        data = context.user_data
        caption = (
            f"🧾 *Yangi to‘lov!*\n\n"
            f"*Ism:* {data.get('name')}\n"
            f"*Telefon:* {data.get('phone')}\n"
            f"*Tuman:* {data.get('district')}\n"
            f"*Pasport:* {data.get('passport')}\n"
            f"*Telegram ID:* `{user_id}`\n"
            f"*Yuborilgan vaqt:* {now}"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{user_id}")]])
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=caption, parse_mode='Markdown', reply_markup=keyboard)
        await update.message.reply_text("To‘lov tekshirilmoqda. Iltimos, kuting.")
    else:
        await update.message.reply_text("Iltimos, avval kerakli ma'lumotlarni to‘ldiring.")

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    if is_valid_phone_number(phone):
        context.user_data["phone"] = phone
        buttons = [
            [KeyboardButton("📝 Náwbetke jazıluw")],
            [KeyboardButton("🔍 Náwbetti tekseriw")]
        ]
        await update.message.reply_text("Quyidagilardan birini tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    else:
        await update.message.reply_text("Telefon raqam noto‘g‘ri formatda.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "pay":
        await query.edit_message_text(
            "💳 To‘lov uchun karta raqami: 9860 0801 7411 0793\n"
            "Ism: Orazbek Yakupbaev\n"
            "Iltimos, to‘lovni amalga oshiring va screenshotni yuboring."
        )
    elif query.data.startswith("approve_"):
        user_id = int(query.data.split("_")[1])
        user_info = context.chat_data.get("pending_users", {}).get(user_id)
        if user_info:
            queue_number = get_next_queue_number()
            user_info["queue_number"] = queue_number
            save_user_data(user_id, user_info)
            context.chat_data["pending_users"].pop(user_id, None)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ To‘lov tasdiqlandi.\nSizning navbat raqamingiz: {queue_number}",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton("📝 Náwbetke jazıluw")],
                    [KeyboardButton("🔍 Náwbetti tekseriw")]
                ], resize_keyboard=True)
            )
            await query.edit_message_text("✅ To‘lov tasdiqlandi.")
        else:
            await query.edit_message_text("❌ Foydalanuvchi ma'lumotlari topilmadi.")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(CallbackQueryHandler(handle_callback))
app.run_polling()