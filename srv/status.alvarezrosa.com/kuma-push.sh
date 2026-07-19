#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/srv/status.alvarezrosa.com/.kuma-push.env"
BASE="http://127.0.0.1:3011/api/push"
DISK_MOUNT="/"
CPU_MAX=90
RAM_MAX=90
DISK_MAX=90
ETH_STATE="/var/lib/kuma-push/eth.last"

[ -r "$ENV_FILE" ] && . "$ENV_FILE"

read -r _ u1 n1 s1 i1 w1 q1 sq1 _ < /proc/stat
sleep 1
read -r _ u2 n2 s2 i2 w2 q2 sq2 _ < /proc/stat
idle=$(( (i2 + w2) - (i1 + w1) ))
total=$(( (u2+n2+s2+i2+w2+q2+sq2) - (u1+n1+s1+i1+w1+q1+sq1) ))
cpu=$(( total > 0 ? (100 * (total - idle)) / total : 0 ))
cpu=$(( cpu < 1 ? 1 : cpu ))

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

push_eth() {
  local token="${ETH_TOKEN:-}" iface="${ETH_IFACE:-}" rx tx cur last delta gb
  [ -z "$token" ] && return 0
  [ -z "$iface" ] && return 0
  [ -r "/sys/class/net/$iface/statistics/rx_bytes" ] || return 0
  rx=$(cat "/sys/class/net/$iface/statistics/rx_bytes")
  tx=$(cat "/sys/class/net/$iface/statistics/tx_bytes")
  cur=$(( rx + tx ))
  mkdir -p "$(dirname "$ETH_STATE")"
  last=$(cat "$ETH_STATE" 2>/dev/null || echo "")
  if [ -z "$last" ]; then
    delta=0
  elif [ "$cur" -lt "$last" ]; then
    delta=$cur
  else
    delta=$(( cur - last ))
  fi
  echo "$cur" > "$ETH_STATE"
  gb=$(awk -v b="$delta" 'BEGIN{g=b/1073741824; if(g<0.001)g=0.001; printf "%.3f", g}')
  curl -fsS -m 10 -o /dev/null -G "$BASE/$token" \
    --data-urlencode "status=up" \
    --data-urlencode "msg=${gb} GB" \
    --data-urlencode "ping=$gb" || true
}

push_eth

push_service() {
  local token="$1" unit="$2" status="down" state
  [ -z "$token" ] && return 0
  state=$(systemctl is-active "$unit" 2>/dev/null || true)
  [ "$state" = "active" ] && status="up"
  curl -fsS -m 10 -o /dev/null -G "$BASE/$token" \
    --data-urlencode "status=$status" \
    --data-urlencode "msg=$unit $state" || true
}

push_service "${RSPAMD_TOKEN:-}"   rspamd
push_service "${RUNNER_TOKEN:-}"   github-runner
push_service "${FAIL2BAN_TOKEN:-}" fail2ban
