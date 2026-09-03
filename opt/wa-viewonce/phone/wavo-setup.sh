#!/data/data/com.termux/files/usr/bin/bash
set -e
if [ ! -r /sdcard/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15 ]; then
    echo "Cannot read the WhatsApp backup. Run: termux-setup-storage   (then tap Allow) and re-run this."
    exit 1
fi
pkg install -y openssh cronie termux-services
mkdir -p "$HOME/.ssh" "$HOME/bin"
cp /sdcard/Download/wavo_key "$HOME/.ssh/wavo_key"
chmod 700 "$HOME/.ssh"; chmod 600 "$HOME/.ssh/wavo_key"
cp /sdcard/Download/wavo-push.sh "$HOME/bin/wavo-push.sh"
chmod +x "$HOME/bin/wavo-push.sh"
echo "--- test run ---"
"$HOME/bin/wavo-push.sh" || true
( crontab -l 2>/dev/null | grep -v wavo-push; echo "7 * * * * \$HOME/bin/wavo-push.sh >> \$HOME/.wavo.log 2>&1" ) | crontab -
sv-enable crond 2>/dev/null || true
sv up crond 2>/dev/null || true
echo "--- done: hourly check installed ---"
crontab -l | grep wavo-push
