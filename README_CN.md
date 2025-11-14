# Scrutiny Prometheus Exporter

Scrutiny SMART 监控系统的 Prometheus Exporter。将 Scrutiny API 数据转换为 Prometheus metrics 格式。

> 📖 [English Documentation](README.md) | [中文文档](README_CN.md)

## 功能特性

- **完整的 SMART 属性导出**: 导出所有可用的 SMART 属性，支持 NVMe 和 ATA/SATA 设备
- **覆盖所有 SMART 字段**: 数值字段（`raw_value`、`worst`、`thresh`、`failure_rate` 等）导出为 gauge 指标，字符串字段（`status`、`raw_string`、`when_failed`）导出为 info 指标
- **缓存机制**: 可配置的缓存时长，减少 API 调用
- **Docker 支持**: 开箱即用的 Docker 镜像，支持多架构（amd64、arm64）
- **GitHub Actions**: 自动化的多平台 Docker 镜像构建
- **健康检查**: 内置健康检查端点

## 快速开始

### 使用 Docker Compose

```bash
# 克隆仓库
git clone <repository-url>
cd exporter

# 构建并运行
make docker-build
make docker-run

# 检查指标
curl http://localhost:9900/metrics
```

### 使用 Docker

```bash
docker build -t scrutiny-exporter:latest .
docker run -d \
  -p 9900:9900 \
  -e SCRUTINY_API_URL=https://smart.example.com \
  scrutiny-exporter:latest
```

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 exporter
python scrutiny_prometheus_exporter.py \
  --api-url https://smart.example.com \
  --port 9900 \
  --cache-duration 60

# 或使用 Make
make run
```

## 配置

### 环境变量（推荐）

环境变量优先级最高，适合在 Docker/Kubernetes 中使用：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `SCRUTINY_API_URL` | `https://smart.example.com` | Scrutiny API URL |
| `EXPORTER_PORT` | `9900` | Exporter HTTP 端口 |
| `API_TIMEOUT` | `10` | API 请求超时时间（秒） |
| `CACHE_DURATION` | `60` | 设备详情缓存时间（秒） |
| `LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |

**Docker Compose 示例**:
```yaml
environment:
  - SCRUTINY_API_URL=https://smart.example.com
  - EXPORTER_PORT=9900
  - CACHE_DURATION=60
  - LOG_LEVEL=INFO
```

### 命令行参数

命令行参数仅在未设置环境变量时生效：

| 参数 | 环境变量 | 默认值 |
|------|---------|--------|
| `--api-url` | `SCRUTINY_API_URL` | `https://smart.example.com` |
| `--port` | `EXPORTER_PORT` | `9900` |
| `--timeout` | `API_TIMEOUT` | `10` |
| `--cache-duration` | `CACHE_DURATION` | `60` |
| `--log-level` | `LOG_LEVEL` | `INFO` |

**本地运行示例**:
```bash
python scrutiny_prometheus_exporter.py \
  --api-url http://localhost:8080 \
  --port 9900 \
  --cache-duration 120
```

## 导出指标字典

### 设备信息指标

#### `scrutiny_device_info`
- **类型**: Gauge
- **说明**: 设备基本信息
- **标签**:
  - `wwn`: 设备 WWN（World Wide Name）
  - `device_name`: 设备名称（如 `/dev/sda`）
  - `model_name`: 设备型号
  - `serial_number`: 序列号
  - `firmware`: 固件版本
  - `protocol`: 设备协议（`nvme`、`ata`、`sata` 等）
  - `host_id`: 主机 ID
  - `form_factor`: 外形规格（`2.5"`、`3.5"`、`M.2` 等）
- **值**: 始终为 `1`（用于标识设备存在）
- **示例**:
  ```
  scrutiny_device_info{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",serial_number="S3Z1NX0K123456",firmware="RVT02B6Q",protocol="ata",host_id="host1",form_factor="2.5\""} 1
  ```

#### `scrutiny_device_capacity_bytes`
- **类型**: Gauge
- **说明**: 设备容量（字节）
- **标签**: `wwn`, `device_name`, `model_name`, `protocol`, `host_id`
- **单位**: 字节
- **示例**:
  ```
  scrutiny_device_capacity_bytes{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1"} 500107862016
  ```

#### `scrutiny_device_status`
- **类型**: Gauge
- **说明**: 设备健康状态
- **标签**: `wwn`, `device_name`, `model_name`, `protocol`, `host_id`
- **值**: 
  - `0`: 通过（passed）
  - `1`: 失败（failed）
