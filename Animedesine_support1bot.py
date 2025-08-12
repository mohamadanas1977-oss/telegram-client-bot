# main.py
import os
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, CallbackQueryHandler, filters
)

# قراءة القيم من Environment Variables
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]  # ID الجروب الخاص بك بصيغة رقمية

ASK_CONTACT, ASK_REQUEST = range(2)

# التحقق من الاشتراك بالقناة
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        m = await context.bot.get_chat_member(os.environ["CHANNEL_USERNAME"], user_id)
        return m.status in ("member", "administrator", "creator")
    except:
        return False

def subscribe_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 اشترك بالقناة", url=os.environ["CHANNEL_LINK"])],
        [InlineKeyboardButton("✅ تم الاشتراك", callback_data="check_sub")]
    ])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # رسالة ترحيب ودية
    await update.message.reply_text(
        f"👋 مرحبًا {user.first_name or user.full_name or 'بك'}!\n"
        "🤗 يسعدني تواصلك معي!\n"
        "قبل أن نبدأ، يسعدني اشتراكك بقناتي أولًا عبر الزر أدناه، ثم اضغط «✅ تم الاشتراك»."
    )

    # الاشتراك الإجباري
    if not await is_member(user.id, context):
        await update.message.reply_text(
            "اشترك بقناتي عبر الزر أدناه، ثم اضغط «✅ تم الاشتراك».",
            reply_markup=subscribe_keyboard()
        )
        return ConversationHandler.END

    # إذا عنده يوزر، نطلب تفاصيل الطلب مباشرة
    if user.username:
        context.user_data["contact"] = f"@{user.username}"
        await update.message.reply_text("📝 اكتب تفاصيل طلبك أو سؤالك الآن ✨:")
        return ASK_REQUEST
    else:
        # إذا ما عنده يوزر، نطلب وسيلة تواصل
        contact_btn = KeyboardButton("📱 مشاركة رقم الهاتف", request_contact=True)
        await update.message.reply_text(
            "📞 رجاءً زودني بوسيلة للتواصل معك (رقم هاتف أو بريد أو أي وسيلة أخرى) 📬",
            reply_markup=ReplyKeyboardMarkup([[contact_btn]], one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_CONTACT

# زر «تم الاشتراك»
async def check_sub_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if not await is_member(user.id, context):
        await query.edit_message_text(
            "❌ لم يتم العثور على اشتراكك، اشترك ثم اضغط «✅ تم الاشتراك».",
            reply_markup=subscribe_keyboard()
        )
        return ConversationHandler.END

    # إذا عنده يوزر
    if user.username:
        context.user_data["contact"] = f"@{user.username}"
        await context.bot.send_message(
            chat_id=user.id,
            text="📝 اكتب تفاصيل طلبك أو سؤالك الآن ✨:"
        )
        return ASK_REQUEST
    else:
        contact_btn = KeyboardButton("📱 مشاركة رقم الهاتف", request_contact=True)
        await context.bot.send_message(
            chat_id=user.id,
            text="📞 رجاءً زودني بوسيلة للتواصل معك (رقم هاتف أو بريد أو أي وسيلة أخرى) 📬",
            reply_markup=ReplyKeyboardMarkup([[contact_btn]], one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_CONTACT

# استقبال وسيلة التواصل
async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        context.user_data["contact"] = update.message.contact.phone_number
        await update.message.reply_text("✅ تم استلام وسيلة التواصل.")
    else:
        context.user_data["contact"] = update.message.text.strip()

    await update.message.reply_text("📝 اكتب تفاصيل طلبك أو سؤالك بالتفصيل ✨:")
    return ASK_REQUEST

# استقبال تفاصيل الطلب
async def get_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request_text = update.message.text.strip()
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

    # إرسال الملخص للجروب الخاص بك
    await context.bot.send_message(
        chat_id=int(CHAT_ID),
        text=summary,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    # رسالة تأكيد للعميل
    await update.message.reply_text(
        "✅ تم استلام طلبك بنجاح! 🎉\n"
        "سأتواصل معك بأقرب وقت ممكن."
    )

    context.user_data.clear()
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(check_sub_cb, pattern="^check_sub$")
        ],
        states={
            ASK_CONTACT: [MessageHandler((filters.CONTACT | (filters.TEXT & ~filters.COMMAND)), get_contact)],
            ASK_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_request)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_user=True, per_chat=True
    )

    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
