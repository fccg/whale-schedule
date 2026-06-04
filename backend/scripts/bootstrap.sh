#!/bin/bash
# bootstrap.sh — Instance environment initialization script
# Runs on GPU instance startup via cloud-init / user-data.
# Reports progress back to the platform via agent heartbeat.
#
# Usage: bootstrap.sh <AGENT_TOKEN> <INSTANCE_ID> <API_BASE>
# Each step outputs STEP:N:STATUS for parsing by the agent.

set -euo pipefail

AGENT_TOKEN="${1:-}"
INSTANCE_ID="${2:-}"
API_BASE="${3:-http://localhost:8000}"
STEP=0
TOTAL_STEPS=6

log_step() {
    local status="$1"
    local msg="$2"
    echo "BOOTSTRAP STEP_${STEP}:${status}: ${msg}"
}

fail_step() {
    local msg="$1"
    echo "BOOTSTRAP STEP_${STEP}:FAIL: ${msg}"
    curl -s -X POST "${API_BASE}/api/agent/heartbeat" \
        -H "Content-Type: application/json" \
        -d "{\"agent_token\":\"${AGENT_TOKEN}\",\"instance_id\":\"${INSTANCE_ID}\",\"bootstrap_step\":${STEP},\"bootstrap_total\":${TOTAL_STEPS},\"bootstrap_status\":\"failed\",\"last_error\":\"${msg}\"}" \
        || true
    exit 1
}

heartbeat_progress() {
    local status="${1:-running}"
    curl -s -X POST "${API_BASE}/api/agent/heartbeat" \
        -H "Content-Type: application/json" \
        -d "{\"agent_token\":\"${AGENT_TOKEN}\",\"instance_id\":\"${INSTANCE_ID}\",\"bootstrap_step\":${STEP},\"bootstrap_total\":${TOTAL_STEPS},\"bootstrap_status\":\"${status}\"}" \
        || true
}

# ---- Step 1: apt update + build-essential + nvidia-container-toolkit ----
STEP=1
log_step "START" "Installing system packages"
apt-get update -qq || fail_step "apt update failed"
apt-get install -y -qq build-essential curl wget jq > /dev/null 2>&1 || fail_step "build-essential install failed"
heartbeat_progress "running"
log_step "DONE" "System packages installed"

# ---- Step 2: CUDA 13 + cuDNN ----
STEP=2
log_step "START" "Verifying CUDA"
if ! command -v nvidia-smi &> /dev/null; then
    fail_step "nvidia-smi not found - GPU not available"
fi
CUDA_VER=$(nvidia-smi | grep -oP "CUDA Version: \K[0-9.]+" || echo "unknown")
echo "CUDA Version: ${CUDA_VER}"
heartbeat_progress "running"
log_step "DONE" "CUDA verified (${CUDA_VER})"

# ---- Step 3: NGC PyTorch container ----
STEP=3
log_step "START" "Pulling NGC PyTorch container"
if command -v docker &> /dev/null; then
    docker pull nvidia/pytorch:26.03-py3 > /dev/null 2>&1 || echo "WARNING: docker pull failed, continuing with local images"
else
    echo "WARNING: docker not available on host, skipping container pull"
fi
heartbeat_progress "running"
log_step "DONE" "NGC PyTorch container ready"

# ---- Step 4: Codex CLI + Claude Code CLI ----
STEP=4
log_step "START" "Installing CLI tools"
# Codex CLI
if ! command -v codex &> /dev/null; then
    curl -fsSL https://codex.openai.com/install.sh | bash > /dev/null 2>&1 || echo "WARNING: codex install skipped"
fi
# Claude Code CLI
if ! command -v claude &> /dev/null; then
    npm install -g @anthropic-ai/claude-code > /dev/null 2>&1 || echo "WARNING: claude-code install skipped"
fi
heartbeat_progress "running"
log_step "DONE" "CLI tools installed"

# ---- Step 5: S3 mount + dataset download ----
STEP=5
log_step "START" "Setting up S3 mount and dataset"
# Placeholder for S3 mount — actual implementation depends on storage backend
echo "S3 mount placeholder: directory /mnt/s3-data"
mkdir -p /mnt/s3-data || echo "WARNING: could not create /mnt/s3-data"
heartbeat_progress "running"
log_step "DONE" "S3 mount placeholder ready"

# ---- Step 6: Install and start gpu-agent ----
STEP=6
log_step "START" "Starting gpu-agent heartbeat loop"
AGENT_DIR="/opt/gpu-agent"
mkdir -p "${AGENT_DIR}"

# Write agent config
cat > "${AGENT_DIR}/agent.conf" << CONF
AGENT_TOKEN=${AGENT_TOKEN}
INSTANCE_ID=${INSTANCE_ID}
API_BASE=${API_BASE}
CONF

# Copy metrics collection script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "${SCRIPT_DIR}/gpu-metrics.sh" ]; then
    cp "${SCRIPT_DIR}/gpu-metrics.sh" "${AGENT_DIR}/gpu-metrics.sh"
    chmod +x "${AGENT_DIR}/gpu-metrics.sh"
fi

# Start agent heartbeat loop in background
nohup bash -c '
AGENT_TOKEN="'"${AGENT_TOKEN}"'"
INSTANCE_ID="'"${INSTANCE_ID}"'"
API_BASE="'"${API_BASE}"'"
AGENT_DIR="'"${AGENT_DIR}"'"
while true; do
    METRICS_JSON=$("${AGENT_DIR}/gpu-metrics.sh" 2>/dev/null || echo "{}")
    curl -s -X POST "${API_BASE}/api/agent/heartbeat" \
        -H "Content-Type: application/json" \
        -d "$(echo "${METRICS_JSON}" | jq --arg token "${AGENT_TOKEN}" --arg iid "${INSTANCE_ID}" '"'"'{agent_token: $token, instance_id: $iid} + .'"'"')" \
        > /dev/null 2>&1 || true
    sleep 10
done
' > "${AGENT_DIR}/agent.log" 2>&1 &

AGENT_PID=$!
echo "Agent PID: ${AGENT_PID}"
heartbeat_progress "done"

log_step "DONE" "Bootstrap complete. Agent running (PID=${AGENT_PID})."
echo "BOOTSTRAP_ALL_DONE"
