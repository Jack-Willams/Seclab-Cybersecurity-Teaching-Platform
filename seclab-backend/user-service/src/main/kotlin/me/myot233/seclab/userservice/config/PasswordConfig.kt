package me.myot233.seclab.userservice.config

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder

@Configuration
class PasswordConfig {
    @Bean
    fun bcryptPasswordEncoder(): BCryptPasswordEncoder = BCryptPasswordEncoder()
}
