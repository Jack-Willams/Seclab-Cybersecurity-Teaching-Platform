package me.myot233.seclab.userservice.service

import me.myot233.seclab.userservice.dto.RegisterRequest
import me.myot233.seclab.userservice.entity.SchoolClassEntity
import me.myot233.seclab.userservice.entity.TeachingClassEntity
import me.myot233.seclab.userservice.entity.TeachingClassStatus
import me.myot233.seclab.userservice.entity.TeachingClassStudentEntity
import me.myot233.seclab.userservice.entity.UserEntity
import me.myot233.seclab.userservice.exception.ApiException
import me.myot233.seclab.userservice.repository.SchoolClassRepository
import me.myot233.seclab.userservice.repository.TeachingClassRepository
import me.myot233.seclab.userservice.repository.TeachingClassStudentRepository
import me.myot233.seclab.userservice.repository.UserRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.mockito.ArgumentCaptor
import org.mockito.Mockito.any
import org.mockito.Mockito.mock
import org.mockito.Mockito.never
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder

class UserRegistrationServiceTest {
    private val userRepository = mock(UserRepository::class.java)
    private val classRepository = mock(SchoolClassRepository::class.java)
    private val teachingClassRepository = mock(TeachingClassRepository::class.java)
    private val teachingClassStudentRepository = mock(TeachingClassStudentRepository::class.java)
    private val jwtTokenService = mock(JwtTokenService::class.java)
    private val userService = UserService(
        userRepository,
        classRepository,
        teachingClassRepository,
        teachingClassStudentRepository,
        PasswordService(BCryptPasswordEncoder()),
        jwtTokenService,
    )

    private fun teachingClass(id: Long, name: String) = TeachingClassEntity(
        teachingClassId = id,
        className = name,
        academicYear = "2026-2027",
        semester = 1,
        teacherId = 1,
        status = TeachingClassStatus.ACTIVE,
    )

    private fun stubActiveClasses(vararg classes: TeachingClassEntity) {
        `when`(teachingClassRepository.findAllByStatusOrderByTeachingClassIdDesc(TeachingClassStatus.ACTIVE))
            .thenReturn(classes.toList())
    }

    private fun registerRequest(className: String?) = RegisterRequest().apply {
        userStudentNumber = STUDENT_NUMBER
        userPassword = "123456"
        userName = "李情"
        userEmail = "liqing@example.com"
        userAcademy = "网络空间安全学院"
        userClass = className
    }

    @BeforeEach
    fun setUp() {
        // 教师端已建：网安241班(4)、网安231班(3)；仓库按 id 倒序返回
        stubActiveClasses(teachingClass(4, "网安241班"), teachingClass(3, "网安231班"))
        `when`(classRepository.findFirstByClassName("网安231班"))
            .thenReturn(SchoolClassEntity(classId = 6, className = "网安231班"))
        `when`(userRepository.existsByUserStudentNumber(STUDENT_NUMBER)).thenReturn(false)
        `when`(userRepository.save(any(UserEntity::class.java))).thenAnswer { invocation ->
            (invocation.arguments[0] as UserEntity).also { it.userId = 70 }
        }
    }

    @Test
    fun `register options only expose active teaching classes`() {
        val options = userService.listRegisterOptions().classes

        assertEquals(listOf("网安231班", "网安241班"), options.map { it.className })
        assertEquals(listOf(3L, 4L), options.map { it.teachingClassId })
    }

    @Test
    fun `duplicate class names collapse to the newest teaching class`() {
        stubActiveClasses(teachingClass(7, "网安231班"), teachingClass(3, "网安231班"))

        val options = userService.listRegisterOptions().classes

        assertEquals(1, options.size)
        assertEquals(7L, options.first().teachingClassId)
    }

    @Test
    fun `registering into a teacher created class joins that class roster`() {
        userService.register(registerRequest("网安231班"))

        val captor = ArgumentCaptor.forClass(TeachingClassStudentEntity::class.java)
        verify(teachingClassStudentRepository).save(captor.capture())
        assertEquals(3L, captor.value.teachingClassId)
        assertEquals(70L, captor.value.studentId)
        assertEquals("SELF_REGISTER", captor.value.source)
    }

    @Test
    fun `registering into a class the teacher never created is rejected`() {
        val error = assertThrows(ApiException::class.java) {
            userService.register(registerRequest("网安299班"))
        }

        assertEquals(400, error.status)
        assertTrue(error.message.contains("网安299班"))
        verify(userRepository, never()).save(any(UserEntity::class.java))
    }

    @Test
    fun `registering into an archived class is rejected`() {
        stubActiveClasses()

        val error = assertThrows(ApiException::class.java) {
            userService.register(registerRequest("网安231班"))
        }

        assertEquals(400, error.status)
        verify(userRepository, never()).save(any(UserEntity::class.java))
    }

    @Test
    fun `registering without a class is rejected`() {
        val error = assertThrows(ApiException::class.java) {
            userService.register(registerRequest(null))
        }

        assertEquals(400, error.status)
        assertEquals("请选择班级", error.message)
        verify(userRepository, never()).save(any(UserEntity::class.java))
    }

    private companion object {
        const val STUDENT_NUMBER = "202401050001"
    }
}
