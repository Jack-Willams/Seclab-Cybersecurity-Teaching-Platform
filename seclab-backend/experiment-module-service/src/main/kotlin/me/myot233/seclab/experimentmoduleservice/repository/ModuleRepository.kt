package me.myot233.seclab.experimentmoduleservice.repository

import me.myot233.seclab.experimentmoduleservice.entity.ModuleEntity
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param

interface ModuleRepository : JpaRepository<ModuleEntity, Int> {
    @Query("select coalesce(max(m.moduleId), 0) from ModuleEntity m")
    fun findMaxId(): Int

    @Query(
        value = """
            SELECT m.*
            FROM module m
            INNER JOIN module_course mc ON mc.module_id = m.module_id
            WHERE mc.course_id = :courseId
            ORDER BY m.module_id ASC
        """,
        nativeQuery = true,
    )
    fun findByCourseId(@Param("courseId") courseId: Int): List<ModuleEntity>
}
