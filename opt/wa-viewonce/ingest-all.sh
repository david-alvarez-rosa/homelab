#!/bin/sh
set -eu
INBOX=/var/lib/wa-viewonce/inbox
MARK=/var/lib/wa-viewonce/last.sha
sleep 5
NEW=
for f in "$INBOX"/*.crypt15; do
    if [ -z "$NEW" ] || [ "$f" -nt "$NEW" ]; then NEW=$f; fi
done
[ -e "$NEW" ] || exit 0
SHA=$(sha256sum "$NEW" | cut -d' ' -f1)
[ -f "$MARK" ] && [ "$(cat "$MARK")" = "$SHA" ] && exit 0
/opt/wa-viewonce/ingest.sh "$NEW"
echo "$SHA" > "$MARK"
