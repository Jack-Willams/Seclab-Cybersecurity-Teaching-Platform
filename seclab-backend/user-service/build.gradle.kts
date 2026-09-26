plugins {
	kotlin("jvm") version "1.9.25"
	kotlin("plugin.spring") version "1.9.25"
	id("org.springframework.boot") version "3.4.3"
	id("io.spring.dependency-management") version "1.1.7"
}

group = "me.myot233.seclab"
version = "0.0.1-SNAPSHOT"

java {
	toolchain {
		languageVersion = JavaLanguageVersion.of(17)
	}
}

repositories {
	mavenCentral()
}

repositories {
    maven { url = uri("https://maven.aliyun.com/repository/public") }
    mavenCentral()
}

extra["springCloudVersion"] = "2024.0.0"

dependencies {
	implementation("org.jetbrains.kotlin:kotlin-reflect")
	implementation("org.springframework.boot:spring-boot-starter-web") // 如果有 web 接口
	implementation("org.springframework.boot:spring-boot-starter-data-jpa") // JPA
	implementation("org.springframework.boot:spring-boot-starter-validation") // 校验
	implementation("org.springframework.security:spring-security-crypto")
	implementation("org.springframework.cloud:spring-cloud-starter-netflix-eureka-client")
	implementation("com.alibaba:druid-spring-boot-starter:1.2.23")
	implementation("com.mysql:mysql-connector-j:8.3.0")
	implementation("org.apache.poi:poi-ooxml:5.3.0") // 队友教师端：教学班学生 xlsx 导入
	runtimeOnly("org.mariadb.jdbc:mariadb-java-client:3.3.3")
	testImplementation("org.springframework.boot:spring-boot-starter-test")
	testImplementation("org.jetbrains.kotlin:kotlin-test-junit5")
}

dependencyManagement {
	imports {
		mavenBom("org.springframework.cloud:spring-cloud-dependencies:${property("springCloudVersion")}")
	}
}

kotlin {
	compilerOptions {
		freeCompilerArgs.addAll("-Xjsr305=strict")
	}
}

tasks.withType<Test> {
	useJUnitPlatform()
}
