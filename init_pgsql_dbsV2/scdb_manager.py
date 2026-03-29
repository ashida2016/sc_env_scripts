import json
import time
import random
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

class SCDBBase:
    """基础类：负责加载配置和提供连接"""
    def __init__(self, config_path="scdb_config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.admin_cfg = self.config["db_admin"]
        self.target_db = self.config["target_db"]

    def get_connection(self, dbname=None, user=None, password=None):
        """获取数据库连接，支持动态切换数据库和用户"""
        conn_params = self.admin_cfg.copy()
        if dbname: conn_params["dbname"] = dbname
        if user: conn_params["user"] = user
        if password: conn_params["password"] = password
        return psycopg2.connect(**conn_params)

class SCDBInitializer(SCDBBase):
    """数据库初始化类"""
    
    def setup_database_and_roles(self):
        """步骤 1: 创建业务数据库和角色（需在 defaultdb 下执行）"""
        print(f"正在准备数据库 {self.target_db} 和基础角色...")
        conn = self.get_connection()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT) # 建库必须开启自动提交
        cursor = conn.cursor()
        
        try:
            # 创建数据库
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.target_db}'")
            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE {self.target_db}")
            
            # 创建用户
            roles = self.config["roles"]
            for role_type, creds in roles.items():
                u, p = creds["user"], creds["password"]
                cursor.execute(f"SELECT 1 FROM pg_roles WHERE rolname = '{u}'")
                if not cursor.fetchone():
                    cursor.execute(f"CREATE ROLE {u} WITH LOGIN PASSWORD '{p}'")
                    
        finally:
            cursor.close()
            conn.close()

    def _init_single_schema(self, schema_id):
        """单个 Schema 的创建逻辑（供多线程调用）"""
        schema_name = f"sch_{schema_id:04d}"
        stock_code = f"{random.randint(1000, 999999):06d}.SZ"
        stock_name = f"模拟股票_{schema_id}"
        roles = self.config["roles"]
        
        # 每个线程必须建立独立连接
        conn = self.get_connection(dbname=self.target_db)
        cursor = conn.cursor()
        try:
            # 1. 创建 Schema 并分配权限
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")
            cursor.execute(f"GRANT USAGE ON SCHEMA {schema_name} TO {roles['fetcher']['user']};")
            cursor.execute(f"GRANT ALL ON SCHEMA {schema_name} TO {roles['writer']['user']};")
            
            # 2. 创建标签表 (Metadata)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.schema_tags (
                    id SERIAL PRIMARY KEY,
                    stock_code VARCHAR(20) NOT NULL,
                    stock_name VARCHAR(100),
                    db_version VARCHAR(10) DEFAULT '1.0',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 插入或更新标签数据
            cursor.execute(f"""
                INSERT INTO {schema_name}.schema_tags (stock_code, stock_name) 
                VALUES (%s, %s) ON CONFLICT DO NOTHING;
            """, (stock_code, stock_name))

            # 3. 创建 K 线表并转换为 TimescaleDB 超表
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.daily_kline (
                    time TIMESTAMP WITH TIME ZONE NOT NULL,
                    open NUMERIC(10, 2),
                    high NUMERIC(10, 2),
                    low NUMERIC(10, 2),
                    close NUMERIC(10, 2),
                    volume BIGINT
                );
            """)
            
            # 将普通表转换为时序超表 (按时间分区，时间块设为 1 个月)
            cursor.execute(f"""
                SELECT create_hypertable('{schema_name}.daily_kline', 'time', 
                chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);
            """)

            # 4. 配置表级读写权限
            cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema_name} TO {roles['fetcher']['user']};")
            cursor.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema_name} TO {roles['writer']['user']};")
            # 确保未来的表也有权限
            cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON TABLES TO {roles['fetcher']['user']};")
            cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT ALL ON TABLES TO {roles['writer']['user']};")

            conn.commit()
            return f"{schema_name} 创建成功 ({stock_code})"
        except Exception as e:
            conn.rollback()
            return f"{schema_name} 创建失败: {str(e)}"
        finally:
            cursor.close()
            conn.close()

    def run(self):
        """执行完整初始化流程"""
        self.setup_database_and_roles()
        
        # 激活 TimescaleDB 插件
        conn = self.get_connection(dbname=self.target_db)
        cursor = conn.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
        conn.commit()
        cursor.close()
        conn.close()

        num_schemas = self.config["init_params"]["num_schemas"]
        max_workers = self.config["init_params"]["max_workers"]
        
        print(f"开始多线程创建 {num_schemas} 个 Schema (并发数: {max_workers})...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._init_single_schema, i+1) for i in range(num_schemas)]
            for future in as_completed(futures):
                print(future.result())
                
        print(f"初始化完成，耗时: {time.time() - start_time:.2f} 秒")


class SCDBTester(SCDBBase):
    """数据库测试类"""
    
    def test_connectivity_and_fetch_tags(self):
        """测试连通性并获取所有 Schema 的标签"""
        print("\n--- 测试连通性与读取标签 ---")
        writer_cfg = self.config["roles"]["writer"]
        try:
            conn = self.get_connection(dbname=self.target_db, user=writer_cfg["user"], password=writer_cfg["password"])
            cursor = conn.cursor()
            
            # 获取所有我们创建的 Schema
            cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'sch_%';")
            schemas = [row[0] for row in cursor.fetchall()]
            print(f"成功连接！共发现 {len(schemas)} 个目标 Schema。")
            
            for schema in schemas:
                cursor.execute(f"SELECT stock_code, stock_name, created_at FROM {schema}.schema_tags LIMIT 1;")
                tag = cursor.fetchone()
                if tag:
                    print(f"[{schema}] 代码: {tag[0]}, 名称: {tag[1]}, 创建于: {tag[2].strftime('%Y-%m-%d %H:%M:%S')}")
                    
            cursor.close()
            conn.close()
            return schemas
        except Exception as e:
            print(f"连通性测试失败: {e}")
            return []

    def simulate_mock_data(self, schemas):
        """为指定的 Schemas 模拟写入 K 线数据"""
        mock_days = self.config["test_params"]["mock_days"]
        print(f"\n--- 为 {len(schemas)} 个库模拟 {mock_days} 天日线数据 ---")
        
        writer_cfg = self.config["roles"]["writer"]
        
        def _insert_mock_data(schema_name):
            conn = self.get_connection(dbname=self.target_db, user=writer_cfg["user"], password=writer_cfg["password"])
            cursor = conn.cursor()
            base_price = random.uniform(10, 100)
            base_date = datetime.now() - timedelta(days=mock_days)
            
            data_tuples = []
            for i in range(mock_days):
                curr_date = base_date + timedelta(days=i)
                open_p = base_price * random.uniform(0.95, 1.05)
                close_p = open_p * random.uniform(0.95, 1.05)
                high_p = max(open_p, close_p) * random.uniform(1.0, 1.05)
                low_p = min(open_p, close_p) * random.uniform(0.95, 1.0)
                vol = int(random.uniform(10000, 1000000))
                data_tuples.append((curr_date, open_p, high_p, low_p, close_p, vol))
            
            # 批量插入
            args_str = ','.join(cursor.mogrify("(%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in data_tuples)
            try:
                cursor.execute(f"INSERT INTO {schema_name}.daily_kline (time, open, high, low, close, volume) VALUES {args_str}")
                conn.commit()
                return f"{schema_name}: 成功写入 {mock_days} 条模拟数据"
            except Exception as e:
                conn.rollback()
                return f"{schema_name}: 写入失败 {e}"
            finally:
                cursor.close()
                conn.close()

        # 使用多线程加速数据模拟
        with ThreadPoolExecutor(max_workers=self.config["init_params"]["max_workers"]) as executor:
            futures = [executor.submit(_insert_mock_data, schema) for schema in schemas]
            for future in as_completed(futures):
                print(future.result())

    def run_stress_test(self, schemas):
        """简单的读写并发压力测试"""
        concurrency = self.config["test_params"]["stress_concurrency"]
        queries = self.config["test_params"]["stress_queries"]
        print(f"\n--- 开始压力测试 (并发数: {concurrency}, 总请求: {queries}) ---")
        
        fetcher_cfg = self.config["roles"]["fetcher"]
        
        def _random_query():
            schema = random.choice(schemas)
            conn = self.get_connection(dbname=self.target_db, user=fetcher_cfg["user"], password=fetcher_cfg["password"])
            cursor = conn.cursor()
            try:
                start = time.time()
                # 模拟查询：获取某只股票最近 5 天的平均收盘价
                cursor.execute(f"""
                    SELECT AVG(close) FROM {schema}.daily_kline 
                    ORDER BY time DESC LIMIT 5;
                """)
                cursor.fetchone()
                return time.time() - start
            finally:
                cursor.close()
                conn.close()

        start_time = time.time()
        success = 0
        latencies = []
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(_random_query) for _ in range(queries)]
            for future in as_completed(futures):
                try:
                    latencies.append(future.result())
                    success += 1
                except Exception:
                    pass
        
        total_time = time.time() - start_time
        print(f"压测完成! 耗时: {total_time:.2f}s, 成功率: {success}/{queries}")
        if latencies:
            print(f"平均延迟: {sum(latencies)/len(latencies)*1000:.2f} ms")


if __name__ == "__main__":
    # 1. 执行初始化
    initializer = SCDBInitializer()
    initializer.run()
    
    # 2. 执行测试
    tester = SCDBTester()
    schemas = tester.test_connectivity_and_fetch_tags()
    if schemas:
        tester.simulate_mock_data(schemas)
        tester.run_stress_test(schemas)