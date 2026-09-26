package me.myot233.seclab.userservice.entity

import jakarta.persistence.*
import java.time.LocalDateTime

@Entity
@Table(name = "student_profile_snapshot")
data class StudentProfileSnapshotEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,

    @Column(name = "user_id")
    var userId: Long? = null,

    @Column(name = "overall_score")
    var overallScore: Double? = null,

    @Column(name = "knowledge_mastery")
    var knowledgeMastery: Double? = null,

    @Column(name = "troubleshooting")
    var troubleshooting: Double? = null,

    @Column(name = "exploration")
    var exploration: Double? = null,

    @Column(name = "ai_collaboration")
    var aiCollaboration: Double? = null,

    @Column(name = "engagement")
    var engagement: Double? = null,

    @Column(name = "badges", columnDefinition = "JSON")
    var badges: String? = null,

    @Column(name = "weaknesses", columnDefinition = "JSON")
    var weaknesses: String? = null,

    @Column(name = "recommendations", columnDefinition = "JSON")
    var recommendations: String? = null,

    @Column(name = "summary")
    var summary: String? = null,

    @Column(name = "evidence", columnDefinition = "JSON")
    var evidence: String? = null,

    @Column(name = "updated_at")
    var updatedAt: LocalDateTime? = null,

    @Column(name = "created_at")
    var createdAt: LocalDateTime? = null
)
