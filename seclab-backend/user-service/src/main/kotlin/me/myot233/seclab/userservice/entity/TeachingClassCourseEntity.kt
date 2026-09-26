package me.myot233.seclab.userservice.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table
import java.time.LocalDate
import java.time.LocalDateTime

@Entity
@Table(name = "teaching_class_course")
open class TeachingClassCourseEntity(
    @field:Id
    @field:GeneratedValue(strategy = GenerationType.IDENTITY)
    @field:Column(name = "teaching_class_course_id")
    open var teachingClassCourseId: Long? = null,

    @field:Column(name = "teaching_class_id", nullable = false)
    open var teachingClassId: Long = 0,

    @field:Column(name = "course_id", nullable = false)
    open var courseId: Int = 0,

    @field:Column(name = "teaching_order", nullable = false)
    open var teachingOrder: Int = 1,

    @field:Column(name = "planned_start_date")
    open var plannedStartDate: LocalDate? = null,

    @field:Column(name = "planned_end_date")
    open var plannedEndDate: LocalDate? = null,

    @field:Column(name = "teaching_content", columnDefinition = "TEXT")
    open var teachingContent: String? = null,

    @field:Column(name = "created_at", nullable = false)
    open var createdAt: LocalDateTime = LocalDateTime.now(),

    @field:Column(name = "updated_at", nullable = false)
    open var updatedAt: LocalDateTime = LocalDateTime.now(),
)
