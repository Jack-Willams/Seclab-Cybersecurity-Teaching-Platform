package me.myot233.seclab.userservice.service

import me.myot233.seclab.userservice.entity.UserEntity
import me.myot233.seclab.userservice.entity.UserRole
import me.myot233.seclab.userservice.exception.ApiException
import me.myot233.seclab.userservice.repository.UserRepository
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service

@Service
class CurrentUserService(
    private val userRepository: UserRepository,
    private val jwtTokenService: JwtTokenService,
) {
    fun requireTeacher(queryToken: String?, authorizationHeader: String?): UserEntity {
        val token = jwtTokenService.resolveToken(queryToken, authorizationHeader)
        val payload = jwtTokenService.parse(token)
        val user = userRepository.findById(payload.userId).orElseThrow {
            ApiException(401, "Token user does not exist", HttpStatus.UNAUTHORIZED)
        }

        if (user.isDeleted == 1) {
            throw ApiException(403, "This account is disabled", HttpStatus.FORBIDDEN)
        }
        if (user.userRole != UserRole.TEACHER) {
            throw ApiException(403, "Only teacher accounts can access this endpoint", HttpStatus.FORBIDDEN)
        }
        return user
    }
}
