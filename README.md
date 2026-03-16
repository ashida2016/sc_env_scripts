# sc_env_scripts

仅用于搭建环境时的各种脚本，也包括运维时的脚本。  
Various scripts for environment setup and operations/maintenance.

## 目录结构 / Directory Structure

```
sc_env_scripts/
├── setup/          # 环境搭建脚本 / Environment setup scripts
│   ├── install_deps.sh       # 安装系统依赖 / Install system dependencies
│   ├── setup_python_env.sh   # 搭建 Python 虚拟环境 / Set up Python virtual environment
│   └── init_config.sh        # 初始化配置文件 / Initialize configuration files
└── ops/            # 运维脚本 / Operations & maintenance scripts
    ├── backup.sh             # 数据备份 / Data backup
    ├── health_check.sh       # 系统健康检查 / System health check
    └── cleanup.sh            # 清理临时文件和日志 / Clean up temp files and logs
```

## 使用方法 / Usage

脚本执行前请先赋予执行权限 / Grant execute permission before running:

```bash
chmod +x setup/*.sh ops/*.sh
```

### 环境搭建 / Environment Setup

#### 安装系统依赖 / Install system dependencies

支持 Ubuntu/Debian 和 CentOS/RHEL 系列 / Supports Ubuntu/Debian and CentOS/RHEL:

```bash
./setup/install_deps.sh
```

#### 搭建 Python 虚拟环境 / Set up Python virtual environment

```bash
# 使用默认路径 (.venv) 和默认依赖文件 (requirements.txt)
# Using default path (.venv) and default requirements file (requirements.txt)
./setup/setup_python_env.sh

# 自定义虚拟环境路径和依赖文件 / Custom venv path and requirements file
./setup/setup_python_env.sh /path/to/venv /path/to/requirements.txt
```

#### 初始化配置文件 / Initialize configuration files

```bash
# 从 config/templates/ 中的 .template 文件初始化配置
# Initialize config from .template files in config/templates/
./setup/init_config.sh

# 自定义模板目录和输出目录 / Custom template and output directories
./setup/init_config.sh config/templates config/
```

### 运维 / Operations

#### 数据备份 / Data backup

```bash
# 使用默认路径 / Using default paths
./ops/backup.sh

# 自定义源目录、目标目录和保留天数 / Custom source, destination and retention days
./ops/backup.sh /var/app/data /var/backups/app 7
```

#### 系统健康检查 / System health check

```bash
./ops/health_check.sh
```

退出码 / Exit codes:
- `0` — 所有检查通过 / All checks passed
- `1` — 有警告 / Warnings found
- `2` — 有严重问题 / Critical issues found

#### 清理临时文件和日志 / Clean up temp files and logs

```bash
# 使用默认路径 / Using default paths
./ops/cleanup.sh

# 自定义日志目录、临时目录、保留天数及应用目录 / Custom log dir, temp dir, retention days, and app dir
./ops/cleanup.sh /var/log/app /tmp/app 30 7 /var/app
```

## 注意事项 / Notes

- 部分脚本需要 `sudo` 权限（如 `install_deps.sh`）/ Some scripts require `sudo` (e.g. `install_deps.sh`)
- 所有脚本均使用 `set -euo pipefail` 保证出错时立即退出 / All scripts use `set -euo pipefail` to exit on errors
