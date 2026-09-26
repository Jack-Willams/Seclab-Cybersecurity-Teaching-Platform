package me.myot233.seclab.userservice.config

import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Configuration
import org.springframework.web.servlet.config.annotation.CorsRegistry
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer

@Configuration
class CorsConfig(
    @Value("\${seclab.cors.allowed-origin-patterns:http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174}")
    private val allowedOriginPatterns: String,
) : WebMvcConfigurer {
    override fun addCorsMappings(registry: CorsRegistry) {
        registry.addMapping("/**")
            .allowedOriginPatterns(*resolveOriginPatterns())
            .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
            .allowedHeaders("*")
            .allowCredentials(true)
            .maxAge(3600)
    }

    private fun resolveOriginPatterns(): Array<String> =
        allowedOriginPatterns
            .split(',')
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .ifEmpty { listOf("*") }
            .toTypedArray()
}
