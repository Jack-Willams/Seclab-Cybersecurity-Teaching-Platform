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
import jakarta.persistence.Table
import java.time.LocalDateTime

@Entity
@Table(name = "`user`")
open class UserEntity(
    @field:Id
    @field:GeneratedValue(strategy = GenerationType.IDENTITY)
    @field:Column(name = "user_id")
    open var userId: Long? = null,

    @field:Column(name = "user_student_number", nullable = false, length = 13)
    open var userStudentNumber: String = "",

    @field:Column(name = "user_password", nullable = false)
    open var userPassword: String = "",

    @field:Column(name = "user_tel", length = 11)
    open var userTel: String? = null,

    @field:Column(name = "user_image")
    open var userImage: String? = null,

    @field:Column(name = "user_name")
    open var userName: String? = null,

    @field:Column(name = "user_academy")
    open var userAcademy: String? = null,

    @field:Column(name = "user_email")
    open var userEmail: String? = null,

    @field:Column(name = "user_gender")
    open var userGender: Int? = 2,

    @field:ManyToOne(fetch = FetchType.LAZY)
    @field:JoinColumn(name = "class_id_class_id")
    open var classInfo: SchoolClassEntity? = null,

    @field:Column(name = "is_admin")
    open var isAdmin: Boolean? = false,

    @field:Enumerated(EnumType.STRING)
    @field:Column(name = "user_role", nullable = false, length = 16)
    open var userRole: UserRole = UserRole.STUDENT,

    @field:Column(name = "is_deleted")
    open var isDeleted: Int? = 0,

    @field:Column(name = "create_time")
    open var createTime: LocalDateTime? = null,
) {
    @PrePersist
    fun prePersist() {
        if (createTime == null) {
            createTime = LocalDateTime.now()
        }
        if (isDeleted == null) {
            isDeleted = 0
        }
        if (isAdmin == null) {
            isAdmin = false
        }
    }
}
