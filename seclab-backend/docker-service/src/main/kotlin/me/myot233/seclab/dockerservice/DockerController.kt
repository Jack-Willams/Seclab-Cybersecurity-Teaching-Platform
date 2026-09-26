package me.myot233.seclab.dockerservice

import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import java.util.concurrent.TimeUnit

@RestController
class DockerController {

    private val labs = mapOf(
        "sqli" to LabTarget("sqli-lab-web-1", 8091),
        "xss" to LabTarget("xss-lab-web-1", 8092),
        "csrf" to LabTarget("csrf-lab-web-1", 8093),
        "cmd" to LabTarget("command-inject-web-1", 8090),
        "upload" to LabTarget("file-upload-lab-web-1", 8094),
        "dir" to LabTarget("directory-traversal-lab-web-1", 8095),
    )

    @GetMapping("/health")
    fun health(): Map<String, Any> = mapOf(
        "status" to "ok",
        "service" to "docker-service",
    )

    @GetMapping("/api/docker/containers/{name}/status")
    fun status(@PathVariable name: String): ResponseEntity<Map<String, Any?>> {
        val result = runDocker("inspect", "-f", "{{.State.Status}}", name)
        return result.toResponse("status") { output ->
            mapOf("container" to name, "status" to output.trim())
        }
    }

    @GetMapping("/api/docker/containers/{name}/ports")
    fun ports(@PathVariable name: String): ResponseEntity<Map<String, Any?>> {
        val result = runDocker("port", name)
        return result.toResponse("ports") { output ->
            mapOf(
                "container" to name,
                "ports" to output.lines().filter { it.isNotBlank() },
            )
        }
    }

    @GetMapping("/api/docker/target-status/{lab}")
    fun targetStatus(@PathVariable lab: String): ResponseEntity<Map<String, Any?>> {
        val target = labs[lab.lowercase()]
            ?: return ResponseEntity.badRequest().body(mapOf("success" to false, "message" to "Unknown lab: $lab"))

        val result = runDocker("inspect", "-f", "{{.State.Status}}", target.containerName)
        return result.toResponse("target-status") { output ->
            val running = output.trim() == "running"
            mapOf(
                "lab" to lab,
                "containerId" to target.containerName,
                "containerExists" to true,
                "containerRunning" to running,
                "hostPort" to target.hostPort,
                "targetUrl" to "http://localhost:${target.hostPort}",
                "status" to if (running) "online" else "offline",
                "message" to if (running) "container is running" else "container is not running",
            )
        }
    }

    @PostMapping("/api/docker/start-{lab}")
    fun startLab(@PathVariable lab: String): ResponseEntity<Map<String, Any?>> {
        val target = labs[lab.lowercase()]
            ?: return ResponseEntity.badRequest().body(mapOf("isSuccess" to 0, "message" to "Unknown lab: $lab"))

        val result = runDocker("start", target.containerName)
        return result.toResponse("start-lab") {
            mapOf(
                "isSuccess" to 1,
                "status" to 200,
                "message" to "container started",
                "data" to mapOf(
                    "lab" to lab,
                    "containerName" to target.containerName,
                    "containerId" to target.containerName,
                    "url" to "http://localhost:${target.hostPort}",
                    "hostPort" to target.hostPort,
                ),
            )
        }
    }

    @PostMapping("/api/docker/containers/{name}/start")
    fun start(@PathVariable name: String): ResponseEntity<Map<String, Any?>> {
        val result = runDocker("start", name)
        return result.toResponse("start") {
            mapOf("container" to name, "started" to true, "output" to it.trim())
        }
    }

    @PostMapping("/api/docker/containers/{name}/stop")
    fun stop(
        @PathVariable name: String,
        @RequestParam(defaultValue = "10") timeoutSeconds: Int,
    ): ResponseEntity<Map<String, Any?>> {
        val result = runDocker("stop", "--time", timeoutSeconds.coerceIn(1, 60).toString(), name)
        return result.toResponse("stop") {
            mapOf("container" to name, "stopped" to true, "output" to it.trim())
        }
    }

    @PostMapping("/api/docker/stop/{name}")
    fun stopCompat(@PathVariable name: String): ResponseEntity<Map<String, Any?>> {
        val result = runDocker("stop", "--time", "10", name)
        return result.toResponse("stop-lab") {
            mapOf(
                "isSuccess" to 1,
                "status" to 200,
                "message" to "container stopped",
                "data" to mapOf("containerName" to name, "output" to it.trim()),
            )
        }
    }

    private fun RunResult.toResponse(
        action: String,
        successBody: (String) -> Map<String, Any?>,
    ): ResponseEntity<Map<String, Any?>> {
        if (exitCode == 0) {
            return ResponseEntity.ok(successBody(stdout))
        }
        val body = mapOf(
            "action" to action,
            "success" to false,
            "exitCode" to exitCode,
            "stdout" to stdout.trim(),
            "stderr" to stderr.trim(),
        )
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(body)
    }

    private fun runDocker(vararg args: String): RunResult {
        val process = ProcessBuilder(listOf("docker") + args)
            .redirectErrorStream(false)
            .start()

        val finished = process.waitFor(30, TimeUnit.SECONDS)
        if (!finished) {
            process.destroyForcibly()
            return RunResult(-1, "", "docker command timed out")
        }

        return RunResult(
            exitCode = process.exitValue(),
            stdout = process.inputStream.bufferedReader().readText(),
            stderr = process.errorStream.bufferedReader().readText(),
        )
    }

    private data class RunResult(
        val exitCode: Int,
        val stdout: String,
        val stderr: String,
    )

    private data class LabTarget(
        val containerName: String,
        val hostPort: Int,
    )
}
