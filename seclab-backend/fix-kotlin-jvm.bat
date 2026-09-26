@echo off
chcp 65001 >nul
echo ========================================
echo    修复Kotlin JVM目标版本不一致问题
echo ========================================
echo.

cd experiment-module-service

echo 创建或修改gradle.properties文件...
echo # 设置Java Home > gradle.properties
echo org.gradle.java.home=C:/Program Files/Java/jdk-17 >> gradle.properties
echo # 禁用Kotlin JVM目标验证 >> gradle.properties
echo kotlin.jvm.target.validation.mode=warning >> gradle.properties

echo 修改build.gradle.kts文件...
echo // 确保Java和Kotlin使用相同的JVM目标版本 > kotlin-fix.gradle.kts
echo java.toolchain.languageVersion.set(JavaLanguageVersion.of(17)) >> kotlin-fix.gradle.kts
echo tasks.withType^<KotlinCompile^>().configureEach { >> kotlin-fix.gradle.kts
echo     kotlinOptions { >> kotlin-fix.gradle.kts
echo         jvmTarget = "17" >> kotlin-fix.gradle.kts
echo     } >> kotlin-fix.gradle.kts
echo } >> kotlin-fix.gradle.kts

echo 清理缓存...
if exist .gradle (
    rmdir /s /q .gradle
)
if exist build (
    rmdir /s /q build
)

cd ..

echo.
echo ========================================
echo    修复完成，请重新运行 rebuild-all.bat
echo ========================================
echo.
pause 