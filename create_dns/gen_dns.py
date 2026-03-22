import json
import os
from datetime import datetime

# 文件路径配置
#BASE_DIR = os.getcwd() 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, 'devices.json')
OUTPUT_DIR = os.path.join(BASE_DIR, 'zones') # 建议先生成到临时目录

def load_config():
    if not os.path.exists(JSON_FILE):
        print(f"[ERROR]错误: 找不到 {JSON_FILE}")
        return None
    with open(JSON_FILE, 'r') as f:
        return json.load(f)

def generate_zones():
    config = load_config()
    if not config: return

    domain = config['domain']
    prefix = config['network_prefix']
    devices = config['devices']
    
    # 自动生成序列号 (YYYYMMDDNN)
    serial = datetime.now().strftime("%Y%m%d01")
    
    # 公用 SOA 模板
    soa_header = f"""
;
; BIND data file for local loopback interface
;
$TTL    604800
@       IN      SOA     ns1.{domain}. admin.{domain}. (
                        {serial}         ; Serial
                        604800         ; Refresh
                        86400          ; Retry
                        2419200        ; Expire
                        604800 )       ; Negative Cache TTL
;
@       IN      NS      ns1.{domain}.
"""

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # --- 生成正向解析文件 ---
    forward_file = os.path.join(OUTPUT_DIR, f"db.{domain}")
    with open(forward_file, 'w') as f:
        f.write(soa_header + "\n")
        for dev in devices:
            f.write(f"{dev['hostname']:<15} IN      A       {dev['ip']}\n")
    
    # --- 生成反向解析文件 ---
    reverse_zone = f"db.{prefix}"
    reverse_file = os.path.join(OUTPUT_DIR, reverse_zone)
    with open(reverse_file, 'w') as f:
        f.write(soa_header + "\n")
        for dev in devices:
            last_octet = dev['ip'].split('.')[-1]
            f.write(f"{last_octet:<15} IN      PTR     {dev['hostname']}.{domain}.\n")

    print(f"[OK]成功！文件已生成至 {OUTPUT_DIR} 目录。")
    print(f"[OK]正向区域: db.{domain}")
    print(f"[OK]反向区域: db.{prefix}")
    print("-----更新-------")
    print("更新正向解析文件： sudo vi /etc/bind/zones/db.home.lan")
    print("更新反向解析文件： sudo vi /etc/bind/zones/db.192.168.1")
    print("-----检查-------")
    print("检查配置文件格式（批量运行）： ")
    print("sudo named-checkconf")
    print("sudo named-checkzone home.lan /etc/bind/zones/db.home.lan")
    print("sudo named-checkzone 1.168.192.in-addr.arpa /etc/bind/zones/db.192.168.1")
    print("-----重启-------")
    print("重启 BIND 服务： sudo systemctl restart named")

if __name__ == "__main__":
    generate_zones()