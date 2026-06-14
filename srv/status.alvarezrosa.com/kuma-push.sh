#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/srv/status.alvarezrosa.com/.kuma-push.env"
BASE="http://127.0.0.1:3011/api/push"
DISK_MOUNT="/"
CPU_MAX=90
RAM_MAX=90
DISK_MAX=90

[ -r "$ENV_FILE" ] && . "$ENV_FILE"

read -r _ u1 n1 s1 i1 w1 q1 sq1 _ < /proc/stat
sleep 1
read -r _ u2 n2 s2 i2 w2 q2 sq2 _ < /proc/stat
idle=$(( (i2 + w2) - (i1 + w1) ))
total=$(( (u2+n2+s2+i2+w2+q2+sq2) - (u1+n1+s1+i1+w1+q1+sq1) ))
cpu=$(( total > 0 ? (100 * (total - idle)) / total : 0 ))

mt=$(awk '/^MemTotal:/{print $2}' /proc/meminfo)
ma=$(awk '/^MemAvailable:/{print $2}' /proc/meminfo)
ram=$(( (100 * (mt - ma)) / mt ))

disk=$(df --output=pcent "$DISK_MOUNT" | tail -1 | tr -dc '0-9')

push() {
  local token="$1" val="$2" max="$3" status="up"
  [ -z "$token" ] && return 0
  [ "$val" -ge "$max" ] && status="down"
  curl -fsS -m 10 -o /dev/null -G "$BASE/$token" \
    --data-urlencode "status=$status" \
    --data-urlencode "msg=${val}%" \
    --data-urlencode "ping=$val" || true
}

push "${CPU_TOKEN:-}"  "$cpu"  "$CPU_MAX"
push "${RAM_TOKEN:-}"  "$ram"  "$RAM_MAX"
push "${DISK_TOKEN:-}" "$disk" "$DISK_MAX"
