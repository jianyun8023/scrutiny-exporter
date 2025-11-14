.PHONY: help build run test clean docker-build docker-run docker-stop

# 默认目标
help:
	@echo "Scrutiny Prometheus Exporter - 可用命令:"
	@echo ""
	@echo "  make build          - 构建 Docker 镜像"
	@echo "  make run            - 本地运行（需要先安装依赖）"
	@echo "  make test           - 运行测试脚本"
	@echo "  make docker-build   - 构建 Docker 镜像"
	@echo "  make docker-run     - 使用 Docker Compose 启动"
	@echo "  make docker-stop    - 停止 Docker 容器"
	@echo "  make docker-logs    - 查看 Docker 日志"
	@echo "  make clean          - 清理临时文件"
	@echo ""

# 本地运行（需要先安装依赖）
run:
	@echo "启动 Scrutiny Prometheus Exporter..."
	python3 scrutiny_prometheus_exporter.py

# 运行测试
test:
	@echo "运行测试脚本..."
	chmod +x test_exporter.sh
	./test_exporter.sh

# 构建 Docker 镜像
build docker-build:
	@echo "构建 Docker 镜像..."
	docker build -t scrutiny-prometheus-exporter:latest .

# Docker Compose 启动
docker-run:
	@echo "使用 Docker Compose 启动..."
	docker-compose up -d
	@echo "✓ Docker 容器已启动"
	@echo "  查看日志: make docker-logs"
	@echo "  查看 metrics: curl http://localhost:9900/metrics"

# Docker Compose 停止
docker-stop:
	@echo "停止 Docker 容器..."
	docker-compose down
	@echo "✓ Docker 容器已停止"

# Docker 日志
docker-logs:
	docker-compose logs -f

# 清理
clean:
	@echo "清理临时文件..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ 清理完成"

