#!/bin/sh
set -eu
C=manual-install-nextcloud-aio-talk-1
EXTRA=https://cloud.alvarezmagan.com
[ "$(docker inspect -f "{{.State.Running}}" "$C" 2>/dev/null)" = true ] || exit 0
docker exec "$C" grep -q "alvarezmagan.com" /conf/signaling.conf 2>/dev/null && exit 0
docker exec "$C" sed -i "s|urls = https://cloud.alvarezrosa.com\$|urls = https://cloud.alvarezrosa.com, $EXTRA|" /conf/signaling.conf
docker exec "$C" pkill -HUP -f nextcloud-spreed-signaling || true
logger -t talk-multidomain "re-applied $EXTRA to signaling.conf and reloaded"
