package me.myot233.seclab.userservice.service

import com.fasterxml.jackson.databind.ObjectMapper
import me.myot233.seclab.userservice.dto.ImportAccountRow
import me.myot233.seclab.userservice.dto.ImportDuplicateRow
import me.myot233.seclab.userservice.dto.ImportErrorRow
import me.myot233.seclab.userservice.dto.TeachingClassImportConfirmResult
import me.myot233.seclab.userservice.dto.TeachingClassImportPreview
import me.myot233.seclab.userservice.dto.TeachingClassStudentResponse
import me.myot233.seclab.userservice.entity.SchoolClassEntity
import me.myot233.seclab.userservice.entity.TeachingClassImportBatchEntity
import me.myot233.seclab.userservice.entity.TeachingClassImportStatus
import me.myot233.seclab.userservice.entity.TeachingClassStudentEntity
import me.myot233.seclab.userservice.entity.UserEntity
import me.myot233.seclab.userservice.entity.UserRole
import me.myot233.seclab.userservice.exception.ApiException
import me.myot233.seclab.userservice.repository.SchoolClassRepository
import me.myot233.seclab.userservice.repository.TeachingClassImportBatchRepository
import me.myot233.seclab.userservice.repository.TeachingClassStudentRepository
import me.myot233.seclab.userservice.repository.UserRepository
import org.apache.poi.ss.usermodel.CellType
import org.apache.poi.ss.usermodel.DataFormatter
import org.apache.poi.xssf.usermodel.XSSFWorkbook
import org.slf4j.LoggerFactory
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.io.ByteArrayInputStream
import java.security.MessageDigest
import java.time.LocalDateTime
import java.util.Locale
import java.util.UUID

