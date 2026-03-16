#!/usr/bin/env bash
# 初始化配置文件 / Initialize configuration files
set -euo pipefail

CONFIG_TEMPLATE_DIR="${1:-config/templates}"
CONFIG_OUTPUT_DIR="${2:-config}"

if [ ! -d "$CONFIG_TEMPLATE_DIR" ]; then
    echo "模板目录不存在: $CONFIG_TEMPLATE_DIR / Template directory not found: $CONFIG_TEMPLATE_DIR" >&2
    exit 1
fi

mkdir -p "$CONFIG_OUTPUT_DIR"

echo "从模板初始化配置... / Initializing configuration from templates..."

for template in "$CONFIG_TEMPLATE_DIR"/*.template; do
    [ -e "$template" ] || continue
    filename=$(basename "$template" .template)
    output="$CONFIG_OUTPUT_DIR/$filename"
    if [ -f "$output" ]; then
        echo "跳过已存在的配置文件: $output / Skipping existing config: $output"
    else
        cp "$template" "$output"
        echo "已创建配置文件: $output / Created config: $output"
    fi
done

echo "配置初始化完成 / Configuration initialization complete"
echo "请根据实际环境修改配置文件 / Please update the config files for your environment"