- **示例**:
  ```
  scrutiny_device_status{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1"} 0
  ```

### 汇总指标

#### `scrutiny_smart_temperature_celsius`
- **类型**: Gauge
- **说明**: 设备温度（摄氏度）
- **标签**: `wwn`, `device_name`, `model_name`, `protocol`, `host_id`
- **单位**: 摄氏度
- **示例**:
  ```
  scrutiny_smart_temperature_celsius{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1"} 35
  ```

#### `scrutiny_smart_power_on_hours`
- **类型**: Gauge
- **说明**: 设备通电时间（小时）
- **标签**: `wwn`, `device_name`, `model_name`, `protocol`, `host_id`
- **单位**: 小时
- **示例**:
  ```
  scrutiny_smart_power_on_hours{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1"} 8760
  ```

#### `scrutiny_smart_power_cycle_count`
- **类型**: Gauge
- **说明**: 设备电源循环次数
- **标签**: `wwn`, `device_name`, `model_name`, `protocol`, `host_id`
- **单位**: 次数
- **示例**:
  ```
  scrutiny_smart_power_cycle_count{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1"} 42
  ```

#### `scrutiny_smart_collector_timestamp`
- **类型**: Gauge
- **说明**: 最后一次数据收集的时间戳（毫秒）
- **标签**: `wwn`, `device_name`, `model_name`, `protocol`, `host_id`
- **单位**: 毫秒（Unix 时间戳）
- **示例**:
  ```
  scrutiny_smart_collector_timestamp{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1"} 1704067200000
  ```

### 完整 SMART 属性指标

所有 SMART 属性按照以下格式导出：

```
scrutiny_smart_attr_{attribute_id}_{property}
```

其中：
- `attribute_id`: SMART 属性 ID（如 `available_spare`、`1`、`194`）
- `property`: Scrutiny 报告的任何数值字段（如 `value`、`raw_value`、`transformed_value`、`worst`、`thresh`、`failure_rate`）

#### 属性 ID 说明

**NVMe 设备常见属性**:
- `available_spare`: 可用备用空间百分比
- `available_spare_threshold`: 可用备用空间阈值
- `percentage_used`: 磨损百分比
- `critical_warning`: 关键警告
- `temperature`: 温度
- `media_errors`: 媒体错误计数
- `num_err_log_entries`: 错误日志条目数

**ATA/SATA 设备常见属性**:
- `1`: 原始读取错误率
- `5`: 重新分配扇区计数
- `9`: 通电时间
- `10`: 主轴启动/停止计数
- `194`: 温度（ATA）
- `197`: 当前待处理扇区计数
- `198`: 离线不可纠正扇区计数
- `199`: UDMA CRC 错误计数

#### 属性字段说明

- `value`: 当前值（归一化值，通常 0-255）
- `raw_value`: 原始值（实际计数或数值）
- `transformed_value`: 转换后的值
- `worst`: 最差值
- `thresh`: 阈值
- `failure_rate`: 失败率
- `when_failed`: 失败时间（字符串，导出为 info 指标）

#### 示例指标

**NVMe 示例**:
```
# 可用备用空间百分比
scrutiny_smart_attr_available_spare_value{wwn="eui.0025385a12345678",device_name="/dev/nvme0n1",model_name="Samsung SSD 980",protocol="nvme",host_id="host1",attribute_id="available_spare"} 100

# 磨损百分比
scrutiny_smart_attr_percentage_used_value{wwn="eui.0025385a12345678",device_name="/dev/nvme0n1",model_name="Samsung SSD 980",protocol="nvme",host_id="host1",attribute_id="percentage_used"} 5

# 温度
scrutiny_smart_attr_temperature_raw_value{wwn="eui.0025385a12345678",device_name="/dev/nvme0n1",model_name="Samsung SSD 980",protocol="nvme",host_id="host1",attribute_id="temperature"} 35
```

**ATA/SATA 示例**:
```
# 重新分配扇区计数（原始值）
scrutiny_smart_attr_5_raw_value{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1",attribute_id="5"} 0

# 待处理扇区计数（原始值）
scrutiny_smart_attr_197_raw_value{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1",attribute_id="197"} 0

# 温度（当前值）
scrutiny_smart_attr_194_value{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1",attribute_id="194"} 35
```

### 字符串 SMART 属性指标

