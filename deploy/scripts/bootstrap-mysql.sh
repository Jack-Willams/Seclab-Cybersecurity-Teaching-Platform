#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/seclab/SecLab}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-seclab-mysql}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-han0.521}"
MYSQL_APP_USER="${MYSQL_APP_USER:-seclab_app}"
MYSQL_APP_PASSWORD="${MYSQL_APP_PASSWORD:-Seclab@123}"
MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-/opt/seclab/data/mysql}"

mkdir -p "$MYSQL_DATA_DIR"

if ! docker ps -a --format '{{.Names}}' | grep -qx "$MYSQL_CONTAINER"; then
  docker run -d --name "$MYSQL_CONTAINER" \
    --restart unless-stopped \
    -p 127.0.0.1:3306:3306 \
    -v "$MYSQL_DATA_DIR:/var/lib/mysql" \
    -e MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
    -e MYSQL_DATABASE=userservice \
    -e MYSQL_USER="$MYSQL_APP_USER" \
    -e MYSQL_PASSWORD="$MYSQL_APP_PASSWORD" \
    -e MYSQL_CHARACTER_SET_SERVER=utf8mb4 \
    -e MYSQL_COLLATION_SERVER=utf8mb4_unicode_ci \
    mysql:8.0 --default-authentication-plugin=mysql_native_password
else
  docker start "$MYSQL_CONTAINER" >/dev/null
fi

echo "Waiting for MySQL..."
for _ in {1..60}; do
  if docker exec "$MYSQL_CONTAINER" mysqladmin ping -uroot -p"$MYSQL_ROOT_PASSWORD" --silent >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

mysql_root() {
  docker exec -i "$MYSQL_CONTAINER" mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 "$@"
}

mysql_root <<SQL
CREATE DATABASE IF NOT EXISTS userservice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS seclab_profile CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS seclab_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS imagedb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MYSQL_APP_USER}'@'%' IDENTIFIED BY '${MYSQL_APP_PASSWORD}';
GRANT ALL PRIVILEGES ON userservice.* TO '${MYSQL_APP_USER}'@'%';
GRANT ALL PRIVILEGES ON seclab_profile.* TO '${MYSQL_APP_USER}'@'%';
GRANT ALL PRIVILEGES ON seclab_db.* TO '${MYSQL_APP_USER}'@'%';
GRANT ALL PRIVILEGES ON imagedb.* TO '${MYSQL_APP_USER}'@'%';
GRANT CREATE, DROP ON *.* TO '${MYSQL_APP_USER}'@'%';
FLUSH PRIVILEGES;
SQL

mysql_root userservice <<'SQL'
CREATE TABLE IF NOT EXISTS `course` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cost_time` int DEFAULT NULL,
  `course_description` varchar(255) NOT NULL,
  `difficulty` int DEFAULT NULL COMMENT '难度,1-5',
  `image_url` varchar(255) DEFAULT NULL,
  `instructor` varchar(255) DEFAULT NULL,
  `course_name` varchar(255) NOT NULL,
  `schedule` varchar(255) DEFAULT NULL,
  `course_status` tinyint DEFAULT NULL,
  `tags` longtext,
  `type` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `module` (
  `module_id` int NOT NULL AUTO_INCREMENT,
  `difficulty` int DEFAULT NULL,
  `image_id` int DEFAULT NULL,
  `introduction` varchar(255) DEFAULT NULL,
  `module_name` varchar(255) DEFAULT NULL,
  `task_points` longtext,
  `type` longtext,
  PRIMARY KEY (`module_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `module_course` (
  `course_id` int NOT NULL,
  `module_id` int NOT NULL,
  KEY `idx_module_course_module_id` (`module_id`),
  KEY `idx_module_course_course_id` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
SQL

import_sql() {
  local file="$1"
  if [[ -f "$file" ]]; then
    echo "Importing $file"
    mysql_root < "$file"
  else
    echo "Skip missing SQL: $file"
  fi
}

import_sql "$PROJECT_DIR/database/sql/user-service-local-init.sql"
import_sql "$PROJECT_DIR/DataStr/userservice_course_seed_from_frontend.sql"
import_sql "$PROJECT_DIR/DataStr/userservice_module_seed_from_frontend.sql"
import_sql "$PROJECT_DIR/DataStr/learning_event.sql"
import_sql "$PROJECT_DIR/DataStr/lab_session_flag.sql"
import_sql "$PROJECT_DIR/DataStr/question_submission.sql"
import_sql "$PROJECT_DIR/DataStr/container_command_event.sql"
import_sql "$PROJECT_DIR/DataStr/container_file_event.sql"
import_sql "$PROJECT_DIR/DataStr/error_event.sql"
import_sql "$PROJECT_DIR/DataStr/student_profile_snapshot.sql"
import_sql "$PROJECT_DIR/DataStr/class_profile_snapshot.sql"
import_sql "$PROJECT_DIR/DataStr/personalized_training.sql"
import_sql "$PROJECT_DIR/DataStr/ai_chat.sql"
import_sql "$PROJECT_DIR/DataStr/operation-session.sql"
import_sql "$PROJECT_DIR/DataStr/seed-demo-scoreboard-data.sql"
import_sql "$PROJECT_DIR/DataStr/seed-demo-teacher-data.sql"

echo "MySQL bootstrap complete."
