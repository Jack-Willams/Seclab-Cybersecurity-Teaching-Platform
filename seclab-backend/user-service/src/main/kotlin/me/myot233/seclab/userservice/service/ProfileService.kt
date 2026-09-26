package me.myot233.seclab.userservice.service

import me.myot233.seclab.userservice.entity.LearningEventEntity
import me.myot233.seclab.userservice.entity.StudentProfileSnapshotEntity
import me.myot233.seclab.userservice.repository.LearningEventRepository
import me.myot233.seclab.userservice.repository.StudentProfileSnapshotRepository
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.LocalDateTime

@Service
class ProfileService(
    private val eventRepository: LearningEventRepository,
    private val snapshotRepository: StudentProfileSnapshotRepository
) {

    @Transactional
    fun saveEvent(eventMap: Map<String, Any>, userId: Long) {
        val event = LearningEventEntity(
            userId = userId,
            eventType = eventMap["eventType"] as? String,
            occurredAt = LocalDateTime.now(),
            createdAt = LocalDateTime.now()
        )
        // just minimum
        eventRepository.save(event)
    }

    @Transactional
    fun recalculateStudentProfile(userId: Long): StudentProfileSnapshotEntity {
        val events = eventRepository.findByUserId(userId)
        val snapshot = snapshotRepository.findByUserId(userId) ?: StudentProfileSnapshotEntity(userId = userId)

        // MVP math
        val knowledgeMastery = events.count { it.eventType == "FLAG_SUBMIT" || it.eventType == "QUESTION_SUBMIT" } * 20.0
        val aiCollaboration = events.count { it.eventType == "AI_ASK" } * 10.0
        val engagement = events.size * 5.0
        val exploration = events.count { it.eventType == "LAB_START" } * 15.0

        snapshot.overallScore = (knowledgeMastery + aiCollaboration + engagement + exploration) / 4.0
        snapshot.knowledgeMastery = knowledgeMastery
        snapshot.aiCollaboration = aiCollaboration
        snapshot.engagement = engagement
        snapshot.exploration = exploration
        snapshot.updatedAt = LocalDateTime.now()

        return snapshotRepository.save(snapshot)
    }

    fun getProfile(userId: Long): StudentProfileSnapshotEntity? {
        return snapshotRepository.findByUserId(userId) ?: recalculateStudentProfile(userId)
    }
}
