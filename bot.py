#!/usr/bin/env python3
"""
Clean Telegram VCF Bot (final)
- Owner controls users via /adduser, /removeuser, /listusers
- /adminvcf : Admin group + Neavy group -> one VCF (with sequential names)
- /txtvcf   : Upload .txt -> split into multiple VCF files with auto-sequence names
- /id       : returns user's numeric Telegram ID
Set environment variables:
  BOT_TOKEN  - Bot token from @BotFather
  OWNER_ID   - Your Telegram numeric ID
"""
import os
import json
import re
import math
import logging
from pathlib import Path
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
USERS_FILE = "users.json"
TMP_DIR = Path(".")
VCF_ENCODING = "utf-8"

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vcf-bot")

if not BOT_TOKEN:
    log.error("BOT_TOKEN environment variable is not set. Exiting.")
    raise SystemExit("BOT_TOKEN env required")

# ---------------- UTIL ----------------
DIGIT_RE = re.compile(r"(\d+)")          # find first group of digits
PHONE_RE = re.compile(r"\+?\d+")         # find phone-like tokens


def load_users():
    if not Path(USERS_FILE).exists():
        # create default with owner
        data = {"allowed": [OWNER_ID]}
        Path(USERS_FILE).write_text(json.dumps(data), encoding="utf-8")
        return data
    try:
        return json.loads(Path(USERS_FILE).read_text(encoding="utf-8"))
    except Exception:
        return {"allowed": [OWNER_ID]}


def save_users(data):
    Path(USERS_FILE).write_text(json.dumps(data), encoding="utf-8")


def allowed(user_id: int) -> bool:
    d = load_users()
    return user_id == OWNER_ID or user_id in d.get("allowed", [])


def parse_numbers_from_text(text: str):
    """Return list of digit tokens found in text (keeps + if present)."""
    return PHONE_RE.findall(text)


def split_base_and_number(s: str):
    """
    Split a string into (prefix, start_num or None, suffix).
    Example: 'A4GF' -> ('A', 4, 'GF')
    If no digits found -> (s, None, '')
    """
    m = DIGIT_RE.search(s)
    if not m:
        return s, None, ""
    start = int(m.group(1))
    pre = s[: m.start(1)]
    suf = s[m.end(1) :]
    return pre, start, suf


def sanitize_filename(name: str) -> str:
    # allow letters, numbers, dot, underscore, dash
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


# ---------------- COMMANDS: OWNER USER MGMT ----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = "WELCOME 🤗 THIS BOT WAS MADE BY @random_0988\n\n"
    txt += "Commands:\n"
    txt += "/adminvcf - create Admin+Neavy VCF (step-by-step)\n"
    txt += "/txtvcf - convert a .txt to split VCF files (step-by-step)\n"
    txt += "/id - show your Telegram ID\n"
    txt += "/adduser <id> - (owner) allow user\n"
    txt += "/removeuser <id> - (owner) remove user\n"
    txt += "/listusers - (owner) list allowed users\n"
    await update.message.reply_text(txt)


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")


async def adduser_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("⛔ Only owner can add users.")
    if not context.args:
        return await update.message.reply_text("Usage: /adduser <telegram_id>")
    try:
        new_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Invalid id. Use numbers only.")
    data = load_users()
    if new_id in data.get("allowed", []):
        return await update.message.reply_text("User already allowed.")
    data["allowed"].append(new_id)
    save_users(data)
    await update.message.reply_text(f"✅ Added {new_id}")


async def removeuser_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("⛔ Only owner can remove users.")
    if not context.args:
        return await update.message.reply_text("Usage: /removeuser <telegram_id>")
    try:
        rid = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Invalid id. Use numbers only.")
    data = load_users()
    if rid == OWNER_ID:
        return await update.message.reply_text("Cannot remove owner.")
    if rid not in data.get("allowed", []):
        return await update.message.reply_text("User not found.")
    data["allowed"].remove(rid)
    save_users(data)
    await update.message.reply_text(f"✅ Removed {rid}")


