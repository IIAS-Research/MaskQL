#!/usr/bin/env bash

set -euo pipefail

readonly REQUIRED_JAVA_MAJOR=24
readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PLUGIN_DIR="$ROOT_DIR/trino/plugins/maskql-plugin"

detect_javac_major() {
    if ! command -v javac >/dev/null 2>&1; then
        return 1
    fi

    local version
    version="$(javac -version 2>&1 | awk '{print $2}')"
    printf '%s\n' "${version}" | awk -F '[.+-]' '{print $1}'
}

run_native_build() {
    mvn -f "$PLUGIN_DIR/pom.xml" -DskipTests package
}

run_docker_build() {
    mkdir -p "$HOME/.m2"

    docker run --rm \
        --user "$(id -u):$(id -g)" \
        -v "$PLUGIN_DIR:/workspace" \
        -v "$HOME/.m2:/var/maven/.m2" \
        -w /workspace \
        maven:3.9-eclipse-temurin-24 \
        mvn -U -DskipTests package -Dmaven.repo.local=/var/maven/.m2/repository
}

if command -v mvn >/dev/null 2>&1; then
    if java_major="$(detect_javac_major)"; then
        if [ "$java_major" -ge "$REQUIRED_JAVA_MAJOR" ]; then
            run_native_build
            exit 0
        fi
    fi
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "MaskQL Trino plugin build requires Java ${REQUIRED_JAVA_MAJOR}+ or Docker." >&2
    exit 1
fi

run_docker_build
