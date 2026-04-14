from flask import jsonify


def success(data=None, message="success", code=0):
    # 成功响应统一结构，前端约定 code === 0 视为成功。
    return jsonify({"code": code, "message": message, "data": data})


def fail(message="error", http_status=400, code=40000, data=None):
    # 失败响应统一结构，方便前端统一 toast 与错误处理。
    response = jsonify({"code": code, "message": message, "data": data})
    response.status_code = http_status
    return response
