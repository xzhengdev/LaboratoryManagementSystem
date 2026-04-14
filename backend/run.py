from app import create_app


# 本文件是开发环境默认启动入口。
# 如果只是想本地直接把 Flask 跑起来，执行 python run.py 即可。
app = create_app()


if __name__ == "__main__":
    # 监听 0.0.0.0 便于本机和局域网设备共同访问。
    app.run(host="0.0.0.0", port=5000, debug=True)
