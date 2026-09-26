package me.myot233.seclab.userservice.controller

import jakarta.validation.Valid
import me.myot233.seclab.userservice.dto.ApiResponse
import me.myot233.seclab.userservice.dto.LoginRequest
import me.myot233.seclab.userservice.dto.LoginResponse
import me.myot233.seclab.userservice.dto.RegisterOptionsResponse
import me.myot233.seclab.userservice.dto.RegisterRequest
import me.myot233.seclab.userservice.dto.UserProfileResponse
import me.myot233.seclab.userservice.dto.UserUpdateRequest
import me.myot233.seclab.userservice.service.JwtTokenService
import me.myot233.seclab.userservice.service.UserService
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestHeader
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/stu")
class StudentController(
    private val userService: UserService,
    private val jwtTokenService: JwtTokenService,
) {
    @PostMapping("/login")
    fun login(@Valid @RequestBody request: LoginRequest): ApiResponse<LoginResponse> =
        ApiResponse.success(userService.login(request), "Login successful")

    /** 注册页拉取可选班级，未登录可访问。 */
    @GetMapping("/register-options")
    fun registerOptions(): ApiResponse<RegisterOptionsResponse> =
        ApiResponse.success(userService.listRegisterOptions(), "可选班级加载成功")

    @PostMapping("/register")
    fun register(@Valid @RequestBody request: RegisterRequest): ApiResponse<Unit> {
        userService.register(request)
        return ApiResponse.success(null, "Registration successful")
    }

    @GetMapping("/profile")
    fun getProfile(
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<UserProfileResponse> =
        ApiResponse.success(
            userService.getProfile(jwtTokenService.resolveToken(token, authorization)),
            "Profile loaded successfully",
        )

    @PostMapping("/updateProfile")
    fun updateProfile(
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
        @Valid @RequestBody request: UserUpdateRequest,
    ): ApiResponse<UserProfileResponse> =
        ApiResponse.success(
            userService.updateProfile(jwtTokenService.resolveToken(token, authorization), request),
            "Profile updated successfully",
        )
}
