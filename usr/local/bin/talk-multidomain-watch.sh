#!/bin/sh
set -eu
C=manual-install-nextcloud-aio-talk-1
EXTRA=https://cloud.alvarezmagan.com

registered() {
    docker logs --since "$(docker inspect -f '{{.State.StartedAt}}' "$C" 2>/dev/null)" "$C" 2>&1 \
        | grep -a "Backend backend-1" | tail -1 | grep -q "alvarezmagan.com"
}

apply() {
    i=0
    while [ "$i" -lt 120 ]; do
        status=$(docker inspect -f '{{.State.Health.Status}}' "$C" 2>/dev/null || true)
        [ "$status" = healthy ] && break
        if [ -z "$status" ] || [ "$status" = "<no value>" ]; then
            docker exec "$C" pgrep -f nextcloud-spreed-signaling >/dev/null 2>&1 && break
        fi
        i=$((i + 1)); sleep 1
    done
    docker exec "$C" grep -q "alvarezmagan.com" /conf/signaling.conf 2>/dev/null \
        || docker exec "$C" sed -i "s|urls = https://cloud.alvarezrosa.com\$|urls = https://cloud.alvarezrosa.com, $EXTRA|" /conf/signaling.conf
    j=0
    while [ "$j" -lt 20 ]; do
        if registered; then
            logger -t talk-multidomain "second domain active in signaling server"
            return 0
        fi
        docker exec "$C" pkill -HUP -f nextcloud-spreed-signaling || true
        j=$((j + 1)); sleep 3
    done
    logger -t talk-multidomain "WARNING: could not confirm $EXTRA after reload attempts"
}

apply || true

docker events --filter "container=$C" --filter "event=start" \
| while read -r _; do
    apply || true
done
