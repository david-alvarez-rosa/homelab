#!/bin/sh
[ "${RENEWED_LINEAGE##*/}" = "alvarezrosa.com" ] || exit 0
cat "$RENEWED_LINEAGE/privkey.pem" "$RENEWED_LINEAGE/fullchain.pem" > /var/lib/znc/znc.pem
chown _znc:_znc /var/lib/znc/znc.pem
chmod 600 /var/lib/znc/znc.pem
systemctl try-restart znc
