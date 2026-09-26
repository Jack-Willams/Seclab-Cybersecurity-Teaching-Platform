package me.myot233.seclab.userservice.exception

import org.springframework.http.HttpStatus

class ApiException(
    val status: Int,
    override val message: String,
    val httpStatus: HttpStatus = HttpStatus.BAD_REQUEST,
) : RuntimeException(message)
