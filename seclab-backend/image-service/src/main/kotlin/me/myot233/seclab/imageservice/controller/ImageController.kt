package me.myot233.seclab.imageservice.controller

import jakarta.servlet.http.HttpServletRequest
import org.springframework.beans.factory.annotation.Value
import org.springframework.core.io.UrlResource
import org.springframework.http.HttpStatus
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.util.StringUtils
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.multipart.MaxUploadSizeExceededException
import org.springframework.web.multipart.MultipartFile
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.nio.file.StandardCopyOption
import java.util.Locale
import java.util.UUID

@RestController
@RequestMapping("/api/images")
class ImageController(
    @Value("\${image.upload-dir:\${image.storage.location:uploads/images}}")
    private val uploadDir: String,
    @Value("\${image.max-file-size-bytes:5242880}")
    private val maxFileSizeBytes: Long,
) {
    private val allowedExtensions = setOf("jpg", "jpeg", "png", "gif", "webp")

    @PostMapping("/upload", consumes = [MediaType.MULTIPART_FORM_DATA_VALUE])
    fun upload(
        @RequestParam(name = "file", required = false) file: MultipartFile?,
        @RequestParam(name = "image", required = false) image: MultipartFile?,
        @RequestParam(name = "avatar", required = false) avatar: MultipartFile?,
        request: HttpServletRequest,
    ): ResponseEntity<Map<String, Any>> {
        val uploadFile = file ?: image ?: avatar
            ?: return error(HttpStatus.BAD_REQUEST, "Image file is required")

        val validationError = validate(uploadFile)
        if (validationError != null) {
            return error(HttpStatus.BAD_REQUEST, validationError)
        }

        val extension = extensionOf(uploadFile.originalFilename.orEmpty())
        val filename = "avatar_${UUID.randomUUID()}.$extension"
        val root = uploadRoot()
        Files.createDirectories(root)

        val target = root.resolve(filename).normalize()
        if (!target.startsWith(root)) {
            return error(HttpStatus.BAD_REQUEST, "Invalid image filename")
        }

        uploadFile.inputStream.use { input ->
            Files.copy(input, target, StandardCopyOption.REPLACE_EXISTING)
        }

        val encodedFilename = URLEncoder.encode(filename, StandardCharsets.UTF_8)
        val url = "${request.scheme}://${request.serverName}:${request.serverPort}${request.contextPath}/api/images/files/$encodedFilename"

        return ResponseEntity.ok(
            mapOf(
                "success" to true,
                "url" to url,
                "filename" to filename,
                "size" to uploadFile.size,
                "contentType" to uploadFile.contentType.orEmpty(),
            ),
        )
    }

    @GetMapping("/files/{filename:.+}")
    fun getFile(@PathVariable filename: String): ResponseEntity<*> {
        val cleanFilename = StringUtils.cleanPath(filename)
        if (!isSafeFilename(cleanFilename) || extensionOf(cleanFilename) !in allowedExtensions) {
            return error(HttpStatus.BAD_REQUEST, "Invalid image filename")
        }

        val root = uploadRoot()
        val target = root.resolve(cleanFilename).normalize()
        if (!target.startsWith(root) || !Files.exists(target) || !Files.isRegularFile(target)) {
            return error(HttpStatus.NOT_FOUND, "Image not found")
        }

        val resource = UrlResource(target.toUri())
        val contentType = Files.probeContentType(target)?.let(MediaType::parseMediaType)
            ?: MediaType.APPLICATION_OCTET_STREAM

        return ResponseEntity.ok()
            .contentType(contentType)
            .body(resource)
    }

    @ExceptionHandler(MaxUploadSizeExceededException::class)
    fun handleMaxUploadSize(): ResponseEntity<Map<String, Any>> =
        error(HttpStatus.PAYLOAD_TOO_LARGE, "Image file is too large")

    private fun validate(file: MultipartFile): String? {
        if (file.isEmpty || file.size <= 0) {
            return "Image file must not be empty"
        }
        if (file.size > maxFileSizeBytes) {
            return "Image file is too large"
        }

        val contentType = file.contentType?.lowercase(Locale.ROOT).orEmpty()
        if (!contentType.startsWith("image/")) {
            return "Only image files are allowed"
        }

        val originalFilename = file.originalFilename.orEmpty()
        if (!isSafeFilename(originalFilename)) {
            return "Invalid image filename"
        }

        val extension = extensionOf(originalFilename)
        if (extension !in allowedExtensions) {
            return "Unsupported image type"
        }

        return null
    }

    private fun uploadRoot(): Path =
        Paths.get(uploadDir).toAbsolutePath().normalize()

    private fun extensionOf(filename: String): String =
        filename.substringAfterLast('.', missingDelimiterValue = "").lowercase(Locale.ROOT)

    private fun isSafeFilename(filename: String): Boolean {
        val cleanFilename = StringUtils.cleanPath(filename)
        return cleanFilename.isNotBlank() &&
            cleanFilename == filename &&
            !cleanFilename.contains("..") &&
            !cleanFilename.contains("/") &&
            !cleanFilename.contains("\\")
    }

    private fun error(status: HttpStatus, message: String): ResponseEntity<Map<String, Any>> =
        ResponseEntity.status(status).body(
            mapOf(
                "success" to false,
                "message" to message,
            ),
        )
}
