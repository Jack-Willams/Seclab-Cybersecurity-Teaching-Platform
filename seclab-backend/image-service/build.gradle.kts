import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    id("org.springframework.boot") version "3.2.3"
    id("io.spring.dependency-management") version "1.1.4"
    kotlin("jvm") version "1.9.25"
    kotlin("plugin.spring") version "1.9.22"
}

group = "me.myot233.seclab"
version = "0.0.1-SNAPSHOT"

java {
    sourceCompatibility = JavaVersion.VERSION_17
}

repositories {
    maven { url = uri("https://maven.aliyun.com/repository/public") }
    maven { url = uri("https://repo.spring.io/release") }
    mavenCentral()
}

dependencies {
    // image-service 只做文件落盘和读取（见 ImageController），不碰数据库。
    // 原来带着 data-jpa + mysql-connector，配的还是写死的 root/1128 + imagedb，
    // 换台机器就连不上；现在只是因为没有 @Entity、Hikari 又是懒连接才侥幸能起来。
    // 一旦有人加个实体就会直接启动失败，所以这里把用不到的持久化依赖去掉。
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    implementation("org.springframework.cloud:spring-cloud-starter-netflix-eureka-client")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

extra["springCloudVersion"] = "2023.0.0"

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
    maxHeapSize = "512m"
    jvmArgs = listOf("-Xms128m", "-Xmx512m", "-XX:MaxMetaspaceSize=256m")
}
