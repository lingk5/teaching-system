from app import create_app  # 这样导入没问题，因为 run.py 在 backend 根目录
import os

app = create_app()

if __name__ == '__main__':
    # 从环境变量读取端口号，默认 5000
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    print(f"🚀 服务器启动在端口 {port}")
    print(f"📱 访问地址：http://127.0.0.1:{port}/pages/login.html")
    app.run(debug=True, port=port)