package me.myot233.seclab.userservice.repository

import me.myot233.seclab.userservice.entity.TeachingClassCourseEntity
import me.myot233.seclab.userservice.entity.TeachingClassEntity
import me.myot233.seclab.userservice.entity.TeachingClassImportBatchEntity
import me.myot233.seclab.userservice.entity.TeachingClassStatus
import me.myot233.seclab.userservice.entity.TeachingClassStudentEntity
import me.myot233.seclab.userservice.entity.TeachingClassStudentId
import org.springframework.data.jpa.repository.EntityGraph
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.data.jpa.repository.Lock
import org.springframework.data.jpa.repository.Modifying
import org.springframework.data.repository.query.Param
import org.springframework.stereotype.Repository
import java.time.LocalDate
import java.time.LocalDateTime
import java.util.Optional
import jakarta.persistence.LockModeType

@Repository
interface TeachingClassRepository : JpaRepository<TeachingClassEntity, Long> {
    @EntityGraph(attributePaths = ["teacher"])
    fun findAllByOrderByUpdatedAtDesc(): List<TeachingClassEntity>

    @EntityGraph(attributePaths = ["teacher"])
    fun findAllByTeacherIdOrderByUpdatedAtDesc(teacherId: Long): List<TeachingClassEntity>

    /** 学生注册可选班级：只取未归档的教学班，同名时由调用方保留最新创建的一个。 */
    @EntityGraph(attributePaths = ["teacher"])
    fun findAllByStatusOrderByTeachingClassIdDesc(status: TeachingClassStatus): List<TeachingClassEntity>

    fun existsByTeacherIdAndAcademicYearAndSemesterAndClassNameIgnoreCase(
        teacherId: Long,
        academicYear: String,
        semester: Int,
        className: String,
    ): Boolean

    fun existsByTeacherIdAndAcademicYearAndSemesterAndClassNameIgnoreCaseAndTeachingClassIdNot(
        teacherId: Long,
        academicYear: String,
        semester: Int,
        className: String,
        teachingClassId: Long,
    ): Boolean
}

@Repository
interface TeachingClassStudentRepository : JpaRepository<TeachingClassStudentEntity, TeachingClassStudentId> {
    fun countByTeachingClassId(teachingClassId: Long): Long

    @Query(
        value = """
            SELECT MAX(le.event_time)
            FROM seclab_profile.learning_event le
            INNER JOIN teaching_class_student tcs ON tcs.student_id = le.user_id
            WHERE tcs.teaching_class_id = :teachingClassId
        """,
        nativeQuery = true,
    )
    fun findLatestActivityAt(@Param("teachingClassId") teachingClassId: Long): LocalDateTime?

    fun existsByTeachingClassIdAndStudentId(teachingClassId: Long, studentId: Long): Boolean

    /**
     * 只属于这个教学班的学生。删除教学班时这些人跟着一起彻底删除；
     * 同时还在别的教学班的学生只丢掉本班归属，账号保留。
     */
    @Query(
        value = """
            SELECT tcs.student_id
            FROM teaching_class_student tcs
            INNER JOIN `user` u ON u.user_id = tcs.student_id
            WHERE tcs.teaching_class_id = :teachingClassId
              AND u.user_role = 'STUDENT'
              AND COALESCE(u.is_admin, 0) = 0
              AND NOT EXISTS (
                    SELECT 1
                    FROM teaching_class_student other
                    WHERE other.student_id = tcs.student_id
                      AND other.teaching_class_id <> :teachingClassId
                  )
        """,
        nativeQuery = true,
    )
    fun findStudentIdsExclusiveTo(@Param("teachingClassId") teachingClassId: Long): List<Long>

    @Query(
        value = """
            SELECT tcs.student_id AS studentId,
                   u.user_student_number AS studentNumber,
                   u.user_name AS studentName,
                   c.class_name AS administrativeClass,
                   tcs.joined_at AS joinedAt,
                   MAX(le.event_time) AS recentActivityAt
            FROM teaching_class_student tcs
            INNER JOIN `user` u ON u.user_id = tcs.student_id
            LEFT JOIN `class` c ON c.class_id = u.class_id_class_id
            LEFT JOIN seclab_profile.learning_event le ON le.user_id = u.user_id
            WHERE tcs.teaching_class_id = :teachingClassId
              AND COALESCE(u.is_deleted, 0) = 0
            GROUP BY tcs.student_id, u.user_student_number, u.user_name,
                     c.class_name, tcs.joined_at
            ORDER BY u.user_student_number
        """,
        nativeQuery = true,
    )
    fun findStudentViews(@Param("teachingClassId") teachingClassId: Long): List<TeachingClassStudentView>

