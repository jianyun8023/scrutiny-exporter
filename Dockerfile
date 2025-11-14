FROM python:3.11-slim

LABEL maintainer="Scrutiny Exporter"
LABEL description="Prometheus Exporter for Scrutiny SMART monitoring"

# 设置工作目录
WORKDIR /app

# 安装 curl 用于健康检查
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY scrutiny_prometheus_exporter.py .

# 设置可执行权限
RUN chmod +x scrutiny_prometheus_exporter.py

# 暴露端口
EXPOSE 9900

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9900/metrics || exit 1

# 运行 exporter
CMD ["python", "scrutiny_prometheus_exporter.py"]