@Service
class TeachingClassImportService(
    private val teachingClassService: TeacherTeachingClassService,
    private val userRepository: UserRepository,
    private val classRepository: SchoolClassRepository,
    private val studentRepository: TeachingClassStudentRepository,
    private val batchRepository: TeachingClassImportBatchRepository,
    private val passwordService: PasswordService,
    private val studentPurgeService: StudentPurgeService,
    private val objectMapper: ObjectMapper,
) {
    @Transactional
    fun preview(
        teacherId: Long,
        teachingClassId: Long,
        fileName: String?,
        bytes: ByteArray,
    ): TeachingClassImportPreview {
        teachingClassService.requireOwner(teacherId, teachingClassId)
        validateFile(fileName, bytes)
        val parsed = parseWorkbook(bytes)
        val existingNumbers = userRepository
            .findAllByUserStudentNumberIn(parsed.validRows.map { it.studentNumber })
            .map { it.userStudentNumber }
            .toHashSet()
        val expiresAt = LocalDateTime.now().plusMinutes(PREVIEW_TTL_MINUTES)
        val result = TeachingClassImportPreview(
            batchId = UUID.randomUUID().toString(),
            newAccounts = parsed.validRows.filterNot { it.studentNumber in existingNumbers },
            existingAccounts = parsed.validRows.filter { it.studentNumber in existingNumbers },
            duplicateRows = parsed.duplicateRows,
            errorRows = parsed.errorRows,
            expiresAt = expiresAt,
        )
        batchRepository.save(
            TeachingClassImportBatchEntity(
                importBatchId = result.batchId,
                teachingClassId = teachingClassId,
                teacherId = teacherId,
                fileSha256 = sha256(bytes),
                previewJson = objectMapper.writeValueAsString(result),
                status = TeachingClassImportStatus.PREVIEWED,
                expiresAt = expiresAt,
            ),
        )
        log.info(
            "teacher={} previewed student import batch={} teachingClass={} valid={} errors={}",
            teacherId,
            result.batchId,
            teachingClassId,
            result.newAccounts.size + result.existingAccounts.size,
            result.errorRows.size,
        )
        return result
    }

    @Transactional
    fun confirm(
        teacherId: Long,
        teachingClassId: Long,
        batchId: String,
    ): TeachingClassImportConfirmResult {
        teachingClassService.requireOwner(teacherId, teachingClassId)
        val batch = batchRepository.findLockedByImportBatchId(batchId).orElseThrow {
            ApiException(404, "导入批次不存在", HttpStatus.NOT_FOUND)
        }
        if (batch.teacherId != teacherId || batch.teachingClassId != teachingClassId) {
            throw ApiException(403, "该导入批次不属于当前教学班", HttpStatus.FORBIDDEN)
        }
        if (batch.status == TeachingClassImportStatus.CONFIRMED) {
            val stored = batch.confirmedResultJson
                ?: throw ApiException(500, "已确认批次缺少结果", HttpStatus.INTERNAL_SERVER_ERROR)
            return objectMapper.readValue(stored, TeachingClassImportConfirmResult::class.java)
        }
        if (batch.status == TeachingClassImportStatus.EXPIRED || LocalDateTime.now().isAfter(batch.expiresAt)) {
            throw ApiException(409, "导入预览已过期，请重新上传", HttpStatus.CONFLICT)
        }

        val preview = objectMapper.readValue(batch.previewJson, TeachingClassImportPreview::class.java)
        val rows = preview.newAccounts + preview.existingAccounts
        val accountByNumber = userRepository
            .findAllByUserStudentNumberIn(rows.map { it.studentNumber })
            .associateBy { it.userStudentNumber }
            .toMutableMap()

        val classCache = mutableMapOf<String, SchoolClassEntity>()
        val createdAccounts = rows.filterNot { it.studentNumber in accountByNumber }.map { row ->
            val administrativeClass = classCache.getOrPut(row.administrativeClass) {
                classRepository.findFirstByClassName(row.administrativeClass)
                    ?: classRepository.save(
                        SchoolClassEntity(
                            className = row.administrativeClass,
                            classDetail = "由教学班名单导入自动创建",
                            isEnd = 0,
                        ),
                    )
            }
            UserEntity(
                userStudentNumber = row.studentNumber,
                userPassword = passwordService.encode(DEFAULT_INITIAL_PASSWORD),
                userName = row.studentName,
                classInfo = administrativeClass,
                isAdmin = false,
                userRole = UserRole.STUDENT,
                isDeleted = 0,
            )
        }
        if (createdAccounts.isNotEmpty()) {
            userRepository.saveAll(createdAccounts).forEach { user ->
                accountByNumber[user.userStudentNumber] = user
            }
        }

        var skippedCount = 0
        val newMemberships = rows.mapNotNull { row ->
            val student = accountByNumber[row.studentNumber]
                ?: throw ApiException(500, "学生账号创建失败", HttpStatus.INTERNAL_SERVER_ERROR)
            val studentId = student.userId
                ?: throw ApiException(500, "学生账号缺少ID", HttpStatus.INTERNAL_SERVER_ERROR)
            if (studentRepository.existsByTeachingClassIdAndStudentId(teachingClassId, studentId)) {
                skippedCount += 1
                null
            } else {
                TeachingClassStudentEntity(
                    teachingClassId = teachingClassId,
                    studentId = studentId,
                    source = "EXCEL_IMPORT",
                )
            }
        }
        if (newMemberships.isNotEmpty()) {
            studentRepository.saveAll(newMemberships)
        }

        val result = TeachingClassImportConfirmResult(
            createdAccountCount = createdAccounts.size,
            addedMemberCount = newMemberships.size,
            skippedMemberCount = skippedCount,
        )
        batch.status = TeachingClassImportStatus.CONFIRMED
        batch.confirmedResultJson = objectMapper.writeValueAsString(result)
        batch.confirmedAt = LocalDateTime.now()
        batchRepository.save(batch)
        log.info(
            "teacher={} confirmed import batch={} teachingClass={} created={} added={} skipped={}",
            teacherId,
            batchId,
            teachingClassId,
            result.createdAccountCount,
            result.addedMemberCount,
            result.skippedMemberCount,
        )
        return result
    }

    @Transactional(readOnly = true)
    fun listStudents(teacherId: Long, teachingClassId: Long): List<TeachingClassStudentResponse> {
        teachingClassService.requireOwner(teacherId, teachingClassId)
        return studentRepository.findStudentViews(teachingClassId).map { row ->
            TeachingClassStudentResponse(
                studentId = row.getStudentId(),
                studentNumber = row.getStudentNumber(),
                studentName = row.getStudentName(),
                administrativeClass = row.getAdministrativeClass(),
                joinedAt = row.getJoinedAt(),
                recentActivityAt = row.getRecentActivityAt(),
            )
        }
    }

    /**
     * 删除学生。早期版本这里只把名单行删掉，账号和学习记录都留着，
     * 教师以为删干净了，学生照样能登录、照样出现在排行榜里，属于设计缺陷。
     * 现在是彻底删除：账号连同 seclab_profile 里的全部学习痕迹一起清掉。
     */
    @Transactional
    fun removeStudent(teacherId: Long, teachingClassId: Long, studentId: Long) {
        teachingClassService.requireOwner(teacherId, teachingClassId)
        if (!studentRepository.existsByTeachingClassIdAndStudentId(teachingClassId, studentId)) {
            throw ApiException(404, "该学生不在此教学班中", HttpStatus.NOT_FOUND)
        }
        val student = userRepository.findById(studentId).orElseThrow {
            ApiException(404, "学生账号不存在", HttpStatus.NOT_FOUND)
        }
        studentPurgeService.purgeStudent(student)
        log.info(
            "teacher={} deleted student={} from teachingClass={} including account and learning data",
            teacherId,
            studentId,
            teachingClassId,
        )
    }

    private fun validateFile(fileName: String?, bytes: ByteArray) {
        if (fileName.isNullOrBlank() || !fileName.lowercase().endsWith(".xlsx")) {
            throw ApiException(400, "只支持.xlsx格式的学生名单")
        }
        if (bytes.isEmpty()) {
            throw ApiException(400, "上传文件不能为空")
        }
        if (bytes.size > MAX_FILE_BYTES) {
            throw ApiException(400, "学生名单不能超过2MB")
        }
    }

    private fun parseWorkbook(bytes: ByteArray): ParsedWorkbook {
        try {
            XSSFWorkbook(ByteArrayInputStream(bytes)).use { workbook ->
                if (workbook.numberOfSheets == 0) {
                    throw ApiException(400, "工作簿中没有学生名单")
                }
                val sheet = workbook.getSheetAt(0)
                val header = sheet.getRow(0) ?: throw ApiException(400, "缺少表头")
                val formatter = DataFormatter(Locale.CHINA)
                val actualHeaders = REQUIRED_HEADERS.indices.map { index ->
                    formatCell(header.getCell(index), formatter)
                }
                if (actualHeaders != REQUIRED_HEADERS) {
                    throw ApiException(400, "表头必须依次为：学号、姓名、行政班")
                }
                if (sheet.lastRowNum > MAX_DATA_ROWS) {
                    throw ApiException(400, "一次最多导入500名学生")
                }

                val validRows = mutableListOf<ImportAccountRow>()
                val duplicateRows = mutableListOf<ImportDuplicateRow>()
                val errorRows = mutableListOf<ImportErrorRow>()
                val firstRowByStudentNumber = mutableMapOf<String, Int>()
                for (index in 1..sheet.lastRowNum) {
                    val excelRowNumber = index + 1
                    val row = sheet.getRow(index) ?: continue
                    val cells = REQUIRED_HEADERS.indices.map { row.getCell(it) }
                    if (cells.all { formatCell(it, formatter).isBlank() }) continue
                    if (cells.any { it?.cellType == CellType.FORMULA }) {
                        errorRows += ImportErrorRow(excelRowNumber, "不允许使用公式")
                        continue
                    }
                    val studentNumber = formatCell(cells[0], formatter).trim()
                    val studentName = formatCell(cells[1], formatter).trim()
                    val administrativeClass = formatCell(cells[2], formatter).trim()
                    val errors = buildList {
                        if (studentNumber.isBlank()) add("学号不能为空")
                        if (studentNumber.length > 13) add("学号不能超过13个字符")
                        if (studentName.isBlank()) add("姓名不能为空")
                        if (studentName.length > 80) add("姓名不能超过80个字符")
                        if (administrativeClass.isBlank()) add("行政班不能为空")
                        if (administrativeClass.length > 120) add("行政班不能超过120个字符")
                    }
                    if (errors.isNotEmpty()) {
                        errorRows += ImportErrorRow(excelRowNumber, errors.joinToString("；"))
                        continue
                    }
                    val firstRow = firstRowByStudentNumber.putIfAbsent(studentNumber, excelRowNumber)
                    if (firstRow != null) {
                        duplicateRows += ImportDuplicateRow(excelRowNumber, studentNumber, firstRow)
                        continue
                    }
                    validRows += ImportAccountRow(
                        rowNumber = excelRowNumber,
                        studentNumber = studentNumber,
                        studentName = studentName,
                        administrativeClass = administrativeClass,
                    )
                }
                return ParsedWorkbook(validRows, duplicateRows, errorRows)
            }
        } catch (exception: ApiException) {
            throw exception
        } catch (exception: Exception) {
            log.warn("failed to parse teaching class workbook: {}", exception.message)
            throw ApiException(400, "无法读取Excel文件，请使用系统模板")
        }
    }

    private fun formatCell(cell: org.apache.poi.ss.usermodel.Cell?, formatter: DataFormatter): String =
        cell?.let(formatter::formatCellValue).orEmpty()

    private fun sha256(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }

    private data class ParsedWorkbook(
        val validRows: List<ImportAccountRow>,
        val duplicateRows: List<ImportDuplicateRow>,
        val errorRows: List<ImportErrorRow>,
    )

    private companion object {
        val log = LoggerFactory.getLogger(TeachingClassImportService::class.java)
        val REQUIRED_HEADERS = listOf("学号", "姓名", "行政班")
        const val MAX_FILE_BYTES = 2 * 1024 * 1024
        const val MAX_DATA_ROWS = 500
        const val PREVIEW_TTL_MINUTES = 30L
        const val DEFAULT_INITIAL_PASSWORD = "123456"
    }
}
