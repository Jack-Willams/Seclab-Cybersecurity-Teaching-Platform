#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://127.0.0.1:8010/docs >/dev/null && echo "ai-agent-service: ok"
curl -fsS http://127.0.0.1:8084/course/overview-list >/dev/null && echo "experiment-module-service: ok"
curl -fsS http://127.0.0.1:8083/stu/profile >/dev/null || echo "user-service profile requires token, service may still be up"

curl -fsS -X POST http://127.0.0.1:8010/api/docker/operation/start \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"module_id":1}' | tee /tmp/seclab-operation-start.json

echo
echo "If operation start returned success, stop it from the UI or POST /api/docker/operation/stop with the session_id."
