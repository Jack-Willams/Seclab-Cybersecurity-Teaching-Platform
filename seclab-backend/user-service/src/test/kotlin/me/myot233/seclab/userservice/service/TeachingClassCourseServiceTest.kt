package me.myot233.seclab.userservice.service

import me.myot233.seclab.userservice.dto.TeachingClassCourseItemRequest
import me.myot233.seclab.userservice.dto.TeachingClassCourseContentUpdateRequest
import me.myot233.seclab.userservice.dto.TeachingClassCourseUpdateRequest
import me.myot233.seclab.userservice.entity.TeachingClassCourseEntity
import me.myot233.seclab.userservice.entity.TeachingClassEntity
import me.myot233.seclab.userservice.exception.ApiException
import me.myot233.seclab.userservice.repository.TeachingClassCourseRepository
import me.myot233.seclab.userservice.repository.TeachingClassCourseView
import me.myot233.seclab.userservice.repository.TeachingClassRepository
import me.myot233.seclab.userservice.repository.TeachingClassStudentRepository
import me.myot233.seclab.userservice.repository.UserRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test
import org.mockito.ArgumentMatchers.anyList
import org.mockito.Mockito.mock
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`
import org.mockito.ArgumentCaptor
import java.time.LocalDate
import java.time.LocalDateTime
import java.util.Optional

class TeachingClassCourseServiceTest {
    private val teachingClassRepository = mock(TeachingClassRepository::class.java)
    private val studentRepository = mock(TeachingClassStudentRepository::class.java)
    private val courseRepository = mock(TeachingClassCourseRepository::class.java)
    private val service = TeacherTeachingClassService(
        teachingClassRepository,
        studentRepository,
        courseRepository,
        mock(UserRepository::class.java),
        mock(StudentPurgeService::class.java),
    )

    @Test
    fun `one teaching class accepts multiple reusable courses in order`() {
        `when`(teachingClassRepository.findById(101)).thenReturn(
            Optional.of(
                TeachingClassEntity(
                    teachingClassId = 101,
                    teacherId = 7,
                    startDate = LocalDate.parse("2026-09-01"),
                    endDate = LocalDate.parse("2027-01-15"),
                ),
            ),
        )
        `when`(courseRepository.findExistingCourseIds(listOf(1, 2))).thenReturn(listOf(1, 2))
        `when`(courseRepository.saveAll(anyList())).thenAnswer { it.arguments[0] }
        `when`(courseRepository.findCourseViews(101)).thenReturn(
            listOf(
                courseView(1, "SQL注入攻防", 1, "2026-09-01", "2026-09-14"),
                courseView(2, "XSS攻防", 2, "2026-09-15", "2026-09-28"),
            ),
        )
        val request = TeachingClassCourseUpdateRequest(
            listOf(
                TeachingClassCourseItemRequest(1, 1, date("2026-09-01"), date("2026-09-14")),
                TeachingClassCourseItemRequest(2, 2, date("2026-09-15"), date("2026-09-28")),
            ),
        )

        val result = service.replaceCourses(teacherId = 7, teachingClassId = 101, request)

        assertEquals(listOf(1, 2), result.map { it.courseId })
        assertEquals(listOf(1, 2), result.map { it.teachingOrder })
    }

    @Test
    fun `teaching order must be contiguous and start at one`() {
        `when`(teachingClassRepository.findById(101)).thenReturn(
            Optional.of(TeachingClassEntity(teachingClassId = 101, teacherId = 7)),
        )
        val request = TeachingClassCourseUpdateRequest(
            listOf(
                TeachingClassCourseItemRequest(1, 1, null, null),
                TeachingClassCourseItemRequest(2, 3, null, null),
            ),
        )

        val error = assertThrows(ApiException::class.java) {
            service.replaceCourses(7, 101, request)
        }

        assertEquals(400, error.status)
    }

    @Test
    fun `teacher can write teaching content for one arranged course`() {
        `when`(teachingClassRepository.findById(101)).thenReturn(
            Optional.of(TeachingClassEntity(teachingClassId = 101, teacherId = 7)),
        )
        `when`(courseRepository.findByTeachingClassIdAndCourseId(101, 1)).thenReturn(
            Optional.of(TeachingClassCourseEntity(teachingClassId = 101, courseId = 1)),
        )
        `when`(courseRepository.findCourseViews(101)).thenReturn(
            listOf(
                courseView(
                    1,
                    "SQL注入攻防",
                    1,
                    "2026-09-01",
                    "2026-09-14",
                    "讲解参数化查询并完成靶场练习",
                ),
            ),
        )

        val result = service.updateCourseContent(
            teacherId = 7,
            teachingClassId = 101,
            courseId = 1,
            request = TeachingClassCourseContentUpdateRequest("  讲解参数化查询并完成靶场练习  "),
        )

        val captor = ArgumentCaptor.forClass(TeachingClassCourseEntity::class.java)
        verify(courseRepository).saveAndFlush(captor.capture())
        assertEquals("讲解参数化查询并完成靶场练习", captor.value.teachingContent)
        assertEquals("讲解参数化查询并完成靶场练习", result.teachingContent)
    }

    @Test
    fun `reordering courses keeps teacher written teaching content`() {
        `when`(teachingClassRepository.findById(101)).thenReturn(
            Optional.of(TeachingClassEntity(teachingClassId = 101, teacherId = 7)),
        )
        `when`(courseRepository.findExistingCourseIds(listOf(1))).thenReturn(listOf(1))
        `when`(courseRepository.findAllByTeachingClassId(101)).thenReturn(
            listOf(
                TeachingClassCourseEntity(
                    teachingClassId = 101,
                    courseId = 1,
                    teachingContent = "保留本班已有教学内容",
                ),
            ),
        )
        var savedContent: String? = null
        `when`(courseRepository.saveAll(anyList())).thenAnswer { invocation ->
            val saved = invocation.arguments[0] as List<*>
            savedContent = (saved.single() as TeachingClassCourseEntity).teachingContent
            saved
        }
        `when`(courseRepository.findCourseViews(101)).thenReturn(
            listOf(courseView(1, "SQL注入攻防", 1, "2026-09-01", "2026-09-14", "保留本班已有教学内容")),
        )

        service.replaceCourses(
            teacherId = 7,
            teachingClassId = 101,
            TeachingClassCourseUpdateRequest(
                listOf(TeachingClassCourseItemRequest(1, 1, date("2026-09-01"), date("2026-09-14"))),
            ),
        )

        assertEquals("保留本班已有教学内容", savedContent)
    }

    private fun courseView(
        courseId: Int,
        courseName: String,
        order: Int,
        start: String,
        end: String,
        teachingContent: String? = null,
    ) = object : TeachingClassCourseView {
        override fun getCourseId() = courseId
        override fun getCourseName() = courseName
        override fun getCourseDescription() = ""
        override fun getTeachingContent() = teachingContent
        override fun getTeachingOrder() = order
        override fun getPlannedStartDate() = date(start)
        override fun getPlannedEndDate() = date(end)
        override fun getCreatedBy(): Long? = null
        override fun getCreatorName(): String? = null
        override fun getUpdatedAt() = LocalDateTime.parse("2026-07-14T12:00:00")
    }

    private fun date(value: String): LocalDate = LocalDate.parse(value)
}
