package me.myot233.seclab.userservice.service

import me.myot233.seclab.userservice.entity.UserEntity
import me.myot233.seclab.userservice.entity.UserRole
import me.myot233.seclab.userservice.exception.ApiException
import org.slf4j.LoggerFactory
import org.springframework.http.HttpStatus
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional

/**
 * 学生与教学班的彻底删除。
 *
 * 教师端的「删除学生」「删除教学班」是不可恢复操作：学生账号连同 seclab_profile
 * 里的全部学习痕迹一起清掉，教学班连同名单、课程安排、教师侧分析记录一起清掉。
 * 早期版本这两个动作只是「移出名单」和「置为归档」，账号和记录都还留着，
 * 教师看到的名单和学生端的数据对不上。
 *
 * 删除顺序必须先子后父，否则会留下永远查不到、也永远删不掉的孤儿行。
 */
@Service
class StudentPurgeService(
    private val jdbcTemplate: NamedParameterJdbcTemplate,
) {
    /** seclab_profile 可能没建（只跑了 user-service 的最小化本地库），缺库时跳过画像清理。 */
    private val profileSchemaReady: Boolean by lazy {
        val count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = :schema",
            mapOf("schema" to PROFILE_SCHEMA),
            Int::class.java,
        ) ?: 0
        (count > 0).also {
            if (!it) log.warn("schema {} 不存在，删除学生时跳过画像数据清理", PROFILE_SCHEMA)
        }
    }

    /**
     * 彻底删除一名学生：账号 + 全部学习数据。教师/管理员账号不允许走这条路径。
     */
    @Transactional
    fun purgeStudent(student: UserEntity) {
        val studentId = student.userId
            ?: throw ApiException(400, "学生账号缺少 userId，无法删除")
        if (student.userRole != UserRole.STUDENT || student.isAdmin == true) {
            throw ApiException(
                403,
                "只能删除学生账号，教师和管理员账号请在管理后台处理",
                HttpStatus.FORBIDDEN,
            )
        }

        if (profileSchemaReady) {
            STUDENT_PROFILE_CLEANUP.forEach { statement -> executeUpdate(statement, "studentId" to studentId) }
        }
        executeUpdate("DELETE FROM `teaching_class_student` WHERE `student_id` = :studentId", "studentId" to studentId)
        executeUpdate("DELETE FROM `user` WHERE `user_id` = :studentId", "studentId" to studentId)
        log.info("purged student={} 及其全部学习数据", studentId)
    }

    /**
     * 删除教学班本身：名单、课程安排、导入批次，以及这个班的教师侧分析 / 干预记录。
     * 学生账号由调用方决定是否一并 [purgeStudent]。
     */
    @Transactional
    fun purgeTeachingClass(teachingClassId: Long) {
        if (profileSchemaReady) {
            TEACHING_CLASS_PROFILE_CLEANUP.forEach { statement ->
                executeUpdate(statement, "teachingClassId" to teachingClassId)
            }
        }
        TEACHING_CLASS_CLEANUP.forEach { statement ->
            executeUpdate(statement, "teachingClassId" to teachingClassId)
        }
        log.info("purged teachingClass={} 及其名单/课程安排/分析记录", teachingClassId)
    }

    private fun executeUpdate(statement: String, vararg params: Pair<String, Any>) {
        jdbcTemplate.update(statement, params.toMap())
    }

    private companion object {
        val log = LoggerFactory.getLogger(StudentPurgeService::class.java)
        const val PROFILE_SCHEMA = "seclab_profile"

        /** 该学生的训练会话产生的生成题；被多处引用，删题前要先清引用。 */
        const val OWN_GENERATED_QUESTIONS = """
            SELECT gq.`generated_question_id`
            FROM `seclab_profile`.`generated_question` gq
            WHERE gq.`training_session_id` IN (
                SELECT ts.`training_session_id`
                FROM `seclab_profile`.`training_session` ts
                WHERE ts.`user_id` = :studentId
            )
        """

        const val OWN_CONVERSATIONS = """
            SELECT ac.`conversation_id`
            FROM `seclab_profile`.`ai_conversation` ac
            WHERE ac.`user_id` = :studentId
        """

        // 先子后父：AI 会话链 -> 生成题链 -> 其余按 user_id/student_id 直删。
        val STUDENT_PROFILE_CLEANUP = listOf(
            "DELETE FROM `seclab_profile`.`ai_context_injection` WHERE `conversation_id` IN ($OWN_CONVERSATIONS)",
            "DELETE FROM `seclab_profile`.`ai_tool_call` WHERE `conversation_id` IN ($OWN_CONVERSATIONS)",
            "DELETE FROM `seclab_profile`.`ai_message` WHERE `conversation_id` IN ($OWN_CONVERSATIONS)",
            "DELETE FROM `seclab_profile`.`ai_conversation` WHERE `user_id` = :studentId",

            "DELETE FROM `seclab_profile`.`teacher_intervention_question` " +
                "WHERE `generated_question_id` IN ($OWN_GENERATED_QUESTIONS)",
            "DELETE FROM `seclab_profile`.`teacher_typical_question` " +
                "WHERE `generated_question_id` IN ($OWN_GENERATED_QUESTIONS)",
            "DELETE FROM `seclab_profile`.`question_knowledge_point` " +
                "WHERE `generated_question_id` IN ($OWN_GENERATED_QUESTIONS)",
            // 该学生做过的作答，以及别人做过的、属于该学生生成题的作答，都要先清掉
            "DELETE FROM `seclab_profile`.`generated_question_attempt` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`generated_question_attempt` " +
                "WHERE `generated_question_id` IN ($OWN_GENERATED_QUESTIONS)",
            "DELETE FROM `seclab_profile`.`generated_question` " +
                "WHERE `training_session_id` IN (" +
                "SELECT ts.`training_session_id` FROM `seclab_profile`.`training_session` ts " +
                "WHERE ts.`user_id` = :studentId)",
            "DELETE FROM `seclab_profile`.`training_session` WHERE `user_id` = :studentId",

            "DELETE FROM `seclab_profile`.`teacher_intervention_student` WHERE `student_id` = :studentId",
            "DELETE FROM `seclab_profile`.`teacher_student_analysis` WHERE `student_id` = :studentId",
            "DELETE FROM `seclab_profile`.`teacher_course_analysis` WHERE `student_id` = :studentId",

            "DELETE FROM `seclab_profile`.`class_profile_student_metric` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`student_profile_feature_daily` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`student_profile_snapshot` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`challenge_completion_event` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`container_command_event` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`container_file_event` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`error_event` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`flag_submission` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`question_submission` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`lab_session` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`operation_session` WHERE `user_id` = :studentId",
            "DELETE FROM `seclab_profile`.`learning_event` WHERE `user_id` = :studentId",
        )

        const val CLASS_INTERVENTIONS = """
            SELECT ti.`intervention_id`
            FROM `seclab_profile`.`teacher_intervention` ti
            WHERE ti.`teaching_class_id` = :teachingClassId
        """

        val TEACHING_CLASS_PROFILE_CLEANUP = listOf(
            "DELETE FROM `seclab_profile`.`teacher_knowledge_exercise` " +
                "WHERE `analysis_id` IN (" +
                "SELECT tka.`analysis_id` FROM `seclab_profile`.`teacher_knowledge_analysis` tka " +
                "WHERE tka.`teaching_class_id` = :teachingClassId)",
            "DELETE FROM `seclab_profile`.`teacher_knowledge_analysis` WHERE `teaching_class_id` = :teachingClassId",

            "DELETE FROM `seclab_profile`.`teacher_intervention_exercise_snapshot` " +
                "WHERE `intervention_id` IN ($CLASS_INTERVENTIONS)",
            "DELETE FROM `seclab_profile`.`teacher_intervention_question` " +
                "WHERE `intervention_id` IN ($CLASS_INTERVENTIONS)",
            "DELETE FROM `seclab_profile`.`teacher_intervention_student` " +
                "WHERE `intervention_id` IN ($CLASS_INTERVENTIONS)",
            "DELETE FROM `seclab_profile`.`teacher_intervention` WHERE `teaching_class_id` = :teachingClassId",

            "DELETE FROM `seclab_profile`.`teacher_student_analysis` WHERE `teaching_class_id` = :teachingClassId",
            "DELETE FROM `seclab_profile`.`teacher_course_analysis` WHERE `teaching_class_id` = :teachingClassId",
            "DELETE FROM `seclab_profile`.`teacher_class_analysis` WHERE `teaching_class_id` = :teachingClassId",
        )

        val TEACHING_CLASS_CLEANUP = listOf(
            "DELETE FROM `teaching_class_import_batch` WHERE `teaching_class_id` = :teachingClassId",
            "DELETE FROM `teaching_class_course` WHERE `teaching_class_id` = :teachingClassId",
            "DELETE FROM `teaching_class_student` WHERE `teaching_class_id` = :teachingClassId",
            "DELETE FROM `teaching_class` WHERE `teaching_class_id` = :teachingClassId",
        )
    }
}
