#!/usr/bin/env bash
# 清理临时文件和日志 / Clean up temporary files and logs
set -euo pipefail

LOG_DIR="${1:-/var/log/app}"
TMP_DIR="${2:-/tmp/app}"
LOG_KEEP_DAYS="${3:-30}"
TMP_KEEP_DAYS="${4:-7}"
APP_DIR="${5:-/var/app}"

FREED_SPACE=0

echo "开始清理... / Starting cleanup..."
echo "时间 / Time: $(date)"
echo ""

cleanup_directory() {
    local dir="$1"
    local days="$2"
    local pattern="${3:-*}"
    local desc="$4"

    if [ ! -d "$dir" ]; then
        echo "目录不存在，跳过: $dir / Directory not found, skipping: $dir"
        return
    fi

    echo "清理 $desc: $dir (保留最近 ${days} 天 / keeping last ${days} days)"
    local before
    before=$(du -sb "$dir" 2>/dev/null | cut -f1 || echo 0)

    find "$dir" -name "$pattern" -type f -mtime +"$days" -delete 2>/dev/null || true

    local after
    after=$(du -sb "$dir" 2>/dev/null | cut -f1 || echo 0)
    local freed=$(( (before - after) / 1024 ))
    FREED_SPACE=$((FREED_SPACE + freed))
    echo "  已释放: ${freed} KB / Freed: ${freed} KB"
}

# 清理日志文件 / Clean up log files
cleanup_directory "$LOG_DIR" "$LOG_KEEP_DAYS" "*.log" "日志文件 / log files"

# 清理临时文件 / Clean up temporary files
cleanup_directory "$TMP_DIR" "$TMP_KEEP_DAYS" "*" "临时文件 / temp files"

# 清理系统临时文件 / Clean up system temp files
echo ""
echo "清理系统临时文件... / Cleaning system temp files..."
find /tmp -type f -atime +"$TMP_KEEP_DAYS" -delete 2>/dev/null || true
find /var/tmp -type f -atime +30 -delete 2>/dev/null || true

# 清理 Python 缓存 / Clean up Python cache
if [ -d "$APP_DIR" ]; then
    echo "清理 Python 缓存... / Cleaning Python cache..."
    find "$APP_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true
fi

echo ""
echo "清理完成，共释放约 ${FREED_SPACE} KB / Cleanup complete, freed approx ${FREED_SPACE} KB"
