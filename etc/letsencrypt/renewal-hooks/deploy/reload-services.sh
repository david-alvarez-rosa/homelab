#!/bin/sh
for s in nginx postfix dovecot; do systemctl reload "$s" 2>/dev/null || true; done
