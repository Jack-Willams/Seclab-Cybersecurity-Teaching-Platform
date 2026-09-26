package me.myot233.seclab.userservice.dto

import jakarta.validation.constraints.Email
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Size

class LoginRequest {
    @field:NotBlank(message = "Student number is required")
    @field:Size(max = 13, message = "Student number must be 13 characters or fewer")
    var userStudentNumber: String? = null

    @field:NotBlank(message = "Password is required")
    var userPassword: String? = null
}

class RegisterRequest {
    @field:NotBlank(message = "Student number is required")
    @field:Size(max = 13, message = "Student number must be 13 characters or fewer")
    var userStudentNumber: String? = null

    @field:NotBlank(message = "Password is required")
    @field:Size(min = 6, max = 72, message = "Password length must be between 6 and 72 characters")
    var userPassword: String? = null

    @field:NotBlank(message = "Name is required")
    var userName: String? = null

    @field:NotBlank(message = "Email is required")
    @field:Email(message = "Email format is invalid")
    var userEmail: String? = null

    @field:Size(max = 11, message = "Phone number must be 11 digits or fewer")
    var userTel: String? = null

    var userAcademy: String? = null
    var userClass: String? = null
    var userImage: String? = null
    var classId: Long? = null
    var userGender: Int? = null
}

class UserUpdateRequest {
    var userId: Long? = null
    var userStudentNumber: String? = null
    var userPassword: String? = null

    @field:Size(max = 11, message = "Phone number must be 11 digits or fewer")
    var userTel: String? = null

    var userImage: String? = null
    var userName: String? = null
    var userAcademy: String? = null
    var userClass: String? = null
    var userEmail: String? = null
    var userGender: Int? = null
    var classId: Long? = null
}

/**
 * 学生注册时可选的班级。只来自教师端已创建且未归档的教学班，
 * 前端不再维护任何硬编码班级列表。
 */
data class RegisterClassOption(
    val teachingClassId: Long,
    val className: String,
    val academicYear: String,
    val semester: Int,
    val teacherName: String?,
)

data class RegisterOptionsResponse(
    val classes: List<RegisterClassOption>,
)

data class LoginResponse(
    val loginData: LoginData,
)

data class LoginData(
    val userId: Long,
    val userStudentNumber: String,
    val userImage: String?,
    val userName: String?,
    val classId: Long?,
    val className: String?,
    val role: String,
    val status: String,
    val token: String,
)

data class UserProfileResponse(
    val userId: Long,
    val userStudentNumber: String,
    val userTel: String?,
    val userImage: String?,
    val userName: String?,
    val userAcademy: String?,
    val userClass: String?,
    val userEmail: String?,
    val userGender: Int?,
    val classId: Long?,
    val createTime: String?,
    val role: String,
    val status: String,
)

data class AdminUserListItemResponse(
    val userId: Long,
    val userStudentNumber: String,
    val userName: String?,
    val userAcademy: String?,
    val userClass: String?,
    val userEmail: String?,
    val userTel: String?,
    val userGender: Int?,
    val classId: Long?,
    val createTime: String?,
    val status: String,
)

/** 管理后台筛选下拉的可选项，取自学生数据本身，避免前端写死一份对不上的名单。 */
data class AdminUserFilterOptions(
    val academies: List<String>,
    val classes: List<String>,
)

data class AdminUserListData(
    val list: List<AdminUserListItemResponse>,
    val total: Long,
    val page: Int,
    val pageSize: Int,
)

class AdminUserCreateRequest {
    @field:NotBlank(message = "Student number is required")
    @field:Size(max = 13, message = "Student number must be 13 characters or fewer")
    var userStudentNumber: String? = null

    @field:NotBlank(message = "Name is required")
    var userName: String? = null

    @field:Size(max = 11, message = "Phone number must be 11 digits or fewer")
    var userTel: String? = null

    @field:Email(message = "Email format is invalid")
    var userEmail: String? = null

    var userAcademy: String? = null
    var userClass: String? = null
    var classId: Long? = null
    var userGender: Int? = null
}

class AdminUserUpdateRequest {
    @field:NotBlank(message = "Name is required")
    var userName: String? = null

    @field:Size(max = 11, message = "Phone number must be 11 digits or fewer")
    var userTel: String? = null

    @field:Email(message = "Email format is invalid")
    var userEmail: String? = null

    var userAcademy: String? = null
    var userClass: String? = null
    var classId: Long? = null
    var userGender: Int? = null
}
