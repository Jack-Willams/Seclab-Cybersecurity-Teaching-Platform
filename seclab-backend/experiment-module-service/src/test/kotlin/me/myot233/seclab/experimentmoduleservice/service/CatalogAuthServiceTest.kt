package me.myot233.seclab.experimentmoduleservice.service

import com.fasterxml.jackson.databind.ObjectMapper
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.core.RowMapper
import org.springframework.web.server.ResponseStatusException
import java.time.Instant
import java.util.Base64
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

class CatalogAuthServiceTest {
    private val objectMapper = ObjectMapper()
    private val jdbcTemplate = StubJdbcTemplate()
    private val service = CatalogAuthService(objectMapper, jdbcTemplate, SECRET)

    @Test
    fun `explicit teacher role can mutate a course without owning a legacy class`() {
        stubUser(userId = 9, role = "TEACHER")

        val context = service.requireTeacherOrAdmin("Bearer ${tokenFor(9)}")

        assertEquals(9, context.userId)
        assertEquals("teacher", context.role)
    }

    @Test
    fun `student role cannot mutate a course`() {
        stubUser(userId = 10, role = "STUDENT")

        val error = assertThrows(ResponseStatusException::class.java) {
            service.requireTeacherOrAdmin("Bearer ${tokenFor(10)}")
        }

        assertEquals(403, error.statusCode.value())
    }

    @Test
    fun `legacy admin role is not routed into teacher workspace`() {
        stubUser(userId = 11, role = "ADMIN")

        val error = assertThrows(ResponseStatusException::class.java) {
            service.requireTeacherOrAdmin("Bearer ${tokenFor(11)}")
        }

        assertEquals(403, error.statusCode.value())
    }

    private fun stubUser(userId: Long, role: String) {
        jdbcTemplate.row = mapOf("userId" to userId, "userRole" to role)
    }

    private fun tokenFor(userId: Long): String {
        val now = Instant.now()
        val header = encodeJson(mapOf("alg" to "HS256", "typ" to "JWT"))
        val payload = encodeJson(
            mapOf(
                "sub" to userId.toString(),
                "studentNumber" to "teacher$userId",
                "iat" to now.epochSecond,
                "exp" to now.plusSeconds(300).epochSecond,
            ),
        )
        val signingInput = "$header.$payload"
        return "$signingInput.${sign(signingInput)}"
    }

    private fun encodeJson(value: Any): String =
        Base64.getUrlEncoder().withoutPadding().encodeToString(objectMapper.writeValueAsBytes(value))

    private fun sign(value: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(SECRET.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        return Base64.getUrlEncoder().withoutPadding()
            .encodeToString(mac.doFinal(value.toByteArray(Charsets.UTF_8)))
    }

    private companion object {
        const val SECRET = "test-secret-with-enough-entropy"
    }

    private class StubJdbcTemplate : JdbcTemplate() {
        var row: Map<String, Any> = emptyMap()

        @Suppress("UNCHECKED_CAST")
        override fun <T : Any?> query(
            sql: String,
            rowMapper: RowMapper<T>,
            vararg args: Any,
        ): MutableList<T> = mutableListOf(row as T)
    }
}
