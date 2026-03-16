#!/usr/bin/env bash
# 安装系统依赖 / Install system dependencies
set -euo pipefail

# 检测操作系统 / Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "无法检测操作系统 / Unable to detect OS" >&2
    exit 1
fi

install_packages() {
    case "$OS" in
        ubuntu|debian)
            sudo apt-get update -y
            sudo apt-get install -y \
                curl \
                wget \
                git \
                vim \
                htop \
                unzip \
                python3 \
                python3-pip \
                python3-venv \
                docker.io \
                docker-compose
            ;;
        centos|rhel|fedora|rocky|almalinux)
            sudo yum install -y epel-release 2>/dev/null || true
            sudo yum install -y \
                curl \
                wget \
                git \
                vim \
                htop \
                unzip \
                python3 \
                python3-pip \
                docker \
                docker-compose
            ;;
        *)
            echo "不支持的操作系统: $OS / Unsupported OS: $OS" >&2
            exit 1
            ;;
    esac
}

echo "开始安装系统依赖... / Installing system dependencies..."
install_packages
echo "系统依赖安装完成 / System dependencies installed successfully"
