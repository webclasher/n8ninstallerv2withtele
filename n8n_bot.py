#!/usr/bin/env python3
import os
import subprocess
import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load config
load_dotenv('/opt/n8n_bot/n8n_bot_config.env')
BOT_TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER = int(os.getenv("AUTHORIZED_USER"))
DOMAIN = os.getenv("DOMAIN")
BACKUP_DIR = "/opt/n8n_backups"

bot = telebot.TeleBot(BOT_TOKEN)
os.makedirs(BACKUP_DIR, exist_ok=True)

def is_authorized(message):
    return message.from_user.id == AUTHORIZED_USER

# /help and /start
@bot.message_handler(commands=["help", "start"])
def help_cmd(message):
    if not is_authorized(message): return
    bot.reply_to(message, """🤖 *n8n Bot Control Panel*

📦 Backup Commands:
/createbackup – Save a new backup
/showbackup – Send latest backup with Restore button
/listbackups – List all backups with delete buttons
/deletebackups – Delete *all* backups (with confirmation)
/restore – Restore last saved backup
📤 Upload a .tar.gz to restore it automatically

⚙️ Management:
/status – Check if container is running
/logs – Show recent logs
/restart – Restart n8n
/update – Update n8n to latest

/help – Show this message again
""", parse_mode="Markdown")

# Docker Status
@bot.message_handler(commands=["status"])
def status(message):
    if not is_authorized(message): return
    out = subprocess.getoutput("docker ps --filter name=n8n")
    bot.reply_to(message, f"📦 *n8n Status:*\n```\n{out}\n```", parse_mode="Markdown")

# Docker Logs
@bot.message_handler(commands=["logs"])
def logs(message):
    if not is_authorized(message): return
    out = subprocess.getoutput("docker logs --tail 50 n8n")
    bot.reply_to(message, f"📄 *n8n Logs:*\n```\n{out}\n```", parse_mode="Markdown")

# Restart n8n
@bot.message_handler(commands=["restart"])
def restart(message):
    if not is_authorized(message): return
    subprocess.run(["docker", "restart", "n8n"])
    bot.reply_to(message, "🔁 n8n restarted!")

# Update n8n
@bot.message_handler(commands=["update"])
def update(message):
    if not is_authorized(message): return
    subprocess.run("docker pull n8nio/n8n:latest", shell=True)
    subprocess.run("docker rm -f n8n", shell=True)
    subprocess.run(
        f"docker run -d --restart unless-stopped --name n8n -p 5678:5678 "
        f"-e N8N_HOST='{DOMAIN}' -e WEBHOOK_URL='https://{DOMAIN}/' "
        f"-e WEBHOOK_TUNNEL_URL='https://{DOMAIN}/' "
        f"-v /var/n8n:/home/node/.n8n n8nio/n8n:latest",
        shell=True
    )
    bot.reply_to(message, "✅ n8n updated and restarted!")

# Create backup
@bot.message_handler(commands=["createbackup"])
def create_backup(message):
    if not is_authorized(message): return
    backup_path = f"{BACKUP_DIR}/n8n-backup-$(date +%F).tar.gz"
    subprocess.run(f"tar -czf {backup_path} /var/n8n", shell=True)
    bot.reply_to(message, f"📦 Backup created:\n`{backup_path}`", parse_mode="Markdown")

# Show latest backup
@bot.message_handler(commands=["showbackup"])
def show_backup(message):
    if not is_authorized(message): return
    latest = subprocess.getoutput(f"ls -t {BACKUP_DIR}/*.tar.gz | head -n 1")
    if os.path.exists(latest):
        bot.send_document(message.chat.id, open(latest, "rb"))
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔁 Restore this Backup", callback_data="restore_backup"))
        bot.send_message(message.chat.id, "📂 Tap below to restore the above backup:", reply_markup=markup)
    else:
        bot.reply_to(message, "⚠️ No backup found.")

# Manual restore
@bot.message_handler(commands=["restore"])
def manual_restore(message):
    if not is_authorized(message): return
    latest = subprocess.getoutput(f"ls -t {BACKUP_DIR}/*.tar.gz | head -n 1")
    if os.path.exists(latest):
        subprocess.run(f"tar -xzf {latest} -C /", shell=True)
        subprocess.run("docker restart n8n", shell=True)
        bot.reply_to(message, "✅ Restored from latest backup.")
    else:
        bot.reply_to(message, "⚠️ No backup found.")

