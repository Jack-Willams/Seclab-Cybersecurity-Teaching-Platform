-- 学生 122（韩力旺）画像快照按天去重
--
-- 问题：能力成长面板的趋势曲线取「最近 8 个合规快照」，而画像每次重算都会写一条快照
--       ——8/9 一天之内就有 14 条（05:34~05:37，综合分 42.00→42.05）。于是这 8 个点
--       全挤在同一天的 3 分钟里，曲线是一条平线。
--
-- 处理：每天只保留 computed_at 最大的那条（当天最后一次重算结果），删除同日重复副本。
--       删掉的都是同一天的中间态，不是独立的学习证据；按天保留后曲线覆盖 7/29~8/9 共
--       8 天，且是真实数据本身的走势：
--         30.68 → 32.15 → 36.38 → 37.64 → 38.28 → 43.51 → 41.99 → 53.45
--
-- 已在执行前把 user_id=122 的全部 170 条快照备份到
--   seclab_profile.student_profile_snapshot_backup_20260809
-- 末尾附回滚语句。

USE seclab_profile;

-- 1) 确认备份存在（应为 170）
SELECT COUNT(*) AS backup_rows
FROM student_profile_snapshot_backup_20260809
WHERE user_id = 122;

-- 2) 预览将删除多少条（执行 3) 之前先看这个数）
SELECT COUNT(*) AS will_delete
FROM student_profile_snapshot s
JOIN (
    SELECT DATE(computed_at) AS d, MAX(computed_at) AS mx
    FROM student_profile_snapshot
    WHERE user_id = 122
    GROUP BY DATE(computed_at)
) k ON DATE(s.computed_at) = k.d AND s.computed_at < k.mx
WHERE s.user_id = 122;

-- 3) 按天去重
DELETE s
FROM student_profile_snapshot s
JOIN (
    SELECT DATE(computed_at) AS d, MAX(computed_at) AS mx
    FROM student_profile_snapshot
    WHERE user_id = 122
    GROUP BY DATE(computed_at)
) k ON DATE(s.computed_at) = k.d AND s.computed_at < k.mx
WHERE s.user_id = 122;

-- 4) 校验：应为每天一条，综合分逐日上升
SELECT DATE(computed_at) AS day, computed_at, overall_score,
       knowledge_mastery_score, troubleshooting_score,
       autonomy_score, ai_collaboration_score, engagement_score
FROM student_profile_snapshot
WHERE user_id = 122
ORDER BY computed_at;

-- ── 回滚（如需还原）────────────────────────────────────────────────
-- DELETE FROM student_profile_snapshot WHERE user_id = 122;
-- INSERT INTO student_profile_snapshot
--   SELECT * FROM student_profile_snapshot_backup_20260809 WHERE user_id = 122;
