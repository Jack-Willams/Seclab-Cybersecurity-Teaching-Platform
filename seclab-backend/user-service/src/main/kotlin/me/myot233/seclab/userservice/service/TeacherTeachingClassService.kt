package me.myot233.seclab.userservice.service

import me.myot233.seclab.userservice.dto.TeachingClassResponse
import me.myot233.seclab.userservice.dto.TeachingClassCourseContentUpdateRequest
import me.myot233.seclab.userservice.dto.TeachingClassCourseResponse
import me.myot233.seclab.userservice.dto.TeachingClassCourseUpdateRequest
import me.myot233.seclab.userservice.dto.TeachingClassDeleteResult
import me.myot233.seclab.userservice.dto.TeachingClassSaveRequest
import me.myot233.seclab.userservice.entity.TeachingClassEntity
import me.myot233.seclab.userservice.entity.TeachingClassStatus
import me.myot233.seclab.userservice.exception.ApiException
import me.myot233.seclab.userservice.repository.TeachingClassCourseRepository
import me.myot233.seclab.userservice.repository.TeachingClassRepository
import me.myot233.seclab.userservice.repository.TeachingClassStudentRepository
import me.myot233.seclab.userservice.repository.UserRepository
import org.slf4j.LoggerFactory
import org.springframework.dao.DataIntegrityViolationException
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.LocalDate

