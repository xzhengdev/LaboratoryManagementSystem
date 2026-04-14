class AppError(Exception):
    # 自定义业务异常：
    # message 给前端展示
    # code 为 HTTP 状态码
    # error_code 为系统内部业务码
    def __init__(self, message, code=400, error_code=40000):
        super().__init__(message)
        self.message = message
        self.code = code
        self.error_code = error_code
