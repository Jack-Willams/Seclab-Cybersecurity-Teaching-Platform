package me.myot233.seclab.dockerservice

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class DockerServiceApplication

fun main(args: Array<String>) {
    runApplication<DockerServiceApplication>(*args)
}
