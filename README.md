# sc_env_scripts
创建环境的各种脚本

# 【Web0】配置 docker_test_webs\fastapi 的 conda 环境
cd ./sc_env_scripts/docker_test_webs/fastapi
conda create -n test_web0 python=3.12 -y
conda activate test_web0
pip install -r requirements.txt
# 运行 
uvicorn main:app --host 0.0.0.0 --port 8180
# 验证
http://localhost:8180/
http://localhost:8180/docs

# 【Web1】配置 docker_test_webs\flask 的 conda 环境
cd ./sc_env_scripts/docker_test_webs/flask
conda create -n test_web1 python=3.12 -y
conda activate test_web1
pip install -r requirements.txt
# 运行 (仅限 linux 平台)
gunicorn -w 4 -b 0.0.0.0:8181 app:app
# 运行 
IDE 工具中直接运行
# 验证
http://localhost:8181/

# 【Web2】配置 docker_test_webs\django 的 conda 环境
cd ./sc_env_scripts/docker_test_webs/django
conda create -n test_web2 python=3.12 -y
conda activate test_web2
pip install -r requirements.txt
# 运行 
python manage.py runserver 0.0.0.0:8182
# 验证
http://localhost:8182/
