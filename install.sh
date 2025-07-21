#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# n8n + Telegram Bot Pro Installer – Version 2.0
# Secure | Production-Ready | GCP/VPS-Ready
# Usage:
# curl -fsSL https://raw.githubusercontent.com/webclasher/n8n-Telegram-Bot-Installer-Final-Version-Pro/main/install.sh | sudo bash -s \
#   "your-domain.com" "you@example.com" "BOT_TOKEN" "TELEGRAM_USER_ID"
# ─────────────────────────────────────────────────────────────

set -euo pipefail

# Input
DOMAIN=${1:-}
EMAIL=${2:-}
BOT_TOKEN=${3:-}
USER_ID=${4:-}

if [[ -z "$DOMAIN" || -z "$EMAIL" || -z "$BOT_TOKEN" || -z "$USER_ID" ]]; then
  echo "❌ Missing arguments. Usage:"
  echo "bash install.sh \"domain.com\" \"you@email.com\" \"BOT_TOKEN\" \"USER_ID\""
  exit 1
fi

BOT_DIR="/opt/n8n_bot"
BACKUP_DIR="/opt/n8n_backups"

echo -e "\n📦 Installing core tools..."
apt update -y
apt install -y bash curl sudo gnupg2 ca-certificates lsb-release unzip

# Docker
echo -e "\n🐳 Installing Docker..."
apt install -y apt-transport-https software-properties-common
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update -y
apt install -y docker-ce docker-ce-cli containerd.io
systemctl enable --now docker

# Run n8n container
echo -e "\n🚀 Launching n8n container..."
mkdir -p /var/n8n && chown 1000:1000 /var/n8n
docker run -d --restart unless-stopped --name n8n -p 5678:5678 \
  -e N8N_HOST="$DOMAIN" \
  -e WEBHOOK_URL="https://$DOMAIN/" \
  -e WEBHOOK_TUNNEL_URL="https://$DOMAIN/" \
  -v /var/n8n:/home/node/.n8n \
  n8nio/n8n:latest

# Nginx + Certbot
echo -e "\n🌐 Installing Nginx + Certbot..."
apt install -y nginx python3-certbot-nginx

echo -e "\n⚙️ Writing Nginx config..."
cat > /etc/nginx/sites-available/n8n <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_buffering off;
        proxy_read_timeout 86400s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/n8n
rm -f /etc/nginx/sites-enabled/default || true
nginx -t && systemctl reload nginx

echo -e "\n🔒 Getting SSL certificate..."
certbot --non-interactive --agree-tos --nginx -m "$EMAIL" -d "$DOMAIN"

# UFW
echo -e "\n🛡️ Enabling UFW firewall..."
apt install -y ufw
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# Telegram Bot
echo -e "\n🤖 Installing Telegram bot..."
apt install -y python3 python3-pip
pip3 install --break-system-packages python-telegram-bot telebot python-dotenv

mkdir -p "$BOT_DIR" "$BACKUP_DIR"

curl -fsSL https://raw.githubusercontent.com/webclasher/n8n-Telegram-Bot-Installer-Final-Version-Pro/refs/heads/main/n8n_bot.py \
  -o "$BOT_DIR/n8n_bot.py"

cat > "$BOT_DIR/n8n_bot_config.env" <<EOF
BOT_TOKEN=$BOT_TOKEN
AUTHORIZED_USER=$USER_ID
DOMAIN=$DOMAIN
EOF

chmod +x "$BOT_DIR/n8n_bot.py"

cat > /etc/systemd/system/n8n-bot.service <<EOF
[Unit]
Description=n8n Telegram Bot
After=network.target docker.service

[Service]
ExecStart=/usr/bin/python3 $BOT_DIR/n8n_bot.py
WorkingDirectory=$BOT_DIR
Restart=always
EnvironmentFile=$BOT_DIR/n8n_bot_config.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable --now n8n-bot.service

# Done
echo -e "\n✅ Installation complete!"
echo -e "🌐 https://$DOMAIN"
echo -e "📦 Bot: /opt/n8n_bot"
echo -e "📁 Backups: /opt/n8n_backups"
echo -e "🤖 Send /help to your bot!"
