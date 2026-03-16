#!/usr/bin/env bash
# 数据备份脚本 / Data backup script
set -euo pipefail

BACKUP_SRC="${1:-/var/app/data}"
BACKUP_DEST="${2:-/var/backups/app}"
BACKUP_KEEP_DAYS="${3:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DEST/backup_$TIMESTAMP.tar.gz"

# 检查源目录 / Check source directory
if [ ! -d "$BACKUP_SRC" ]; then
    echo "错误: 备份源目录不存在: $BACKUP_SRC / Error: Source directory not found: $BACKUP_SRC" >&2
    exit 1
fi

# 创建备份目标目录 / Create backup destination directory
mkdir -p "$BACKUP_DEST"

echo "开始备份 $BACKUP_SRC -> $BACKUP_FILE"
echo "Starting backup $BACKUP_SRC -> $BACKUP_FILE"

if tar -czf "$BACKUP_FILE" -C "$(dirname "$BACKUP_SRC")" "$(basename "$BACKUP_SRC")"; then
    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    echo "备份成功，文件大小: $BACKUP_SIZE / Backup successful, size: $BACKUP_SIZE"
else
    echo "备份失败 / Backup failed" >&2
    exit 1
fi

# 清理旧备份 / Remove old backups
echo "清理 $BACKUP_KEEP_DAYS 天前的旧备份... / Removing backups older than $BACKUP_KEEP_DAYS days..."
find "$BACKUP_DEST" -name "backup_*.tar.gz" -mtime +"$BACKUP_KEEP_DAYS" -delete
echo "备份完成 / Backup complete"
