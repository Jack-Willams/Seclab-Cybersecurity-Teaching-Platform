package me.myot233.seclab.userservice.dto

data class ApiResponse<T>(
    val isSuccess: Int,
    val status: Int,
    val message: String,
    val data: T?,
) {
    companion object {
        fun <T> success(data: T?, message: String = "success"): ApiResponse<T> =
            ApiResponse(isSuccess = 1, status = 200, message = message, data = data)

        fun <T> failure(status: Int, message: String, data: T? = null): ApiResponse<T> =
            ApiResponse(isSuccess = 0, status = status, message = message, data = data)

        fun <T> error(status: Int, message: String, data: T? = null): ApiResponse<T> =
            failure(status = status, message = message, data = data)
    }
}
