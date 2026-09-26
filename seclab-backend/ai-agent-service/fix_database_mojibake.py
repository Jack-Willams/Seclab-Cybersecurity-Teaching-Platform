"""数据库乱码修复脚本

用于清理已经在 MySQL 中被错误编码存储的中文数据（mojibake）。
本脚本会依次处理以下数据库和表，尝试用 latin-1 / cp1252 / gbk / gb18030
等编码逆向恢复原文，并 UPDATE 回数据库。

处理顺序：
  1. userservice.course   — 课程名称（乱码源头）
  2. userservice.module   — 模块名称（乱码源头）
  3. seclab_profile.student_profile_snapshot — 已存的画像快照 JSON

使用前请：
1. 备份数据库
2. 按需设置环境变量（MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD）
3. 运行：python fix_database_mojibake.py
"""
import json
import os
import re
import sys
from typing import Any, Iterable, Optional

import pymysql

BASE_CONN = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "123456"),
    "charset": "utf8mb4",
}

# 按数据库分组的修复任务。
# 乱码的"源头"是 userservice.course / userservice.module 的名称字段，
# 画像快照 (seclab_profile.student_profile_snapshot.profile_summary_json)
# 里的乱码是这些源数据被序列化后残留的结果——两处都要修。
DATABASES_TO_FIX = [
    {
        "database": os.getenv("USERSERVICE_DATABASE", "userservice"),
        "tables": [
            {
                "table": "course",
                "id": "id",
                "columns": ["course_name", "course_description", "tags"],
            },
            {
                "table": "module",
                "id": "module_id",
                "columns": ["module_name", "introduction", "type"],
            },
        ],
    },
    {
        "database": os.getenv("MYSQL_DATABASE", "seclab_profile"),
        "tables": [
            {
                "table": "student_profile_snapshot",
                "id": "snapshot_id",
                "columns": [],  # profile_summary_json 单独处理
                "json_column": "profile_summary_json",
            },
        ],
    },
]

CJK_PATTERN = re.compile(r"[一-鿿㐀-䶿]")


def _contains_cjk(text: str) -> bool:
    return bool(CJK_PATTERN.search(text or ""))


def repair_double_encoded_utf8(text: str) -> str:
    """检测并修复因编码错误导致的乱码（mojibake）。

    安全策略：只在确认是乱码时修复，防止把正确中文"修复"成乱码。

    策略 1: Latin-1/CP1252 → UTF-8（安全：仅 0x80-0xFF 字符触发，
             正确中文均在 U+4E00 以上，不会被误修复）
    策略 2: GBK → UTF-8。不再要求同时包含 ASCII 字母——纯 CJK 乱码
             （如 "鐭ヨ瘑鎺屾彙" → "知识掌握"）同样需要修复。
             安全性：正确 UTF-8 中文 encode 成 GBK 再以 UTF-8 解码，
             几乎必然抛 UnicodeDecodeError 或得到非 CJK 结果，被
             _contains_cjk 拦截，不会误伤正确数据。
    策略 3: 包含 "?" 的疑似乱码（原始字节不可逆丢失场景）。
    """
    if not text or not isinstance(text, str):
        return text

    if text.isascii():
        return text

    latin1_high = sum(1 for ch in text if 0x80 <= ord(ch) <= 0xFF)
    has_cjk = _contains_cjk(text)

    # 策略 1：Latin-1/CP1252 → UTF-8（安全：仅 0x80-0xFF 字符触发）
    if latin1_high > 0:
        for enc in ("latin-1", "cp1252", "iso-8859-15"):
            try:
                repaired = text.encode(enc).decode("utf-8")
                if repaired != text and _contains_cjk(repaired):
                    return repaired
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

    # 策略 2：GBK → UTF-8。不要求 ASCII 字母，纯 CJK 乱码也能修复。
    if has_cjk and latin1_high == 0:
        for enc in ("gb18030", "gbk"):
            try:
                repaired = text.encode(enc).decode("utf-8")
                if repaired != text and _contains_cjk(repaired):
                    return repaired
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

    # 策略 3：包含 "?" 的疑似乱码
    if "?" in text and has_cjk and len(text) < 60:
        for enc in ("gbk", "gb18030"):
            try:
                repaired = text.encode(enc).decode("utf-8", errors="replace")
                repaired = repaired.replace("�", "")
                if _contains_cjk(repaired) and sum(1 for c in repaired if c == "?") < sum(
                    1 for c in text if c == "?"
                ):
                    return repaired
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

    return text


