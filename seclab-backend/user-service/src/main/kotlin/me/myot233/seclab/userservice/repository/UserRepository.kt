package me.myot233.seclab.userservice.repository

import me.myot233.seclab.userservice.entity.UserEntity
import org.springframework.data.domain.Page
import org.springframework.data.domain.Pageable
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.EntityGraph
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param
import org.springframework.stereotype.Repository

@Repository
interface UserRepository : JpaRepository<UserEntity, Long> {
    fun existsByUserStudentNumber(userStudentNumber: String): Boolean
    fun existsByUserStudentNumberAndUserIdNot(userStudentNumber: String, userId: Long): Boolean

    fun findByUserStudentNumber(userStudentNumber: String): UserEntity?
    fun findAllByUserStudentNumberIn(userStudentNumbers: Collection<String>): List<UserEntity>

    @Query(
        """
            SELECT DISTINCT u.userAcademy
            FROM UserEntity u
            WHERE (u.isAdmin = false OR u.isAdmin IS NULL)
              AND u.userAcademy IS NOT NULL
              AND u.userAcademy <> ''
            ORDER BY u.userAcademy
        """,
    )
    fun findDistinctStudentAcademies(): List<String>

    @Query(
        """
            SELECT DISTINCT c.className
            FROM UserEntity u
            JOIN u.classInfo c
            WHERE (u.isAdmin = false OR u.isAdmin IS NULL)
              AND c.className <> ''
            ORDER BY c.className
        """,
    )
    fun findDistinctStudentClassNames(): List<String>

    @EntityGraph(attributePaths = ["classInfo"])
    @Query(
        value = """
            SELECT u
            FROM UserEntity u
            LEFT JOIN u.classInfo c
            WHERE (u.isAdmin = false OR u.isAdmin IS NULL)
              AND NOT EXISTS (
                    SELECT managed.classId
                    FROM SchoolClassEntity managed
                    WHERE managed.adminId = u.userId
                      AND COALESCE(managed.isEnd, 0) = 0
                  )
              AND (
                    :keyword IS NULL
                    OR u.userStudentNumber LIKE CONCAT('%', :keyword, '%')
                    OR COALESCE(u.userName, '') LIKE CONCAT('%', :keyword, '%')
                    OR COALESCE(u.userEmail, '') LIKE CONCAT('%', :keyword, '%')
                    OR COALESCE(u.userTel, '') LIKE CONCAT('%', :keyword, '%')
                  )
              AND (:academy IS NULL OR COALESCE(u.userAcademy, '') = :academy)
              AND (:className IS NULL OR COALESCE(c.className, '') = :className)
              AND (:classId IS NULL OR c.classId = :classId)
              AND (:deletedFlag IS NULL OR COALESCE(u.isDeleted, 0) = :deletedFlag)
              AND (:gender IS NULL OR u.userGender = :gender)
        """,
        countQuery = """
            SELECT COUNT(u)
            FROM UserEntity u
            LEFT JOIN u.classInfo c
            WHERE (u.isAdmin = false OR u.isAdmin IS NULL)
              AND NOT EXISTS (
                    SELECT managed.classId
                    FROM SchoolClassEntity managed
                    WHERE managed.adminId = u.userId
                      AND COALESCE(managed.isEnd, 0) = 0
                  )
              AND (
                    :keyword IS NULL
                    OR u.userStudentNumber LIKE CONCAT('%', :keyword, '%')
                    OR COALESCE(u.userName, '') LIKE CONCAT('%', :keyword, '%')
                    OR COALESCE(u.userEmail, '') LIKE CONCAT('%', :keyword, '%')
                    OR COALESCE(u.userTel, '') LIKE CONCAT('%', :keyword, '%')
                  )
              AND (:academy IS NULL OR COALESCE(u.userAcademy, '') = :academy)
              AND (:className IS NULL OR COALESCE(c.className, '') = :className)
              AND (:classId IS NULL OR c.classId = :classId)
              AND (:deletedFlag IS NULL OR COALESCE(u.isDeleted, 0) = :deletedFlag)
              AND (:gender IS NULL OR u.userGender = :gender)
        """,
    )
    fun searchStudentsForAdmin(
        @Param("keyword") keyword: String?,
        @Param("academy") academy: String?,
        @Param("className") className: String?,
        @Param("classId") classId: Long?,
        @Param("deletedFlag") deletedFlag: Int?,
        @Param("gender") gender: Int?,
        pageable: Pageable,
    ): Page<UserEntity>
}
