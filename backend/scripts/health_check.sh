#!/bin/bash
# health_check.sh — Verify GPU instance health after bootstrap.
# Outputs JSON suitable for platform consumption.
#
# Checks:
#   1. nvidia-smi available + CUDA version
#   2. GPU count > 0
#   3. PyTorch GPU tensor test
#   4. CLI tools (codex / claude) version check
#   5. S3 mount path accessible
#   6. Metrics agent running
#   7. External network reachability (5 targets)

set -euo pipefail

OUTPUT_JSON="{\"checks\":[]}"
PASSED=0
FAILED=0

add_check() {
    local name="$1"
    local status="$2"
    local detail="$3"
    OUTPUT_JSON=$(echo "${OUTPUT_JSON}" | jq \
        --arg name "${name}" \
        --arg status "${status}" \
        --arg detail "${detail}" \
        '.checks += [{"name": $name, "status": $status, "detail": $detail}]')
    if [ "${status}" = "pass" ]; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
}

# 1. nvidia-smi
if command -v nvidia-smi &> /dev/null && nvidia-smi -L &> /dev/null; then
    CUDA_V=$(nvidia-smi | grep -oP "CUDA Version: \K[0-9.]+" || echo "unknown")
    GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l)
    add_check "nvidia-smi" "pass" "CUDA=${CUDA_V}, GPU count=${GPU_COUNT}"
else
    add_check "nvidia-smi" "fail" "nvidia-smi not available"
fi

# 2. GPU count > 0
if [ "${GPU_COUNT:-0}" -gt 0 ]; then
    add_check "gpu_count" "pass" "Found ${GPU_COUNT} GPU(s)"
else
    add_check "gpu_count" "fail" "No GPUs detected"
fi

# 3. Docker
if command -v docker &> /dev/null; then
    DOCKER_VER=$(docker --version 2>/dev/null || echo "unknown")
    add_check "docker" "pass" "${DOCKER_VER}"
else
    add_check "docker" "fail" "Docker not found"
fi

# 4. Container image check
if command -v docker &> /dev/null; then
    if docker image inspect nvidia/pytorch:26.03-py3 &> /dev/null; then
        add_check "container_image" "pass" "nvidia/pytorch:26.03-py3 exists"
    else
        add_check "container_image" "warn" "nvidia/pytorch:26.03-py3 not pulled"
    fi
fi

# 5. CLI tools
if command -v codex &> /dev/null; then
    add_check "codex_cli" "pass" "$(codex --version 2>/dev/null || echo 'installed')"
else
    add_check "codex_cli" "warn" "codex CLI not installed"
fi
if command -v claude &> /dev/null; then
    add_check "claude_cli" "pass" "$(claude --version 2>/dev/null || echo 'installed')"
else
    add_check "claude_cli" "warn" "claude CLI not installed"
fi

# 6. S3 mount path
if [ -d /mnt/s3-data ] && [ -r /mnt/s3-data ] && [ -w /mnt/s3-data ]; then
    add_check "s3_mount" "pass" "/mnt/s3-data is read-write"
else
    add_check "s3_mount" "warn" "/mnt/s3-data not fully accessible"
fi

# 7. Metrics agent running
if pgrep -f "gpu-metrics.sh" > /dev/null; then
    add_check "metrics_agent" "pass" "Agent process running"
else
    add_check "metrics_agent" "warn" "Agent process not found (may be running in container)"
fi

# 8. External network reachability
for target in "huggingface.co" "cloudflare.com" "google.com" "api.openai.com" "aws.amazon.com"; do
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "https://${target}" 2>/dev/null | grep -qE "^(200|301|302|403)"; then
        add_check "net_${target}" "pass" "reachable"
    else
        add_check "net_${target}" "fail" "unreachable"
    fi
done

FINAL=$(echo "${OUTPUT_JSON}" | jq \
    --argjson passed "${PASSED}" \
    --argjson failed "${FAILED}" \
    --arg overall "$([ "${FAILED}" -eq 0 ] && echo "pass" || echo "partial_fail")" \
    '. + {passed: $passed, failed: $failed, overall: $overall}')

echo "${FINAL}"
