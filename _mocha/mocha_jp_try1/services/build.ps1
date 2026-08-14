# Cross-compile each service to a static linux/amd64 binary named `main` for the
# golang-binary Docker image (x86_64 / Amazon Linux 2023 / Alpine, CGO disabled).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$env:CGO_ENABLED = "0"
$env:GOOS = "linux"
$env:GOARCH = "amd64"

foreach ($svc in @("ui-service", "core-service", "worker-service")) {
    Write-Host "building $svc -> dist/$svc/main"
    New-Item -ItemType Directory -Force -Path "dist/$svc" | Out-Null
    go build -trimpath -ldflags="-s -w" -o "dist/$svc/main" "./cmd/$svc"
}

Write-Host "done. Binaries in dist/<service>/main"
