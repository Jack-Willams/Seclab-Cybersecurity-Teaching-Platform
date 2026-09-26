package me.myot233.seclab.experimentmoduleservice.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.Table

@Entity
@Table(name = "course")
class CourseEntity(
    @field:Id
    @field:Column(name = "id")
    val id: Int = 0,
    @field:Column(name = "course_name", nullable = false)
    val courseName: String = "",
    @field:Column(name = "course_description", nullable = false)
    val courseDescription: String = "",
    @field:Column(name = "difficulty")
    val difficulty: Int? = null,
    @field:Column(name = "image_url")
    val imageUrl: String? = null,
    @field:Column(name = "instructor")
    val instructor: String? = null,
    @field:Column(name = "created_by")
    val createdBy: Long? = null,
    @field:Column(name = "course_status")
    val courseStatus: Int? = null,
    @field:Column(name = "tags")
    val tags: String? = null,
    @field:Column(name = "type")
    val type: String? = null,
)
