#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/srv/status.alvarezrosa.com/.kuma-push.env"
BASE="http://127.0.0.1:3011/api/push"
DISK_MOUNT="/"
CPU_MAX=90
RAM_MAX=90
DISK_MAX=90
TEMP_MAX=90
ETH_STATE="/var/lib/kuma-push/eth.last"
MODEM_STATE="/var/lib/kuma-push/modem.last"

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

temp=0
hw=$(grep -lx k10temp /sys/class/hwmon/hwmon*/name 2>/dev/null | head -1 || true)
if [ -n "$hw" ]; then
  sum=0
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sum=$(( sum + $(cat "${hw%/name}/temp1_input") ))
    sleep 1
  done
  temp=$(( sum / 10000 ))
fi

push() {
  local token="$1" val="$2" max="$3" unit="${4:-%}" status="up"
  [ -z "$token" ] && return 0
  [ "$val" -ge "$max" ] && status="down"
  curl -fsS -m 10 -o /dev/null -G "$BASE/$token" \
    --data-urlencode "status=$status" \
    --data-urlencode "msg=${val}${unit}" \
    --data-urlencode "ping=$val" || true
}

push "${CPU_TOKEN:-}"  "$cpu"  "$CPU_MAX"
push "${RAM_TOKEN:-}"  "$ram"  "$RAM_MAX"
push "${DISK_TOKEN:-}" "$disk" "$DISK_MAX"
[ "$temp" -gt 0 ] && push "${TEMP_TOKEN:-}" "$temp" "$TEMP_MAX" "°C"

push_net() {
  local token="$1" iface="$2" state="$3" rx tx cur last delta gb
  [ -z "$token" ] && return 0
  [ -z "$iface" ] && return 0
  [ -r "/sys/class/net/$iface/statistics/rx_bytes" ] || return 0
  rx=$(cat "/sys/class/net/$iface/statistics/rx_bytes")
  tx=$(cat "/sys/class/net/$iface/statistics/tx_bytes")
  cur=$(( rx + tx ))
  mkdir -p "$(dirname "$state")"
  last=$(cat "$state" 2>/dev/null || echo "")
  if [ -z "$last" ]; then
    delta=0
  elif [ "$cur" -lt "$last" ]; then
    delta=$cur
  else
    delta=$(( cur - last ))
  fi
  echo "$cur" > "$state"
  gb=$(awk -v b="$delta" 'BEGIN{g=b/1073741824; if(g<0.001)g=0.001; printf "%.3f", g}')
  curl -fsS -m 10 -o /dev/null -G "$BASE/$token" \
    --data-urlencode "status=up" \
    --data-urlencode "msg=${gb} GB" \
    --data-urlencode "ping=$gb" || true
}

push_net "${ETH_TOKEN:-}" "${ETH_IFACE:-}" "$ETH_STATE"
push_net "${MODEM_TOKEN:-}" "${MODEM_IFACE:-}" "$MODEM_STATE"

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
