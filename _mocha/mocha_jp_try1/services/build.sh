#!/usr/bin/env bash
# Cross-compile each service to a static linux/amd64 binary named `main`, so it
# can be dropped next to dockerfiles/golang-binary/Dockerfile (which COPYs `main`).
# Target: x86_64 / Amazon Linux 2023 / Alpine container (CGO disabled -> static).
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p dist

for svc in ui-service core-service worker-service; do
  echo "building $svc -> dist/$svc/main"
  mkdir -p "dist/$svc"
  CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w" -o "dist/$svc/main" "./cmd/$svc"
done

echo "done. Binaries in dist/<service>/main"
