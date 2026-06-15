#!/bin/sh
# Reapply the Talk second-domain signaling fix the instant the AIO Talk
# container (re)starts. /start.sh inside that container regenerates
# /conf/signaling.conf from NC_DOMAIN on every start, wiping the second
# domain, so it must be reapplied on each start. The talk-multidomain-fix
# timer is a backstop; this watcher removes the post-restart gap.
set -eu
C=manual-install-nextcloud-aio-talk-1
EXTRA=https://cloud.alvarezmagan.com

apply() {
    # Wait up to 60s for the signaling server to be up so the HUP reload lands.
    i=0
    while [ "$i" -lt 60 ]; do
        docker exec "$C" pgrep -f nextcloud-spreed-signaling >/dev/null 2>&1 && break
        i=$((i + 1)); sleep 1
    done
    docker exec "$C" grep -q "alvarezmagan.com" /conf/signaling.conf 2>/dev/null \
        || docker exec "$C" sed -i "s|urls = https://cloud.alvarezrosa.com\$|urls = https://cloud.alvarezrosa.com, $EXTRA|" /conf/signaling.conf
    # Reload unconditionally: the file may already carry the domain while the
    # running server (started after a regenerate) still has the old allow-list.
    docker exec "$C" pkill -HUP -f nextcloud-spreed-signaling || true
    logger -t talk-multidomain "watcher reapplied $EXTRA after Talk container start"
}

# Catch the container if it is already up (covers service restarts / missed events).
apply || true

docker events --filter "container=$C" --filter "event=start" \
| while read -r _; do
    apply || true
done
