package me.myot233.seclab.experimentmoduleservice.exception

import me.myot233.seclab.experimentmoduleservice.dto.ApiResponse
import org.springframework.dao.DataIntegrityViolationException
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import org.springframework.web.server.ResponseStatusException

@RestControllerAdvice
class GlobalExceptionHandler {
    @ExceptionHandler(IllegalArgumentException::class)
    fun handleBadRequest(exception: IllegalArgumentException): ResponseEntity<ApiResponse<Unit>> =
        ResponseEntity
            .status(HttpStatus.BAD_REQUEST)
            .body(ApiResponse.failure(400, exception.message ?: "请求参数不合法"))

    @ExceptionHandler(NoSuchElementException::class)
    fun handleNotFound(exception: NoSuchElementException): ResponseEntity<ApiResponse<Unit>> =
        ResponseEntity
            .status(HttpStatus.NOT_FOUND)
            .body(ApiResponse.failure(404, exception.message ?: "资源不存在"))

    @ExceptionHandler(DataIntegrityViolationException::class)
    fun handleConflict(exception: DataIntegrityViolationException): ResponseEntity<ApiResponse<Unit>> =
        ResponseEntity
            .status(HttpStatus.CONFLICT)
            .body(ApiResponse.failure(409, exception.message ?: "数据冲突，无法完成当前操作"))

    @ExceptionHandler(ResponseStatusException::class)
    fun handleResponseStatus(exception: ResponseStatusException): ResponseEntity<ApiResponse<Unit>> {
        val status = HttpStatus.resolve(exception.statusCode.value()) ?: HttpStatus.INTERNAL_SERVER_ERROR
        return ResponseEntity
            .status(status)
            .body(ApiResponse.failure(status.value(), exception.reason ?: status.reasonPhrase))
    }

    @ExceptionHandler(Exception::class)
    fun handleUnexpectedException(exception: Exception): ResponseEntity<ApiResponse<Unit>> =
        ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ApiResponse.failure(500, exception.message ?: "服务器内部错误"))
}
