#!/bin/bash
set -euo pipefail
curl -fsS http://localhost:8080/health || curl -fsS http://localhost/
