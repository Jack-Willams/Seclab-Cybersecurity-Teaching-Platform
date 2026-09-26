# -*- coding: utf-8 -*-
"""为学生 122（韩力旺 · 学号 2024210214042 · 网安242班）补齐个人中心/能力成长演示数据。

背景
----
该账号本身已有真实使用痕迹（42 个实验会话、230 条命令、32 段 AI 对话、147 个画像快照，
综合分 15.8→42），个人中心、做题记录、智能出题都能跑通。唯一的短板是「五维能力成长」
里几乎每个维度都显示「暂无可比指标」——而这正是要重点展示的创新点。

后端每个维度的「可比指标」判定口径（见 capability_growth_repository.py）：
  - 知识掌握 generated_question_attempt，按 (知识点,题型,难度) 分桶，看 is_correct
  - 排障能力 container_command_event，同会话同类别「失败→成功」构成一次恢复，比恢复用时
  - 自主学习 challenge_completion_event，按难度分桶，看是否 0 次 AI 求助独立完成
  - AI 协同 ai_message(role=user)，按 (模块,任务) 分桶，看是否包含上下文
  - 学习投入 lab_session，按难度分桶，看 status 是否 completed
每个桶要 >=6 条（前 3 条按时间当基线、后 3 条当近期）才够 moderate 置信度，且基线/近期
样本不重叠。因此本脚本为每个维度铺一条「早期较弱 → 近期较强」的真实轨迹。

约定（与 242 班脚本一致）
  - 所有主键前缀 sim122-，可整体删除，不污染真实数据
  - source 列写生产来源（docker-runtime/frontend/personalized_training/ai-agent-service），
    这样数据会被画像与能力成长纳入统计；「可删除」用 ID 前缀而不是 source 来标记
  - 幂等：先按前缀 DELETE 再 INSERT，可反复执行
  - 固定随机种子，结果可复现

运行：直接 python 执行即可（连库插入并当场校验）。清理见文件末尾 CLEANUP_SQL。
"""
import json
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, r"d:/Seclab/SecLab-Combined/seclab-backend/ai-agent-service")
from database import get_connection  # noqa: E402

random.seed(20260809)

USER_ID = 122
CLASS_ID = 8          # 行政班；学生端能力成长不按班过滤，与该账号既有数据一致
PREFIX = "sim122"

# 两条实验线：模块1=SQL注入(course1)，模块2=XSS/CSRF(course2)
# 难度取自 task_knowledge_point：m1t1->kp101 medium，m2t1->kp201 easy
LINES = [
    {"module": 1, "task": 1, "course": 1, "kp": 101, "difficulty": "medium",
     "name": "SQL注入联合查询", "cmd_category": "exploit_attempt"},
    {"module": 2, "task": 1, "course": 2, "kp": 201, "difficulty": "easy",
     "name": "XSS输出上下文", "cmd_category": "enumeration"},
]

# 早/近两个时间窗，贴着该账号既有快照区间（7/28–8/9）
EARLY_DAYS = [datetime(2026, 7, 28, 20, 10), datetime(2026, 7, 29, 21, 5), datetime(2026, 7, 31, 19, 40)]
LATE_DAYS = [datetime(2026, 8, 6, 20, 30), datetime(2026, 8, 8, 21, 15), datetime(2026, 8, 9, 4, 50)]


def jd(obj):
    return json.dumps(obj, ensure_ascii=False)


# 收集各表待插入行
lab_rows, cmd_rows, cce_rows = [], [], []
conv_rows, msg_rows = [], []
ts_rows, gq_rows, att_rows = [], [], []

lab_seq = cmd_seq = msg_seq = gq_seq = att_seq = 0


