import json
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import threading
import time
import random
import sys, os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

class TSDBManager:
    def __init__(self, config_path='pgsql_test.json'):
        """初始化管理器，加载 JSON 配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.cfg = json.load(f)
        except Exception as e:
            print(f"❌ 无法读取配置文件 {config_path}: {e}")
            sys.exit(1)

    # ================= 私有辅助方法 =================
    
    def _get_super_conn(self, dbname="defaultdb"):
        """获取超级管理员直连底层的连接 (注意: 默认库已改为 defaultdb)"""
        conn = psycopg2.connect(
            host=self.cfg["DB_HOST"],
            port=self.cfg["DB_PORT"],
            user=self.cfg["SUPER_USER"],
            password=self.cfg["SUPER_PASS"],
            dbname=dbname
        )
        return conn

    def _get_leader_conn(self, dbname, use_pgbouncer=False, timeout=None):
        """获取业务账号的连接 (可选择是否走 PgBouncer)"""
        host = self.cfg["PGBOUNCER_HOST"] if use_pgbouncer else self.cfg["DB_HOST"]
        port = self.cfg["PGBOUNCER_PORT"] if use_pgbouncer else self.cfg["DB_PORT"]
        
        kwargs = {
            "host": host,
            "port": port,
            "user": self.cfg["DB_LEADER"],
            "password": self.cfg["DB_LEADER_PWD"],
            "dbname": dbname
        }
        if timeout:
            kwargs["connect_timeout"] = timeout
            
        return psycopg2.connect(**kwargs)

    def _generate_mock_klines(self, days):
        """生成模拟的股票日K线数据"""
        records = []
        start_date = datetime.now() - timedelta(days=days)
        current_close = 100.00 
        
        for i in range(days):
            record_time = start_date + timedelta(days=i)
            open_price = current_close + random.uniform(-1, 1)
            close_price = open_price + random.uniform(-3, 3)
            high_price = max(open_price, close_price) + random.uniform(0, 2)
            low_price = min(open_price, close_price) - random.uniform(0, 2)
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
            current_close = close_price
        return records

    # ================= 业务公开方法 =================

    def init_time_dbs(self):
        """功能 1: 初始化所有时序数据库及账号"""
        print(f">>> 正在连接底层主数据库 ({self.cfg['DB_HOST']}) 初始化全局配置...")
        conn = self._get_super_conn()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        leader = self.cfg["DB_LEADER"]
        super_user = self.cfg["SUPER_USER"]
        
        # 仅当业务账号不同于超级账号时才创建，避免报错
        if leader != super_user:
            cur.execute(f"SELECT 1 FROM pg_roles WHERE rolname='{leader}'")
            if not cur.fetchone():
                print(f">>> 正在创建管理员账号: {leader} ...")
                cur.execute(f"CREATE ROLE {leader} WITH LOGIN PASSWORD '{self.cfg['DB_LEADER_PWD']}';")
                cur.execute(f"ALTER ROLE {leader} SET timezone TO '{self.cfg['TIMEZONE']}';")
        
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        existing_dbs = [row[0] for row in cur.fetchall()]

        db_count = self.cfg["DB_COUNT"]
        print(f">>> 开始创建 {db_count} 个数据库...")
        for i in range(1, db_count + 1):
            dbname = f"{self.cfg['DB_PREFIX']}{i}"
            if dbname not in existing_dbs:
                cur.execute(f"CREATE DATABASE {dbname} WITH OWNER {leader} ENCODING 'UTF8';")
                cur.execute(f"ALTER DATABASE {dbname} SET timezone TO '{self.cfg['TIMEZONE']}';")
        cur.close()
        conn.close()

        print("\n>>> 开始为每个数据库安装 TimescaleDB 扩展...")
        for i in range(1, db_count + 1):
            dbname = f"{self.cfg['DB_PREFIX']}{i}"
            try:
                conn = self._get_super_conn(dbname)
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cur = conn.cursor()
                cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                cur.close()
                conn.close()
            except Exception as e:
                print(f"❌ 初始化 {dbname} 失败: {e}")

        print(f"\n[OK] {db_count} 个时序数据库初始化完成！")

    def mock_kline_data(self):
        """功能 2: 创建超表并灌入模拟数据"""
        db_count = self.cfg["DB_COUNT"]
        days = self.cfg["DAYS_TO_MOCK"]
        table = self.cfg["TABLE_NAME"]
        time_col = self.cfg["TIME_COLUMN"]
        
        print(f">>> 准备在 {db_count} 个数据库中创建 K 线超表并写入 {days} 天的测试数据...")
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            {time_col} TIMESTAMPTZ NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            open_price NUMERIC(10, 2),
            high_price NUMERIC(10, 2),
            low_price NUMERIC(10, 2),
            close_price NUMERIC(10, 2),
            volume BIGINT
        );
        """
        create_hypertable_sql = f"SELECT create_hypertable('{table}', '{time_col}', if_not_exists => TRUE);"
        insert_sql = f"INSERT INTO {table} ({time_col}, symbol, open_price, high_price, low_price, close_price, volume) VALUES (%s, %s, %s, %s, %s, %s, %s);"

        success_count = 0
        for i in range(1, db_count + 1):
            db_name = f"{self.cfg['DB_PREFIX']}{i}"
            try:
                # 灌库属于大批量直连写入操作，绕开 PgBouncer 直接写底层可以提升速度
                conn = self._get_leader_conn(db_name, use_pgbouncer=False)
                cursor = conn.cursor()
                cursor.execute(create_table_sql)
                cursor.execute(create_hypertable_sql)
                
                mock_data = self._generate_mock_klines(days)
                cursor.executemany(insert_sql, mock_data)
                
                conn.commit()
                cursor.close()
                conn.close()
                
                success_count += 1
                if success_count % int(db_count / 10) == 0:
                    print(f"[{success_count:03d}/{db_count}] 进度更新: 成功写入库 {db_name}")
            except Exception as e:
                print(f"[{i:03d}/{db_count}] 在 {db_name} 操作时发生错误: {e}")

        print(f"\n>>> 测试数据初始化完成！成功写入 {success_count} 个数据库。")

    def fix_indexes(self):
        """功能 3: 检查并修复底层超表和倒排索引"""
        db_count = self.cfg["DB_COUNT"]
        table = self.cfg["TABLE_NAME"]
        time_col = self.cfg["TIME_COLUMN"]
        
        print(f">>> 开始遍历 {db_count} 个数据库，确保建立倒排索引...")
        success_count = 0

        for i in range(1, db_count + 1):
            dbname = f"{self.cfg['DB_PREFIX']}{i}"
            try:
                conn = self._get_super_conn(dbname)
                conn.autocommit = True
                cur = conn.cursor()
                
                cur.execute(f"SELECT to_regclass('{table}');")
                if cur.fetchone()[0] is None:
                    continue

                cur.execute(f"SELECT create_hypertable('{table}', '{time_col}', migrate_data => true, if_not_exists => true);")
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{time_col}_desc ON {table} ({time_col} DESC);")

                success_count += 1
                cur.close()
                conn.close()
            except Exception as e:
                print(f"❌ 修复 {dbname} 失败: {e}")

        print(f"\n[OK] 批量优化完成！成功优化: {success_count} 个数据库")

    def test_pgbouncer(self):
        """功能 4: PgBouncer 高并发查询压测"""
        concurrency = self.cfg["CONCURRENCY"]
        total_req = self.cfg["TOTAL_REQUESTS"]
        db_count = self.cfg["DB_COUNT"]
        query = f"SELECT * FROM {self.cfg['TABLE_NAME']} ORDER BY {self.cfg['TIME_COLUMN']} DESC LIMIT 100;"
        
        print(f">>> 🚀 开始 PgBouncer 高并发压测...")
        print(f">>> 目标: {self.cfg['PGBOUNCER_HOST']}:{self.cfg['PGBOUNCER_PORT']} | 并发: {concurrency} | 请求: {total_req}")

        stats = {'success': 0, 'fail': 0, 'time': 0}
        lock = threading.Lock()

        def _worker(req_id):
            target_db = f"{self.cfg['DB_PREFIX']}{random.randint(1, db_count)}"
            start_time = time.time()
            conn = None
            try:
                # 压测必须走 PgBouncer
                conn = self._get_leader_conn(target_db, use_pgbouncer=True, timeout=5)
                cur = conn.cursor()
                cur.execute(query)
                _ = cur.fetchall()
                cur.close()
                with lock:
                    stats['success'] += 1
                    stats['time'] += (time.time() - start_time)
            except Exception:
                with lock:
                    stats['fail'] += 1
            finally:
                if conn: conn.close()

        start_wall = time.time()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(_worker, i) for i in range(total_req)]
            completed = 0
            for _ in as_completed(futures):
                completed += 1
                if completed % int(total_req/10) == 0:
                    print(f"进度: {completed} / {total_req} 已完成...")
        wall_duration = time.time() - start_wall

        print("\n" + "="*40)
        print(f"✅ 成功: {stats['success']} | ❌ 失败/超时: {stats['fail']}")
        print(f"⏱️ 总耗时: {wall_duration:.2f} 秒")
        if stats['success'] > 0:
            print(f"🚀 QPS: {total_req / wall_duration:.2f} req/s | 延迟: {(stats['time'] / stats['success']) * 1000:.2f} ms")
        print("="*40)

    def drop_time_dbs(self):
        """功能 5: 危险操作 - 删库跑路"""
        print("\n⚠️ 警告：准备执行批量删除操作！")
        confirm = input("输入 'yes' 确认删除所有数据库及数据: ")
        if confirm.lower() != 'yes':
            print("已取消删除操作。")
            return

        conn = self._get_super_conn()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        db_count = self.cfg["DB_COUNT"]
        success_count = 0
        
        for i in range(1, db_count + 1):
            db_name = f"{self.cfg['DB_PREFIX']}{i}"
            try:
                cursor.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid();")
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name};")
                success_count += 1
                if success_count % int(db_count / 10) == 0:
                    print(f"[{success_count:03d}/{db_count}] 成功清理数据库 {db_name}")
            except Exception as e:
                print(f"❌ 清理 {db_name} 时发生错误: {e}")
                
        if self.cfg["DB_LEADER"] != self.cfg["SUPER_USER"]:
            try:
                cursor.execute(f"DROP ROLE IF EXISTS {self.cfg['DB_LEADER']};")
                print(f"✅ 管理员角色 {self.cfg['DB_LEADER']} 已删除。")
            except Exception as e:
                print(f"❌ 删除角色时发生错误: {e}")

        cursor.close()
        conn.close()
        print(f"\n[OK] 清理完毕！成功删除了 {success_count} 套库。")

# ================= 交互式菜单 =================
if __name__ == "__main__":

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    JSON_FILE = os.path.join(BASE_DIR, 'pgsql_test.json')

    manager = TSDBManager(JSON_FILE)
    
    menu = """
========================================
 PostgreSQL / TimescaleDB 管理套件
========================================
 1. 初始化时序数据库及账号 (Init DBs)
 2. 灌入模拟 K 线数据 (Mock Data)
 3. 检查/修复超表及时间倒排索引 (Fix Indexes)
 4. 执行 PgBouncer 高并发压测 (Stress Test)
 5. 危险：清空并删除所有测试库 (Drop DBs)
 0. 退出
========================================
"""
    while True:
        print(menu)
        choice = input("请输入对应的数字执行操作: ").strip()
        
        if choice == '1':
            manager.init_time_dbs()
        elif choice == '2':
            manager.mock_kline_data()
        elif choice == '3':
            manager.fix_indexes()
        elif choice == '4':
            manager.test_pgbouncer()
        elif choice == '5':
            manager.drop_time_dbs()
        elif choice == '0':
            print("退出管理套件。")
            break
        else:
            print("无效输入，请重新选择。")

