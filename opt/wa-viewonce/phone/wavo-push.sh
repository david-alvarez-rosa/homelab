#!/data/data/com.termux/files/usr/bin/sh
BK=/sdcard/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15
KEY=$HOME/.ssh/wavo_key
HOST=wavo@alvarezrosa.com
MARK=$HOME/.wavo-last
SSHOPT="-i $KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=25"
[ -r "$BK" ] || { echo "$(date -Is) no readable backup (run termux-setup-storage?)"; exit 1; }
ANS=$(ssh $SSHOPT "$HOST" ask) || { echo "$(date -Is) ask failed"; exit 1; }
set -- $ANS
[ "$1" = "want" ] || { echo "$(date -Is) idle"; exit 0; }
NEED=$2
MT=$(stat -c %Y "$BK")
if [ "$MT" -le "$NEED" ]; then
    echo "$(date -Is) backup predates the pending message, waiting for the next WhatsApp backup"
    exit 0
fi
SIG="$MT-$(stat -c %s "$BK")"
if [ "$(cat "$MARK" 2>/dev/null)" = "$SIG" ]; then
    echo "$(date -Is) this backup was already sent"
    exit 0
fi
echo "$(date -Is) pushing $(stat -c %s "$BK") bytes"
if cat "$BK" | ssh $SSHOPT "$HOST" push; then
    echo "$SIG" > "$MARK"
    echo "$(date -Is) pushed"
else
    echo "$(date -Is) push failed"
    exit 1
fi
