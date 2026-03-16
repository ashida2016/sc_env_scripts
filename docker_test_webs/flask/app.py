# 欢迎程序
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Welcome to Flask on Docker! (Python 3.12)"

if  __name__ == "__main__":
    app.run(host="0.0.0.0", port=8181, debug=True)

