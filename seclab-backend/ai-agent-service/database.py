import pymysql

from config import (
    MYSQL_CHARSET,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)


def get_connection(use_database: bool = True):
    """Create a short-lived MySQL connection for repository operations."""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE if use_database else None,
        charset=MYSQL_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def ensure_database() -> None:
    """Create the configured database if it does not exist."""
    database_name = MYSQL_DATABASE.replace("`", "``")
    with get_connection(use_database=False) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
