package me.myot233.seclab.userservice.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.FetchType
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.ManyToOne
import jakarta.persistence.PrePersist
import jakarta.persistence.PreUpdate
import jakarta.persistence.Table
import java.time.LocalDate
import java.time.LocalDateTime

enum class TeachingClassStatus {
    ACTIVE,
    ARCHIVED,
}

@Entity
@Table(name = "teaching_class")
open class TeachingClassEntity(
    @field:Id
    @field:GeneratedValue(strategy = GenerationType.IDENTITY)
    @field:Column(name = "teaching_class_id")
    open var teachingClassId: Long? = null,

    @field:Column(name = "class_name", nullable = false, length = 120)
    open var className: String = "",

    @field:Column(name = "academic_year", nullable = false, length = 9)
    open var academicYear: String = "",

    @field:Column(name = "semester", nullable = false)
    open var semester: Int = 1,

    @field:Column(name = "teacher_id", nullable = false)
    open var teacherId: Long = 0,

    @field:ManyToOne(fetch = FetchType.LAZY)
    @field:JoinColumn(name = "teacher_id", insertable = false, updatable = false)
    open var teacher: UserEntity? = null,

    @field:Column(name = "start_date")
    open var startDate: LocalDate? = null,

    @field:Column(name = "end_date")
    open var endDate: LocalDate? = null,

    @field:Enumerated(EnumType.STRING)
    @field:Column(name = "status", nullable = false, length = 16)
    open var status: TeachingClassStatus = TeachingClassStatus.ACTIVE,

    @field:Column(name = "created_at", nullable = false)
    open var createdAt: LocalDateTime = LocalDateTime.now(),

    @field:Column(name = "updated_at", nullable = false)
    open var updatedAt: LocalDateTime = LocalDateTime.now(),
) {
    @PrePersist
    fun prePersist() {
        val now = LocalDateTime.now()
        createdAt = now
        updatedAt = now
    }

    @PreUpdate
    fun preUpdate() {
        updatedAt = LocalDateTime.now()
    }
}
