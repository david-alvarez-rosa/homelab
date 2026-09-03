#!/bin/sh
set -eu
CONF="${WA_VIEWONCE_CONF:-/etc/wa-viewonce.conf}"
KEY=$(python3 -c "import json;print(json.load(open('$CONF'))['backup_key'])")
TMP=$(mktemp -d /tmp/wavo.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
/opt/wa-viewonce/venv/bin/wadecrypt "$KEY" "$1" "$TMP/msgstore.db" >/dev/null 2>&1
exec python3 /opt/wa-viewonce/harvest.py "$TMP/msgstore.db" ${2:-}
