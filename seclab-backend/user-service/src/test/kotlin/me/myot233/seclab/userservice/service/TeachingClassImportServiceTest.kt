package me.myot233.seclab.userservice.service

import com.fasterxml.jackson.databind.ObjectMapper
import me.myot233.seclab.userservice.dto.ImportAccountRow
import me.myot233.seclab.userservice.dto.TeachingClassImportPreview
import me.myot233.seclab.userservice.entity.TeachingClassEntity
import me.myot233.seclab.userservice.entity.TeachingClassImportBatchEntity
import me.myot233.seclab.userservice.entity.TeachingClassImportStatus
import me.myot233.seclab.userservice.repository.SchoolClassRepository
import me.myot233.seclab.userservice.repository.TeachingClassImportBatchRepository
import me.myot233.seclab.userservice.repository.TeachingClassStudentRepository
import me.myot233.seclab.userservice.repository.UserRepository
import org.apache.poi.xssf.usermodel.XSSFWorkbook
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test
import org.mockito.ArgumentMatchers.any
import org.mockito.ArgumentMatchers.anyList
import org.mockito.Mockito.mock
import org.mockito.Mockito.times
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder
import me.myot233.seclab.userservice.exception.ApiException
import java.io.ByteArrayOutputStream
import java.time.LocalDateTime
import java.util.Optional
import java.util.UUID

class TeachingClassImportServiceTest {
    private val teachingClassService = mock(TeacherTeachingClassService::class.java)
    private val userRepository = mock(UserRepository::class.java)
    private val classRepository = mock(SchoolClassRepository::class.java)
    private val studentRepository = mock(TeachingClassStudentRepository::class.java)
    private val batchRepository = mock(TeachingClassImportBatchRepository::class.java)
    private val studentPurgeService = mock(StudentPurgeService::class.java)
    private val objectMapper = ObjectMapper().findAndRegisterModules()
    private val service = TeachingClassImportService(
        teachingClassService,
        userRepository,
        classRepository,
        studentRepository,
        batchRepository,
        PasswordService(BCryptPasswordEncoder(4)),
        studentPurgeService,
        objectMapper,
    )

    @Test
    fun `removing a student deletes the account instead of only unlinking it`() {
        val student = me.myot233.seclab.userservice.entity.UserEntity(
            userId = 55,
            userStudentNumber = "202401050001",
        )
        `when`(teachingClassService.requireOwner(7, 101)).thenReturn(
            TeachingClassEntity(teachingClassId = 101, teacherId = 7),
        )
        `when`(studentRepository.existsByTeachingClassIdAndStudentId(101, 55)).thenReturn(true)
        `when`(userRepository.findById(55)).thenReturn(Optional.of(student))

        service.removeStudent(7, 101, 55)

        verify(studentPurgeService).purgeStudent(student)
    }

    @Test
    fun `removing a student that is not in the class is rejected`() {
        `when`(teachingClassService.requireOwner(7, 101)).thenReturn(
            TeachingClassEntity(teachingClassId = 101, teacherId = 7),
        )
        `when`(studentRepository.existsByTeachingClassIdAndStudentId(101, 55)).thenReturn(false)

        val error = assertThrows(ApiException::class.java) {
            service.removeStudent(7, 101, 55)
        }

        assertEquals(404, error.status)
        // purgeStudent 的入参在 Kotlin 里是非空类型，用 any() 匹配器会先触发空检查，
        // 这里直接断言整个 mock 没被碰过。
        org.mockito.Mockito.verifyNoInteractions(studentPurgeService)
    }

    @Test
    fun `preview classifies new duplicate and invalid rows without writing users`() {
        `when`(teachingClassService.requireOwner(7, 101)).thenReturn(
            TeachingClassEntity(teachingClassId = 101, teacherId = 7),
        )
        `when`(userRepository.findAllByUserStudentNumberIn(anyList())).thenReturn(emptyList())
        `when`(batchRepository.save(any(TeachingClassImportBatchEntity::class.java))).thenAnswer { it.arguments[0] }

        val preview = service.preview(
            teacherId = 7,
            teachingClassId = 101,
            fileName = "学生名单.xlsx",
            bytes = workbookBytes(
                listOf("20260001", "张晨", "网安232班"),
                listOf("20260001", "张晨", "网安232班"),
                listOf("bad-number-too-long", "", "网安232班"),
            ),
        )

        assertEquals(1, preview.newAccounts.size)
        assertEquals(1, preview.duplicateRows.size)
        assertEquals(1, preview.errorRows.size)
        verify(userRepository, times(0)).saveAll<me.myot233.seclab.userservice.entity.UserEntity>(any())
    }

    @Test
    fun `confirming one batch twice returns stored result without creating users twice`() {
        val batchId = UUID.randomUUID().toString()
        val preview = TeachingClassImportPreview(
            batchId = batchId,
            newAccounts = listOf(ImportAccountRow(2, "20260001", "张晨", "网安232班")),
            existingAccounts = emptyList(),
            duplicateRows = emptyList(),
            errorRows = emptyList(),
            expiresAt = LocalDateTime.now().plusMinutes(30),
        )
        val batch = TeachingClassImportBatchEntity(
            importBatchId = batchId,
            teachingClassId = 101,
            teacherId = 7,
            previewJson = objectMapper.writeValueAsString(preview),
            status = TeachingClassImportStatus.PREVIEWED,
            expiresAt = preview.expiresAt,
        )
        `when`(teachingClassService.requireOwner(7, 101)).thenReturn(
            TeachingClassEntity(teachingClassId = 101, teacherId = 7),
        )
        `when`(batchRepository.findLockedByImportBatchId(batchId)).thenReturn(Optional.of(batch))
        `when`(userRepository.findAllByUserStudentNumberIn(listOf("20260001"))).thenReturn(emptyList())
        `when`(classRepository.findFirstByClassName("网安232班")).thenReturn(null)
        `when`(classRepository.save(any())).thenAnswer { invocation ->
            invocation.getArgument<me.myot233.seclab.userservice.entity.SchoolClassEntity>(0).apply { classId = 5 }
        }
        `when`(userRepository.saveAll(anyList())).thenAnswer { invocation ->
            invocation.getArgument<List<me.myot233.seclab.userservice.entity.UserEntity>>(0)
                .onEachIndexed { index, user -> user.userId = 100L + index }
        }
        `when`(studentRepository.existsByTeachingClassIdAndStudentId(101, 100)).thenReturn(false)

        val first = service.confirm(7, 101, batchId)
        val second = service.confirm(7, 101, batchId)

        assertEquals(first, second)
        verify(userRepository, times(1)).saveAll(anyList())
    }

    @Test
    fun `teacher cannot list students from another teachers class`() {
        `when`(teachingClassService.requireOwner(7, 102)).thenThrow(ApiException(403, "forbidden"))

        val error = assertThrows(ApiException::class.java) {
            service.listStudents(7, 102)
        }

        assertEquals(403, error.status)
    }

    private fun workbookBytes(vararg rows: List<String>): ByteArray {
        val workbook = XSSFWorkbook()
        val sheet = workbook.createSheet("学生名单")
        val header = sheet.createRow(0)
        listOf("学号", "姓名", "行政班").forEachIndexed { index, value ->
            header.createCell(index).setCellValue(value)
        }
        rows.forEachIndexed { rowIndex, values ->
            val row = sheet.createRow(rowIndex + 1)
            values.forEachIndexed { columnIndex, value -> row.createCell(columnIndex).setCellValue(value) }
        }
        return ByteArrayOutputStream().use { output ->
            workbook.use { it.write(output) }
            output.toByteArray()
        }
    }
}
