# sc_env_scripts
创建、调试、测试 docker 环境的各种脚本

# 运行环境说明
## 【Web0】配置 docker_test_webs\fastapi 的 conda 环境
cd ./sc_env_scripts/docker_test_webs/fastapi <br>
conda create -n test_web0 python=3.12 -y <br>
conda activate test_web0 <br>
pip install -r requirements.txt <br>
### 运行 
uvicorn main:app --host 0.0.0.0 --port 8180 <br>
### 验证
http://localhost:8180/
http://localhost:8180/docs

## 【Web1】配置 docker_test_webs\flask 的 conda 环境
cd ./sc_env_scripts/docker_test_webs/flask <br>
conda create -n test_web1 python=3.12 -y <br>
conda activate test_web1 <br>
pip install -r requirements.txt <br>
### 运行 (仅限 linux 平台)
gunicorn -w 4 -b 0.0.0.0:8181 app:app <br>
### 运行 
IDE 工具中直接运行 <br>
### 验证
http://localhost:8181/ <br>

## 【Web2】配置 docker_test_webs\django 的 conda 环境
cd ./sc_env_scripts/docker_test_webs/django <br>
conda create -n test_web2 python=3.12 -y <br>
conda activate test_web2 <br>
pip install -r requirements.txt <br>
### 运行 
python manage.py runserver 0.0.0.0:8182 <br>
### 验证
http://localhost:8182/ <br>

## init_pgsql_dbas 运行环境
conda create -n init_pgsql_dbs python=3.12 -y <br>
conda activate init_pgsql_dbs <br>
pip install -r requirements.txt <br>

# ---------------------------------------------------
# init_pgsql_dbs 工具集使用说明
init_time_dbs.py    -> 创建 n 个时序数据库及每个库的 DBA <br>
mock_kline_data.py  -> 生成模拟的 K 线数据 <br>
fix_indexes.py      -> 调整索引 ( Optional ) <br>
test_pgbouncer.py   -> 并发压力测试 <br>
drop_time_dbs.py    -> 删除 n 个时序数据库及每个库的 DBA <br>
# ---------------------------------------------------