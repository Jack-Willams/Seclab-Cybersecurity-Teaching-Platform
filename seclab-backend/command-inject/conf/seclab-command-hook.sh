#!/usr/bin/env bash

# Reusable interactive bash hook for SecLab command-event collection.
# It reports the last history command after each prompt returns; it does not
# watch file changes and it does not collect full command output.

if [ -n "${SECLAB_COMMAND_HOOK_LOADED:-}" ]; then
  return 0 2>/dev/null || exit 0
fi

export SECLAB_COMMAND_HOOK_LOADED=1
: "${SECLAB_AGENT_URL:=http://host.docker.internal:8010}"
: "${SECLAB_COMMAND_SOURCE:=hook}"
: "${SECLAB_CONTAINER_NAME:=${HOSTNAME:-unknown}}"

_seclab_last_history_id=""

_seclab_report_command() {
  local exit_code="$1"
  local history_line history_id command cwd endpoint

  history_line="$(HISTTIMEFORMAT= history 1 2>/dev/null || true)"
  history_id="$(printf '%s' "$history_line" | awk '{print $1}')"
  command="$(printf '%s' "$history_line" | sed -E 's/^[[:space:]]*[0-9]+[[:space:]]+//')"

  if [ -z "$command" ] || [ "$history_id" = "$_seclab_last_history_id" ]; then
    return "$exit_code"
  fi
  _seclab_last_history_id="$history_id"

  case "$command" in
    history*|exit|logout)
      return "$exit_code"
      ;;
  esac

  command="$(printf '%.2000s' "$command")"
  cwd="$(pwd -P 2>/dev/null || pwd)"
  endpoint="${SECLAB_AGENT_URL%/}/api/container/commands"

  if command -v php >/dev/null 2>&1; then
    php -r '
      $url = $argv[1];
      $payload = [
        "lab_session_id" => getenv("SECLAB_LAB_SESSION_ID") ?: null,
        "user_id" => getenv("SECLAB_USER_ID") ?: null,
        "class_id" => getenv("SECLAB_CLASS_ID") ?: null,
        "course_id" => getenv("SECLAB_COURSE_ID") ?: null,
        "module_id" => getenv("SECLAB_MODULE_ID") ?: null,
        "task_id" => getenv("SECLAB_TASK_ID") ?: null,
        "container_name" => getenv("SECLAB_CONTAINER_NAME") ?: gethostname(),
        "command" => $argv[2],
        "cwd" => $argv[4],
        "exit_code" => is_numeric($argv[3]) ? intval($argv[3]) : null,
        "duration_ms" => null,
        "output_digest" => null,
        "source" => getenv("SECLAB_COMMAND_SOURCE") ?: "hook",
        "request_id" => "cmd-" . bin2hex(random_bytes(8)),
        "executed_at" => gmdate("c"),
      ];
      $options = [
        "http" => [
          "method" => "POST",
          "header" => "Content-Type: application/json\r\n",
          "content" => json_encode($payload, JSON_UNESCAPED_UNICODE),
          "timeout" => 2,
        ],
      ];
      @file_get_contents($url, false, stream_context_create($options));
    ' "$endpoint" "$command" "$exit_code" "$cwd" >/dev/null 2>&1 || true
  fi

  return "$exit_code"
}

_seclab_prompt_command() {
  local exit_code="$?"
  _seclab_report_command "$exit_code"
  return "$exit_code"
}

case ";${PROMPT_COMMAND:-};" in
  *";_seclab_prompt_command;"*) ;;
  *) PROMPT_COMMAND="_seclab_prompt_command${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
esac
