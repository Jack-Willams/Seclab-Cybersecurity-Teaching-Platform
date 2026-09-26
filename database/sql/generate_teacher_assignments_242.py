# -*- coding: utf-8 -*-
"""为 242 班（教学班 5）构造「教师下发强化练习」的两端演示数据。

覆盖的链路：
  教师端 教学分析 → 教学行动面板（下发记录、完成进度）
  学生端 个人中心 → 老师布置（待开始 / 进行中 / 已完成 三种状态）

设计要点
  - 走 create_intervention() 真实代码路径建下发单，不手工拼 teacher_intervention 行，
    这样字段校验（班级归属、题目归属、action_type）和真实下发完全一致
  - 学生完成度是后端从 training_session 的题目数与作答数反推的
    （见 resolve_assignment_status），所以「已完成」必须真的有题目和作答，
    不能只把 assignment_status 改成 COMPLETED
  - 主角 122（韩力旺）在三张单子里分别处于 已完成 / 进行中 / 待开始，
    同班同学给出不同进度，教师端的完成率才不是 0% 或 100%
  - 幂等：按 title 前缀清理旧单据，按 ID 前缀清理练习数据，可反复执行

运行：python generate_teacher_assignments_242.py
"""
import json
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, r"d:/Seclab/SecLab-Combined/seclab-backend/ai-agent-service")
from database import get_connection                                    # noqa: E402
from teacher_intervention_repository import create_intervention        # noqa: E402

random.seed(20260809)

TEACHER_ID = 1
CLASS_ID = 5            # 教学班：网安242班
ADMIN_CLASS_ID = 8      # 行政班，与该班学生既有数据一致
HERO = 122              # 韩力旺
PREFIX = "sim122-asg"
TITLE_TAG = "【强化】"   # 用于幂等清理

# 三张下发单。questions 用 122 自己训练里生成的题（归属校验要求出题人是本班学生）
PLANS = [
    {
        "key": "done",
        "title": f"{TITLE_TAG}SQL注入联合查询列数判断 · 专项强化",
        "action_type": "TARGETED_PRACTICE",
        "course_id": 1,
        "kp": 101,
        "description": "本实验该知识点错题率 46%，为错题学生下发三道递进练习：先判列数，再定回显位，最后读表。",
        "students": [HERO, 92, 93, 94],
        "hero_state": "COMPLETED",
        "days_ago": 6,
    },
    {
        "key": "doing",
        "title": f"{TITLE_TAG}XSS 输出上下文判断 · 专项强化",
        "action_type": "TARGETED_PRACTICE",
        "course_id": 2,
        "kp": 201,
        "description": "属性区与文本区的转义要求混淆是本班共性问题，安排上下文识别专项练习。",
        "students": [HERO, 95, 96],
        "hero_state": "STARTED",
        "days_ago": 2,
    },
    {
        "key": "todo",
        "title": f"{TITLE_TAG}XSS 防御边界与 CSP · 课堂例题",
        "action_type": "LESSON_EXAMPLE",
        "course_id": 2,
        "kp": 203,
        "description": "该知识点错题率 66%，选为下节课讲评例题，请提前预习并完成自测。",
        "students": [HERO, 97, 98, 99],
        "hero_state": "PENDING",
        "days_ago": 0,
    },
]

# 每张单子给学生的练习题（下发后学生开练时会落成自己的训练会话）
EXERCISES = {
    "done": [
        ("判断 UNION 注入列数", "目标页面 id 参数可注入，如何确定原查询的列数？请写出判断步骤。",
         "从 ORDER BY 1 递增试探，首次报错的序号减一即为列数，再用 UNION SELECT NULL 补齐验证。", 1, 95),
        ("定位回显位置", "已知列数为 4，如何确定哪一列会在页面上回显？",
         "用 UNION SELECT 1,2,3,4 观察页面显示的数字，该数字所在列即回显位。", 1, 90),
        ("从回显位读取表名", "拿到回显位后，如何读取当前库的所有表名？",
         "在回显位放 group_concat(table_name)，FROM information_schema.tables WHERE table_schema=database()。", 0, 55),
    ],
    "doing": [
        ("识别输出上下文", "同一段用户输入分别落在 <div> 内和 value=\"\" 属性里，转义要求有何不同？",
         "文本区需转义 < > &；属性区还需转义引号，否则可闭合属性注入事件处理器。", 1, 92),
        ("属性区闭合利用", "输入被放进 value=\"[输入]\"，且只过滤了尖括号，能否触发脚本？",
         "可以。用引号闭合 value 后接 onfocus/onmouseover 等事件属性即可，无需尖括号。", None, 0),
        ("选择正确的编码函数", "面对 HTML 属性区输出，应使用哪种编码？",
         "应使用 HTML 属性编码（含引号），而不是仅做 HTML 文本编码。", None, 0),
    ],
}


def jd(obj):
    return json.dumps(obj, ensure_ascii=False)


