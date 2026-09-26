#!/bin/bash
set -u

# Watch X11 resolution changes triggered by noVNC SetDesktopSize. XFCE's
# panel can keep its old absolute position after RandR changes, so restart
# panel/desktop in the real XFCE session whenever the framebuffer size moves.

export DISPLAY="${DISPLAY:-:1}"
last=""

load_xfce_env() {
  local pid
  pid="$(pgrep -n xfce4-panel || pgrep -n xfdesktop || true)"
  if [ -z "$pid" ] || [ ! -r "/proc/$pid/environ" ]; then
    return 0
  fi

  local env_file
  env_file="$(mktemp)"
  tr '\0' '\n' < "/proc/$pid/environ" > "$env_file"

  local value
  value="$(grep '^DISPLAY=' "$env_file" | tail -n 1 | cut -d= -f2- || true)"
  [ -n "$value" ] && export DISPLAY="$value"

  value="$(grep '^DBUS_SESSION_BUS_ADDRESS=' "$env_file" | tail -n 1 | cut -d= -f2- || true)"
  [ -n "$value" ] && export DBUS_SESSION_BUS_ADDRESS="$value"

  value="$(grep '^SESSION_MANAGER=' "$env_file" | tail -n 1 | cut -d= -f2- || true)"
  [ -n "$value" ] && export SESSION_MANAGER="$value"

  rm -f "$env_file"
}

for _ in $(seq 1 30); do
  load_xfce_env
  xdpyinfo >/dev/null 2>&1 && break
  sleep 1
done

while true; do
  load_xfce_env
  cur="$(xdpyinfo 2>/dev/null | awk '/dimensions:/ {print $2}')"
  if [ -n "$cur" ] && [ "$cur" != "$last" ]; then
    if [ -n "$last" ]; then
      sleep 0.5
      xfce4-panel --restart >/dev/null 2>&1 &
      xfdesktop --reload >/dev/null 2>&1 &
    fi
    last="$cur"
  fi
  sleep 2
done
