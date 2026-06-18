#!/usr/bin/env bash
set -euo pipefail

# Ensure cache and output dirs exist
mkdir -p "${WORK_DIR:-/work}/cache" "${WORK_DIR:-/work}/output" "${WORK_DIR:-/work}/binaries"

# Print environment info
echo "Starting tools container"
echo "GHIDRA_INSTALL_DIR=${GHIDRA_INSTALL_DIR:-/opt/ghidra}"
echo "WORK_DIR=${WORK_DIR:-/work}"
echo "MAX_GHIDRA_JOBS=${MAX_GHIDRA_JOBS:-1}"

# Start FastAPI server
exec uvicorn job_server:app --host 0.0.0.0 --port 8000 --log-level info