package me.myot233.seclab.experimentmoduleservice.service

import com.fasterxml.jackson.databind.ObjectMapper
import me.myot233.seclab.experimentmoduleservice.dto.CourseMutationRequest
import me.myot233.seclab.experimentmoduleservice.entity.CourseEntity
import me.myot233.seclab.experimentmoduleservice.repository.CourseRepository
import me.myot233.seclab.experimentmoduleservice.repository.ModuleRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test
import org.mockito.ArgumentCaptor
import org.mockito.Mockito.mock
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.web.server.ResponseStatusException
import java.util.Optional

class CoursePermissionTest {
    private val courseRepository = mock(CourseRepository::class.java)
    private val moduleRepository = mock(ModuleRepository::class.java)
    private val jdbcTemplate = mock(JdbcTemplate::class.java)
    private val service = CatalogQueryService(
        courseRepository,
        moduleRepository,
        ObjectMapper(),
        jdbcTemplate,
    )

    @Test
    fun `course creation records token teacher as creator`() {
        `when`(courseRepository.findMaxId()).thenReturn(6)
        `when`(courseRepository.save(org.mockito.ArgumentMatchers.any(CourseEntity::class.java))).thenAnswer {
            it.arguments[0]
        }

        service.createCourse(teacherId = 7, request = request())

        val captor = ArgumentCaptor.forClass(CourseEntity::class.java)
        verify(courseRepository).save(captor.capture())
        assertEquals(7, captor.value.createdBy)
    }

    @Test
    fun `only course creator can update it`() {
        `when`(courseRepository.findById(3)).thenReturn(
            Optional.of(CourseEntity(id = 3, courseName = "旧课程", courseDescription = "说明", createdBy = 8)),
        )

        val error = assertThrows(ResponseStatusException::class.java) {
            service.updateCourse(teacherId = 7, id = 3, request = request())
        }

        assertEquals(403, error.statusCode.value())
    }

    @Test
    fun `legacy shared course without creator remains read only`() {
        `when`(courseRepository.findById(3)).thenReturn(
            Optional.of(CourseEntity(id = 3, courseName = "系统课程", courseDescription = "说明", createdBy = null)),
        )

        val error = assertThrows(ResponseStatusException::class.java) {
            service.deleteCourse(teacherId = 7, id = 3)
        }

        assertEquals(403, error.statusCode.value())
    }

    private fun request() = CourseMutationRequest(
        courseName = "Web安全基础",
        courseDescription = "面向本科生的Web安全实践课程",
        difficulty = 3,
        teacherName = "王老师",
        category = "web",
    )
}
