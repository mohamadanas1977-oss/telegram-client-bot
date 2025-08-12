# Animedesine_support1bot.py
# python-telegram-bot==21.4

import os
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, CallbackQueryHandler, filters
)

# ===== Env Vars من Koyeb =====
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_USERNAME = os.environ["CHANNEL_USERNAME"]     # مثال: @animedesine
CHANNEL_LINK = os.environ["CHANNEL_LINK"]             # مثال: https://t.me/animedesine
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])      # مثال: -4975906769
# ==============================

ASK_CONTACT, ASK_REQUEST = range(2)

# زرّ الاشتراك
def subscribe_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 اشترك بالقناة", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ تم الاشتراك", callback_data="check_sub")]
    ])

# فحص الاشتراك
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        m = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ("member", "administrator", "creator")
    except:
        return False

# /start — ترحيب للجميع ثم منطق التحقق
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or user.full_name or "بك"

    # 1) رسالة ترحيبية (للجميع)
    await update.message.reply_text(
        f"👋 مرحبًا {name}!\n"
        f"يسعدني تواصلك معي 😄\n"
        f"كيف أستطيع خدمتك اليوم؟ 😊"
    )

    # 2) التحقق من الاشتراك
    if await is_member(user.id, context):
        # مشترك مسبقًا → مباشرة نطلب التفاصيل أو وسيلة تواصل
        if user.username:
            context.user_data["contact"] = f"@{user.username}"
            await update.message.reply_text("📝 اكتب تفاصيل طلبك الآن ✨:")
            return ASK_REQUEST
        else:
            contact_btn = KeyboardButton("📱 مشاركة رقم الهاتف", request_contact=True)
            await update.message.reply_text(
                "📞 رجاءً زوّدني بوسيلة للتواصل (رقم هاتفك أو بريدك…)\n"
                "يمكنك مشاركة رقمك بالزر أدناه:",
                reply_markup=ReplyKeyboardMarkup([[contact_btn]], one_time_keyboard=True, resize_keyboard=True)
            )
            return ASK_CONTACT
    else:
        # غير مشترك → رسالة الاشتراك فقط
        await update.message.reply_text(
            "📢 لطفًا اشترك بالقناة أولًا عبر الزر أدناه، ثم اضغط «✅ تم الاشتراك».",
            reply_markup=subscribe_keyboard()
        )
        return ConversationHandler.END

# زر “تم الاشتراك”
async def check_sub_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if not await is_member(user.id, context):
        await query.edit_message_text(
            "❌ ما زلت غير مشترك.\nاشترك ثم اضغط «✅ تم الاشتراك».",
            reply_markup=subscribe_keyboard()
        )
        return ConversationHandler.END

    # صار مشترك الآن → نكمل لجمع التفاصيل
    await query.edit_message_text("✅ تم التحقق من الاشتراك، شكرًا لك! 🙏")

    if user.username:
        context.user_data["contact"] = f"@{user.username}"
        await context.bot.send_message(chat_id=user.id, text="📝 اكتب تفاصيل طلبك الآن ✨:")
        return ASK_REQUEST
    else:
        contact_btn = KeyboardButton("📱 مشاركة رقم الهاتف", request_contact=True)
        await context.bot.send_message(
            chat_id=user.id,
            text="📞 رجاءً زوّدني بوسيلة للتواصل (رقم هاتفك أو بريدك…)\n"
                 "يمكنك مشاركة رقمك بالزر أدناه:",
            reply_markup=ReplyKeyboardMarkup([[contact_btn]], one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_CONTACT

# استقبال وسيلة التواصل
async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        context.user_data["contact"] = update.message.contact.phone_number
        await update.message.reply_text("✅ تم استلام رقمك، شكرًا لك!")
    else:
        context.user_data["contact"] = (update.message.text or "").strip()

    await update.message.reply_text("📝 الآن اكتب تفاصيل طلبك بالتفصيل 📦✨:")
    return ASK_REQUEST

# استقبال تفاصيل الطلب + ملخص للمدير + تأكيد للعميل
async def get_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request_text = (update.message.text or "").strip()
    context.user_data["request"] = request_text

    user = update.effective_user
    contact = context.user_data.get("contact", "غير محدد")

    summary = (
        "📩 <b>طلب جديد</b>\n"
        f"👤 من: <b>{user.full_name}</b>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📞 تواصل: <b>{contact}</b>\n"
        f"📝 الطلب:\n{request_text}"
    )

    # يرسل للمدير فقط
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=summary,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    # 5) تأكيد للعميل
    await update.message.reply_text(
        "✅ تم استلام طلبك! سأتابع معك بأقرب وقت ممكن.\n"
        "شكرًا لك 🙏"
    )

    context.user_data.clear()
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start),
                      CallbackQueryHandler(check_sub_cb, pattern="^check_sub$")],
        states={
            ASK_CONTACT: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), get_contact)],
            ASK_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_request)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_user=True, per_chat=True
    )

    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
