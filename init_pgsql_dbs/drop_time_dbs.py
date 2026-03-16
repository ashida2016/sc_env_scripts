import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
import sys

# ================= 配置参数 =================
DB_HOST = "192.168.1.70"  # 务必直连真实数据库，不要连 PgBouncer
DB_PORT = "5432"

SUPER_USER = "postgres"
SUPER_PASS = "NhyCf2026^"

DB_PREFIX = "scdb_"

NEW_ADMIN = "scteamleader"
# NEW_ADMIN_PASS = "Dfcf2026^"  # 你可以自行修改

TOTAL_DBS = 100

# ============================================

def drop_all_databases():
    print(">>> ⚠️ 警告：正在连接底层数据库，准备执行批量删除操作！")
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=SUPER_USER,
            password=SUPER_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        # 开启自动提交，DROP DATABASE 必须在事务块外部执行
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
    except Exception as e:
        print(f"连接失败: {e}")
        sys.exit(1)

    print(f">>> 开始清理 {TOTAL_DBS} 个逻辑数据库及对应用户...")
    
    success_count = 0
    for i in range(1, TOTAL_DBS + 1):
        db_name = f"{DB_PREFIX}{i:03d}"
        # 这里假设所有数据库都使用同一个管理员账号，如果每个库有不同的用户，请修改为对应的用户名
        user_name = NEW_ADMIN  

        try:
            # 1. 强制断开该数据库的所有现有连接 (重要！否则删库会卡死或报错)
            terminate_sql = f"""
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE datname = '{db_name}' AND pid <> pg_backend_pid();
            """
            cursor.execute(terminate_sql)
            
            # 2. 删除数据库 (必须先删库，释放对应用户的所有权)
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name};")
            
            # 3. 删除对应的租户角色
            cursor.execute(f"DROP ROLE IF EXISTS {user_name};")
            
            success_count += 1
            if success_count % int(TOTAL_DBS / 10) == 0:
                print(f"[{success_count:03d}/{TOTAL_DBS}] 进度更新: 成功清理 {db_name} 及 {user_name}")
                
        except Exception as e:
            print(f"[{i:03d}/{TOTAL_DBS}] 清理 {db_name} 时发生错误: {e}")

    cursor.close()
    conn.close()
    print(f"\n清理完毕！成功删除了 {success_count} 套库和用户。系统已恢复纯净状态。")

if __name__ == "__main__":
    drop_all_databases()