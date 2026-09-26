package me.myot233.seclab.userservice.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.Id
import jakarta.persistence.Table
import java.time.LocalDateTime

enum class TeachingClassImportStatus {
    PREVIEWED,
    CONFIRMED,
    EXPIRED,
}

@Entity
@Table(name = "teaching_class_import_batch")
open class TeachingClassImportBatchEntity(
    @field:Id
    @field:Column(name = "import_batch_id", length = 36)
    open var importBatchId: String = "",

    @field:Column(name = "teaching_class_id", nullable = false)
    open var teachingClassId: Long = 0,

    @field:Column(name = "teacher_id", nullable = false)
    open var teacherId: Long = 0,

    @field:Column(name = "file_sha256", nullable = false, length = 64)
    open var fileSha256: String = "",

    @field:Column(name = "preview_json", nullable = false, columnDefinition = "json")
    open var previewJson: String = "{}",

    @field:Column(name = "confirmed_result_json", columnDefinition = "json")
    open var confirmedResultJson: String? = null,

    @field:Enumerated(EnumType.STRING)
    @field:Column(name = "status", nullable = false, length = 16)
    open var status: TeachingClassImportStatus = TeachingClassImportStatus.PREVIEWED,

    @field:Column(name = "expires_at", nullable = false)
    open var expiresAt: LocalDateTime = LocalDateTime.now().plusMinutes(30),

    @field:Column(name = "created_at", nullable = false)
    open var createdAt: LocalDateTime = LocalDateTime.now(),

    @field:Column(name = "confirmed_at")
    open var confirmedAt: LocalDateTime? = null,
)
