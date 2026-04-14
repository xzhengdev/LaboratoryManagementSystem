from app import create_app


# 这是“无热重载”的启动脚本，适合后台常驻运行或前端联调。
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
