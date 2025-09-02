import os
import json
import logging
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
USERS_FILE = "users.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- User Management ----
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def allowed(uid):
    users = load_users()
    return uid == OWNER_ID or uid in users

# ---- /start ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if allowed(uid):
        await update.message.reply_text("✅ Welcome! Use /adminvcf or /txtvcf to create VCF files.")
    else:
        await update.message.reply_text("⛔ You are not authorized. Contact the owner.")

# ---- Admin+Neavy VCF ----
ADMIN_NUMS, ADMIN_NAME, NEAVY_NUMS, NEAVY_NAME, FILE_NAME = range(5)

async def adminvcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update.effective_user.id):
        return await update.message.reply_text("⛔ Not authorized")
    await update.message.reply_text("Send Admin numbers separated by commas:")
    return ADMIN_NUMS

async def admin_nums(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_nums'] = update.message.text.split(',')
    await update.message.reply_text("Enter base name for Admin contacts:")
    return ADMIN_NAME

async def admin_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_name'] = update.message.text.strip()
    await update.message.reply_text("Send Neavy numbers separated by commas:")
    return NEAVY_NUMS

async def neavy_nums(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['neavy_nums'] = update.message.text.split(',')
    await update.message.reply_text("Enter base name for Neavy contacts:")
    return NEAVY_NAME

async def neavy_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['neavy_name'] = update.message.text.strip()
    await update.message.reply_text("Enter file name for VCF:")
    return FILE_NAME

async def file_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fname = update.message.text.strip()
    admin_nums = [n.strip() for n in context.user_data['admin_nums'] if n.strip()]
    neavy_nums = [n.strip() for n in context.user_data['neavy_nums'] if n.strip()]
    admin_name = context.user_data['admin_name']
    neavy_name = context.user_data['neavy_name']

    vcf_content = ""
    for i, num in enumerate(admin_nums, 1):
        vcf_content += f"BEGIN:VCARD\nVERSION:3.0\nFN:{admin_name}{i}\nTEL:{num}\nEND:VCARD\n"
    for i, num in enumerate(neavy_nums, 1):
        vcf_content += f"BEGIN:VCARD\nVERSION:3.0\nFN:{neavy_name}{i}\nTEL:{num}\nEND:VCARD\n"

    fpath = f"{fname}.vcf"
    with open(fpath, "w") as f:
        f.write(vcf_content)

    await update.message.reply_document(InputFile(fpath))
    return ConversationHandler.END

# ---- TXT to VCF ----
TXT_FILE, CONTACTS_PER_FILE, BASE_VCF_NAME, BASE_CONTACT_NAME = range(4,8)

async def txtvcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update.effective_user.id):
        return await update.message.reply_text("⛔ Not authorized")
    await update.message.reply_text("Send me a .txt file with phone numbers (one per line).")
    return TXT_FILE

async def handle_txtfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    path = await doc.get_file()
    file_path = "numbers.txt"
    await path.download_to_drive(file_path)
    with open(file_path) as f:
        numbers = [line.strip() for line in f if line.strip()]
    context.user_data['numbers'] = numbers
    await update.message.reply_text(f"Got {len(numbers)} numbers. How many contacts per VCF?")
    return CONTACTS_PER_FILE

async def contacts_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['per_file'] = int(update.message.text.strip())
    await update.message.reply_text("Enter base VCF filename (e.g., A4F):")
    return BASE_VCF_NAME

async def base_vcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['base_vcf'] = update.message.text.strip()
    await update.message.reply_text("Enter base Contact name (e.g., A4GF):")
    return BASE_CONTACT_NAME

async def base_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    base_vcf = context.user_data['base_vcf']
    base_contact = update.message.text.strip()
    per_file = context.user_data['per_file']
    numbers = context.user_data['numbers']

    files = []
    for idx in range(0, len(numbers), per_file):
        batch = numbers[idx:idx+per_file]
        vcf_content = ""
        for j, num in enumerate(batch, 1):
            vcf_content += f"BEGIN:VCARD\nVERSION:3.0\nFN:{base_contact}{idx+j}\nTEL:{num}\nEND:VCARD\n"
        fname = f"{base_vcf}_{idx//per_file+1}.vcf"
        with open(fname, "w") as f:
            f.write(vcf_content)
        files.append(fname)

    for f in files:
        await update.message.reply_document(InputFile(f))
    return ConversationHandler.END

# ---- Main ----
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("adminvcf", adminvcf)],
        states={
            ADMIN_NUMS: [MessageHandler(filters.TEXT, admin_nums)],
            ADMIN_NAME: [MessageHandler(filters.TEXT, admin_name)],
            NEAVY_NUMS: [MessageHandler(filters.TEXT, neavy_nums)],
            NEAVY_NAME: [MessageHandler(filters.TEXT, neavy_name)],
            FILE_NAME: [MessageHandler(filters.TEXT, file_name)],
        },
        fallbacks=[],
    )
    txt_conv = ConversationHandler(
        entry_points=[CommandHandler("txtvcf", txtvcf)],
        states={
            TXT_FILE: [MessageHandler(filters.Document.MimeType("text/plain"), handle_txtfile)],
            CONTACTS_PER_FILE: [MessageHandler(filters.TEXT, contacts_per_file)],
            BASE_VCF_NAME: [MessageHandler(filters.TEXT, base_vcf)],
            BASE_CONTACT_NAME: [MessageHandler(filters.TEXT, base_contact)],
        },
        fallbacks=[],
    )

    app.add_handler(admin_conv)
    app.add_handler(txt_conv)

    app.run_polling()

if __name__ == "__main__":
    main()