async def listusers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("⛔ Only owner can list users.")
    data = load_users()
    await update.message.reply_text("Allowed users:\n" + "\n".join(map(str, data.get("allowed", []))))


# ---------------- CONVERSATIONS: ADMIN + NEAVY ----------------
A_ADMIN_NUMS, A_ADMIN_BASE, A_NEAVY_NUMS, A_NEAVY_BASE, A_FILENAME = range(5)


async def adminvcf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update.effective_user.id):
        return await update.message.reply_text("⛔ You are not allowed.")
    await update.message.reply_text(
        "Send ADMIN numbers (comma / newline / space separated). Example:\n413639, 1361616, 6166"
    )
    return A_ADMIN_NUMS


async def adminvcf_admin_nums(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nums = parse_numbers_from_text(update.message.text)
    if not nums:
        return await update.message.reply_text("No numbers found. Send admin numbers again.")
    context.user_data["admin_nums"] = nums
    await update.message.reply_text("Send ADMIN contact base name (example: F1) — bot will sequence F1,F2,...")
    return A_ADMIN_BASE


async def adminvcf_admin_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_base"] = update.message.text.strip()
    await update.message.reply_text("Send NEAVY numbers (comma / newline / space separated).")
    return A_NEAVY_NUMS


async def adminvcf_neavy_nums(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nums = parse_numbers_from_text(update.message.text)
    if not nums:
        return await update.message.reply_text("No numbers found. Send neavy numbers again.")
    context.user_data["neavy_nums"] = nums
    await update.message.reply_text("Send NEAVY contact base name (example: a1) — bot will sequence a1,a2,...")
    return A_NEAVY_BASE


async def adminvcf_neavy_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["neavy_base"] = update.message.text.strip()
    await update.message.reply_text("Send final VCF file name (example: ZXC).")
    return A_FILENAME


async def adminvcf_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fname_raw = update.message.text.strip()
    fname_safe = sanitize_filename(fname_raw) or "admin_neavy"
    admin_nums = context.user_data.get("admin_nums", [])
    neavy_nums = context.user_data.get("neavy_nums", [])
    admin_base = context.user_data.get("admin_base", "")
    neavy_base = context.user_data.get("neavy_base", "")

    # build vcard content
    lines = []
    # admin group
    pre_a, start_a, suf_a = split_base_and_number(admin_base)
    for i, num in enumerate(admin_nums):
        if start_a is not None:
            name = f"{pre_a}{start_a + i}{suf_a}"
        else:
            name = f"{admin_base}{i+1}"
        lines.extend(["BEGIN:VCARD", "VERSION:3.0", f"FN:{name}", f"TEL:{num}", "END:VCARD"])

    # neavy group
    pre_n, start_n, suf_n = split_base_and_number(neavy_base)
    for i, num in enumerate(neavy_nums):
        if start_n is not None:
            name = f"{pre_n}{start_n + i}{suf_n}"
        else:
            name = f"{neavy_base}{i+1}"
        lines.extend(["BEGIN:VCARD", "VERSION:3.0", f"FN:{name}", f"TEL:{num}", "END:VCARD"])

    vcf_text = "\n".join(lines) + "\n"
    path = TMP_DIR / f"{fname_safe}.vcf"
    path.write_text(vcf_text, encoding=VCF_ENCODING)

    await update.message.reply_document(document=InputFile(str(path)), filename=path.name)
    return ConversationHandler.END


# ---------------- CONVERSATIONS: TXT -> VCF ----------------
T_FILE, T_PER_FILE, T_BASE_VCF, T_BASE_CONTACT = range(10, 14)


async def txtvcf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update.effective_user.id):
        return await update.message.reply_text("⛔ You are not allowed.")
    await update.message.reply_text("Send a .txt file with phone numbers (one per line or mixed).")
    return T_FILE


async def txtvcf_receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # expects a Document (.txt)
    doc = update.message.document
    if not doc:
        return await update.message.reply_text("Please send a .txt file (as a document).")
    saved = TMP_DIR / f"{update.effective_user.id}_numbers.txt"
    fileobj = await doc.get_file()
    await fileobj.download_to_drive(str(saved))
    text = saved.read_text(encoding="utf-8", errors="ignore")
    numbers = parse_numbers_from_text(text)
    if not numbers:
        return await update.message.reply_text("No numbers detected in the file. Upload a proper .txt.")
    context.user_data["numbers"] = numbers
    await update.message.reply_text(f"Got {len(numbers)} numbers. How many contacts per VCF file? (send a number)")
    return T_PER_FILE


async def txtvcf_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        per = int(update.message.text.strip())
        if per <= 0:
            raise ValueError()
    except Exception:
        per = len(context.user_data.get("numbers", []))
    context.user_data["per_file"] = per
    await update.message.reply_text("Enter base VCF filename (example: A4F). Bot will make A4F.vcf, A5F.vcf, ...")
    return T_BASE_VCF


async def txtvcf_base_vcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["base_vcf"] = update.message.text.strip()
    await update.message.reply_text("Enter base Contact name (example: A4GF). Bot will name contacts sequentially.")
    return T_BASE_CONTACT


async def txtvcf_base_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    base_vcf_raw = context.user_data.get("base_vcf", "contacts")
    base_contact_raw = update.message.text.strip()
    numbers = context.user_data.get("numbers", [])
    per = context.user_data.get("per_file", max(1, len(numbers)))

    # parse base patterns
    pre_v, start_v, suf_v = split_base_and_number(base_vcf_raw)
    pre_c, start_c, suf_c = split_base_and_number(base_contact_raw)

    # create files
    files_sent = []
    total = len(numbers)
    total_files = math.ceil(total / per) if per else 1
    global_idx = 0  # counts contacts sequentially across files (0-indexed)

    for file_idx in range(total_files):
        chunk = numbers[file_idx * per : file_idx * per + per]
        # determine file name
        if start_v is not None:
            file_num = start_v + file_idx
            fname_core = f"{pre_v}{file_num}{suf_v}"
        else:
            fname_core = f"{base_vcf_raw}_{file_idx+1}"
        fname_safe = sanitize_filename(fname_core) + ".vcf"
        lines = []
        for k, num in enumerate(chunk):
            if start_c is not None:
                contact_num = start_c + global_idx
                name = f"{pre_c}{contact_num}{suf_c}"
            else:
                name = f"{base_contact_raw}{global_idx+1}"
            lines.extend(["BEGIN:VCARD", "VERSION:3.0", f"FN:{name}", f"TEL:{num}", "END:VCARD"])
            global_idx += 1

        vcf_text = "\n".join(lines) + "\n"
        path = TMP_DIR / fname_safe
        path.write_text(vcf_text, encoding=VCF_ENCODING)
        files_sent.append(path)

    # send files one by one
    for p in files_sent:
        await update.message.reply_document(document=InputFile(str(p)), filename=p.name)

    return ConversationHandler.END


# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # basic commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("adduser", adduser_cmd))
    app.add_handler(CommandHandler("removeuser", removeuser_cmd))
    app.add_handler(CommandHandler("listusers", listusers_cmd))

    # admin+neavy
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("adminvcf", adminvcf_start)],
        states={
            A_ADMIN_NUMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, adminvcf_admin_nums)],
            A_ADMIN_BASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adminvcf_admin_base)],
            A_NEAVY_NUMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, adminvcf_neavy_nums)],
            A_NEAVY_BASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adminvcf_neavy_base)],
            A_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, adminvcf_filename)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    app.add_handler(admin_conv)

    # txt -> vcf
    txt_conv = ConversationHandler(
        entry_points=[CommandHandler("txtvcf", txtvcf_start)],
        states={
            T_FILE: [MessageHandler(filters.Document.FileExtension("txt") | filters.Document.MimeType("text/plain"), txtvcf_receive_file)],
            T_PER_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, txtvcf_per_file)],
            T_BASE_VCF: [MessageHandler(filters.TEXT & ~filters.COMMAND, txtvcf_base_vcf)],
            T_BASE_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, txtvcf_base_contact)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    app.add_handler(txt_conv)

    log.info("Bot starting...")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
