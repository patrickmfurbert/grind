#!/usr/bin/env bash
set -euo pipefail
podman volume create grind-qdrant
podman run -d --replace --name grind-qdrant -p 6333:6333 \
  -v grind-qdrant:/qdrant/storage docker.io/qdrant/qdrant:latest