字符串字段（如 `status`、`raw_string`、`status_reason`、`when_failed`）导出为 info 指标：

```
scrutiny_smart_attr_{attribute_id}_{property}_info
```

#### 标签说明

- 标准设备标签：`wwn`, `device_name`, `model_name`, `protocol`, `host_id`, `attribute_id`
- `value`: 字符串值

#### 示例

```
# 状态信息
scrutiny_smart_attr_critical_warning_status_info{wwn="eui.0025385a12345678",device_name="/dev/nvme0n1",model_name="Samsung SSD 980",protocol="nvme",host_id="host1",attribute_id="critical_warning",value="0"} 1

# 原始字符串
scrutiny_smart_attr_5_raw_string_info{wwn="5002538e40a22929",device_name="/dev/sda",model_name="Samsung SSD 860",protocol="ata",host_id="host1",attribute_id="5",value="000000000000"} 1
```

**查询示例**:
```promql
# 查找所有非零的关键警告
scrutiny_smart_attr_critical_warning_status_info{value!="0"}

# 查找有失败记录的属性
scrutiny_smart_attr_*_when_failed_info{value!=""}
```

### 统计指标

#### `scrutiny_devices_total`
- **类型**: Gauge
- **说明**: 监控的设备总数
- **标签**: 无
- **示例**:
  ```
  scrutiny_devices_total 5
  ```

#### `scrutiny_devices_by_protocol`
- **类型**: Gauge
- **说明**: 按协议分类的设备数量
- **标签**: `protocol`（协议类型：`nvme`、`ata`、`sata` 等）
- **示例**:
  ```
  scrutiny_devices_by_protocol{protocol="nvme"} 2
  scrutiny_devices_by_protocol{protocol="ata"} 3
  ```

## Prometheus 配置

添加到 `prometheus.yml`（参考 `examples/prometheus.yml`）：

```yaml
scrape_configs:
  - job_name: 'scrutiny'
    static_configs:
      - targets: ['localhost:9900']
    scrape_interval: 60s  # SMART 数据更新较慢
    scrape_timeout: 10s
```

## Grafana Dashboard

本项目提供了一个完整的 Grafana Dashboard，用于可视化 SMART 监控数据。

### Dashboard 预览

![Grafana Dashboard 概览](docs/images/image.png)

![Grafana Dashboard 详情](docs/images/image1.png)

### 功能特性

- **设备概览**: 总设备数、协议分布、故障统计
- **温度监控**: 实时温度图表和历史趋势
- **使用统计**: 通电时间、电源循环计数
- **SSD 健康**: NVMe 磨损度、可用备用空间
- **错误追踪**: ATA 和 NVMe 关键错误指标
- **设备列表**: 综合设备信息表格

### 快速导入

1. 登录 Grafana
2. 点击 **"+"** -> **"Import"**
3. 上传 `grafana_dashboard.json` 文件
4. 选择 Prometheus 数据源
5. 点击 **"Import"**

### 详细说明

完整的 Dashboard 使用指南请参考：[docs/GRAFANA_PANELS.md](./docs/GRAFANA_PANELS.md)

### Dashboard 文件

- `grafana_dashboard.json`: Dashboard JSON 配置文件
- `docs/GRAFANA_PANELS.md`: Dashboard 完整指南（包含导入、配置、面板详情和使用建议）

### Grafana Dashboard 导入

Dashboard 可以通过以下方式导入：

1. **UI 导入**（推荐）：在 Grafana UI 中直接导入 `grafana_dashboard.json`
2. **Provisioning**：将 Dashboard JSON 放到 Grafana provisioning 目录

详细说明请参考 [docs/GRAFANA_PANELS.md](./docs/GRAFANA_PANELS.md)。

## 告警

本项目还提供了 Prometheus 告警规则配置，请参考：
- `examples/prometheus_alerts.yml`: 预配置的告警规则
- 包含温度、设备状态、SMART 属性等关键指标的告警

## Docker 镜像

### 构建

```bash
make docker-build
```

### GitHub Container Registry

镜像会自动构建并推送到 GitHub Container Registry：

```
ghcr.io/jianyun8023/scrutiny-exporter:latest
```

**拉取最新镜像**：
```bash
docker pull ghcr.io/jianyun8023/scrutiny-exporter:latest
```

### 多架构支持

Docker 镜像支持多种架构：
- **linux/amd64**: Intel/AMD 64 位处理器
- **linux/arm64**: ARM 64 位处理器（Apple Silicon、ARM 服务器）

