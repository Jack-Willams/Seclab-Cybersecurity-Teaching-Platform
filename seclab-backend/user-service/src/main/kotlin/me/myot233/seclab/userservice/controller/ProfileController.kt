package me.myot233.seclab.userservice.controller

import me.myot233.seclab.userservice.dto.ApiResponse
import me.myot233.seclab.userservice.entity.StudentProfileSnapshotEntity
import me.myot233.seclab.userservice.service.JwtTokenService
import me.myot233.seclab.userservice.service.ProfileService
import org.springframework.web.bind.annotation.CookieValue
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestHeader
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api/profile")
class ProfileController(
    private val profileService: ProfileService,
    private val jwtTokenService: JwtTokenService,
) {
    @PostMapping("/events")
    fun reportEvent(
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
        @CookieValue(name = "token", required = false) token: String?,
        @RequestBody request: Map<String, Any>,
    ): ApiResponse<String> {
        val resolvedToken = jwtTokenService.resolveToken(token, authorization)
            ?: return ApiResponse.error(401, "Unauthorized")

        val payload = jwtTokenService.parse(resolvedToken)
        profileService.saveEvent(request, payload.userId)
        profileService.recalculateStudentProfile(payload.userId)
        return ApiResponse.success("ok", "Event saved")
    }

    @GetMapping("/student/me")
    fun getMyProfile(
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
        @CookieValue(name = "token", required = false) token: String?,
    ): ApiResponse<StudentProfileSnapshotEntity?> {
        val resolvedToken = jwtTokenService.resolveToken(token, authorization)
            ?: return ApiResponse.error(401, "Unauthorized")

        val payload = jwtTokenService.parse(resolvedToken)
        val profile = profileService.getProfile(payload.userId)
        return ApiResponse.success(profile, "Profile fetched")
    }

    @PostMapping("/student/{userId}/recalculate")
    fun recalculateProfile(
        @PathVariable userId: Long,
    ): ApiResponse<StudentProfileSnapshotEntity> {
        val profile = profileService.recalculateStudentProfile(userId)
        return ApiResponse.success(profile, "Profile recalculated")
    }
}
