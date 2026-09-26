package me.myot233.seclab.experimentmoduleservice.controller

import me.myot233.seclab.experimentmoduleservice.dto.ApiResponse
import me.myot233.seclab.experimentmoduleservice.dto.CourseMutationRequest
import me.myot233.seclab.experimentmoduleservice.dto.CourseSummaryDto
import me.myot233.seclab.experimentmoduleservice.dto.ModuleOverviewDto
import me.myot233.seclab.experimentmoduleservice.service.CatalogAuthService
import me.myot233.seclab.experimentmoduleservice.service.CatalogQueryService
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestHeader
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/course")
class CourseController(
    private val catalogQueryService: CatalogQueryService,
    private val catalogAuthService: CatalogAuthService,
) {
    @GetMapping("/overview-list")
    fun overviewList(): ApiResponse<List<CourseSummaryDto>> =
        ApiResponse.success(catalogQueryService.listCourses())

    @GetMapping("/{id}")
    fun detail(@PathVariable id: Int): ApiResponse<CourseSummaryDto> =
        ApiResponse.success(catalogQueryService.getCourse(id))

    @PostMapping
    fun create(
        @RequestBody request: CourseMutationRequest,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<CourseSummaryDto> {
        val currentUser = catalogAuthService.requireTeacherOrAdmin(authorization)
        return ApiResponse.success(catalogQueryService.createCourse(currentUser.userId, request), "课程创建成功")
    }

    @PutMapping("/{id}")
    fun update(
        @PathVariable id: Int,
        @RequestBody request: CourseMutationRequest,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<CourseSummaryDto> {
        val currentUser = catalogAuthService.requireTeacherOrAdmin(authorization)
        return ApiResponse.success(catalogQueryService.updateCourse(currentUser.userId, id, request), "课程更新成功")
    }

    @DeleteMapping("/{id}")
    fun delete(
        @PathVariable id: Int,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<Unit> {
        val currentUser = catalogAuthService.requireTeacherOrAdmin(authorization)
        catalogQueryService.deleteCourse(currentUser.userId, id)
        return ApiResponse.success(Unit, "课程删除成功")
    }

    @GetMapping("/{courseId}/modules")
    fun listCourseModules(@PathVariable courseId: Int): ApiResponse<List<ModuleOverviewDto>> =
        ApiResponse.success(catalogQueryService.listCourseModules(courseId))

    @PostMapping("/{courseId}/modules/{moduleId}")
    fun addCourseModule(
        @PathVariable courseId: Int,
        @PathVariable moduleId: Int,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<List<ModuleOverviewDto>> {
        val currentUser = catalogAuthService.requireTeacherOrAdmin(authorization)
        return ApiResponse.success(
            catalogQueryService.addModuleToCourse(currentUser.userId, courseId, moduleId),
            "实验已添加到课程",
        )
    }

    @DeleteMapping("/{courseId}/modules/{moduleId}")
    fun removeCourseModule(
        @PathVariable courseId: Int,
        @PathVariable moduleId: Int,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<List<ModuleOverviewDto>> {
        val currentUser = catalogAuthService.requireTeacherOrAdmin(authorization)
        return ApiResponse.success(
            catalogQueryService.removeModuleFromCourse(currentUser.userId, courseId, moduleId),
            "实验已从课程移除",
        )
    }
}
