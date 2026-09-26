package me.myot233.seclab.userservice.service

import com.fasterxml.jackson.databind.ObjectMapper
import me.myot233.seclab.userservice.entity.UserEntity
import me.myot233.seclab.userservice.exception.ApiException
import org.springframework.beans.factory.annotation.Value
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import java.security.MessageDigest
import java.time.Instant
import java.util.Base64
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

data class TokenPayload(
    val userId: Long,
    val studentNumber: String,
)

@Service
class JwtTokenService(
    private val objectMapper: ObjectMapper,
    @Value("\${seclab.jwt.secret}") private val secret: String,
    @Value("\${seclab.jwt.expire-millis}") private val expireMillis: Long,
) {
    fun generate(user: UserEntity): String {
        val userId = user.userId ?: throw ApiException(500, "User id is missing", HttpStatus.INTERNAL_SERVER_ERROR)
        val now = Instant.now()
        val header = mapOf("alg" to "HS256", "typ" to "JWT")
        val payload = mapOf(
            "sub" to userId.toString(),
            "studentNumber" to user.userStudentNumber,
            "iat" to now.epochSecond,
            "exp" to now.plusMillis(expireMillis).epochSecond,
        )

        val encodedHeader = encodeJson(header)
        val encodedPayload = encodeJson(payload)
        val signingInput = "$encodedHeader.$encodedPayload"
        return "$signingInput.${sign(signingInput)}"
    }

    fun parse(token: String?): TokenPayload {
        val normalizedToken = token?.trim().orEmpty()
        if (normalizedToken.isBlank()) {
            throw ApiException(401, "Token is required", HttpStatus.UNAUTHORIZED)
        }

        val parts = normalizedToken.split('.')
        if (parts.size != 3) {
            throw ApiException(401, "Token format is invalid", HttpStatus.UNAUTHORIZED)
        }

        val signingInput = "${parts[0]}.${parts[1]}"
        val expectedSignature = sign(signingInput)
        if (!MessageDigest.isEqual(expectedSignature.toByteArray(), parts[2].toByteArray())) {
            throw ApiException(401, "Token signature is invalid", HttpStatus.UNAUTHORIZED)
        }

        val payloadJson = String(Base64.getUrlDecoder().decode(parts[1]), Charsets.UTF_8)
        val payload = objectMapper.readTree(payloadJson)
        val exp = payload.get("exp")?.asLong()
            ?: throw ApiException(401, "Token expiration is missing", HttpStatus.UNAUTHORIZED)
        if (Instant.now().epochSecond >= exp) {
            throw ApiException(401, "Token has expired", HttpStatus.UNAUTHORIZED)
        }

        val userId = payload.get("sub")?.asText()?.toLongOrNull()
            ?: throw ApiException(401, "Token subject is missing", HttpStatus.UNAUTHORIZED)
        val studentNumber = payload.get("studentNumber")?.asText().orEmpty()
        return TokenPayload(userId = userId, studentNumber = studentNumber)
    }

    fun resolveToken(queryToken: String?, authorizationHeader: String?): String? {
        if (!queryToken.isNullOrBlank()) {
            return queryToken
        }
        if (!authorizationHeader.isNullOrBlank() && authorizationHeader.startsWith("Bearer ")) {
            return authorizationHeader.removePrefix("Bearer ").trim()
        }
        return null
    }

    private fun encodeJson(value: Any): String =
        Base64.getUrlEncoder()
            .withoutPadding()
            .encodeToString(objectMapper.writeValueAsBytes(value))

    private fun sign(value: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        return Base64.getUrlEncoder().withoutPadding().encodeToString(mac.doFinal(value.toByteArray(Charsets.UTF_8)))
    }
}
