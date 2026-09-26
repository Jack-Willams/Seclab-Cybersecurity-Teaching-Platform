#!/bin/bash
set -u

export DISPLAY="${DISPLAY:-:1}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-/root/.config}"

WALLPAPER_DIR="/opt/seclab-wallpapers"
LAB_ID="${SECLAB_LAB_BASE_ID:-}"
LOG_PREFIX="[set-wallpaper]"

case "$LAB_ID" in
  1) wallpaper="$WALLPAPER_DIR/sql-injection.jpg" ;;
  2) wallpaper="$WALLPAPER_DIR/xss.jpg" ;;
  3) wallpaper="$WALLPAPER_DIR/csrf.jpg" ;;
  4) wallpaper="$WALLPAPER_DIR/command-injection.jpg" ;;
  5) wallpaper="$WALLPAPER_DIR/file-upload.jpg" ;;
  6) wallpaper="$WALLPAPER_DIR/directory-traversal.jpg" ;;
  *) wallpaper="$WALLPAPER_DIR/default.jpg" ;;
esac

if [ ! -f "$wallpaper" ]; then
  echo "$LOG_PREFIX wallpaper not found: $wallpaper"
  exit 0
fi

read_proc_env() {
  local pid="$1"
  local key="$2"

  tr '\0' '\n' <"/proc/$pid/environ" 2>/dev/null | awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }'
}

set_property() {
  local property="$1"
  local type="$2"
  local value="$3"

  if xfconf-query -c xfce4-desktop -p "$property" >/dev/null 2>&1; then
    xfconf-query -c xfce4-desktop -p "$property" -s "$value" >/dev/null 2>&1 || true
  else
    xfconf-query -c xfce4-desktop -p "$property" -n -t "$type" -s "$value" >/dev/null 2>&1 || true
  fi
}

set_monitor_wallpaper() {
  local monitor="$1"
  local workspace="$2"
  local base="/backdrop/screen0/$monitor"

  if [ -n "$workspace" ]; then
    base="$base/$workspace"
  fi

  # image-style=4 keeps the whole image visible and preserves aspect ratio.
  set_property "$base/color-style" int 1
  set_property "$base/image-style" int 4
  set_property "$base/image-show" bool true
  set_property "$base/image-path" string "$wallpaper"
  set_property "$base/last-image" string "$wallpaper"
  set_property "$base/last-single-image" string "$wallpaper"
}

apply_to_current_session() {
  for workspace in workspace0 workspace1 workspace2 workspace3; do
    set_monitor_wallpaper monitorVNC-0 "$workspace"
  done

  for monitor in monitor0 monitor1; do
    set_monitor_wallpaper "$monitor" ""
  done

  timeout 5s xfdesktop --reload >/dev/null 2>&1 || true
}

applied=0
seen_buses=""

for _ in $(seq 1 45); do
  xdpyinfo >/dev/null 2>&1 || {
    sleep 1
    continue
  }

  for pid in $(pgrep -x xfdesktop 2>/dev/null); do
    session_display="$(read_proc_env "$pid" DISPLAY)"
    session_bus="$(read_proc_env "$pid" DBUS_SESSION_BUS_ADDRESS)"
    session_manager="$(read_proc_env "$pid" SESSION_MANAGER)"

    if [ -z "$session_display" ] || [ -z "$session_bus" ]; then
      continue
    fi

    case " $seen_buses " in
      *" $session_bus "*) continue ;;
    esac
    seen_buses="$seen_buses $session_bus"

    export DISPLAY="$session_display"
    export DBUS_SESSION_BUS_ADDRESS="$session_bus"
    if [ -n "$session_manager" ]; then
      export SESSION_MANAGER="$session_manager"
    else
      unset SESSION_MANAGER
    fi

    if xfconf-query -c xfce4-desktop -l >/dev/null 2>&1; then
      apply_to_current_session
      applied=1
      echo "$LOG_PREFIX applied lab $LAB_ID wallpaper on pid $pid: $wallpaper"
    fi
  done

  if [ "$applied" -eq 1 ]; then
    exit 0
  fi

  sleep 1
done

echo "$LOG_PREFIX xfdesktop session is not ready"
exit 0
