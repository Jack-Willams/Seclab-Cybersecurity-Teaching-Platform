import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    kotlin("jvm") version "1.9.25"
    kotlin("plugin.spring") version "1.9.25"
    kotlin("plugin.jpa") version "1.9.25"          // 支持 JPA 注解
    id("org.springframework.boot") version "3.1.4" // Spring Boot 3.1.x 目前稳定版本
    id("io.spring.dependency-management") version "1.1.0" // 官方推荐版本
}

group = "me.myot233.seclab"
version = "0.0.1-SNAPSHOT"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(17)
    }
}

repositories {
    maven { url = uri("https://maven.aliyun.com/repository/public") }
    mavenCentral()
}

extra["springCloudVersion"] = "2022.0.5" // 或你其它服务用的版本

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    implementation("org.springframework.cloud:spring-cloud-starter-loadbalancer")
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")

    implementation("org.springframework.cloud:spring-cloud-starter-netflix-eureka-client")
    implementation("org.springframework.cloud:spring-cloud-starter-openfeign")

    implementation("mysql:mysql-connector-java:8.0.33")

    // Hibernate 性能优化工具，可�?    implementation("io.hypersistence:hypersistence-utils-hibernate-63:3.9.2")

    // Jackson 支持 Jakarta XML Bind 注解
    implementation("com.fasterxml.jackson.module:jackson-module-jakarta-xmlbind-annotations")

    // Docker Java 客户端，如果项目中需要操�?Docker
    implementation("com.github.docker-java:docker-java-core:3.4.2")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit5")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

dependencyManagement {
    imports {
        mavenBom("org.springframework.cloud:spring-cloud-dependencies:${property("springCloudVersion")}")
    }
}

tasks.withType<KotlinCompile> {
    kotlinOptions {
        freeCompilerArgs += "-Xjsr305=strict"
        jvmTarget = "17"
    }
}

tasks.withType<Test> {
    useJUnitPlatform()
}
