#!/usr/bin/env bash
#
# Build and publish an AWS Lambda layer for one or more Python packages.
#
# The layer is built inside a Docker container that matches the Lambda
# runtime so that any compiled (C-extension) dependencies are ABI-compatible.
# Dependencies are installed into the "python/" directory that Lambda expects
# at the root of the layer archive.
#
# Usage:
#   ./layer.sh <package> [package ...]
#
# Environment overrides:
#   LAYER_NAME    Name of the layer          (default: derived from first package)
#   DESCRIPTION   Layer description          (default: "<LAYER_NAME> layer")
#   RUNTIME       Python runtime             (default: python3.14)
#   ARCH          x86_64 | arm64             (default: x86_64)
#   LICENSE       License info               (default: MIT)
#   AWS_PROFILE   AWS CLI profile to use     (default: current environment)
#   AWS_REGION    AWS region to publish in   (default: current environment)
#
# Examples:
#   ./layer.sh scapy
#   LAYER_NAME=alchemy ./layer.sh sqlalchemy pymysql
#   ARCH=arm64 RUNTIME=python3.12 ./layer.sh requests

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <package> [package ...]" >&2
  exit 1
fi

PACKAGES=("$@")
RUNTIME="${RUNTIME:-python3.14}"
ARCH="${ARCH:-x86_64}"
LICENSE="${LICENSE:-MIT}"
LAYER_NAME="${LAYER_NAME:-${PACKAGES[0]}}"
DESCRIPTION="${DESCRIPTION:-${LAYER_NAME} layer}"

# Derive the Docker image tag from the runtime: python3.14 -> python:3.14-slim
DOCKER_IMAGE="python:${RUNTIME#python}-slim"

# Map the layer architecture to a Lambda-compatible value and Docker platform.
case "${ARCH}" in
  x86_64) COMPATIBLE_ARCH="x86_64"; DOCKER_PLATFORM="linux/amd64" ;;
  arm64)  COMPATIBLE_ARCH="arm64";  DOCKER_PLATFORM="linux/arm64" ;;
  *) echo "Unsupported ARCH '${ARCH}' (use x86_64 or arm64)" >&2; exit 1 ;;
esac

# Pass AWS_PROFILE / AWS_REGION through to the CLI only if they are set.
AWS_ARGS=()
[[ -n "${AWS_PROFILE:-}" ]] && AWS_ARGS+=(--profile "${AWS_PROFILE}")
[[ -n "${AWS_REGION:-}"  ]] && AWS_ARGS+=(--region "${AWS_REGION}")

# ---------------------------------------------------------------------------
# Preconditions
# ---------------------------------------------------------------------------
for cmd in docker zip aws; do
  command -v "${cmd}" >/dev/null 2>&1 || { echo "Required command '${cmd}' not found in PATH" >&2; exit 1; }
done

WORKDIR="$(mktemp -d)"
ZIP_FILE="${WORKDIR}/${LAYER_NAME}.zip"
trap 'rm -rf "${WORKDIR}"' EXIT

echo ">> Building layer '${LAYER_NAME}' (${RUNTIME}, ${ARCH}) with: ${PACKAGES[*]}"

# ---------------------------------------------------------------------------
# Install dependencies inside a runtime-matched container
# ---------------------------------------------------------------------------
# Lambda resolves layer packages from "python/" at the archive root, so install
# directly into "${WORKDIR}/python". The container writes as root, so ownership
# is fixed afterwards to keep the host tidy.
mkdir -p "${WORKDIR}/python"

docker run --rm \
  --platform "${DOCKER_PLATFORM}" \
  -v "${WORKDIR}/python:/opt/python" \
  "${DOCKER_IMAGE}" \
  bash -c "pip install --no-cache-dir --upgrade ${PACKAGES[*]} -t /opt/python"

# ---------------------------------------------------------------------------
# Package the layer
# ---------------------------------------------------------------------------
echo ">> Creating ${ZIP_FILE}"
( cd "${WORKDIR}" && zip -qr "${ZIP_FILE}" python )

# ---------------------------------------------------------------------------
# Publish the layer version
# ---------------------------------------------------------------------------
echo ">> Publishing layer version to AWS"
LAYER_ARN="$(aws lambda publish-layer-version \
  "${AWS_ARGS[@]}" \
  --layer-name "${LAYER_NAME}" \
  --description "${DESCRIPTION}" \
  --license-info "${LICENSE}" \
  --zip-file "fileb://${ZIP_FILE}" \
  --compatible-runtimes "${RUNTIME}" \
  --compatible-architectures "${COMPATIBLE_ARCH}" \
  --query 'LayerVersionArn' \
  --output text)"

echo ">> Published: ${LAYER_ARN}"