def fix_string(value: Optional[str]) -> tuple[Optional[str], bool]:
    if value is None or not isinstance(value, str):
        return value, False
    if value.isascii():
        return value, False
    repaired = repair_double_encoded_utf8(value)
    if repaired != value:
        return repaired, True
    return value, False


def fix_json_recursive(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        new_val, changed = fix_string(value)
        return new_val, changed
    if isinstance(value, list):
        changed = False
        new_list = []
        for item in value:
            new_item, item_changed = fix_json_recursive(item)
            new_list.append(new_item)
            changed = changed or item_changed
        return new_list, changed
    if isinstance(value, dict):
        changed = False
        new_dict = {}
        for k, v in value.items():
            new_v, v_changed = fix_json_recursive(v)
            new_dict[k] = new_v
            changed = changed or v_changed
        return new_dict, changed
    return value, False


def iter_rows(cursor, table: str, batch: int = 200) -> Iterable[dict]:
    cursor.execute(f"SELECT * FROM `{table}`")
    while True:
        rows = cursor.fetchmany(batch)
        if not rows:
            break
        for row in rows:
            yield row


def _table_exists(cursor, table: str) -> bool:
    cursor.execute("SHOW TABLES LIKE %s", (table,))
    return cursor.fetchone() is not None


def fix_table(cursor, conn, table_cfg: dict) -> int:
    table = table_cfg["table"]
    id_col = table_cfg["id"]
    columns = table_cfg.get("columns", [])
    json_col = table_cfg.get("json_column")
    print(f"\n>>> 处理表 `{table}` (id={id_col}, 字段={columns}, json={json_col})")

    fixed_rows = 0
    fixed_cells = 0
    for row in iter_rows(cursor, table):
        updates = {}
        for col in columns:
            original = row.get(col)
            if original is None:
                continue
            new_val, changed = fix_string(original)
            if changed:
                updates[col] = new_val
        if json_col:
            raw = row.get(json_col)
            if raw is not None:
                if isinstance(raw, (bytes, bytearray)):
                    try:
                        raw = raw.decode("utf-8")
                    except Exception:
                        continue
                try:
                    parsed = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    parsed = None
                if parsed is not None:
                    new_parsed, changed = fix_json_recursive(parsed)
                    if changed:
                        updates[json_col] = json.dumps(new_parsed, ensure_ascii=False)
        if updates:
            fixed_rows += 1
            fixed_cells += len(updates)
            set_clause = ", ".join(f"`{k}` = %s" for k in updates.keys())
            params = list(updates.values()) + [row[id_col]]
            try:
                cursor.execute(
                    f"UPDATE `{table}` SET {set_clause} WHERE `{id_col}` = %s",
                    params,
                )
            except Exception as e:
                print(f"  ! UPDATE 失败: id={row[id_col]} err={e}")
                continue
    if fixed_rows:
        conn.commit()
    print(f"  修复完成: {fixed_rows} 行 / {fixed_cells} 个字段")
    return fixed_rows


def fix_database(db_cfg: dict) -> int:
    database = db_cfg["database"]
    print(f"\n########## 数据库 `{database}` ##########")
    print(f"连接到 {BASE_CONN['host']}:{BASE_CONN['port']}/{database}")
    try:
        conn = pymysql.connect(
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            **BASE_CONN,
        )
    except Exception as e:
        print(f"  连接失败（跳过该库）: {e}")
        return 0

    subtotal = 0
    try:
        with conn.cursor() as cursor:
            for table_cfg in db_cfg["tables"]:
                if not _table_exists(cursor, table_cfg["table"]):
                    print(f"  表 `{table_cfg['table']}` 不存在，跳过")
                    continue
                subtotal += fix_table(cursor, conn, table_cfg)
    finally:
        conn.close()
    return subtotal


def main():
    total = 0
    for db_cfg in DATABASES_TO_FIX:
        total += fix_database(db_cfg)
    print(f"\n=== 全部完成: 共修复 {total} 行 ===")


if __name__ == "__main__":
    main()
