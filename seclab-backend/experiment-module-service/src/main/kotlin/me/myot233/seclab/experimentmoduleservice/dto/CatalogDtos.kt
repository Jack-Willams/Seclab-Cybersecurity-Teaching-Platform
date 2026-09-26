package me.myot233.seclab.experimentmoduleservice.dto

data class CourseSummaryDto(
    val id: Int,
    val name: String,
    val description: String,
    val difficulty: Int,
    val imageUrl: String,
    val type: String,
    val tags: List<String>,
    val status: String,
    val courseId: Int = id,
    val courseName: String = name,
    val courseDescription: String = description,
    val courseImage: String = imageUrl,
    val teacherName: String? = null,
    val category: String? = type,
    val createTime: String? = null,
    val createdBy: Long? = null,
    val creatorEditable: Boolean = createdBy != null,
)

data class ModuleOverviewDto(
    val id: Int,
    val name: String,
    val description: String,
    val difficulty: Int,
    val type: String,
    val status: String,
    val estimatedTime: String,
    val score: Int,
    val prerequisites: List<Int> = emptyList(),
    val moduleId: Int = id,
    val moduleName: String = name,
    val moduleDescription: String = description,
    val courseId: Int? = null,
    val courseIds: List<Int> = emptyList(),
    val image: String? = null,
)

data class CourseMutationRequest(
    val courseName: String,
    val courseDescription: String,
    val difficulty: Int? = null,
    val imageUrl: String? = null,
    val teacherName: String? = null,
    val category: String? = null,
    val tags: List<String> = emptyList(),
    val status: String? = null,
)

data class ModuleMutationRequest(
    val moduleName: String,
    val moduleDescription: String,
    val difficulty: Int? = null,
    val type: String? = null,
    val image: String? = null,
)
