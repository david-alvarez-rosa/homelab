#!/bin/sh
set -eu
INBOX=/var/lib/wa-viewonce/inbox
MARK=/var/lib/wa-viewonce/last.sha
sleep 5
NEW=$(ls -t "$INBOX"/*.crypt15 2>/dev/null | head -1) || exit 0
[ -n "${NEW:-}" ] || exit 0
SHA=$(sha256sum "$NEW" | cut -d' ' -f1)
[ -f "$MARK" ] && [ "$(cat "$MARK")" = "$SHA" ] && exit 0
/opt/wa-viewonce/ingest.sh "$NEW"
echo "$SHA" > "$MARK"
