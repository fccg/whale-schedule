#!/bin/bash
# gpu-metrics.sh — Collect GPU instance telemetry metrics.
# Outputs JSON matching the platform's expected format.
#
# Fields:
#   cpu_percent, memory_percent, memory_used_gb, memory_total_gb,
#   disk_used_gb, disk_total_gb, net_up_mbps, net_down_mbps,
#   gpus: [{index, utilization, vram_percent, vram_used_gb, vram_total_gb, temp_c, power_w}]

set -euo pipefail

# ---- CPU ----
CPU_PERCENT=0
if command -v top &> /dev/null; then
    CPU_PERCENT=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 2>/dev/null || echo 0)
elif [ -f /proc/stat ]; then
    # Parse /proc/stat
    read -r _ user nice system idle _ < /proc/stat
    TOTAL=$((user + nice + system + idle))
    IDLE=${idle:-0}
    if [ "${TOTAL}" -gt 0 ]; then
        CPU_PERCENT=$(awk "BEGIN {printf \"%.1f\", 100 - (${IDLE} * 100 / ${TOTAL})}")
    fi
fi

# ---- Memory ----
MEM_TOTAL=0
MEM_USED=0
MEM_PERCENT=0
if [ -f /proc/meminfo ]; then
    MEM_TOTAL_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    MEM_AVAIL_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
    MEM_TOTAL=$((MEM_TOTAL_KB / 1024 / 1024))
    MEM_USED=$(( (MEM_TOTAL_KB - MEM_AVAIL_KB) / 1024 / 1024 ))
    if [ "${MEM_TOTAL_KB}" -gt 0 ]; then
        MEM_PERCENT=$(awk "BEGIN {printf \"%.1f\", (${MEM_TOTAL_KB} - ${MEM_AVAIL_KB}) * 100.0 / ${MEM_TOTAL_KB}}")
    fi
fi

# ---- Disk ----
DISK_USED=0
DISK_TOTAL=0
if command -v df &> /dev/null; then
    DISK_INFO=$(df -BG / 2>/dev/null | tail -1)
    DISK_TOTAL=$(echo "${DISK_INFO}" | awk '{print $2}' | sed 's/G//')
    DISK_USED=$(echo "${DISK_INFO}" | awk '{print $3}' | sed 's/G//')
fi

# ---- Network (placeholder — requires speedtest-cli for real values) ----
NET_UP=0
NET_DOWN=0

# ---- GPU details ----
GPUS_JSON="[]"
if command -v nvidia-smi &> /dev/null; then
    GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l)
    GPUS_JSON=$(nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw \
        --format=csv,noheader,nounits 2>/dev/null | while IFS=, read -r idx util vram_used vram_total temp power; do
        idx=$(echo "${idx}" | xargs)
        util=$(echo "${util}" | xargs)
        vram_used=$(echo "${vram_used}" | xargs | sed 's/MiB//')
        vram_total=$(echo "${vram_total}" | xargs | sed 's/MiB//')
        temp=$(echo "${temp}" | xargs)
        power=$(echo "${power}" | xargs)

        vram_used_gb=$(awk "BEGIN {printf \"%.1f\", ${vram_used:-0} / 1024}")
        vram_total_gb=$(awk "BEGIN {printf \"%.1f\", ${vram_total:-0} / 1024}")
        vram_percent=0
        if [ -n "${vram_used}" ] && [ -n "${vram_total}" ] && [ "${vram_total}" != "0" ]; then
            vram_percent=$(awk "BEGIN {printf \"%.1f\", ${vram_used} * 100.0 / ${vram_total}}")
        fi

        echo "{\"index\":${idx},\"utilization\":${util:-0},\"vram_percent\":${vram_percent},\"vram_used_gb\":${vram_used_gb},\"vram_total_gb\":${vram_total_gb},\"temp_c\":${temp:-0},\"power_w\":${power:-0}}"
    done | jq -s '.')
elif [ -f /proc/driver/nvidia/gpus ]; then
    # Fallback: iterate over /proc entries
    GPU_IDX=0
    GPUS_JSON=$(for gpu in /proc/driver/nvidia/gpus/*; do
        if [ -d "${gpu}" ]; then
            echo "{\"index\":${GPU_IDX},\"utilization\":0,\"vram_percent\":0,\"vram_used_gb\":0,\"vram_total_gb\":0,\"temp_c\":0,\"power_w\":0}"
            GPU_IDX=$((GPU_IDX + 1))
        fi
    done | jq -s '.')
fi

CPU_VAL=$(awk "BEGIN {printf \"%.1f\", ${CPU_PERCENT:-0}}")
MEM_USED_VAL=$(awk "BEGIN {printf \"%.1f\", ${MEM_USED:-0}}")
MEM_TOTAL_VAL=$(awk "BEGIN {printf \"%.1f\", ${MEM_TOTAL:-0}}")

jq -n \
    --argjson cpu_percent "${CPU_VAL}" \
    --argjson memory_percent "${MEM_PERCENT:-0}" \
    --argjson memory_used_gb "${MEM_USED_VAL}" \
    --argjson memory_total_gb "${MEM_TOTAL_VAL}" \
    --argjson disk_used_gb "${DISK_USED:-0}" \
    --argjson disk_total_gb "${DISK_TOTAL:-0}" \
    --argjson net_up_mbps "${NET_UP:-0}" \
    --argjson net_down_mbps "${NET_DOWN:-0}" \
    --argjson gpus "${GPUS_JSON}" \
    '{
        cpu_percent: $cpu_percent,
        memory_percent: $memory_percent,
        memory_used_gb: $memory_used_gb,
        memory_total_gb: $memory_total_gb,
        disk_used_gb: $disk_used_gb,
        disk_total_gb: $disk_total_gb,
        net_up_mbps: $net_up_mbps,
        net_down_mbps: $net_down_mbps,
        gpus: $gpus
    }'
