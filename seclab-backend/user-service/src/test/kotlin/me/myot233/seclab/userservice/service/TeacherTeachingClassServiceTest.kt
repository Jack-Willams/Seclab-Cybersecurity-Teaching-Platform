package me.myot233.seclab.userservice.service

import me.myot233.seclab.userservice.dto.TeachingClassSaveRequest
import me.myot233.seclab.userservice.entity.TeachingClassEntity
import me.myot233.seclab.userservice.entity.TeachingClassStatus
import me.myot233.seclab.userservice.entity.UserEntity
import me.myot233.seclab.userservice.exception.ApiException
import me.myot233.seclab.userservice.repository.TeachingClassCourseRepository
import me.myot233.seclab.userservice.repository.TeachingClassRepository
import me.myot233.seclab.userservice.repository.TeachingClassStudentRepository
import me.myot233.seclab.userservice.repository.UserRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.mockito.ArgumentMatchers.any
import org.mockito.Mockito.mock
import org.mockito.Mockito.never
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`
import java.time.LocalDate
import java.util.Optional

class TeacherTeachingClassServiceTest {
    private val teachingClassRepository = mock(TeachingClassRepository::class.java)
    private val studentRepository = mock(TeachingClassStudentRepository::class.java)
    private val courseRepository = mock(TeachingClassCourseRepository::class.java)
    private val userRepository = mock(UserRepository::class.java)
    private val studentPurgeService = mock(StudentPurgeService::class.java)
    private val service = TeacherTeachingClassService(
        teachingClassRepository,
        studentRepository,
        courseRepository,
        userRepository,
        studentPurgeService,
    )

    @Test
    fun `teacher lists only their own classes`() {
        val ownedClass = teachingClass(id = 101, teacherId = 7, name = "网络安全232班")
        val otherTeacherClass = teachingClass(id = 102, teacherId = 8, name = "网络安全231班")
        `when`(teachingClassRepository.findAllByTeacherIdOrderByUpdatedAtDesc(7))
            .thenReturn(listOf(ownedClass))
        `when`(studentRepository.countByTeachingClassId(101)).thenReturn(32L)
        `when`(studentRepository.countByTeachingClassId(102)).thenReturn(28L)
        `when`(courseRepository.countByTeachingClassId(101)).thenReturn(6L)
        `when`(courseRepository.countByTeachingClassId(102)).thenReturn(5L)

        val result = service.listAll(currentTeacherId = 7)

        assertEquals(listOf(101L), result.map { it.teachingClassId })
        assertTrue(result[0].canManage)
        assertEquals(32, result[0].studentCount)
    }

    @Test
    fun `teacher cannot read another teachers class detail`() {
        val otherTeacherClass = teachingClass(id = 102, teacherId = 8, name = "other class")
        `when`(teachingClassRepository.findById(102)).thenReturn(Optional.of(otherTeacherClass))

        val error = assertThrows(ApiException::class.java) {
            service.getDetail(7, 102)
        }

        assertEquals(403, error.status)
    }

    @Test
    fun `teacher cannot read another teachers course arrangements`() {
        val otherTeacherClass = teachingClass(id = 102, teacherId = 8, name = "other class")
        `when`(teachingClassRepository.findById(102)).thenReturn(Optional.of(otherTeacherClass))

        val error = assertThrows(ApiException::class.java) {
            service.listCourses(7, 102)
        }

        assertEquals(403, error.status)
    }

    @Test
    fun `teacher cannot update another teachers class`() {
        val otherTeacherClass = teachingClass(id = 102, teacherId = 8, name = "网络安全231班")
        `when`(teachingClassRepository.findById(102)).thenReturn(Optional.of(otherTeacherClass))

        val error = assertThrows(ApiException::class.java) {
            service.update(7, 102, validRequest())
        }

        assertEquals(403, error.status)
    }

    @Test
    fun `end date cannot precede start date`() {
        val request = validRequest().copy(
            startDate = LocalDate.parse("2026-09-01"),
            endDate = LocalDate.parse("2026-08-31"),
        )

        val error = assertThrows(ApiException::class.java) {
            service.create(7, request)
        }

        assertEquals(400, error.status)
    }

    @Test
    fun `create normalizes name and assigns current teacher`() {
        `when`(
            teachingClassRepository.existsByTeacherIdAndAcademicYearAndSemesterAndClassNameIgnoreCase(
                7,
                "2026-2027",
                1,
                "网络安全232班",
            ),
        ).thenReturn(false)
        `when`(teachingClassRepository.save(any(TeachingClassEntity::class.java))).thenAnswer { invocation ->
            (invocation.getArgument<TeachingClassEntity>(0)).apply { teachingClassId = 101 }
        }

        val result = service.create(7, validRequest().copy(className = "  网络安全232班  "))

        assertEquals(101, result.teachingClassId)
        assertEquals(7, result.teacherId)
        assertEquals("网络安全232班", result.className)
        assertTrue(result.canManage)
    }

    @Test
    fun `deleting a class purges it and the students that belong only to it`() {
        val ownedClass = teachingClass(id = 101, teacherId = 7, name = "网络安全232班")
        val exclusiveStudent = UserEntity(userId = 55, userStudentNumber = "202401050001")
        `when`(teachingClassRepository.findById(101)).thenReturn(Optional.of(ownedClass))
        `when`(studentRepository.findStudentIdsExclusiveTo(101)).thenReturn(listOf(55L))
        `when`(studentRepository.countByTeachingClassId(101)).thenReturn(3L)
        `when`(userRepository.findById(55)).thenReturn(Optional.of(exclusiveStudent))

        val result = service.delete(7, 101)

        // 只属于本班的删掉，另外 2 名跨班学生保留账号
        assertEquals(1, result.deletedStudentCount)
        assertEquals(2, result.keptStudentCount)
        verify(studentPurgeService).purgeStudent(exclusiveStudent)
        verify(studentPurgeService).purgeTeachingClass(101)
    }

    @Test
    fun `teacher cannot delete another teachers class`() {
        val otherTeacherClass = teachingClass(id = 102, teacherId = 8, name = "网络安全231班")
        `when`(teachingClassRepository.findById(102)).thenReturn(Optional.of(otherTeacherClass))

        val error = assertThrows(ApiException::class.java) {
            service.delete(7, 102)
        }

        assertEquals(403, error.status)
        verify(studentPurgeService, never()).purgeTeachingClass(102)
    }

    private fun teachingClass(id: Long, teacherId: Long, name: String) = TeachingClassEntity(
        teachingClassId = id,
        className = name,
        academicYear = "2026-2027",
        semester = 1,
        teacherId = teacherId,
        status = TeachingClassStatus.ACTIVE,
    )

    private fun validRequest() = TeachingClassSaveRequest(
        className = "网络安全232班",
        academicYear = "2026-2027",
        semester = 1,
        startDate = LocalDate.parse("2026-09-01"),
        endDate = LocalDate.parse("2027-01-15"),
    )
}
