#!/bin/bash
# Scrutiny Prometheus Exporter 快速测试脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
SCRUTINY_API="${SCRUTINY_API_URL:-https://smart.pve.icu}"
EXPORTER_PORT="${EXPORTER_PORT:-9900}"
METRICS_URL="http://localhost:${EXPORTER_PORT}/metrics"

echo "=========================================="
echo "Scrutiny Prometheus Exporter 测试"
echo "=========================================="
echo ""

# 检查依赖
echo "1. 检查依赖..."
command -v python3 >/dev/null || { echo -e "${RED}✗${NC} python3 未安装"; exit 1; }
command -v curl >/dev/null || { echo -e "${RED}✗${NC} curl 未安装"; exit 1; }
echo -e "${GREEN}✓${NC} 依赖检查通过"
echo ""

# 检查 Python 依赖
echo "2. 检查 Python 依赖..."
if ! pip3 show prometheus-client requests >/dev/null 2>&1; then
    echo "安装依赖..."
    pip3 install -q -r requirements.txt
fi
echo -e "${GREEN}✓${NC} Python 依赖已安装"
echo ""

# 测试 API 连接
echo "3. 测试 Scrutiny API..."
if curl -sf --max-time 10 "${SCRUTINY_API}/api/summary" >/dev/null; then
    echo -e "${GREEN}✓${NC} API 连接正常"
else
    echo -e "${RED}✗${NC} API 连接失败: ${SCRUTINY_API}"
    exit 1
fi
echo ""

# 启动 exporter
echo "4. 启动 Exporter..."
if lsof -i :${EXPORTER_PORT} >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC} 端口 ${EXPORTER_PORT} 已被占用，尝试停止..."
    pkill -f "scrutiny_prometheus_exporter.py" || true
    sleep 2
fi

python3 ./scrutiny_prometheus_exporter.py \
    --api-url "${SCRUTINY_API}" \
    --port "${EXPORTER_PORT}" \
    --log-level INFO > /tmp/scrutiny_exporter.log 2>&1 &
EXPORTER_PID=$!

sleep 5

if ps -p $EXPORTER_PID >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Exporter 启动成功 (PID: $EXPORTER_PID)"
else
    echo -e "${RED}✗${NC} Exporter 启动失败"
    cat /tmp/scrutiny_exporter.log
    exit 1
fi
echo ""

# 测试 metrics 端点
echo "5. 测试 Metrics 端点..."
sleep 3

if curl -sf "${METRICS_URL}" >/dev/null; then
    echo -e "${GREEN}✓${NC} Metrics 端点可访问"
    
    metrics=$(curl -s "${METRICS_URL}")
    total=$(echo "$metrics" | grep -v "^#" | grep -v "^$" | wc -l | tr -d ' ')
    smart_count=$(echo "$metrics" | grep -c "scrutiny_smart_attr_" || echo "0")
    
    echo ""
    echo "统计信息:"
    echo "  总 metrics 数: ${total}"
    echo "  SMART 属性数: ${smart_count}"
    echo ""
    echo "示例 metrics:"
    echo "$metrics" | grep -E "scrutiny_device_info|scrutiny_smart_temperature_celsius" | head -2
else
    echo -e "${RED}✗${NC} Metrics 端点不可访问"
    kill $EXPORTER_PID 2>/dev/null || true
    exit 1
fi
echo ""

# 验证核心 metrics
echo "6. 验证核心 Metrics..."
required=(
    "scrutiny_device_info"
    "scrutiny_smart_temperature_celsius"
    "scrutiny_devices_total"
)

all_ok=true
for metric in "${required[@]}"; do
    if echo "$metrics" | grep -q "$metric"; then
        echo -e "${GREEN}✓${NC} $metric"
    else
        echo -e "${RED}✗${NC} $metric (缺失)"
        all_ok=false
    fi
done

if [ "$all_ok" = true ]; then
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    echo "=========================================="
    echo ""
    echo "Exporter 运行中 (PID: $EXPORTER_PID)"
    echo "Metrics: ${METRICS_URL}"
    echo "日志: tail -f /tmp/scrutiny_exporter.log"
    echo "停止: kill $EXPORTER_PID"
else
    echo ""
    echo -e "${RED}✗ 部分测试失败${NC}"
    kill $EXPORTER_PID 2>/dev/null || true
    exit 1
fi