# Restore via inline button
@bot.callback_query_handler(func=lambda call: call.data == "restore_backup")
def restore_button(call):
    if call.from_user.id != AUTHORIZED_USER:
        bot.answer_callback_query(call.id, "❌ Unauthorized")
        return
    latest = subprocess.getoutput(f"ls -t {BACKUP_DIR}/*.tar.gz | head -n 1")
    if os.path.exists(latest):
        subprocess.run(f"tar -xzf {latest} -C /", shell=True)
        subprocess.run("docker restart n8n", shell=True)
        bot.send_message(call.message.chat.id, "✅ Backup restored successfully.")
        bot.answer_callback_query(call.id, "✅ Restored!")
    else:
        bot.send_message(call.message.chat.id, "⚠️ No backup to restore.")
        bot.answer_callback_query(call.id, "❌ No backup found.")

# Handle uploaded .tar.gz
@bot.message_handler(content_types=["document"])
def upload_backup(message):
    if not is_authorized(message): return
    doc = message.document
    if not doc.file_name.endswith(".tar.gz"):
        bot.reply_to(message, "⚠️ Only .tar.gz backup files are supported.")
        return
    try:
        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        path = f"{BACKUP_DIR}/{doc.file_name}"
        with open(path, "wb") as f:
            f.write(downloaded)
        subprocess.run(f"tar -xzf {path} -C /", shell=True)
        subprocess.run("docker restart n8n", shell=True)
        bot.reply_to(message, f"✅ Backup `{doc.file_name}` restored and n8n restarted!", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Restore failed: {str(e)}")

# List all backups with delete buttons
@bot.message_handler(commands=["listbackups"])
def list_backups(message):
    if not is_authorized(message): return
    files = subprocess.getoutput(f"ls -1t {BACKUP_DIR}/*.tar.gz 2>/dev/null").splitlines()
    if not files:
        bot.reply_to(message, "📁 No backups found.")
        return
    for f in files:
        filename = os.path.basename(f)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"🔥 Delete {filename}", callback_data=f"prompt_delete_{filename}"))
        bot.send_message(message.chat.id, f"📦 *{filename}*", reply_markup=markup, parse_mode="Markdown")

# Ask for confirmation before delete
@bot.callback_query_handler(func=lambda call: call.data.startswith("prompt_delete_"))
def prompt_confirm_delete(call):
    if call.from_user.id != AUTHORIZED_USER:
        bot.answer_callback_query(call.id, "❌ Unauthorized")
        return
    filename = call.data.replace("prompt_delete_", "")
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete"),
        InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{filename}")
    )
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=f"⚠️ Confirm delete: *{filename}*?",
                          reply_markup=markup,
                          parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# Delete confirmed file
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_"))
def delete_specific_backup(call):
    if call.from_user.id != AUTHORIZED_USER:
        bot.answer_callback_query(call.id, "❌ Unauthorized")
        return
    filename = call.data.replace("confirm_delete_", "")
    file_path = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            bot.edit_message_text(chat_id=call.message.chat.id,
                                  message_id=call.message.message_id,
                                  text=f"✅ Deleted: `{filename}`", parse_mode="Markdown")
            bot.answer_callback_query(call.id, "🗑️ Deleted")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")
    else:
        bot.answer_callback_query(call.id, "⚠️ File not found")

# Cancel button
@bot.callback_query_handler(func=lambda call: call.data == "cancel_delete")
def cancel_delete_action(call):
    if call.from_user.id != AUTHORIZED_USER:
        bot.answer_callback_query(call.id, "❌ Unauthorized")
        return
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text="❌ Deletion canceled.")
    bot.answer_callback_query(call.id, "Cancelled")

# Confirm "Delete All" command
@bot.message_handler(commands=["deletebackups"])
def confirm_delete_all(message):
    if not is_authorized(message): return
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete"),
        InlineKeyboardButton("🗑️ Yes, Delete All", callback_data="delete_all_backups")
    )
    bot.send_message(message.chat.id, "⚠️ Are you sure you want to delete *ALL* backups?",
                     reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "delete_all_backups")
def delete_all_backups(call):
    if call.from_user.id != AUTHORIZED_USER:
        bot.answer_callback_query(call.id, "❌ Unauthorized")
        return
    subprocess.run(f"rm -f {BACKUP_DIR}/*.tar.gz", shell=True)
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text="✅ All backups deleted.")
    bot.answer_callback_query(call.id, "🗑️ All deleted")

# Start polling
bot.polling()
