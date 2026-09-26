package me.myot233.seclab.userservice.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.IdClass
import jakarta.persistence.Table
import java.io.Serializable
import java.time.LocalDateTime

data class TeachingClassStudentId(
    var teachingClassId: Long = 0,
    var studentId: Long = 0,
) : Serializable

@Entity
@Table(name = "teaching_class_student")
@IdClass(TeachingClassStudentId::class)
open class TeachingClassStudentEntity(
    @field:Id
    @field:Column(name = "teaching_class_id")
    open var teachingClassId: Long = 0,

    @field:Id
    @field:Column(name = "student_id")
    open var studentId: Long = 0,

    @field:Column(name = "source", nullable = false, length = 24)
    open var source: String = "EXCEL_IMPORT",

    @field:Column(name = "joined_at", nullable = false)
    open var joinedAt: LocalDateTime = LocalDateTime.now(),
)
