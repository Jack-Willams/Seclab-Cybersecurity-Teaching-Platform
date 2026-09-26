package me.myot233.seclab.userservice.controller

import jakarta.validation.Valid
import me.myot233.seclab.userservice.dto.ApiResponse
import me.myot233.seclab.userservice.dto.TeachingClassResponse
import me.myot233.seclab.userservice.dto.TeachingClassImportConfirmResult
import me.myot233.seclab.userservice.dto.TeachingClassImportPreview
import me.myot233.seclab.userservice.dto.TeachingClassCourseResponse
import me.myot233.seclab.userservice.dto.TeachingClassCourseContentUpdateRequest
import me.myot233.seclab.userservice.dto.TeachingClassCourseUpdateRequest
import me.myot233.seclab.userservice.dto.TeachingClassDeleteResult
import me.myot233.seclab.userservice.dto.TeachingClassSaveRequest
import me.myot233.seclab.userservice.dto.TeachingClassStudentResponse
import me.myot233.seclab.userservice.service.CurrentUserService
import me.myot233.seclab.userservice.service.TeachingClassImportService
import me.myot233.seclab.userservice.service.TeacherTeachingClassService
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PatchMapping
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestHeader
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.bind.annotation.RequestPart
import org.springframework.web.multipart.MultipartFile

@RestController
@RequestMapping("/api/teacher/teaching-classes")
class TeacherTeachingClassController(
    private val currentUserService: CurrentUserService,
    private val teachingClassService: TeacherTeachingClassService,
    private val importService: TeachingClassImportService,
) {
    @GetMapping
    fun list(
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<List<TeachingClassResponse>> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            teachingClassService.listAll(teacher.userId ?: 0),
            "教学班列表加载成功",
        )
    }

    @GetMapping("/{teachingClassId}")
    fun detail(
        @PathVariable teachingClassId: Long,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<TeachingClassResponse> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            teachingClassService.getDetail(teacher.userId ?: 0, teachingClassId),
            "教学班详情加载成功",
        )
    }

    @PostMapping
    fun create(
        @Valid @RequestBody request: TeachingClassSaveRequest,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<TeachingClassResponse> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            teachingClassService.create(teacher.userId ?: 0, request),
            "教学班创建成功",
        )
    }

    @PutMapping("/{teachingClassId}")
    fun update(
        @PathVariable teachingClassId: Long,
        @Valid @RequestBody request: TeachingClassSaveRequest,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<TeachingClassResponse> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            teachingClassService.update(teacher.userId ?: 0, teachingClassId, request),
            "教学班信息已更新",
        )
    }

    @DeleteMapping("/{teachingClassId}")
    fun delete(
        @PathVariable teachingClassId: Long,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<TeachingClassDeleteResult> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        val result = teachingClassService.delete(teacher.userId ?: 0, teachingClassId)
        val kept = if (result.keptStudentCount > 0) {
            "，另有 ${result.keptStudentCount} 名学生因还在其他教学班而保留"
        } else {
            ""
        }
        return ApiResponse.success(result, "教学班已删除，同时删除 ${result.deletedStudentCount} 名学生$kept")
    }

    @GetMapping("/{teachingClassId}/students")
    fun listStudents(
        @PathVariable teachingClassId: Long,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<List<TeachingClassStudentResponse>> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            importService.listStudents(teacher.userId ?: 0, teachingClassId),
            "学生名单加载成功",
        )
    }

    @PostMapping("/{teachingClassId}/students/import/preview")
    fun previewStudentImport(
        @PathVariable teachingClassId: Long,
        @RequestPart("file") file: MultipartFile,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<TeachingClassImportPreview> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            importService.preview(
                teacherId = teacher.userId ?: 0,
                teachingClassId = teachingClassId,
                fileName = file.originalFilename,
                bytes = file.bytes,
            ),
            "名单校验完成，请确认后导入",
        )
    }

    @PostMapping("/{teachingClassId}/students/import/{batchId}/confirm")
    fun confirmStudentImport(
        @PathVariable teachingClassId: Long,
        @PathVariable batchId: String,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<TeachingClassImportConfirmResult> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            importService.confirm(teacher.userId ?: 0, teachingClassId, batchId),
            "学生名单导入完成",
        )
    }

    @DeleteMapping("/{teachingClassId}/students/{studentId}")
    fun removeStudent(
        @PathVariable teachingClassId: Long,
        @PathVariable studentId: Long,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<Unit> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        importService.removeStudent(teacher.userId ?: 0, teachingClassId, studentId)
        return ApiResponse.success(null, "学生已删除，账号和全部学习记录已一并清除")
    }

    @GetMapping("/{teachingClassId}/courses")
    fun listCourses(
        @PathVariable teachingClassId: Long,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<List<TeachingClassCourseResponse>> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            teachingClassService.listCourses(teacher.userId ?: 0, teachingClassId),
            "教学安排加载成功",
        )
    }

    @PutMapping("/{teachingClassId}/courses")
    fun replaceCourses(
        @PathVariable teachingClassId: Long,
        @RequestBody request: TeachingClassCourseUpdateRequest,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<List<TeachingClassCourseResponse>> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            teachingClassService.replaceCourses(teacher.userId ?: 0, teachingClassId, request),
            "教学安排已保存",
        )
    }

    @PatchMapping("/{teachingClassId}/courses/{courseId}/content")
    fun updateCourseContent(
        @PathVariable teachingClassId: Long,
        @PathVariable courseId: Int,
        @Valid @RequestBody request: TeachingClassCourseContentUpdateRequest,
        @RequestParam(required = false) token: String?,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<TeachingClassCourseResponse> {
        val teacher = currentUserService.requireTeacher(token, authorization)
        return ApiResponse.success(
            teachingClassService.updateCourseContent(teacher.userId ?: 0, teachingClassId, courseId, request),
            "教学内容已保存",
        )
    }
}
