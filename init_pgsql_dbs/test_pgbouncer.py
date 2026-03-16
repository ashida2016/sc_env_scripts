import psycopg2
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 核心配置区 ---
# 必须指向 PgBouncer 的 IP 和端口！
PGBOUNCER_HOST = "192.168.1.71"  
PGBOUNCER_PORT = "5432"

DB_LEADER = "scteamleader"
DB_LEADER_PWD = "Dfcf2026^"  

DB_PREFIX = "scdb_"
DB_COUNT = 100

# --- 压测参数 ---
# 并发线程数（模拟同时发起请求的客户端数量）
CONCURRENCY = 1  
# 总请求次数
TOTAL_REQUESTS = 1  

# --- 查询语句配置 ---
# 请将这里替换为你实际的 K 线表名和查询逻辑。
# 这里模拟一个典型的时序查询：获取某只股票最近 100 条 K 线数据并按时间倒序
TEST_QUERY = """
    SELECT * FROM stock_k_lines 
    ORDER BY time DESC 
    LIMIT 100;
"""
# 如果你的表名不同，或者想先测纯连接性能，可以用这个代替：
# TEST_QUERY = "SELECT NOW(), pg_sleep(0.01);"

# 统计变量
success_count = 0
fail_count = 0
total_time = 0
lock = threading.Lock()

def simulate_client_query(request_id):
    """模拟单个客户端发起一次完整的连接、查询、断开流程"""
    global success_count, fail_count, total_time
    
    # 随机挑选一个数据库 (scdb_001 ~ scdb_100)
    target_db = f"{DB_PREFIX}{random.randint(1, DB_COUNT):03d}"
    
    start_time = time.time()
    conn = None
    try:
        # 连接到 PgBouncer
        conn = psycopg2.connect(
            host=PGBOUNCER_HOST,
            port=PGBOUNCER_PORT,
            user=DB_LEADER,
            password=DB_LEADER_PWD,
            dbname=target_db,
            connect_timeout=5
        )
        cur = conn.cursor()
        
        # 执行查询
        cur.execute(TEST_QUERY)
        # 强制抓取结果以确保网络 IO 完成
        _ = cur.fetchall() 
        
        cur.close()
        
        with lock:
            success_count += 1
            total_time += (time.time() - start_time)
            
    except Exception as e:
        with lock:
            fail_count += 1
        # 如果你想看具体的报错（如连接超时），可以取消下面这行的注释
        print(f"请求 {request_id} 失败: {e}")
    finally:
        if conn:
            conn.close() # 释放连接，PgBouncer 会将其回收进入连接池

def run_stress_test():
    print(f"🚀 开始 PgBouncer 高并发压测...")
    print(f"👉 目标: {PGBOUNCER_HOST}:{PGBOUNCER_PORT}")
    print(f"👉 并发数 (Threads): {CONCURRENCY}")
    print(f"👉 总请求量: {TOTAL_REQUESTS}\n")
    
    start_wall_time = time.time()
    
    # 使用线程池狂暴拉起并发请求
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(simulate_client_query, i) for i in range(TOTAL_REQUESTS)]
        
        # 显示进度条逻辑 (简单打印)
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 500 == 0:
                print(f"进度: {completed} / {TOTAL_REQUESTS} 已完成...")

    end_wall_time = time.time()
    wall_duration = end_wall_time - start_wall_time
    
    # --- 打印压测报告 ---
    print("\n" + "="*40)
    print("📊 压测结果报告")
    print("="*40)
    print(f"✅ 成功请求: {success_count}")
    print(f"❌ 失败/超时: {fail_count}")
    print(f"⏱️  总耗时:   {wall_duration:.2f} 秒")
    
    if success_count > 0:
        qps = TOTAL_REQUESTS / wall_duration
        avg_latency = (total_time / success_count) * 1000
        print(f"🚀 QPS (每秒查询): {qps:.2f} req/s")
        print(f"延迟 (平均响应): {avg_latency:.2f} ms")
    print("="*40)

if __name__ == "__main__":
    run_stress_test()