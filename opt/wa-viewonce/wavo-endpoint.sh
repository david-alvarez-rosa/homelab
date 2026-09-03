#!/bin/sh
set -eu
INBOX=/var/lib/wa-viewonce/inbox
MAX=2147483648
case "${SSH_ORIGINAL_COMMAND:-push}" in
    ask)
        cat /var/lib/wa-viewonce/want 2>/dev/null || echo idle
        ;;
    push)
        TMP="$INBOX/.incoming.$$"
        trap 'rm -f "$TMP"' EXIT
        head -c "$MAX" > "$TMP"
        SIZE=$(stat -c %s "$TMP")
        if [ "$SIZE" -lt 1048576 ]; then
            echo "rejected: only $SIZE bytes" >&2
            exit 1
        fi
        mv "$TMP" "$INBOX/msgstore.db.crypt15"
        trap - EXIT
        echo "accepted $SIZE bytes"
        ;;
    *)
        echo "unknown request" >&2
        exit 1
        ;;
esac
