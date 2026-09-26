package me.myot233.seclab.userservice.repository

import me.myot233.seclab.userservice.entity.SchoolClassEntity
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository

@Repository
interface SchoolClassRepository : JpaRepository<SchoolClassEntity, Long> {
    fun findFirstByClassName(className: String): SchoolClassEntity?

    fun existsByAdminId(adminId: Long): Boolean
}
