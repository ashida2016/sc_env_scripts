#!/usr/bin/env bash
# 搭建 Python 虚拟环境 / Set up Python virtual environment
set -euo pipefail

VENV_DIR="${1:-.venv}"
REQUIREMENTS_FILE="${2:-requirements.txt}"

# 检查 Python3 是否已安装 / Check if Python3 is installed
if ! command -v python3 &>/dev/null; then
    echo "错误: 未找到 python3，请先运行 install_deps.sh / Error: python3 not found, run install_deps.sh first" >&2
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "使用 $PYTHON_VERSION / Using $PYTHON_VERSION"

# 创建虚拟环境 / Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "虚拟环境已存在: $VENV_DIR / Virtual environment already exists: $VENV_DIR"
else
    echo "创建虚拟环境: $VENV_DIR / Creating virtual environment: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# 激活虚拟环境 / Activate virtual environment
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# 升级 pip / Upgrade pip
pip install --upgrade pip

# 安装依赖 / Install dependencies
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "从 $REQUIREMENTS_FILE 安装依赖 / Installing dependencies from $REQUIREMENTS_FILE"
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "未找到 $REQUIREMENTS_FILE，跳过依赖安装 / $REQUIREMENTS_FILE not found, skipping dependency installation"
fi

echo ""
echo "虚拟环境设置完成 / Virtual environment setup complete"
echo "激活命令 / Activate with: source $VENV_DIR/bin/activate"
