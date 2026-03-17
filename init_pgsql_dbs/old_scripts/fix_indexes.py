import psycopg2

# --- 数据库连接配置 (必须直连真实的 PG，绕过 PgBouncer) ---
DB_HOST = "192.168.1.70"  
DB_PORT = "5432"
# 使用超级管理员执行底层表结构变更
SUPER_USER = "postgres"
SUPER_PASS = "NhyCf2026^"

# --- 业务配置 ---
DB_PREFIX = "scdb_"
DB_COUNT = 100
TABLE_NAME = "stock_k_lines"  # 模拟数据表名
TIME_COLUMN = "time"       # 表示时间的字段名，通常是 time 或 created_at

def fix_all_databases():
    print(f"🚀 开始遍历 100 个数据库，将表 {TABLE_NAME} 转换为 TimescaleDB 超表...")
    
    success_count = 0
    fail_count = 0

    for i in range(1, DB_COUNT + 1):
        dbname = f"{DB_PREFIX}{i:03d}"
        print(f"[{i:03d}/{DB_COUNT}] 正在优化 {dbname} ...", end=" ", flush=True)
        
        conn = None
        try:
            # 连接到具体的数据库
            conn = psycopg2.connect(
                host=DB_HOST, 
                port=DB_PORT, 
                user=SUPER_USER, 
                password=SUPER_PASS, 
                dbname=dbname
            )
            # DDL 操作（如建表、修改结构）建议开启自动提交
            conn.autocommit = True
            cur = conn.cursor()
            
            # 1. 检查表是否存在
            cur.execute(f"SELECT to_regclass('{TABLE_NAME}');")
            if cur.fetchone()[0] is None:
                print(f"⚠️ 跳过 (表 {TABLE_NAME} 不存在)")
                continue

            # 2. 将普通表转换为 TimescaleDB 超表
            # migrate_data=true 允许表中已有数据时进行转换
            # if_not_exists=true 防止重复转换报错
            convert_sql = f"""
                SELECT create_hypertable(
                    '{TABLE_NAME}', 
                    '{TIME_COLUMN}', 
                    migrate_data => true, 
                    if_not_exists => true
                );
            """
            cur.execute(convert_sql)
            
            # 3. (可选) 强制再补一个明确的复合索引或倒排索引，以防万一
            index_sql = f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_{TIME_COLUMN}_desc 
                ON {TABLE_NAME} ({TIME_COLUMN} DESC);
            """
            cur.execute(index_sql)

            print("✅ 转换并建立索引成功")
            success_count += 1
            
            cur.close()
        except Exception as e:
            # 捕获异常，防止一个库报错导致整个脚本退出
            print(f"❌ 失败: {e}")
            fail_count += 1
        finally:
            if conn:
                conn.close()

    print("\n" + "="*40)
    print("🎉 批量优化完成！")
    print(f"成功: {success_count} 个数据库")
    print(f"失败: {fail_count} 个数据库")
    print("="*40)

if __name__ == "__main__":
    fix_all_databases()