def cleanup(cur):
    cur.execute(
        "SELECT intervention_id FROM teacher_intervention WHERE title LIKE %s AND teaching_class_id=%s",
        (f"{TITLE_TAG}%", CLASS_ID),
    )
    ids = [int(r["intervention_id"]) for r in cur.fetchall() or []]
    if ids:
        ph = ",".join(["%s"] * len(ids))
        for tbl in ("teacher_intervention_exercise_snapshot", "teacher_intervention_question",
                    "teacher_intervention_student", "teacher_intervention"):
            cur.execute(f"DELETE FROM {tbl} WHERE intervention_id IN ({ph})", ids)
    like = f"{PREFIX}-%"
    cur.execute("DELETE FROM generated_question_attempt WHERE attempt_id LIKE %s", (like,))
    cur.execute("DELETE FROM generated_question WHERE generated_question_id LIKE %s", (like,))
    cur.execute("DELETE FROM training_session WHERE training_session_id LIKE %s", (like,))
    return len(ids)


def build_practice(cur, plan, intervention_id, student_id, answered_count):
    """给学生落一份练习会话：题目全给，作答只给前 answered_count 道。"""
    key = plan["key"]
    items = EXERCISES.get(key) or []
    if not items:
        return None
    started = datetime.now() - timedelta(days=plan["days_ago"], hours=1)
    ts_id = f"{PREFIX}-{key}-ts-{student_id}"
    cur.execute(
        """INSERT INTO training_session (training_session_id,user_id,class_id,course_id,
             profile_snapshot_id,source_type,diagnose_result_json,training_context_json,created_at)
           VALUES (%s,%s,%s,%s,NULL,'teacher_assignment',%s,%s,%s)""",
        (ts_id, student_id, ADMIN_CLASS_ID, plan["course_id"],
         jd({"weak_knowledge_points": [{"knowledge_point_id": plan["kp"]}]}),
         jd({"source": "teacher_assignment", "interventionId": intervention_id}), started),
    )
    for idx, (title, stem, answer, correct, score) in enumerate(items, start=1):
        gq_id = f"{PREFIX}-{key}-q{idx}-{student_id}"
        cur.execute(
            """INSERT INTO generated_question (generated_question_id,question_numeric_id,training_session_id,
                 question_type,knowledge_point_id,module_id,task_id,difficulty,title,stem,options_json,
                 standard_answer,reference_answer,explanation,scoring_rubric_json,source_model,raw_ai_json,created_at)
               VALUES (%s,%s,%s,'short_answer',%s,NULL,NULL,'medium',%s,%s,NULL,%s,%s,%s,NULL,'deepseek-chat',NULL,%s)""",
            (gq_id, 122_500_000 + abs(hash(gq_id)) % 400_000, ts_id, plan["kp"],
             title, stem, answer, answer, answer, started),
        )
        if idx <= answered_count:
            cur.execute(
                """INSERT INTO generated_question_attempt (attempt_id,training_session_id,generated_question_id,
                     user_id,answer_json,is_correct,score,cost_time,submission_id,profile_rebuild_snapshot_id,submitted_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NULL,NULL,%s)""",
                (f"{PREFIX}-{key}-a{idx}-{student_id}", ts_id, gq_id, student_id,
                 jd({"text": answer if correct else "只写出了判断思路，没有给出完整步骤"}),
                 correct, score, random.randint(70, 180),
                 started + timedelta(minutes=6 * idx)),
            )
    return ts_id


def main():
    conn = get_connection()
    created = []
    try:
        with conn.cursor() as cur:
            removed = cleanup(cur)
        conn.commit()
        print("清理旧下发单 %d 张" % removed)

        for plan in PLANS:
            result = create_intervention(
                teacher_id=TEACHER_ID,
                class_id=CLASS_ID,
                course_id=plan["course_id"],
                title=plan["title"],
                action_type=plan["action_type"],
                student_ids=plan["students"],
                knowledge_point_id=plan["kp"],
                description=plan["description"],
                due_at=datetime.now() + timedelta(days=7 - plan["days_ago"]),
            )
            iid = int(result["interventionId"])
            created.append((plan, iid))
            print("已下发 #%d %s（%d 人）" % (iid, plan["title"], len(plan["students"])))

        # 推进学生进度：主角按 hero_state，同班同学给出参差进度
        with conn.cursor() as cur:
            for plan, iid in created:
                items = EXERCISES.get(plan["key"]) or []
                total = len(items)
                hero_answered = total if plan["hero_state"] == "COMPLETED" else (1 if plan["hero_state"] == "STARTED" else 0)
                roster = [(HERO, hero_answered)]
                # 同学：交替给「全做完 / 做一半 / 没开始」
                for i, sid in enumerate(s for s in plan["students"] if s != HERO):
                    roster.append((sid, [total, max(1, total // 2), 0][i % 3]))

                for sid, answered in roster:
                    if not total or answered == 0:
                        continue  # 待开始：不建会话，状态保持 PENDING
                    ts_id = build_practice(cur, plan, iid, sid, answered)
                    status = "COMPLETED" if answered >= total else "STARTED"
                    started = datetime.now() - timedelta(days=plan["days_ago"], hours=1)
                    cur.execute(
                        """UPDATE teacher_intervention_student
                           SET training_session_id=%s, assignment_status=%s, started_at=%s, completed_at=%s
                           WHERE intervention_id=%s AND student_id=%s""",
                        (ts_id, status, started,
                         (started + timedelta(hours=1)) if status == "COMPLETED" else None, iid, sid),
                    )
        conn.commit()
    finally:
        conn.close()
    print("完成。")


if __name__ == "__main__":
    main()
