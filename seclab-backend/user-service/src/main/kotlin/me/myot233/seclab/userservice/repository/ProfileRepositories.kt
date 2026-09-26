package me.myot233.seclab.userservice.repository

import me.myot233.seclab.userservice.entity.LearningEventEntity
import me.myot233.seclab.userservice.entity.StudentProfileSnapshotEntity
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository

@Repository
interface LearningEventRepository : JpaRepository<LearningEventEntity, Long> {
    fun findByUserId(userId: Long): List<LearningEventEntity>
}

@Repository
interface StudentProfileSnapshotRepository : JpaRepository<StudentProfileSnapshotEntity, Long> {
    fun findByUserId(userId: Long): StudentProfileSnapshotEntity?
}
