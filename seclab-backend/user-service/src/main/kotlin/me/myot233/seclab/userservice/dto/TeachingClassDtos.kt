package me.myot233.seclab.userservice.dto

import jakarta.validation.constraints.Max
import jakarta.validation.constraints.Min
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Pattern
import jakarta.validation.constraints.Size
import java.time.LocalDate
import java.time.LocalDateTime

data class TeachingClassSaveRequest(
    @field:NotBlank(message = "教学班名称不能为空")
    @field:Size(max = 120, message = "教学班名称不能超过120个字符")
    val className: String,

    @field:Pattern(regexp = "\\d{4}-\\d{4}", message = "学年格式应为2026-2027")
    val academicYear: String,

    @field:Min(1, message = "学期只能为1或2")
    @field:Max(2, message = "学期只能为1或2")
    val semester: Int,

    val startDate: LocalDate? = null,
    val endDate: LocalDate? = null,
)

data class TeachingClassResponse(
    val teachingClassId: Long,
    val className: String,
    val academicYear: String,
    val semester: Int,
    val teacherId: Long,
    val teacherName: String?,
    val startDate: LocalDate?,
    val endDate: LocalDate?,
    val status: String,
    val studentCount: Int,
    val courseCount: Int,
    val currentCourse: String?,
    val lastActiveAt: LocalDateTime?,
    val canManage: Boolean,
    val createdAt: LocalDateTime,
    val updatedAt: LocalDateTime,
)

/** 删除教学班的结果：真正被删掉的学生数，以及因为还在别的教学班而保留的学生数。 */
data class TeachingClassDeleteResult(
    val deletedStudentCount: Int,
    val keptStudentCount: Int,
)

data class ImportAccountRow(
    val rowNumber: Int,
    val studentNumber: String,
    val studentName: String,
    val administrativeClass: String,
)

data class ImportDuplicateRow(
    val rowNumber: Int,
    val studentNumber: String,
    val firstRowNumber: Int,
)

data class ImportErrorRow(
    val rowNumber: Int,
    val message: String,
)

data class TeachingClassImportPreview(
    val batchId: String,
    val newAccounts: List<ImportAccountRow>,
    val existingAccounts: List<ImportAccountRow>,
    val duplicateRows: List<ImportDuplicateRow>,
    val errorRows: List<ImportErrorRow>,
    val expiresAt: LocalDateTime,
)

data class TeachingClassImportConfirmResult(
    val createdAccountCount: Int,
    val addedMemberCount: Int,
    val skippedMemberCount: Int,
)

data class TeachingClassStudentResponse(
    val studentId: Long,
    val studentNumber: String,
    val studentName: String?,
    val administrativeClass: String?,
    val joinedAt: LocalDateTime,
    val recentActivityAt: LocalDateTime?,
)

data class TeachingClassCourseItemRequest(
    val courseId: Int,
    val teachingOrder: Int,
    val plannedStartDate: LocalDate? = null,
    val plannedEndDate: LocalDate? = null,
)

data class TeachingClassCourseUpdateRequest(
    val items: List<TeachingClassCourseItemRequest>,
)

data class TeachingClassCourseContentUpdateRequest(
    @field:Size(max = 2000, message = "教学内容不能超过2000个字符")
    val teachingContent: String? = null,
)

data class TeachingClassCourseResponse(
    val courseId: Int,
    val courseName: String,
    val courseDescription: String,
    val teachingContent: String?,
    val teachingOrder: Int,
    val plannedStartDate: LocalDate?,
    val plannedEndDate: LocalDate?,
    val createdBy: Long?,
    val creatorName: String?,
    val updatedAt: LocalDateTime,
)
