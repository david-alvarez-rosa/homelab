#!/bin/sh
set -eu
C=manual-install-nextcloud-aio-talk-1
D=/srv/cloud.alvarezrosa.com/manual-install
ENVF=$D/.env
EXTRA=https://cloud.alvarezmagan.com
TURN_LOCAL=127.0.0.1

[ "$(docker inspect -f "{{.State.Running}}" "$C" 2>/dev/null)" = true ] || exit 0

if ! docker exec "$C" grep -q "alvarezmagan.com" /conf/signaling.conf 2>/dev/null; then
    docker exec "$C" sed -i "s|urls = https://cloud.alvarezrosa.com\$|urls = https://cloud.alvarezrosa.com, $EXTRA|" /conf/signaling.conf
    docker exec "$C" pkill -HUP -f nextcloud-spreed-signaling || true
    logger -t talk-multidomain "re-applied $EXTRA to signaling.conf and reloaded"
fi

if ! grep -q "^TURN_DOMAIN=$TURN_LOCAL\$" "$ENVF"; then
    sed -i "/^TURN_DOMAIN=/d" "$ENVF"
    sed -i "/^TURN_SECRET=/a TURN_DOMAIN=$TURN_LOCAL" "$ENVF"
    logger -t talk-multidomain "restored TURN_DOMAIN=$TURN_LOCAL in .env"
fi

if ! docker exec "$C" grep -q "turn_server = \"$TURN_LOCAL\"" /conf/janus.jcfg 2>/dev/null; then
    S=$(docker exec "$C" eturnalctl info 2>/dev/null | sed -n "s/^Active TURN sessions: //p")
    if [ "${S:-1}" = 0 ]; then
        cd "$D" && docker compose up -d --force-recreate nextcloud-aio-talk >/dev/null 2>&1
        logger -t talk-multidomain "janus turn_server drifted from $TURN_LOCAL; recreated talk container"
    else
        logger -t talk-multidomain "janus turn_server drifted from $TURN_LOCAL; deferring recreate (${S:-?} active TURN sessions)"
    fi
fi