@Service
class TeacherTeachingClassService(
    private val teachingClassRepository: TeachingClassRepository,
    private val studentRepository: TeachingClassStudentRepository,
    private val courseRepository: TeachingClassCourseRepository,
    private val userRepository: UserRepository,
    private val studentPurgeService: StudentPurgeService,
) {
    @Transactional(readOnly = true)
    fun listAll(currentTeacherId: Long): List<TeachingClassResponse> =
        teachingClassRepository.findAllByTeacherIdOrderByUpdatedAtDesc(currentTeacherId).map { entity ->
            entity.toResponse(currentTeacherId)
        }

    @Transactional(readOnly = true)
    fun getDetail(currentTeacherId: Long, teachingClassId: Long): TeachingClassResponse =
        requireOwner(currentTeacherId, teachingClassId).toResponse(currentTeacherId)

    @Transactional
    fun create(currentTeacherId: Long, request: TeachingClassSaveRequest): TeachingClassResponse {
        val normalized = validateAndNormalize(request)
        if (
            teachingClassRepository.existsByTeacherIdAndAcademicYearAndSemesterAndClassNameIgnoreCase(
                currentTeacherId,
                normalized.academicYear,
                normalized.semester,
                normalized.className,
            )
        ) {
            throw conflict("同一学期已存在同名教学班")
        }

        val saved = saveWithConflictMapping(
            TeachingClassEntity(
                className = normalized.className,
                academicYear = normalized.academicYear,
                semester = normalized.semester,
                teacherId = currentTeacherId,
                startDate = normalized.startDate,
                endDate = normalized.endDate,
            ),
        )
        log.info("teacher={} created teachingClass={}", currentTeacherId, saved.teachingClassId)
        return saved.toResponse(currentTeacherId)
    }

    @Transactional
    fun update(
        currentTeacherId: Long,
        teachingClassId: Long,
        request: TeachingClassSaveRequest,
    ): TeachingClassResponse {
        val entity = requireOwner(currentTeacherId, teachingClassId)
        if (entity.status == TeachingClassStatus.ARCHIVED) {
            throw conflict("已归档教学班不能修改")
        }
        val normalized = validateAndNormalize(request)
        if (
            teachingClassRepository
                .existsByTeacherIdAndAcademicYearAndSemesterAndClassNameIgnoreCaseAndTeachingClassIdNot(
                    currentTeacherId,
                    normalized.academicYear,
                    normalized.semester,
                    normalized.className,
                    teachingClassId,
                )
        ) {
            throw conflict("同一学期已存在同名教学班")
        }

        entity.className = normalized.className
        entity.academicYear = normalized.academicYear
        entity.semester = normalized.semester
        entity.startDate = normalized.startDate
        entity.endDate = normalized.endDate
        val saved = saveWithConflictMapping(entity)
        log.info("teacher={} updated teachingClass={}", currentTeacherId, teachingClassId)
        return saved.toResponse(currentTeacherId)
    }

    /**
     * 删除教学班。早期版本这里只是把状态置为 ARCHIVED，班还留在库里、学生也还挂着，
     * 教师以为删掉了，学生端却照样能看到，属于设计缺陷。现在是真删：
     * 名单、课程安排、导入批次、该班的教师侧分析与干预记录全部清掉，
     * 只属于这个班的学生连账号带学习数据一起删除（跨班学生只丢本班归属）。
     */
    @Transactional
    fun delete(currentTeacherId: Long, teachingClassId: Long): TeachingClassDeleteResult {
        requireOwner(currentTeacherId, teachingClassId)

        val exclusiveStudentIds = studentRepository.findStudentIdsExclusiveTo(teachingClassId)
        val totalMemberCount = studentRepository.countByTeachingClassId(teachingClassId).toInt()
        exclusiveStudentIds.forEach { studentId ->
            userRepository.findById(studentId).ifPresent(studentPurgeService::purgeStudent)
        }
        studentPurgeService.purgeTeachingClass(teachingClassId)

        log.info(
            "teacher={} deleted teachingClass={} deletedStudents={} keptStudents={}",
            currentTeacherId,
            teachingClassId,
            exclusiveStudentIds.size,
            totalMemberCount - exclusiveStudentIds.size,
        )
        return TeachingClassDeleteResult(
            deletedStudentCount = exclusiveStudentIds.size,
            keptStudentCount = totalMemberCount - exclusiveStudentIds.size,
        )
    }

    @Transactional(readOnly = true)
    fun listCourses(currentTeacherId: Long, teachingClassId: Long): List<TeachingClassCourseResponse> {
        requireOwner(currentTeacherId, teachingClassId)
        return courseRepository.findCourseViews(teachingClassId).map { it.toResponse() }
    }

    @Transactional
    fun updateCourseContent(
        teacherId: Long,
        teachingClassId: Long,
        courseId: Int,
        request: TeachingClassCourseContentUpdateRequest,
    ): TeachingClassCourseResponse {
        val teachingClass = requireOwner(teacherId, teachingClassId)
        if (teachingClass.status == TeachingClassStatus.ARCHIVED) {
            throw conflict("已归档教学班不能修改教学内容")
        }
        val arrangement = courseRepository.findByTeachingClassIdAndCourseId(teachingClassId, courseId).orElseThrow {
            ApiException(404, "该课程不在当前教学安排中", HttpStatus.NOT_FOUND)
        }
        arrangement.teachingContent = normalizeTeachingContent(request.teachingContent)
        courseRepository.saveAndFlush(arrangement)
        log.info("teacher={} updated teaching content for teachingClass={} course={}", teacherId, teachingClassId, courseId)
        return courseRepository.findCourseViews(teachingClassId)
            .firstOrNull { it.getCourseId() == courseId }
            ?.toResponse()
            ?: throw ApiException(404, "教学安排不存在", HttpStatus.NOT_FOUND)
    }

    @Transactional
    fun replaceCourses(
        teacherId: Long,
        teachingClassId: Long,
        request: TeachingClassCourseUpdateRequest,
    ): List<TeachingClassCourseResponse> {
        val teachingClass = requireOwner(teacherId, teachingClassId)
        if (teachingClass.status == TeachingClassStatus.ARCHIVED) {
            throw conflict("已归档教学班不能修改课程安排")
        }
        if (request.items.size > MAX_COURSES_PER_CLASS) {
            throw ApiException(400, "一个教学班最多安排50门课程")
        }
        val courseIds = request.items.map { it.courseId }
        if (courseIds.toSet().size != courseIds.size) {
            throw ApiException(400, "同一门课程不能重复安排")
        }
        val expectedOrders = (1..request.items.size).toList()
        if (request.items.map { it.teachingOrder }.sorted() != expectedOrders) {
            throw ApiException(400, "课程顺序必须从1开始连续编号")
        }
        request.items.forEach { item -> validateCourseDates(teachingClass, item.plannedStartDate, item.plannedEndDate) }
        if (courseIds.isNotEmpty()) {
            val existingCourseIds = courseRepository.findExistingCourseIds(courseIds).toSet()
            val missingCourseIds = courseIds.filterNot(existingCourseIds::contains)
            if (missingCourseIds.isNotEmpty()) {
                throw ApiException(400, "课程不存在：${missingCourseIds.joinToString()}")
            }
        }

        val existingTeachingContent = courseRepository.findAllByTeachingClassId(teachingClassId)
            .associate { it.courseId to it.teachingContent }
        courseRepository.deleteArrangements(teachingClassId)
        courseRepository.flush()
        if (request.items.isNotEmpty()) {
            courseRepository.saveAll(
                request.items.map { item ->
                    me.myot233.seclab.userservice.entity.TeachingClassCourseEntity(
                        teachingClassId = teachingClassId,
                        courseId = item.courseId,
                        teachingOrder = item.teachingOrder,
                        plannedStartDate = item.plannedStartDate,
                        plannedEndDate = item.plannedEndDate,
                        teachingContent = existingTeachingContent[item.courseId],
                    )
                },
            )
            courseRepository.flush()
        }
        log.info("teacher={} replaced courses for teachingClass={} count={}", teacherId, teachingClassId, request.items.size)
        return courseRepository.findCourseViews(teachingClassId).map { it.toResponse() }
    }

    @Transactional(readOnly = true)
    fun requireOwner(currentTeacherId: Long, teachingClassId: Long): TeachingClassEntity {
        val entity = findClass(teachingClassId)
        if (entity.teacherId != currentTeacherId) {
            throw ApiException(403, "只有该教学班的负责教师可以执行此操作", HttpStatus.FORBIDDEN)
        }
        return entity
    }

    private fun findClass(teachingClassId: Long): TeachingClassEntity =
        teachingClassRepository.findById(teachingClassId).orElseThrow {
            ApiException(404, "教学班不存在", HttpStatus.NOT_FOUND)
        }

    private fun validateAndNormalize(request: TeachingClassSaveRequest): TeachingClassSaveRequest {
        val name = request.className.trim()
        if (name.isEmpty()) {
            throw ApiException(400, "教学班名称不能为空")
        }
        if (name.length > 120) {
            throw ApiException(400, "教学班名称不能超过120个字符")
        }
        val match = ACADEMIC_YEAR_REGEX.matchEntire(request.academicYear.trim())
            ?: throw ApiException(400, "学年格式应为2026-2027")
        val startYear = match.groupValues[1].toInt()
        val endYear = match.groupValues[2].toInt()
        if (endYear != startYear + 1) {
            throw ApiException(400, "学年必须是连续两个年份")
        }
        if (request.semester !in 1..2) {
            throw ApiException(400, "学期只能为1或2")
        }
        if (request.startDate != null && request.endDate != null && request.endDate.isBefore(request.startDate)) {
            throw ApiException(400, "结束日期不能早于开始日期")
        }
        return request.copy(className = name, academicYear = "${startYear}-${endYear}")
    }

    private fun saveWithConflictMapping(entity: TeachingClassEntity): TeachingClassEntity =
        try {
            teachingClassRepository.save(entity)
        } catch (exception: DataIntegrityViolationException) {
            throw conflict("同一学期已存在同名教学班", exception)
        }

    private fun validateCourseDates(
        teachingClass: TeachingClassEntity,
        startDate: LocalDate?,
        endDate: LocalDate?,
    ) {
        if (startDate != null && endDate != null && endDate.isBefore(startDate)) {
            throw ApiException(400, "课程结束日期不能早于开始日期")
        }
        if (teachingClass.startDate != null && startDate != null && startDate.isBefore(teachingClass.startDate)) {
            throw ApiException(400, "课程开始日期不能早于教学班开始日期")
        }
        if (teachingClass.endDate != null && endDate != null && endDate.isAfter(teachingClass.endDate)) {
            throw ApiException(400, "课程结束日期不能晚于教学班结束日期")
        }
    }

    private fun normalizeTeachingContent(content: String?): String? {
        val normalized = content?.trim()?.takeIf { it.isNotEmpty() }
        if (normalized != null && normalized.length > MAX_TEACHING_CONTENT_LENGTH) {
            throw ApiException(400, "教学内容不能超过2000个字符")
        }
        return normalized
    }

    private fun me.myot233.seclab.userservice.repository.TeachingClassCourseView.toResponse() =
        TeachingClassCourseResponse(
            courseId = getCourseId(),
            courseName = getCourseName(),
            courseDescription = getCourseDescription(),
            teachingContent = getTeachingContent(),
            teachingOrder = getTeachingOrder(),
            plannedStartDate = getPlannedStartDate(),
            plannedEndDate = getPlannedEndDate(),
            createdBy = getCreatedBy(),
            creatorName = getCreatorName(),
            updatedAt = getUpdatedAt(),
        )

    private fun TeachingClassEntity.toResponse(currentTeacherId: Long): TeachingClassResponse {
        val id = teachingClassId ?: 0
        return TeachingClassResponse(
            teachingClassId = id,
            className = className,
            academicYear = academicYear,
            semester = semester,
            teacherId = teacherId,
            teacherName = teacher?.userName,
            startDate = startDate,
            endDate = endDate,
            status = status.name,
            studentCount = studentRepository.countByTeachingClassId(id).toInt(),
            courseCount = courseRepository.countByTeachingClassId(id).toInt(),
            currentCourse = courseRepository.findCurrentCourseName(id, LocalDate.now()),
            lastActiveAt = studentRepository.findLatestActivityAt(id),
            canManage = teacherId == currentTeacherId,
            createdAt = createdAt,
            updatedAt = updatedAt,
        )
    }

    private fun conflict(message: String, cause: Throwable? = null): ApiException =
        ApiException(409, message, HttpStatus.CONFLICT).also {
            if (cause != null) it.initCause(cause)
        }

    private companion object {
        val log = LoggerFactory.getLogger(TeacherTeachingClassService::class.java)
        val ACADEMIC_YEAR_REGEX = Regex("^(\\d{4})-(\\d{4})$")
        const val MAX_COURSES_PER_CLASS = 50
        const val MAX_TEACHING_CONTENT_LENGTH = 2000
    }
}
