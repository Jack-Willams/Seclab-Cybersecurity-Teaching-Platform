package me.myot233.seclab.experimentmoduleservice.service

import com.fasterxml.jackson.core.type.TypeReference
import com.fasterxml.jackson.databind.ObjectMapper
import me.myot233.seclab.experimentmoduleservice.dto.CourseMutationRequest
import me.myot233.seclab.experimentmoduleservice.dto.CourseSummaryDto
import me.myot233.seclab.experimentmoduleservice.dto.ModuleMutationRequest
import me.myot233.seclab.experimentmoduleservice.dto.ModuleOverviewDto
import me.myot233.seclab.experimentmoduleservice.entity.CourseEntity
import me.myot233.seclab.experimentmoduleservice.entity.ModuleEntity
import me.myot233.seclab.experimentmoduleservice.repository.CourseRepository
import me.myot233.seclab.experimentmoduleservice.repository.ModuleRepository
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.http.HttpStatus
import org.springframework.web.server.ResponseStatusException

@Service
class CatalogQueryService(
    private val courseRepository: CourseRepository,
    private val moduleRepository: ModuleRepository,
    private val objectMapper: ObjectMapper,
    private val jdbcTemplate: JdbcTemplate,
) {
    fun listCourses(): List<CourseSummaryDto> =
        courseRepository.findAll()
            .sortedBy { it.id }
            .map(::toCourseSummaryDto)

    fun listModules(): List<ModuleOverviewDto> {
        val courseIdsByModule = loadCourseIdsByModule()
        return moduleRepository.findAll()
            .sortedBy { it.moduleId }
            .map { module ->
                val courseIds = courseIdsByModule[module.moduleId].orEmpty()
                toModuleOverviewDto(module, courseIds.firstOrNull(), courseIds)
            }
    }

    fun getCourse(id: Int): CourseSummaryDto =
        toCourseSummaryDto(
            courseRepository.findById(id).orElseThrow { NoSuchElementException("课程不存在: $id") }
        )

    @Transactional
    fun createCourse(teacherId: Long, request: CourseMutationRequest): CourseSummaryDto {
        validateCourseRequest(request)
        val saved = courseRepository.save(
            CourseEntity(
                id = courseRepository.findMaxId() + 1,
                courseName = request.courseName.trim(),
                courseDescription = request.courseDescription.trim(),
                difficulty = normalizeDifficulty(request.difficulty),
                imageUrl = request.imageUrl?.trim()?.takeIf { it.isNotEmpty() },
                instructor = request.teacherName?.trim()?.takeIf { it.isNotEmpty() },
                createdBy = teacherId,
                courseStatus = mapCourseStatusToDb(request.status),
                tags = stringifyStringList(request.tags),
                type = normalizeType(request.category),
            )
        )
        return toCourseSummaryDto(saved)
    }

    @Transactional
    fun updateCourse(teacherId: Long, id: Int, request: CourseMutationRequest): CourseSummaryDto {
        validateCourseRequest(request)
        val existing = courseRepository.findById(id).orElseThrow { NoSuchElementException("课程不存在: $id") }
        requireCourseOwner(teacherId, existing)
        val saved = courseRepository.save(
            CourseEntity(
                id = existing.id,
                courseName = request.courseName.trim(),
                courseDescription = request.courseDescription.trim(),
                difficulty = normalizeDifficulty(request.difficulty),
                imageUrl = request.imageUrl?.trim()?.takeIf { it.isNotEmpty() },
                instructor = request.teacherName?.trim()?.takeIf { it.isNotEmpty() } ?: existing.instructor,
                createdBy = existing.createdBy,
                courseStatus = mapCourseStatusToDb(request.status),
                tags = stringifyStringList(request.tags),
                type = normalizeType(request.category),
            )
        )
        return toCourseSummaryDto(saved)
    }

    @Transactional
    fun deleteCourse(teacherId: Long, id: Int) {
        val existing = courseRepository.findById(id).orElseThrow { NoSuchElementException("课程不存在: $id") }
        requireCourseOwner(teacherId, existing)
        jdbcTemplate.update("DELETE FROM module_course WHERE course_id = ?", id)
        courseRepository.deleteById(id)
    }

    @Transactional
    fun createModule(request: ModuleMutationRequest): ModuleOverviewDto {
        validateModuleRequest(request)
        val saved = moduleRepository.save(
            ModuleEntity(
                moduleId = moduleRepository.findMaxId() + 1,
                moduleName = request.moduleName.trim(),
                introduction = request.moduleDescription.trim(),
                difficulty = normalizeDifficulty(request.difficulty),
                imageId = request.image?.trim()?.toIntOrNull(),
                type = request.type?.trim()?.takeIf { it.isNotEmpty() },
            )
        )
        return toModuleOverviewDto(saved)
    }

    @Transactional
    fun updateModule(id: Int, request: ModuleMutationRequest): ModuleOverviewDto {
        validateModuleRequest(request)
        val existing = moduleRepository.findById(id).orElseThrow { NoSuchElementException("实验不存在: $id") }
        val saved = moduleRepository.save(
            ModuleEntity(
                moduleId = existing.moduleId,
                moduleName = request.moduleName.trim(),
                introduction = request.moduleDescription.trim(),
                difficulty = normalizeDifficulty(request.difficulty),
                imageId = request.image?.trim()?.toIntOrNull() ?: existing.imageId,
                type = request.type?.trim()?.takeIf { it.isNotEmpty() },
            )
        )
        return toModuleOverviewDto(saved)
    }

    @Transactional
    fun deleteModule(id: Int) {
        if (!moduleRepository.existsById(id)) {
            throw NoSuchElementException("实验不存在: $id")
        }
        jdbcTemplate.update("DELETE FROM module_course WHERE module_id = ?", id)
        moduleRepository.deleteById(id)
    }

    fun listCourseModules(courseId: Int): List<ModuleOverviewDto> {
        requireCourse(courseId)
        return moduleRepository.findByCourseId(courseId)
            .map { toModuleOverviewDto(it, courseId, listOf(courseId)) }
    }

    @Transactional
    fun addModuleToCourse(teacherId: Long, courseId: Int, moduleId: Int): List<ModuleOverviewDto> {
        requireCourseOwner(teacherId, requireCourse(courseId))
        requireModule(moduleId)
        jdbcTemplate.update(
            "INSERT IGNORE INTO module_course (course_id, module_id) VALUES (?, ?)",
            courseId,
            moduleId,
        )
        return listCourseModules(courseId)
    }

    @Transactional
    fun removeModuleFromCourse(teacherId: Long, courseId: Int, moduleId: Int): List<ModuleOverviewDto> {
        requireCourseOwner(teacherId, requireCourse(courseId))
        requireModule(moduleId)
        jdbcTemplate.update(
            "DELETE FROM module_course WHERE course_id = ? AND module_id = ?",
            courseId,
            moduleId,
        )
        return listCourseModules(courseId)
    }

    private fun toCourseSummaryDto(course: CourseEntity): CourseSummaryDto =
        CourseSummaryDto(
            id = course.id,
            name = course.courseName,
            description = course.courseDescription,
            difficulty = normalizeDifficulty(course.difficulty),
            imageUrl = course.imageUrl.orEmpty(),
            type = normalizeType(course.type),
            tags = parseStringList(course.tags),
            status = mapCourseStatus(course.courseStatus),
            teacherName = course.instructor?.takeIf { it.isNotBlank() },
            category = normalizeType(course.type),
            createTime = null,
            createdBy = course.createdBy,
        )

    private fun toModuleOverviewDto(
        module: ModuleEntity,
        courseId: Int? = null,
        courseIds: List<Int> = courseId?.let(::listOf).orEmpty(),
    ): ModuleOverviewDto =
        ModuleOverviewDto(
            id = module.moduleId,
            name = module.moduleName.orEmpty(),
            description = module.introduction.orEmpty(),
            difficulty = normalizeDifficulty(module.difficulty),
            type = normalizeModuleType(module.type),
            status = "available",
            estimatedTime = estimateDuration(module.difficulty),
            score = calculateScore(module.difficulty),
            courseId = courseId,
            courseIds = courseIds,
            image = module.imageId?.toString(),
        )

    private fun requireCourse(courseId: Int): CourseEntity =
        courseRepository.findById(courseId).orElseThrow { NoSuchElementException("课程不存在: $courseId") }

    private fun requireCourseOwner(teacherId: Long, course: CourseEntity) {
        if (course.createdBy == null || course.createdBy != teacherId) {
            throw ResponseStatusException(HttpStatus.FORBIDDEN, "只有课程创建者可以修改该课程")
        }
    }

    private fun requireModule(moduleId: Int) {
        if (!moduleRepository.existsById(moduleId)) {
            throw NoSuchElementException("实验不存在: $moduleId")
        }
    }

    private fun loadCourseIdsByModule(): Map<Int, List<Int>> =
        jdbcTemplate.query(
            """
            SELECT module_id, course_id
            FROM module_course
            ORDER BY module_id, course_id
            """.trimIndent(),
        ) { rs, _ -> rs.getInt("module_id") to rs.getInt("course_id") }
            .groupBy({ it.first }, { it.second })

    private fun normalizeDifficulty(difficulty: Int?): Int = difficulty?.coerceIn(1, 5) ?: 3

    private fun mapCourseStatus(status: Int?): String =
        when (status) {
            null -> "available"
            0 -> "draft"
            1 -> "available"
            2 -> "archived"
            else -> "available"
        }

    private fun normalizeType(type: String?): String =
        type?.trim()?.takeIf { it.isNotEmpty() } ?: "web"

    private fun stringifyStringList(values: List<String>): String =
        values
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .joinToString(",")

    private fun normalizeModuleType(type: String?): String {
        val parsed = parseStringList(type)
        return parsed.firstOrNull()
            ?: type?.trim()?.takeIf { it.isNotEmpty() }
            ?: "未分类模块"
    }

    private fun parseStringList(raw: String?): List<String> {
        val normalized = raw?.trim()?.takeIf { it.isNotEmpty() } ?: return emptyList()
        return try {
            if (normalized.startsWith("[")) {
                objectMapper.readValue(normalized, object : TypeReference<List<String>>() {})
                    .map { it.trim() }
                    .filter { it.isNotEmpty() }
            } else {
                normalized.split(",")
                    .map { it.trim().trim('"') }
                    .filter { it.isNotEmpty() }
            }
        } catch (_: Exception) {
            normalized.split(",")
                .map { it.trim().trim('"') }
                .filter { it.isNotEmpty() }
        }
    }

    private fun estimateDuration(difficulty: Int?): String =
        when (normalizeDifficulty(difficulty)) {
            1 -> "1-2小时"
            2 -> "2-3小时"
            3 -> "3-4小时"
            4 -> "4-5小时"
            else -> "5小时"
        }

    private fun calculateScore(difficulty: Int?): Int =
        when (normalizeDifficulty(difficulty)) {
            1 -> 35
            2 -> 50
            3 -> 65
            4 -> 80
            else -> 95
        }

    private fun mapCourseStatusToDb(status: String?): Int =
        when (status?.trim()?.lowercase()) {
            "draft" -> 0
            "archived" -> 2
            else -> 1
        }

    private fun validateCourseRequest(request: CourseMutationRequest) {
        if (request.courseName.isBlank()) {
            throw IllegalArgumentException("课程名称不能为空")
        }
        if (request.courseDescription.isBlank()) {
            throw IllegalArgumentException("课程描述不能为空")
        }
    }

    private fun validateModuleRequest(request: ModuleMutationRequest) {
        if (request.moduleName.isBlank()) {
            throw IllegalArgumentException("实验名称不能为空")
        }
        if (request.moduleDescription.isBlank()) {
            throw IllegalArgumentException("实验描述不能为空")
        }
    }
}
