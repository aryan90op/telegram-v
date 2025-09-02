import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ==============================
# ENV VARIABLES
# ==============================
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
allowed_users = set([OWNER_ID])

# ==============================
# STATES
# ==============================
TXT_FILE, TXT_SPLIT, TXT_NAME, TXT_CNAME = range(4)
ADMIN_NUMBERS, ADMIN_NAME, NEAVY_NUMBERS, NEAVY_NAME, FINAL_VCF_NAME = range(5)

# ==============================
# HELPERS
# ==============================
def make_vcf_entry(name, number):
    return f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{number}\nEND:VCARD\n"

async def check_access(update: Update):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text("🚫 Access Denied!\nOnly authorized users can use this bot.")
        return False
    return True

# ==============================
# COMMANDS
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤗 WELCOME!\n\nTHIS BOT WAS MADE BY @random_0988\n\n"
        "Use:\n"
        "• /txtvcf → Convert TXT → VCF\n"
        "• /adminvcf → Create Admin + Neavy VCF\n"
        "• /myid → Get your Telegram ID\n"
    )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")

async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can add users.")
        return
    try:
        uid = int(context.args[0])
        allowed_users.add(uid)
        await update.message.reply_text(f"✅ User {uid} added.")
    except:
        await update.message.reply_text("⚠️ Usage: /adduser <telegram_id>")

async def removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can remove users.")
        return
    try:
        uid = int(context.args[0])
        if uid in allowed_users:
            allowed_users.remove(uid)
            await update.message.reply_text(f"🚫 User {uid} removed.")
        else:
            await update.message.reply_text("⚠️ User not found in allowed list.")
    except:
        await update.message.reply_text("⚠️ Usage: /removeuser <telegram_id>")

# ==============================
# TXT → VCF HANDLER
# ==============================
async def txtvcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return ConversationHandler.END
    await update.message.reply_text("📂 Send me your .txt file with numbers.")
    return TXT_FILE

async def handle_txt_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file = await doc.get_file()
    content = await file.download_as_bytearray()
    numbers = content.decode("utf-8").splitlines()
    context.user_data["numbers"] = [n.strip() for n in numbers if n.strip()]
    await update.message.reply_text(f"✅ Got {len(context.user_data['numbers'])} numbers.\nHow many contacts per VCF?")
    return TXT_SPLIT

async def handle_txt_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["split"] = int(update.message.text)
    await update.message.reply_text("📛 Enter base VCF file name:")
    return TXT_NAME

async def handle_txt_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["vcf_name"] = update.message.text
    await update.message.reply_text("👤 Enter base contact name:")
    return TXT_CNAME

async def handle_txt_cname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cname = update.message.text
    numbers = context.user_data["numbers"]
    split = context.user_data["split"]
    base_name = context.user_data["vcf_name"]

    files = []
    for i in range(0, len(numbers), split):
        part = numbers[i:i+split]
        vcf_content = ""
        for idx, num in enumerate(part, start=1):
            contact_name = f"{cname}{i//split+idx}"
            vcf_content += make_vcf_entry(contact_name, num)
        filename = f"{base_name}{i//split+1}.vcf"
        with open(filename, "w") as f:
            f.write(vcf_content)
        await update.message.reply_document(document=open(filename, "rb"))
        files.append(filename)

    await update.message.reply_text("✅ TXT → VCF conversion complete.")
    return ConversationHandler.END

# ==============================
# ADMIN + NEAVY HANDLER
# ==============================
async def adminvcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return ConversationHandler.END
    await update.message.reply_text("📞 Enter admin numbers (comma separated):")
    return ADMIN_NUMBERS

async def handle_admin_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_numbers"] = [n.strip() for n in update.message.text.split(",") if n.strip()]
    await update.message.reply_text("👤 Enter base name for admin contacts:")
    return ADMIN_NAME

async def handle_admin_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_name"] = update.message.text
    await update.message.reply_text("📞 Enter neavy numbers (comma separated):")
    return NEAVY_NUMBERS

async def handle_neavy_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["neavy_numbers"] = [n.strip() for n in update.message.text.split(",") if n.strip()]
    await update.message.reply_text("👤 Enter base name for neavy contacts:")
    return NEAVY_NAME

async def handle_neavy_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["neavy_name"] = update.message.text
    await update.message.reply_text("💾 Enter final VCF file name:")
    return FINAL_VCF_NAME

async def handle_final_vcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_numbers = context.user_data["admin_numbers"]
    neavy_numbers = context.user_data["neavy_numbers"]
    admin_name = context.user_data["admin_name"]
    neavy_name = context.user_data["neavy_name"]
    filename = update.message.text + ".vcf"

    vcf_content = ""
    for idx, num in enumerate(admin_numbers, start=1):
        vcf_content += make_vcf_entry(f"{admin_name}{idx}", num)
    for idx, num in enumerate(neavy_numbers, start=1):
        vcf_content += make_vcf_entry(f"{neavy_name}{idx}", num)

    with open(filename, "w") as f:
        f.write(vcf_content)

    await update.message.reply_document(document=open(filename, "rb"))
    await update.message.reply_text("✅ Admin + Neavy VCF created.")
    return ConversationHandler.END

# ==============================
# MAIN
# ==============================
def main():
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("adduser", adduser))
    app.add_handler(CommandHandler("removeuser", removeuser))

    # TXT → VCF Conversation
    txt_conv = ConversationHandler(
        entry_points=[CommandHandler("txtvcf", txtvcf)],
        states={
            TXT_FILE: [MessageHandler(filters.Document.FileExtension("txt"), handle_txt_file)],
            TXT_SPLIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_txt_split)],
            TXT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_txt_name)],
            TXT_CNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_txt_cname)],
        },
        fallbacks=[],
    )
    app.add_handler(txt_conv)

    # Admin + Neavy Conversation
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("adminvcf", adminvcf)],
        states={
            ADMIN_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_numbers)],
            ADMIN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_name)],
            NEAVY_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_neavy_numbers)],
            NEAVY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_neavy_name)],
            FINAL_VCF_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_final_vcf)],
        },
        fallbacks=[],
    )
    app.add_handler(admin_conv)

    app.run_polling()

if __name__ == "__main__":
    main()
    
