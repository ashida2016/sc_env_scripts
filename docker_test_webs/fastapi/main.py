# 欢迎程序
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI on Docker! (Python 3.12)"}
