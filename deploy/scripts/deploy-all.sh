#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/seclab/SecLab}"
DEPLOY_DIR="$PROJECT_DIR/deploy"
SYSTEMD_DIR="/etc/systemd/system"
NGINX_AVAILABLE="/etc/nginx/sites-available/seclab"
NGINX_ENABLED="/etc/nginx/sites-enabled/seclab"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-pypi.tuna.tsinghua.edu.cn}"

mkdir -p /opt/seclab/logs /opt/seclab/data/mysql

if ! id seclab >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin seclab
fi
usermod -aG docker seclab 2>/dev/null || true
chown -R seclab:seclab /opt/seclab/logs

systemctl stop seclab-ai-agent seclab-user-service seclab-experiment-module 2>/dev/null || true
docker rm -f seclab-ai-agent seclab-user-service seclab-experiment-module-service 2>/dev/null || true
pkill -f 'user-service.*bootRun|experiment-module-service.*bootRun|docker-api-server.js' 2>/dev/null || true
fuser -k 8010/tcp 8083/tcp 8084/tcp 2>/dev/null || true

bash "$DEPLOY_DIR/scripts/bootstrap-mysql.sh"

cd "$PROJECT_DIR/seclab-backend/ai-agent-service"
python3 -m venv venv
./venv/bin/pip install -i "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST" --upgrade pip
./venv/bin/pip install -i "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST" -r requirements.txt
./venv/bin/pip install -i "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST" cryptography uvicorn

cd "$PROJECT_DIR/seclab-backend"
chmod +x ./gradlew
printf 'org.gradle.java.installations.paths=/usr/lib/jvm/java-17-openjdk-amd64\n' > gradle.properties
./gradlew :user-service:bootJar :experiment-module-service:bootJar

cd "$PROJECT_DIR/seclab-backend/operation-image"
docker build -t seclab-op-web-tools:1.0 .

for lab in sqli-lab xss-lab csrf-lab command-inject file-upload-lab directory-traversal-lab; do
  if [[ -f "$PROJECT_DIR/seclab-backend/$lab/docker-compose.yml" ]]; then
    if docker compose version >/dev/null 2>&1; then
      (cd "$PROJECT_DIR/seclab-backend/$lab" && docker compose up -d)
    else
      (cd "$PROJECT_DIR/seclab-backend/$lab" && docker-compose up -d)
    fi
  fi
done

cd "$PROJECT_DIR/SecLab-FrontEnd-2"
npm install
npm run build

install -m 0644 "$DEPLOY_DIR/systemd/seclab-ai-agent.service" "$SYSTEMD_DIR/seclab-ai-agent.service"
install -m 0644 "$DEPLOY_DIR/systemd/seclab-user-service.service" "$SYSTEMD_DIR/seclab-user-service.service"
install -m 0644 "$DEPLOY_DIR/systemd/seclab-experiment-module.service" "$SYSTEMD_DIR/seclab-experiment-module.service"
systemctl daemon-reload
systemctl enable --now seclab-ai-agent seclab-user-service seclab-experiment-module

install -m 0644 "$DEPLOY_DIR/nginx/seclab.conf" "$NGINX_AVAILABLE"
ln -sfn "$NGINX_AVAILABLE" "$NGINX_ENABLED"
nginx -t
systemctl restart nginx

echo "SecLab deployment finished. Open http://<server-ip>:8088/ from the campus LAN."
