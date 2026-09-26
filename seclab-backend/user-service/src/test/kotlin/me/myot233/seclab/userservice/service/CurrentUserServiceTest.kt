package me.myot233.seclab.userservice.service

import me.myot233.seclab.userservice.entity.UserEntity
import me.myot233.seclab.userservice.entity.UserRole
import me.myot233.seclab.userservice.exception.ApiException
import me.myot233.seclab.userservice.repository.UserRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test
import org.mockito.Mockito.mock
import org.mockito.Mockito.`when`
import java.util.Optional

class CurrentUserServiceTest {
    private val userRepository = mock(UserRepository::class.java)
    private val jwtTokenService = mock(JwtTokenService::class.java)
    private val currentUserService = CurrentUserService(userRepository, jwtTokenService)

    @Test
    fun `teacher role can open teacher workspace before owning a class`() {
        val teacher = UserEntity(
            userId = 9,
            userStudentNumber = "teacher01",
            userRole = UserRole.TEACHER,
        )
        `when`(jwtTokenService.resolveToken("token", null)).thenReturn("token")
        `when`(jwtTokenService.parse("token")).thenReturn(TokenPayload(9, "teacher01"))
        `when`(userRepository.findById(9)).thenReturn(Optional.of(teacher))

        assertEquals(9, currentUserService.requireTeacher("token", null).userId)
    }

    @Test
    fun `student role is rejected from teacher endpoints`() {
        val student = UserEntity(
            userId = 10,
            userStudentNumber = "20260001",
            userRole = UserRole.STUDENT,
        )
        `when`(jwtTokenService.resolveToken("token", null)).thenReturn("token")
        `when`(jwtTokenService.parse("token")).thenReturn(TokenPayload(10, "20260001"))
        `when`(userRepository.findById(10)).thenReturn(Optional.of(student))

        val error = assertThrows(ApiException::class.java) {
            currentUserService.requireTeacher("token", null)
        }

        assertEquals(403, error.status)
    }

    @Test
    fun `disabled teacher is rejected`() {
        val teacher = UserEntity(
            userId = 11,
            userStudentNumber = "teacher02",
            userRole = UserRole.TEACHER,
            isDeleted = 1,
        )
        `when`(jwtTokenService.resolveToken(null, "Bearer token")).thenReturn("token")
        `when`(jwtTokenService.parse("token")).thenReturn(TokenPayload(11, "teacher02"))
        `when`(userRepository.findById(11)).thenReturn(Optional.of(teacher))

        val error = assertThrows(ApiException::class.java) {
            currentUserService.requireTeacher(null, "Bearer token")
        }

        assertEquals(403, error.status)
    }
}