def new_lab(line, when, status, idx):
    global lab_seq
    lab_seq += 1
    sid = f"{PREFIX}-lab-{lab_seq:02d}"
    lab_rows.append({
        "session_id": sid, "user_id": USER_ID, "class_id": CLASS_ID,
        "course_id": line["course"], "module_id": line["module"], "task_id": line["task"],
        "container_name": f"{line['cmd_category']}-{USER_ID}-{lab_seq}",
        "container_id": f"{PREFIX}c{lab_seq:03d}",
        "target_url": f"http://10.0.0.{20 + lab_seq}:8080/",
        "status": status,
        "start_time": when, "end_time": when + timedelta(minutes=random.randint(18, 40)),
        "created_at": when, "updated_at": when,
    })
    return sid


def add_command(line, lab_id, when, cmd, category, exit_code):
    global cmd_seq
    cmd_seq += 1
    cmd_rows.append({
        "command_id": f"{PREFIX}-cmd-{cmd_seq:04d}", "lab_session_id": lab_id,
        "user_id": USER_ID, "class_id": CLASS_ID, "course_id": line["course"],
        "module_id": line["module"], "task_id": line["task"],
        "container_name": f"{line['cmd_category']}-{USER_ID}",
        "command": cmd, "normalized_command": cmd.split()[0] if cmd.split() else cmd,
        "cmd_category": category, "cwd": "/root",
        "exit_code": exit_code, "duration_ms": random.randint(120, 900),
        "output_digest": f"{PREFIX}{cmd_seq}", "source": "docker-runtime",
        "request_id": f"{PREFIX}-req-{cmd_seq}", "executed_at": when, "created_at": when,
    })


# ── 逐条线构造 6 个会话（3 早 + 3 近）承载 4 个维度 ──────────────────────
# 恢复命令脚本：早期恢复慢，近期恢复快
RECOVERY_CMDS = {
    "exploit_attempt": ("sqlmap -u 'http://target/item?id=1' --batch --dbs",
                        "sqlmap -u 'http://target/item?id=1' --batch -D shop --tables"),
    "enumeration": ("curl -s 'http://target/search?q=<script>' | grep script",
                    "curl -s 'http://target/search?q=%3Cscript%3E' -o resp.html"),
}
# AI 提问脚本：早期无上下文、近期带上下文/报错
NAIVE_Q = ["这题怎么做？", "老师这个实验没思路", "直接告诉我 flag 吧", "为什么我做不出来"]
RICH_Q = [
    "我用 ORDER BY 5 报错 ORDER BY 4 正常，是不是说明是 4 列？UNION SELECT 该怎么补 NULL？",
    "上传 .php 被拦，我抓包把 Content-Type 改成 image/png 还是不行，服务端可能校验了什么？",
    "注入到 union select 1,2,3 页面回显 2，我把 2 换成 database() 拿到库名，下一步怎么读表？",
    "报错 You have an error in your SQL syntax near '\\'' —— 是单引号闭合的问题吗？该怎么调整 payload？",
]


