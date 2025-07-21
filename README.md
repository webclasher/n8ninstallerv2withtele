curl -fsSL https://raw.githubusercontent.com/webclasher/n8n-Telegram-Bot-Installer-Final-Version-Pro/main/install.sh | sudo bash -s \
  "your-domain.com" "you@example.com" "BOT_TOKEN" "TELEGRAM_USER_ID"


or 


curl -fsSL https://raw.githubusercontent.com/webclasher/n8n-Telegram-Bot-Installer-Final-Version-Pro/refs/heads/main/install.sh | sudo bash -s \
  "n8n.yourdomain.com" \
  "youremial@gmail.com" \
  "bottoken" \
  "telegramchatid"








Installation
Run this single command on your Debian-based server:

bash
Copy
Edit
curl -fsSL https://raw.githubusercontent.com/webclasher/n8n-Telegram-Bot-Installer-Final-Version-Pro/main/install.sh | sudo bash -s \
  "your-domain.com" "you@example.com" "BOT_TOKEN" "TELEGRAM_USER_ID"
Replace:

your-domain.com with your domain

you@example.com with your email for SSL cert

BOT_TOKEN with your Telegram bot token

TELEGRAM_USER_ID with your Telegram user ID (to restrict access)

Bot Commands
Backup Management
/createbackup – Create a backup of n8n data

/showbackup – Get the latest backup file with restore option

/listbackups – List all backups with individual delete buttons

/deletebackups – Delete all backups (confirmation required)

Upload a .tar.gz file to restore a backup directly

System Management
/status – Check n8n container status

/logs – Show recent logs

/restart – Restart n8n container

/update – Update n8n to the latest version

/restore – Restore from latest backup

Help
/help or /start – Show this help message

Notes
Backups are stored in /opt/n8n_backups

Bot code is located at /opt/n8n_bot/n8n_bot.py

The bot runs as a systemd service: n8n-bot.service

Only the authorized Telegram user ID can control the bot

Contributing
Feel free to fork, submit issues or PRs!
