#!/bin/bash

# 1. 运行 Python 脚本生成新配置
python3 gen_dns.py

# 1.5 手工处理生成的文件（如果需要）
# -- 编辑正向解析文件，添加 SOA 和 NS 记录
# sudo vi /etc/bind/zones/db.home.lan
# -- 编辑反向解析文件，添加 SOA 和 NS 记录
# sudo vi /etc/bind/zones/db.192.168.1
# -- 在重启之前，检查语法是否正确
# sudo named-checkconf
# sudo named-checkzone home.lan /etc/bind/zones/db.home.lan
# sudo named-checkzone 1.168.192.in-addr.arpa /etc/bind/zones/db.192.168.1

# 2. 检查生成的语法是否正确 (以正向文件为例)
# 注意：这里需要替换为你实际的域名
named-checkzone home.lan ./zones/db.home.lan > /dev/null

if [ $? -eq 0 ]; then
    echo "[OK]语法检查通过，正在同步至 BIND..."
    sudo cp ./zones/db.* /etc/bind/zones/
    sudo systemctl reload named
    echo "[OK]DNS 服务已重载！"
else
    echo "[NG]语法检查失败，请检查 JSON 格式！"
fi