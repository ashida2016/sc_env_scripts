#!/usr/bin/env bash
# 系统健康检查 / System health check
set -euo pipefail

EXIT_CODE=0
WARN_CPU=80
WARN_MEM=85
WARN_DISK=90

# 颜色输出 / Color output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

check_pass() { echo -e "${GREEN}[OK]${NC} $1"; }
check_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; EXIT_CODE=1; }
check_fail() { echo -e "${RED}[FAIL]${NC} $1"; EXIT_CODE=2; }

echo "========== 系统健康检查 / System Health Check =========="
echo "时间 / Time: $(date)"
echo ""

# CPU 使用率 / CPU usage
CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}' | tr -d '%id,' 2>/dev/null || \
           vmstat 1 1 | tail -1 | awk '{print $15}')
CPU_USED=$((100 - ${CPU_IDLE%.*}))
echo "CPU 使用率 / CPU Usage: ${CPU_USED}%"
if [ "$CPU_USED" -ge "$WARN_CPU" ]; then
    check_warn "CPU 使用率过高: ${CPU_USED}% (阈值: ${WARN_CPU}%) / CPU usage high: ${CPU_USED}%"
else
    check_pass "CPU 使用率正常 / CPU usage normal: ${CPU_USED}%"
fi

echo ""

# 内存使用率 / Memory usage
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_USED=$(free -m | awk '/^Mem:/{print $3}')
MEM_PCT=$((MEM_USED * 100 / MEM_TOTAL))
echo "内存使用率 / Memory Usage: ${MEM_PCT}% (${MEM_USED}M / ${MEM_TOTAL}M)"
if [ "$MEM_PCT" -ge "$WARN_MEM" ]; then
    check_warn "内存使用率过高: ${MEM_PCT}% (阈值: ${WARN_MEM}%) / Memory usage high"
else
    check_pass "内存使用率正常 / Memory usage normal: ${MEM_PCT}%"
fi

echo ""

# 磁盘使用率 / Disk usage
echo "磁盘使用率 / Disk Usage:"
while IFS= read -r line; do
    USAGE=$(echo "$line" | awk '{print $5}' | tr -d '%')
    MOUNT=$(echo "$line" | awk '{print $6}')
    if [ "$USAGE" -ge "$WARN_DISK" ]; then
        check_fail "磁盘空间不足: $MOUNT ${USAGE}% (阈值: ${WARN_DISK}%) / Disk full: $MOUNT"
    elif [ "$USAGE" -ge "$((WARN_DISK - 10))" ]; then
        check_warn "磁盘空间较少: $MOUNT ${USAGE}% / Disk space low: $MOUNT"
    else
        check_pass "磁盘空间正常: $MOUNT ${USAGE}% / Disk OK: $MOUNT"
    fi
done < <(df -h | awk 'NR>1 && $1 != "tmpfs" && $1 !~ /^\/dev\/loop/')

echo ""

# 检查常用服务 / Check common services
SERVICES=("docker" "sshd" "nginx" "cron")
echo "服务状态 / Service Status:"
for svc in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        check_pass "服务运行中: $svc / Service running: $svc"
    elif ! systemctl list-units --type=service 2>/dev/null | grep -q "$svc"; then
        echo "  [SKIP] 服务未安装: $svc / Service not installed: $svc"
    else
        check_warn "服务未运行: $svc / Service not running: $svc"
    fi
done

echo ""
echo "========== 检查完成 / Check Complete =========="
exit $EXIT_CODE
