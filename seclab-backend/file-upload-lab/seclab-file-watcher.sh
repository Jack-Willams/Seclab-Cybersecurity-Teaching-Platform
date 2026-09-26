#!/usr/bin/env sh

# Reusable polling watcher for SecLab file-change collection.
# It reports create/modify/delete events for one directory. It does not inspect
# file contents beyond a SHA-256 digest and does not perform profiling.

set -u

: "${SECLAB_AGENT_URL:=http://host.docker.internal:8010}"
: "${SECLAB_FILE_WATCH_DIR:=/var/www/html/uploads}"
: "${SECLAB_FILE_WATCH_INTERVAL:=2}"
: "${SECLAB_FILE_SOURCE:=watcher}"
: "${SECLAB_CONTAINER_NAME:=${HOSTNAME:-unknown}}"

STATE_DIR="/tmp/seclab-file-watcher"
CURRENT_STATE="$STATE_DIR/current.tsv"
PREVIOUS_STATE="$STATE_DIR/previous.tsv"
mkdir -p "$STATE_DIR"
: > "$PREVIOUS_STATE"

_sha256_file() {
  if [ -f "$1" ] && command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" 2>/dev/null | awk '{print $1}'
  else
    printf ''
  fi
}

_file_size() {
  if [ -f "$1" ]; then
    wc -c < "$1" 2>/dev/null | tr -d ' '
  else
    printf ''
  fi
}

_file_ext() {
  base="$(basename "$1")"
  case "$base" in
    *.*) printf '.%s' "${base##*.}" | tr '[:upper:]' '[:lower:]' ;;
    *) printf '' ;;
  esac
}

_is_key_file() {
  base="$(basename "$1" | tr '[:upper:]' '[:lower:]')"
  ext="$(_file_ext "$1")"
  case "$base" in
    exploit.py|payload.txt|script.sh|index.php|config.php) return 0 ;;
  esac
  case "$ext" in
    .php|.py|.sh) return 0 ;;
  esac
  return 1
}

_json_escape() {
  php -r 'echo json_encode($argv[1], JSON_UNESCAPED_UNICODE);' "$1"
}

_json_number_or_null() {
  case "${1:-}" in
    ''|*[!0-9]*) printf 'null' ;;
    *) printf '%s' "$1" ;;
  esac
}

_post_event() {
  action="$1"
  file_path="$2"
  size_before="$3"
  size_after="$4"
  sha256="$5"
  file_ext="$(_file_ext "$file_path")"
  is_key=false
  if _is_key_file "$file_path"; then
    is_key=true
  fi

  endpoint="${SECLAB_AGENT_URL%/}/api/container/files"
  request_id="file-$(date +%s)-$$-$(basename "$file_path" | tr -cd 'A-Za-z0-9._-' | cut -c1-24)"

  payload="$(cat <<EOF
{
  "lab_session_id": $(_json_escape "${SECLAB_LAB_SESSION_ID:-}"),
  "user_id": $(_json_number_or_null "${SECLAB_USER_ID:-}"),
  "class_id": $(_json_number_or_null "${SECLAB_CLASS_ID:-}"),
  "course_id": $(_json_number_or_null "${SECLAB_COURSE_ID:-}"),
  "module_id": $(_json_number_or_null "${SECLAB_MODULE_ID:-}"),
  "task_id": $(_json_number_or_null "${SECLAB_TASK_ID:-}"),
  "container_name": $(_json_escape "$SECLAB_CONTAINER_NAME"),
  "file_path": $(_json_escape "$file_path"),
  "file_ext": $(_json_escape "$file_ext"),
  "action": $(_json_escape "$action"),
  "size_before": ${size_before:-null},
  "size_after": ${size_after:-null},
  "sha256": $(_json_escape "$sha256"),
  "is_key_file": $is_key,
  "source": $(_json_escape "$SECLAB_FILE_SOURCE"),
  "request_id": $(_json_escape "$request_id"),
  "changed_at": $(_json_escape "$(date -u +%Y-%m-%dT%H:%M:%SZ)")
}
EOF
)"

  php -r '
    $url = $argv[1];
    $payload = $argv[2];
    $options = [
      "http" => [
        "method" => "POST",
        "header" => "Content-Type: application/json\r\n",
        "content" => $payload,
        "timeout" => 2,
      ],
    ];
    @file_get_contents($url, false, stream_context_create($options));
  ' "$endpoint" "$payload" >/dev/null 2>&1 || true
}

_snapshot() {
  : > "$CURRENT_STATE"
  if [ ! -d "$SECLAB_FILE_WATCH_DIR" ]; then
    return
  fi
  find "$SECLAB_FILE_WATCH_DIR" -type f 2>/dev/null | sort | while IFS= read -r file_path; do
    size="$(_file_size "$file_path")"
    sha="$(_sha256_file "$file_path")"
    printf '%s\t%s\t%s\n' "$file_path" "$size" "$sha" >> "$CURRENT_STATE"
  done
}

_get_previous_line() {
  grep -F "$(printf '%s\t' "$1")" "$PREVIOUS_STATE" 2>/dev/null | head -n 1 || true
}

echo "[SecLabFileWatcher] watching $SECLAB_FILE_WATCH_DIR"
_snapshot
cp "$CURRENT_STATE" "$PREVIOUS_STATE"

while true; do
  sleep "$SECLAB_FILE_WATCH_INTERVAL"
  _snapshot

  while IFS="$(printf '\t')" read -r file_path size_after sha_after; do
    [ -n "${file_path:-}" ] || continue
    old_line="$(_get_previous_line "$file_path")"
    if [ -z "$old_line" ]; then
      _post_event "create" "$file_path" "" "$size_after" "$sha_after"
    else
      old_size="$(printf '%s' "$old_line" | awk -F '\t' '{print $2}')"
      old_sha="$(printf '%s' "$old_line" | awk -F '\t' '{print $3}')"
      if [ "$old_size" != "$size_after" ] || [ "$old_sha" != "$sha_after" ]; then
        _post_event "modify" "$file_path" "$old_size" "$size_after" "$sha_after"
      fi
    fi
  done < "$CURRENT_STATE"

  while IFS="$(printf '\t')" read -r file_path size_before sha_before; do
    [ -n "${file_path:-}" ] || continue
    if ! grep -F "$(printf '%s\t' "$file_path")" "$CURRENT_STATE" >/dev/null 2>&1; then
      _post_event "delete" "$file_path" "$size_before" "" ""
    fi
  done < "$PREVIOUS_STATE"

  cp "$CURRENT_STATE" "$PREVIOUS_STATE"
done
