#!/bin/bash
set -euo pipefail
systemctl daemon-reload || true
systemctl start <APP>
