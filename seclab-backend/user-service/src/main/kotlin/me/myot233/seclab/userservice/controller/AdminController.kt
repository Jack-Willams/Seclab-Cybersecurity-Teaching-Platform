package me.myot233.seclab.userservice.controller

import jakarta.validation.Valid
import me.myot233.seclab.userservice.dto.AdminUserCreateRequest
import me.myot233.seclab.userservice.dto.AdminUserFilterOptions
import me.myot233.seclab.userservice.dto.AdminUserListData
import me.myot233.seclab.userservice.dto.AdminUserListItemResponse
import me.myot233.seclab.userservice.dto.AdminUserUpdateRequest
import me.myot233.seclab.userservice.dto.ApiResponse
import me.myot233.seclab.userservice.service.JwtTokenService
import me.myot233.seclab.userservice.service.UserService
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestHeader
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/admin")
class AdminController(
    private val userService: UserService,
    private val jwtTokenService: JwtTokenService,
) {
    @GetMapping("/users")
    fun listUsers(
        @RequestParam(defaultValue = "1") page: Int,
        @RequestParam(defaultValue = "10") pageSize: Int,
        @RequestParam(required = false) keyword: String?,
        @RequestParam(required = false) academy: String?,
        @RequestParam(required = false) className: String?,
        @RequestParam(required = false) classId: Long?,
        @RequestParam(required = false) status: String?,
        @RequestParam(required = false) gender: Int?,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<AdminUserListData> =
        ApiResponse.success(
            userService.listStudentsForAdmin(
                token = jwtTokenService.resolveToken(token, authorization),
                page = page,
                pageSize = pageSize,
                keyword = keyword,
                academy = academy,
                className = className,
                classId = classId,
                status = status,
                gender = gender,
            ),
            "Student list loaded successfully",
        )

    @GetMapping("/user-filters")
    fun listUserFilterOptions(
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<AdminUserFilterOptions> =
        ApiResponse.success(
            userService.listAdminUserFilterOptions(jwtTokenService.resolveToken(token, authorization)),
            "Filter options loaded successfully",
        )

    @PostMapping("/users")
    fun createUser(
        @Valid @RequestBody request: AdminUserCreateRequest,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<AdminUserListItemResponse> =
        ApiResponse.success(
            userService.createStudentForAdmin(
                token = jwtTokenService.resolveToken(token, authorization),
                request = request,
            ),
            "Student created successfully",
        )

    @PutMapping("/users/{userId}")
    fun updateUser(
        @PathVariable userId: Long,
        @Valid @RequestBody request: AdminUserUpdateRequest,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<AdminUserListItemResponse> =
        ApiResponse.success(
            userService.updateStudentForAdmin(
                token = jwtTokenService.resolveToken(token, authorization),
                userId = userId,
                request = request,
            ),
            "Student updated successfully",
        )

    @DeleteMapping("/users/{userId}")
    fun deleteUser(
        @PathVariable userId: Long,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<Unit> {
        userService.deleteStudentForAdmin(
            token = jwtTokenService.resolveToken(token, authorization),
            userId = userId,
        )
        return ApiResponse.success(null, "Student deleted successfully")
    }

    @PostMapping("/users/{userId}/reset-password")
    fun resetPassword(
        @PathVariable userId: Long,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<Unit> {
        userService.resetStudentPasswordForAdmin(
            token = jwtTokenService.resolveToken(token, authorization),
            userId = userId,
        )
        return ApiResponse.success(null, "Password reset successfully")
    }
}
