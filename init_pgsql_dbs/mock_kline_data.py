import psycopg2
from datetime import datetime, timedelta
import random
import time

# ================= 配置参数 =================
DB_HOST = "192.168.1.70"  # 务必直连真实数据库，不要连 PgBouncer
DB_PORT = "5432"               # DDL(建表)操作，保持直连底层引擎最稳妥

SUPER_USER = "postgres"
SUPER_PASS = "NhyCf2026^"

DB_PREFIX = "scdb_"

TOTAL_DBS = 100
DAYS_TO_MOCK = 30              # 模拟过去 30 天的数据

# ============================================

def generate_mock_klines(days):
    """生成模拟的股票日K线数据"""
    records = []
    # 以今天为基准，往前推 30 天
    start_date = datetime.now() - timedelta(days=days)
    
    # 设定一个初始基准价格
    current_close = 100.00 
    
    for i in range(days):
        record_time = start_date + timedelta(days=i)
        
        # 模拟价格波动 (开盘价通常在昨天收盘价附近)
        open_price = current_close + random.uniform(-1, 1)
        # 模拟当日收盘价
        close_price = open_price + random.uniform(-3, 3)
        # 最高价必须大于等于开盘和收盘中的最大值
        high_price = max(open_price, close_price) + random.uniform(0, 2)
        # 最低价必须小于等于开盘和收盘中的最小值
        low_price = min(open_price, close_price) - random.uniform(0, 2)
        # 模拟成交量
        volume = int(random.uniform(10000, 100000))
        
        records.append((
            record_time.strftime('%Y-%m-%d 00:00:00+00'), 
            'MOCK_STK', 
            round(open_price, 2), 
            round(high_price, 2), 
            round(low_price, 2), 
            round(close_price, 2), 
            volume
        ))
        
        current_close = close_price # 更新基准价格供下一天使用
        
    return records

def run_test_data_insertion():
    print(f">>> 准备在 {TOTAL_DBS} 个数据库中创建 K 线超表并写入 {DAYS_TO_MOCK} 天的测试数据...")
    
    # 建表与转换为超表的 SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS stock_k_lines (
        time TIMESTAMPTZ NOT NULL,
        symbol VARCHAR(10) NOT NULL,
        open_price NUMERIC(10, 2),
        high_price NUMERIC(10, 2),
        low_price NUMERIC(10, 2),
        close_price NUMERIC(10, 2),
        volume BIGINT
    );
    """
    # 转换为 TimescaleDB 超表 (按 time 字段进行时间分区)
    create_hypertable_sql = """
    SELECT create_hypertable('stock_k_lines', 'time', if_not_exists => TRUE);
    """
    
    insert_sql = """
    INSERT INTO stock_k_lines (time, symbol, open_price, high_price, low_price, close_price, volume)
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """

    success_count = 0

    for i in range(1, TOTAL_DBS + 1):
        db_name = f"{DB_PREFIX}{i:03d}"
        try:
            conn = psycopg2.connect(
                dbname=db_name,
                user=SUPER_USER,
                password=SUPER_PASS,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()

            # 1. 创建普通表
            cursor.execute(create_table_sql)
            
            # 2. 将普通表转换为时序超表
            cursor.execute(create_hypertable_sql)
            
            # 3. 生成并插入测试数据
            mock_data = generate_mock_klines(DAYS_TO_MOCK)
            cursor.executemany(insert_sql, mock_data)
            
            # 提交事务
            conn.commit()
            
            cursor.close()
            conn.close()
            
            success_count += 1
            if success_count % int(TOTAL_DBS / 10) == 0:
                print(f"[{success_count:03d}/{TOTAL_DBS}] 进度更新: 成功写入库 {db_name}")
                
        except Exception as e:
            print(f"[{i:03d}/{TOTAL_DBS}] 在 {db_name} 操作时发生错误: {e}")

    print(f"\n>>> 测试数据初始化完成！成功写入 {success_count} 个数据库。")

if __name__ == "__main__":
    run_test_data_insertion()