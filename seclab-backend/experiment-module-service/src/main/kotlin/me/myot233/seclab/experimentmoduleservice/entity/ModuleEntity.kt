package me.myot233.seclab.experimentmoduleservice.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.Table

@Entity
@Table(name = "module")
class ModuleEntity(
    @field:Id
    @field:Column(name = "module_id")
    val moduleId: Int = 0,
    @field:Column(name = "module_name")
    val moduleName: String? = null,
    @field:Column(name = "introduction")
    val introduction: String? = null,
    @field:Column(name = "difficulty")
    val difficulty: Int? = null,
    @field:Column(name = "image_id")
    val imageId: Int? = null,
    @field:Column(name = "type")
    val type: String? = null,
)
