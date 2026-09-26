package me.myot233.seclab.experimentmoduleservice.controller

import me.myot233.seclab.experimentmoduleservice.dto.ApiResponse
import me.myot233.seclab.experimentmoduleservice.dto.ModuleMutationRequest
import me.myot233.seclab.experimentmoduleservice.dto.ModuleOverviewDto
import me.myot233.seclab.experimentmoduleservice.service.CatalogAuthService
import me.myot233.seclab.experimentmoduleservice.service.CatalogQueryService
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestHeader
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/stu/module")
class ModuleController(
    private val catalogQueryService: CatalogQueryService,
    private val catalogAuthService: CatalogAuthService,
) {
    @GetMapping("/modules")
    fun listModules(): ApiResponse<List<ModuleOverviewDto>> =
        ApiResponse.success(catalogQueryService.listModules())

    @PostMapping("/modules")
    fun listModulesByPost(): ApiResponse<List<ModuleOverviewDto>> =
        ApiResponse.success(catalogQueryService.listModules())

    @PostMapping
    fun createModule(
        @RequestBody request: ModuleMutationRequest,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<ModuleOverviewDto> {
        catalogAuthService.requireTeacherOrAdmin(authorization)
        return ApiResponse.success(catalogQueryService.createModule(request), "实验创建成功")
    }

    @PutMapping("/{id}")
    fun updateModule(
        @PathVariable id: Int,
        @RequestBody request: ModuleMutationRequest,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<ModuleOverviewDto> {
        catalogAuthService.requireTeacherOrAdmin(authorization)
        return ApiResponse.success(catalogQueryService.updateModule(id, request), "实验更新成功")
    }

    @DeleteMapping("/{id}")
    fun deleteModule(
        @PathVariable id: Int,
        @RequestHeader(name = "Authorization", required = false) authorization: String?,
    ): ApiResponse<Unit> {
        catalogAuthService.requireTeacherOrAdmin(authorization)
        catalogQueryService.deleteModule(id)
        return ApiResponse.success(Unit, "实验删除成功")
    }
}