镜像使用多平台 manifest，Docker 会自动拉取适合您系统的架构。

### 构建触发

镜像在以下情况下会自动构建并推送：
- **手动触发**: 通过 GitHub Actions workflow_dispatch
- **分支推送**: main 或 master 分支
- **Git 标签**: 匹配 `v*` 模式的标签（如 `v1.2.3`）
- **Pull Request**: 仅构建（不推送到 registry）
- **GitHub Release**: 发布 release 时

### 标签

以下标签格式会自动生成：

- `latest`: main/master 分支的最新构建
- `<branch>`: 分支名称（如 `main`、`master`）
- `<branch>-<sha>`: 带 commit SHA 的分支特定构建
- `v<version>`: 语义化版本标签（如 `v1.2.3` → `1.2.3`）
- `<major>.<minor>`: 主版本和次版本（如 `v1.2.3` → `1.2`）
- `pr-<number>`: Pull Request 构建

### 镜像标签（Labels）

所有镜像都包含 OCI 标准标签：
- `org.opencontainers.image.title`: Scrutiny Prometheus Exporter
- `org.opencontainers.image.description`: Prometheus Exporter for Scrutiny SMART monitoring system
- `org.opencontainers.image.vendor`: 仓库所有者
- `org.opencontainers.image.source`: GitHub 仓库 URL
- `org.opencontainers.image.version`: Git 标签或分支名称
- `org.opencontainers.image.created`: 构建时间戳
- `org.opencontainers.image.revision`: Git commit SHA
- `org.opencontainers.image.licenses`: MIT

## 开发

### 测试

```bash
# 运行测试脚本
make test

# 或手动运行
./test_exporter.sh
```

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 使用调试日志运行
python scrutiny_prometheus_exporter.py --log-level DEBUG
```

## 项目结构

```
exporter/
├── scrutiny_prometheus_exporter.py  # 主程序
├── Dockerfile                        # Docker 镜像构建
├── docker-compose.yml                # Exporter 单独部署
├── requirements.txt                  # Python 依赖
├── Makefile                          # 便捷命令
├── test_exporter.sh                  # 测试脚本
│
├── grafana_dashboard.json            # Grafana Dashboard JSON
│
├── docs/                             # 文档目录
│   └── GRAFANA_PANELS.md             # Dashboard 完整指南
│
├── examples/                         # 示例配置目录
│   ├── env.example                   # 环境变量示例
│   ├── prometheus.yml                # Prometheus 抓取配置示例
│   └── prometheus_alerts.yml         # Prometheus 告警规则
│
├── README.md                         # 主文档（英文）
├── README_CN.md                      # 主文档（中文）
│
└── .github/workflows/build.yml       # CI/CD 工作流
```

## 架构

### 数据流

1. Prometheus 抓取 `/metrics` 端点
2. Exporter 调用 `/api/summary` 获取设备列表
3. 对于每个设备，exporter 调用 `/api/device/{wwn}/details`（带缓存）
4. Exporter 将 SMART 数据转换为 Prometheus metrics 格式
5. 返回指标给 Prometheus

### 缓存

- 设备详情缓存 `--cache-duration` 秒（默认：60 秒）
- 当多个 Prometheus 实例同时抓取时减少 API 调用
- 使用锁实现线程安全的缓存

## 性能

- **API 调用**: 1 次（summary）+ N 次（设备详情，已缓存）
- **推荐抓取间隔**: 60 秒（SMART 数据更新较慢）
- **缓存时长**: 60 秒（可配置）

## 故障排除

### Exporter 无法启动

检查日志：
```bash
# Docker
docker logs scrutiny-exporter

# 本地
tail -f /tmp/scrutiny_exporter.log
```

### 指标中没有 SMART 属性

- 检查 Scrutiny API 是否可访问
- 验证设备详情 API 是否返回数据
- 检查 exporter 日志中的错误
- 等待缓存过期后重试

### API 调用频率过高

- 增加 `--cache-duration`（如 120 秒）
- 降低 Prometheus 抓取频率
- 使用多个共享缓存的 Prometheus 实例

## 许可证

MIT License

## 贡献

欢迎贡献！请提交 issue 或 pull request。

## 支持

如有问题和疑问：
- GitHub Issues: [创建 issue](https://github.com/jianyun8023/scrutiny-exporter/issues)
- 文档: 查看本 README

