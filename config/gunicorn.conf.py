# gunicorn.conf.py
import multiprocessing

# 绑定地址和端口
bind = "0.0.0.0:5000"

# 工作进程数，根据CPU核心数计算
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 每个工作进程的最大并发连接数
worker_connections = 1000

# 请求超时时间（秒）
timeout = 120

# 每个worker处理的最大请求数后重启，防止内存泄漏
max_requests = 1000

# 重启时的随机抖动，避免所有worker同时重启
max_requests_jitter = 100

# 预加载应用
preload_app = True

# 日志配置
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"

# 进程名
proc_name = "google-sheet-validator"

# 优雅重启超时时间
graceful_timeout = 30

# Keep-Alive时间
keepalive = 5