package me.myot233.seclab.userservice.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table

@Entity
@Table(name = "`class`")
open class SchoolClassEntity(
    @field:Id
    @field:GeneratedValue(strategy = GenerationType.IDENTITY)
    @field:Column(name = "class_id")
    open var classId: Long? = null,

    @field:Column(name = "class_name", nullable = false)
    open var className: String = "",

    @field:Column(name = "class_detail")
    open var classDetail: String? = null,

    @field:Column(name = "admin_id")
    open var adminId: Long? = null,

    @field:Column(name = "is_end")
    open var isEnd: Int? = 0,
)
