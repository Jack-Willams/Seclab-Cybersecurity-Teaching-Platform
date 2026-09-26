package me.myot233.seclab.userservice.entity

import jakarta.persistence.*
import java.time.LocalDateTime

@Entity
@Table(name = "learning_event")
data class LearningEventEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,

    @Column(name = "user_id")
    var userId: Long? = null,

    @Column(name = "event_type")
    var eventType: String? = null,

    @Column(name = "course_id")
    var courseId: Long? = null,

    @Column(name = "module_id")
    var moduleId: Long? = null,

    @Column(name = "lab_id")
    var labId: Long? = null,

    @Column(name = "question_id")
    var questionId: Long? = null,

    @Column(name = "success")
    var success: Boolean? = null,

    @Column(name = "score")
    var score: Int? = null,

    @Column(name = "duration_seconds")
    var durationSeconds: Int? = null,

    @Column(name = "command")
    var command: String? = null,

    @Column(name = "error_message")
    var errorMessage: String? = null,

    @Column(name = "ai_message")
    var aiMessage: String? = null,

    @Column(name = "metadata", columnDefinition = "JSON")
    var metadata: String? = null,

    @Column(name = "occurred_at")
    var occurredAt: LocalDateTime? = null,

    @Column(name = "created_at")
    var createdAt: LocalDateTime? = null
)
