#!/data/data/com.termux/files/usr/bin/bash
LOG=/sdcard/Download/wavo-svc.log
exec > "$LOG" 2>&1
echo "=== svc $(date -Is) ==="
echo "SVDIR=${SVDIR:-unset}"
pgrep -l runsvdir || echo "runsvdir not running"
export SVDIR="$PREFIX/var/service"
if ! pgrep -f runsvdir >/dev/null; then
    echo "starting runsvdir manually"
    nohup runsvdir "$SVDIR" >/dev/null 2>&1 &
    sleep 4
fi
set -x
sv-enable crond
sv up crond
sleep 3
sv status crond
pgrep -l crond
set +x
echo "=== SVC DONE $(date -Is) ==="