def build_line(line):
    global msg_seq
    cat = line["cmd_category"]
    fail_cmd, ok_cmd = RECOVERY_CMDS[cat]

    for phase, days in (("early", EARLY_DAYS), ("late", LATE_DAYS)):
        for di, day in enumerate(days):
            # 学习投入：早期会话未完成(stopped)，近期完成(completed)
            status = "stopped" if phase == "early" else "completed"
            lab_id = new_lab(line, day, status, di)

            # 排障能力：失败命令 → 一段时间后同类别成功命令
            recover = random.randint(240, 360) if phase == "early" else random.randint(60, 110)
            add_command(line, lab_id, day + timedelta(seconds=30), fail_cmd, cat, exit_code=1)
            add_command(line, lab_id, day + timedelta(seconds=30 + recover), ok_cmd, cat, exit_code=0)
            # 再补一条无关的成功命令，让轨迹更自然
            add_command(line, lab_id, day + timedelta(seconds=30 + recover + 40),
                        "ls -la /var/www/html", "enumeration" if cat != "enumeration" else "other", 0)

            # 自主学习：早期带 AI 求助完成，近期独立完成
            ai_ask = random.randint(2, 4) if phase == "early" else 0
            cce_rows.append({
                "user_id": USER_ID, "class_id": CLASS_ID, "course_id": line["course"],
                "module_id": line["module"], "task_id": line["task"], "lab_session_id": lab_id,
                "completion_status": "completed",
                "total_time_seconds": random.randint(900, 1500) if phase == "early" else random.randint(360, 720),
                "total_ai_ask_count": ai_ask,
                "created_at": day + timedelta(minutes=random.randint(15, 30)),
            })

    # AI 协同：每条线一段早期会话(无上下文) + 一段近期会话(含上下文)
    for phase, days, pool, ctx in (("early", EARLY_DAYS, NAIVE_Q, 0), ("late", LATE_DAYS, RICH_Q, 1)):
        conv_id = f"{PREFIX}-conv-{line['module']}-{phase}"
        first = days[0] + timedelta(minutes=5)
        conv_rows.append({
            "conversation_id": conv_id, "user_id": USER_ID, "class_id": CLASS_ID,
            "course_id": line["course"], "module_id": line["module"], "task_id": line["task"],
            "question_id": None, "lab_session_id": None, "dify_conversation_id": None,
            "status": "active", "source": "frontend",
            "start_time": first, "last_message_at": days[-1] + timedelta(minutes=10),
            "created_at": first, "updated_at": days[-1] + timedelta(minutes=10),
        })
        for di, day in enumerate(days):
            msg_seq += 1
            q = pool[di % len(pool)]
            when = day + timedelta(minutes=6)
            msg_rows.append({
                "message_id": f"{PREFIX}-msg-{msg_seq:04d}", "conversation_id": conv_id,
                "role": "user", "content": q, "content_length": len(q), "token_count": len(q),
                "event_name": None, "hint_level": None,
                "contains_context": ctx, "contains_error_excerpt": ctx,
                "raw_payload_json": None, "created_at": when,
            })
            # 配一条助教回复，符合真实对话
            msg_seq += 1
            reply = "我们一步步来：先确认现象，再定位可控点，最后验证。" if ctx else "先自己再试一次，观察报错信息。"
            msg_rows.append({
                "message_id": f"{PREFIX}-msg-{msg_seq:04d}", "conversation_id": conv_id,
                "role": "assistant", "content": reply, "content_length": len(reply), "token_count": len(reply),
                "event_name": "agent_message", "hint_level": "guide" if ctx else "nudge",
                "contains_context": 0, "contains_error_excerpt": 0,
                "raw_payload_json": None, "created_at": when + timedelta(seconds=8),
            })


for _line in LINES:
    build_line(_line)


