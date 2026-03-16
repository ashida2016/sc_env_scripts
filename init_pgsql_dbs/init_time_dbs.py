import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# --- 配置区 ---
DB_HOST = "192.168.1.70"  # 务必直连真实数据库，不要连 PgBouncer
DB_PORT = "5432"

SUPER_USER = "postgres"
SUPER_PASS = "NhyCf2026^"

DB_LEADER = "scteamleader"
DB_LEADER_PWD = "Dfcf2026^"  

DB_PREFIX = "scdb_"
DB_COUNT = 100

TIMEZONE = "Asia/Shanghai"

def get_connection(dbname="postgres"):
    """获取数据库连接并设置为自动提交模式（CREATE DATABASE 必须在自动提交模式下运行）"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=SUPER_USER,
        password=SUPER_PASS,
        dbname=dbname
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def init_system():
    print("正在连接主数据库初始化全局配置...")
    conn = get_connection()
    cur = conn.cursor()

    # 1. 创建全局管理员角色 scteamleader
    cur.execute(f"SELECT 1 FROM pg_roles WHERE rolname='{DB_LEADER}'")
    if not cur.fetchone():
        print(f"正在创建管理员账号: {DB_LEADER} ...")
        # 赋予登录权限，并设置默认时区为上海
        cur.execute(f"CREATE ROLE {DB_LEADER} WITH LOGIN PASSWORD '{DB_LEADER_PWD}';")
        cur.execute(f"ALTER ROLE {DB_LEADER} SET timezone TO '{TIMEZONE}';")
    else:
        print(f"管理员账号 {DB_LEADER} 已存在，跳过创建。")

    # 获取已有的数据库列表，防止重复创建报错
    cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
    existing_dbs = [row[0] for row in cur.fetchall()]

    # 2. 批量创建 100 个数据库
    for i in range(1, DB_COUNT + 1):
        dbname = f"{DB_PREFIX}{i:03d}"  # 生成类似 scdb_001, scdb_010 的名字
        
        if dbname not in existing_dbs:
            print(f"正在创建数据库: {dbname} ...")
            # 指定 UTF8 编码以支持中文存储，并将所有权赋予 scteamleader
            cur.execute(f"CREATE DATABASE {dbname} WITH OWNER {DB_LEADER} ENCODING 'UTF8';")
            
            # 强制设置数据库级别的时区为上海
            cur.execute(f"ALTER DATABASE {dbname} SET timezone TO '{TIMEZONE}';")
        else:
            print(f"数据库 {dbname} 已存在，跳过创建。")

    cur.close()
    conn.close()

def init_timescaledb_extensions():
    print("\n开始为每个数据库安装 TimescaleDB 扩展...")
    
    for i in range(1, DB_COUNT + 1):
        dbname = f"{DB_PREFIX}{i:03d}"
        print(f"[{i}/{DB_COUNT}] 正在初始化 {dbname} 的时序功能...")
        
        try:
            # 必须单独连接到刚刚创建的目标数据库来安装扩展
            conn = get_connection(dbname)
            cur = conn.cursor()
            
            # 安装时序核心扩展
            cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"初始化 {dbname} 失败: {e}")

if __name__ == "__main__":
    try:
        init_system()
        init_timescaledb_extensions()
        print(f"\n[OK]所有 {DB_COUNT} 个时序数据库初始化完成！")
        print(f"[OK]后续业务代码请使用账号: {DB_LEADER} 连接 PgBouncer ({DB_HOST}:{DB_PORT}) 来访问这些数据库。")
    except Exception as e:
        print(f"[NG]发生致命错误: {e}")