    @Modifying
    @Query(
        "DELETE FROM TeachingClassStudentEntity membership " +
            "WHERE membership.teachingClassId = :teachingClassId AND membership.studentId = :studentId",
    )
    fun removeMember(
        @Param("teachingClassId") teachingClassId: Long,
        @Param("studentId") studentId: Long,
    ): Int
}

interface TeachingClassStudentView {
    fun getStudentId(): Long
    fun getStudentNumber(): String
    fun getStudentName(): String?
    fun getAdministrativeClass(): String?
    fun getJoinedAt(): LocalDateTime
    fun getRecentActivityAt(): LocalDateTime?
}

@Repository
interface TeachingClassCourseRepository : JpaRepository<TeachingClassCourseEntity, Long> {
    fun countByTeachingClassId(teachingClassId: Long): Long

    fun findAllByTeachingClassId(teachingClassId: Long): List<TeachingClassCourseEntity>

    fun findByTeachingClassIdAndCourseId(teachingClassId: Long, courseId: Int): Optional<TeachingClassCourseEntity>

    @Query(
        value = """
            SELECT c.course_name
            FROM teaching_class_course tcc
            INNER JOIN course c ON c.id = tcc.course_id
            WHERE tcc.teaching_class_id = :teachingClassId
              AND (tcc.planned_start_date IS NULL OR tcc.planned_start_date <= :today)
              AND (tcc.planned_end_date IS NULL OR tcc.planned_end_date >= :today)
            ORDER BY tcc.teaching_order
            LIMIT 1
        """,
        nativeQuery = true,
    )
    fun findCurrentCourseName(
        @Param("teachingClassId") teachingClassId: Long,
        @Param("today") today: LocalDate,
    ): String?

    @Query(
        value = "SELECT id FROM course WHERE id IN (:courseIds)",
        nativeQuery = true,
    )
    fun findExistingCourseIds(@Param("courseIds") courseIds: Collection<Int>): List<Int>

    @Query(
        value = """
            SELECT tcc.course_id AS courseId,
                   c.course_name AS courseName,
                   c.course_description AS courseDescription,
                   tcc.teaching_content AS teachingContent,
                   tcc.teaching_order AS teachingOrder,
                   tcc.planned_start_date AS plannedStartDate,
                   tcc.planned_end_date AS plannedEndDate,
                   c.created_by AS createdBy,
                   creator.user_name AS creatorName,
                   tcc.updated_at AS updatedAt
            FROM teaching_class_course tcc
            INNER JOIN course c ON c.id = tcc.course_id
            LEFT JOIN `user` creator ON creator.user_id = c.created_by
            WHERE tcc.teaching_class_id = :teachingClassId
            ORDER BY tcc.teaching_order
        """,
        nativeQuery = true,
    )
    fun findCourseViews(@Param("teachingClassId") teachingClassId: Long): List<TeachingClassCourseView>

    @Modifying
    @Query("DELETE FROM TeachingClassCourseEntity item WHERE item.teachingClassId = :teachingClassId")
    fun deleteArrangements(@Param("teachingClassId") teachingClassId: Long): Int
}

interface TeachingClassCourseView {
    fun getCourseId(): Int
    fun getCourseName(): String
    fun getCourseDescription(): String
    fun getTeachingContent(): String?
    fun getTeachingOrder(): Int
    fun getPlannedStartDate(): LocalDate?
    fun getPlannedEndDate(): LocalDate?
    fun getCreatedBy(): Long?
    fun getCreatorName(): String?
    fun getUpdatedAt(): LocalDateTime
}

@Repository
interface TeachingClassImportBatchRepository : JpaRepository<TeachingClassImportBatchEntity, String> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT batch FROM TeachingClassImportBatchEntity batch WHERE batch.importBatchId = :batchId")
    fun findLockedByImportBatchId(@Param("batchId") batchId: String): Optional<TeachingClassImportBatchEntity>
}