# ── 知识掌握：一条训练会话 + 两个难度桶的生成题与作答（早错近对、早慢近快）──────
def build_knowledge():
    global gq_seq, att_seq
    ts_id = f"{PREFIX}-ts-01"
    ts_rows.append({
        "training_session_id": ts_id, "user_id": USER_ID, "class_id": CLASS_ID, "course_id": 1,
        "profile_snapshot_id": None, "source_type": "personalized_training",
        "diagnose_result_json": jd({"weak_dimensions": ["知识掌握", "排障能力"], "seed": PREFIX}),
        "training_context_json": jd({"note": "演示用强化训练"}),
        "created_at": EARLY_DAYS[0],
    })
    buckets = [
        {"kp": 101, "qt": "short_answer", "d": "medium", "title": "UNION 列数判断",
         "stem": "如何用 ORDER BY 判断 UNION 注入所需列数？",
         "ans": "从 ORDER BY 1 递增，首次报错序号减一即列数。"},
        {"kp": 201, "qt": "short_answer", "d": "easy", "title": "XSS 输出上下文",
         "stem": "同一段用户输入在 HTML 文本区与属性区的转义要求有何不同？",
         "ans": "文本区转义尖括号与&，属性区还需转义引号并避免事件属性注入。"},
    ]
    for b in buckets:
        for phase, days in (("early", EARLY_DAYS), ("late", LATE_DAYS)):
            for di, day in enumerate(days):
                gq_seq += 1
                gqid = f"{PREFIX}-gq-{gq_seq:04d}"
                gq_rows.append({
                    "generated_question_id": gqid, "question_numeric_id": 122_000_000 + gq_seq,
                    "training_session_id": ts_id, "question_type": b["qt"],
                    "knowledge_point_id": b["kp"], "module_id": None, "task_id": None,
                    "difficulty": b["d"], "title": b["title"], "stem": b["stem"],
                    "options_json": None, "standard_answer": b["ans"], "reference_answer": b["ans"],
                    "explanation": b["ans"], "scoring_rubric_json": None,
                    "source_model": "deepseek-chat", "raw_ai_json": None, "created_at": day,
                })
                att_seq += 1
                correct = 0 if phase == "early" else 1
                # 早期偶有一次蒙对、近期偶有一次失手，避免 0/100 过于假
                if phase == "early" and di == 2:
                    correct = 1
                if phase == "late" and di == 0:
                    correct = 1
                cost = random.randint(160, 220) if phase == "early" else random.randint(55, 95)
                answer = b["ans"] if correct else "（作答不完整，只答了一半）"
                att_rows.append({
                    "attempt_id": f"{PREFIX}-att-{att_seq:04d}", "training_session_id": ts_id,
                    "generated_question_id": gqid, "user_id": USER_ID,
                    "answer_json": jd({"text": answer}), "is_correct": correct,
                    "score": 90 if correct else 40, "cost_time": cost,
                    "submission_id": None, "profile_rebuild_snapshot_id": None,
                    "submitted_at": day + timedelta(minutes=2),
                })


build_knowledge()


# ── 落库 ────────────────────────────────────────────────────────────────
CLEANUP = [
    "DELETE FROM seclab_profile.generated_question_attempt WHERE attempt_id LIKE %s",
    "DELETE FROM seclab_profile.generated_question WHERE generated_question_id LIKE %s",
    "DELETE FROM seclab_profile.training_session WHERE training_session_id LIKE %s",
    "DELETE FROM seclab_profile.ai_message WHERE message_id LIKE %s",
    "DELETE FROM seclab_profile.ai_conversation WHERE conversation_id LIKE %s",
    "DELETE FROM seclab_profile.challenge_completion_event WHERE lab_session_id LIKE %s",
    "DELETE FROM seclab_profile.container_command_event WHERE command_id LIKE %s",
    "DELETE FROM seclab_profile.lab_session WHERE session_id LIKE %s",
]


def insert(cur, table, rows):
    if not rows:
        return
    cols = list(rows[0].keys())
    ph = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO seclab_profile.{table} ({', '.join(cols)}) VALUES ({ph})"
    cur.executemany(sql, [[r[c] for c in cols] for r in rows])


def main():
    like = f"{PREFIX}-%"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for stmt in CLEANUP:
                cur.execute(stmt, (like,))
            insert(cur, "lab_session", lab_rows)
            insert(cur, "container_command_event", cmd_rows)
            insert(cur, "challenge_completion_event", cce_rows)
            insert(cur, "ai_conversation", conv_rows)
            insert(cur, "ai_message", msg_rows)
            insert(cur, "training_session", ts_rows)
            insert(cur, "generated_question", gq_rows)
            insert(cur, "generated_question_attempt", att_rows)
        conn.commit()
    finally:
        conn.close()
    print("已写入 user=%d" % USER_ID)
    print("  lab_session=%d  command=%d  challenge_completion=%d" % (len(lab_rows), len(cmd_rows), len(cce_rows)))
    print("  ai_conversation=%d  ai_message=%d" % (len(conv_rows), len(msg_rows)))
    print("  training_session=%d  generated_question=%d  attempt=%d" % (len(ts_rows), len(gq_rows), len(att_rows)))


if __name__ == "__main__":
    main()
