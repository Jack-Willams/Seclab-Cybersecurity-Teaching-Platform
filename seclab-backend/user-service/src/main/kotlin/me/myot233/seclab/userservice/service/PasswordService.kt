package me.myot233.seclab.userservice.service

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder
import org.springframework.stereotype.Service
import java.security.MessageDigest

data class PasswordCheckResult(
    val matched: Boolean,
    val shouldUpgrade: Boolean,
)

@Service
class PasswordService(
    private val passwordEncoder: BCryptPasswordEncoder,
) {
    fun encode(rawPassword: String): String = passwordEncoder.encode(rawPassword)

    fun verify(rawPassword: String, storedPassword: String): PasswordCheckResult {
        if (storedPassword.isBlank()) {
            return PasswordCheckResult(matched = false, shouldUpgrade = false)
        }

        if (isBcrypt(storedPassword)) {
            return PasswordCheckResult(
                matched = passwordEncoder.matches(rawPassword, storedPassword),
                shouldUpgrade = false,
            )
        }

        val legacyMatched = storedPassword == rawPassword ||
            storedPassword.equals(md5(rawPassword), ignoreCase = true)

        return PasswordCheckResult(
            matched = legacyMatched,
            shouldUpgrade = legacyMatched,
        )
    }

    private fun isBcrypt(value: String): Boolean =
        value.startsWith("\$2a\$") || value.startsWith("\$2b\$") || value.startsWith("\$2y\$")

    private fun md5(value: String): String {
        val digest = MessageDigest.getInstance("MD5").digest(value.toByteArray(Charsets.UTF_8))
        return digest.joinToString(separator = "") { "%02x".format(it) }
    }
}
