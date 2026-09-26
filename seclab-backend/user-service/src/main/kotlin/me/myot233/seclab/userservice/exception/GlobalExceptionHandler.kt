package me.myot233.seclab.userservice.exception

import me.myot233.seclab.userservice.dto.ApiResponse
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.validation.FieldError
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice

@RestControllerAdvice
class GlobalExceptionHandler {
    @ExceptionHandler(ApiException::class)
    fun handleApiException(exception: ApiException): ResponseEntity<ApiResponse<Unit>> =
        ResponseEntity
            .status(exception.httpStatus)
            .body(ApiResponse.failure(exception.status, exception.message))

    @ExceptionHandler(MethodArgumentNotValidException::class)
    fun handleValidationException(exception: MethodArgumentNotValidException): ResponseEntity<ApiResponse<Unit>> {
        val message = exception.bindingResult.allErrors
            .firstOrNull()
            ?.let { error ->
                val fieldName = (error as? FieldError)?.field
                if (fieldName.isNullOrBlank()) error.defaultMessage else "${fieldName}: ${error.defaultMessage}"
            }
            ?: "Request validation failed"

        return ResponseEntity
            .status(HttpStatus.BAD_REQUEST)
            .body(ApiResponse.failure(400, message))
    }

    @ExceptionHandler(Exception::class)
    fun handleUnexpectedException(exception: Exception): ResponseEntity<ApiResponse<Unit>> =
        ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ApiResponse.failure(500, exception.message ?: "Internal server error"))
}
