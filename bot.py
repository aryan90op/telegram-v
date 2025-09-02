import os
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# --- CONFIG ---
BOT_TOKEN = "8446746599:AAHbefmZlzWyUEjB1sGgXfV8EraCdaDUJ9c"   # put your BotFather token
OWNER_ID =  6497509361        # your Telegram numeric ID
ALLOWED_USERS = {OWNER_ID}     # only owner at start

# --- STATES ---
(
    ADMIN_NUMBERS, ADMIN_NAME,
    NEAVY_NUMBERS, NEAVY_NAME,
    VCF_FILENAME,
    TXT_FILE, TXT_SPLIT, TXT_FILENAME, TXT_CONTACTNAME
) = range(9)


# --- OWNER SYSTEM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    await update.message.reply_text("WELCOME 🤗 THIS BOT WAS MADE BY @random_0988\n\nCommands:\n/adminvcf - Create Admin+Neavy VCF\n/txtvcf - Convert TXT → VCF\n/adduser <id>\n/removeuser <id>")


async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        uid = int(context.args[0])
        ALLOWED_USERS.add(uid)
        await update.message.reply_text(f"✅ Added user {uid}")
    except:
        await update.message.reply_text("Usage: /adduser <id>")


async def removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        uid = int(context.args[0])
        ALLOWED_USERS.discard(uid)
        await update.message.reply_text(f"❌ Removed user {uid}")
    except:
        await update.message.reply_text("Usage: /removeuser <id>")


# --- ADMIN + NEAVY ---
async def adminvcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Not authorized.")
        return ConversationHandler.END
    await update.message.reply_text("📌 Send ADMIN numbers separated by commas (,)")
    return ADMIN_NUMBERS


async def admin_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_numbers"] = update.message.text.split(",")
    await update.message.reply_text("✍️ Enter base name for ADMIN (e.g., F)")
    return ADMIN_NAME


async def admin_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_name"] = update.message.text.strip()
    await update.message.reply_text("📌 Send NEAVY numbers separated by commas (,)")
    return NEAVY_NUMBERS


async def neavy_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["neavy_numbers"] = update.message.text.split(",")
    await update.message.reply_text("✍️ Enter base name for NEAVY (e.g., A)")
    return NEAVY_NAME


async def neavy_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["neavy_name"] = update.message.text.strip()
    await update.message.reply_text("💾 Enter filename for VCF (without .vcf)")
    return VCF_FILENAME


async def vcf_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = update.message.text.strip() + ".vcf"
    admin_numbers = context.user_data["admin_numbers"]
    admin_name = context.user_data["admin_name"]
    neavy_numbers = context.user_data["neavy_numbers"]
    neavy_name = context.user_data["neavy_name"]

    contacts = []
    # Admin
    for i, num in enumerate(admin_numbers, 1):
        contacts.append((f"{admin_name}{i}", num.strip()))
    # Neavy
    for i, num in enumerate(neavy_numbers, 1):
        contacts.append((f"{neavy_name}{i}", num.strip()))

    with open(filename, "w") as f:
        for name, num in contacts:
            f.write("BEGIN:VCARD\nVERSION:3.0\n")
            f.write(f"N:{name};;;\nFN:{name}\n")
            f.write(f"TEL:{num}\nEND:VCARD\n")

    with open(filename, "rb") as f:
        await update.message.reply_document(InputFile(f, filename=filename), caption="✅ Generated VCF")

    os.remove(filename)
    return ConversationHandler.END


# --- TXT → VCF ---
async def txtvcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Not authorized.")
        return ConversationHandler.END
    await update.message.reply_text("📂 Send your .txt file with numbers")
    return TXT_FILE


async def txt_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    path = await doc.get_file()
    file_path = "numbers.txt"
    await path.download_to_drive(file_path)

    with open(file_path) as f:
        numbers = [line.strip() for line in f if line.strip()]
    context.user_data["txt_numbers"] = numbers

    await update.message.reply_text("🔢 How many contacts per VCF?")
    return TXT_SPLIT


async def txt_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["txt_split"] = int(update.message.text)
    await update.message.reply_text("💾 Enter base filename (e.g., A4F)")
    return TXT_FILENAME


async def txt_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["txt_filename"] = update.message.text.strip()
    await update.message.reply_text("✍️ Enter base contact name (e.g., A4GF)")
    return TXT_CONTACTNAME


async def txt_contactname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    basefile = context.user_data["txt_filename"]
    basename = update.message.text.strip()
    split = context.user_data["txt_split"]
    numbers = context.user_data["txt_numbers"]

    file_count = 1
    for i in range(0, len(numbers), split):
        chunk = numbers[i:i+split]
        filename = f"{basefile}{file_count}.vcf"
        with open(filename, "w") as f:
            for j, num in enumerate(chunk, 1):
                cname = f"{basename}{j}"
                f.write("BEGIN:VCARD\nVERSION:3.0\n")
                f.write(f"N:{cname};;;\nFN:{cname}\n")
                f.write(f"TEL:{num}\nEND:VCARD\n")
        with open(filename, "rb") as f:
            await update.message.reply_document(InputFile(f, filename=filename), caption=f"📁 {filename}")
        os.remove(filename)
        file_count += 1

    return ConversationHandler.END


# --- MAIN ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adduser", adduser))
    app.add_handler(CommandHandler("removeuser", removeuser))

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("adminvcf", adminvcf)],
        states={
            ADMIN_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_numbers)],
            ADMIN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_name)],
            NEAVY_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, neavy_numbers)],
            NEAVY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, neavy_name)],
            VCF_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, vcf_filename)],
        },
        fallbacks=[],
    )

    txt_conv = ConversationHandler(
        entry_points=[CommandHandler("txtvcf", txtvcf)],
        states={
            TXT_FILE: [MessageHandler(filters.Document.TEXT, txt_file)],
            TXT_SPLIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, txt_split)],
            TXT_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, txt_filename)],
            TXT_CONTACTNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, txt_contactname)],
        },
        fallbacks=[],
    )

    app.add_handler(admin_conv)
    app.add_handler(txt_conv)

    app.run_polling()


if __name__ == "__main__":
    main()
                                         
