#!/data/data/com.termux/files/usr/bin/bash
LOG=/sdcard/Download/wavo-setup.log
exec > "$LOG" 2>&1
echo "=== wavo setup $(date -Is) ==="
set -x
BK=/sdcard/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15
if [ ! -r "$BK" ]; then
    set +x
    echo "FAIL: cannot read $BK -- run termux-setup-storage and tap Allow"
    exit 1
fi
pkg install -y openssh cronie termux-services
mkdir -p "$HOME/.ssh" "$HOME/bin"
cp /sdcard/Download/wavo_key "$HOME/.ssh/wavo_key"
chmod 700 "$HOME/.ssh"
chmod 600 "$HOME/.ssh/wavo_key"
cp /sdcard/Download/wavo-push.sh "$HOME/bin/wavo-push.sh"
chmod +x "$HOME/bin/wavo-push.sh"
"$HOME/bin/wavo-push.sh" || true
( crontab -l 2>/dev/null | grep -v wavo-push; echo "7 * * * * \$HOME/bin/wavo-push.sh >> \$HOME/.wavo.log 2>&1" ) | crontab -
sv-enable crond || true
sv up crond || true
crontab -l
set +x
echo "=== SETUP COMPLETE $(date -Is) ==="
