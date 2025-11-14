# 示例配置文件

本目录包含 Scrutiny Prometheus Exporter 的示例配置文件。

## 文件说明

### `env.example`
环境变量配置示例，包含所有可配置的环境变量及其说明。

**使用方法**:
```bash
cp env.example .env
# 编辑 .env 文件，填入实际配置值
```

### `prometheus.yml`
Prometheus 抓取配置示例，展示如何配置 Prometheus 抓取 exporter 的 metrics。

**使用方法**:
1. 将配置添加到你的 Prometheus 主配置文件
2. 或使用此文件作为独立配置（适用于测试环境）

**关键配置**:
- `scrape_interval`: 抓取间隔（建议 60s）
- `scrape_timeout`: 抓取超时（建议 10s）
- `static_configs`: exporter 地址配置

### `prometheus_alerts.yml`
Prometheus 告警规则配置，包含以下告警：

- **设备故障告警**: 当设备状态为故障时触发
- **温度告警**: 当设备温度超过阈值时触发
- **SMART 属性告警**: 当关键 SMART 属性异常时触发
  - ATA 设备：重新分配扇区、待处理扇区
  - NVMe 设备：磨损度、可用备用空间、介质错误

**使用方法**:
1. 在 `prometheus.yml` 中添加告警规则配置：
   ```yaml
   rule_files:
     - "prometheus_alerts.yml"
   ```
2. 或使用 Prometheus Operator 的 AlertRule CRD

## 配置说明

### Prometheus 配置要点

1. **抓取间隔**: SMART 数据更新较慢，建议设置 `scrape_interval: 60s`
2. **超时设置**: 确保 `scrape_timeout` 足够长（建议 10s）
3. **标签保留**: 建议保留所有标签以便在 Grafana 中过滤

### 告警规则说明

所有告警规则都包含：
- `severity` 标签：用于告警路由
- `host_id` 和 `device_name` 标签：便于定位问题设备
- 合理的阈值：根据实际环境调整

## 自定义配置

根据你的实际环境，可能需要调整：
- Exporter 地址和端口
- 抓取间隔和超时
- 告警阈值
- 告警通知渠道（在 Alertmanager 中配置）

