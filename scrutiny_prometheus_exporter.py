#!/usr/bin/env python3
"""
Scrutiny Prometheus Exporter
将 Scrutiny API 数据转换为 Prometheus metrics 格式
完整版本：导出所有 SMART 属性
"""

import argparse
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily, REGISTRY

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('scrutiny_exporter')


class DeviceDetailsCache:
    """设备详情缓存"""
    
    def __init__(self, cache_duration: int = 60):
        self.cache_duration = cache_duration  # 缓存时间（秒）
        self.cache = {}  # {wwn: (data, timestamp)}
        self.lock = threading.Lock()
    
    def get(self, wwn: str) -> Optional[Dict[str, Any]]:
        """获取缓存数据"""
        with self.lock:
            if wwn in self.cache:
                data, timestamp = self.cache[wwn]
                if time.time() - timestamp < self.cache_duration:
                    logger.debug(f"缓存命中: {wwn}")
                    return data
                else:
                    # 缓存过期，删除
                    logger.debug(f"缓存过期: {wwn}")
                    del self.cache[wwn]
            return None
    
    def set(self, wwn: str, data: Dict[str, Any]):
        """设置缓存数据"""
        with self.lock:
            self.cache[wwn] = (data, time.time())
            logger.debug(f"缓存已更新: {wwn}")
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            logger.debug("缓存已清空")


class ScrutinyCollector:
    """Scrutiny 数据收集器"""
    
    def __init__(self, api_url: str, timeout: int = 10, cache_duration: int = 60):
        self.api_url = api_url
        self.timeout = timeout
        self.cache = DeviceDetailsCache(cache_duration)
        
    def collect(self):
        """收集 metrics 数据"""
        try:
            # 第一阶段：获取设备列表
            logger.debug("获取设备列表...")
            response = requests.get(f"{self.api_url}/api/summary", timeout=self.timeout)
            response.raise_for_status()
            summary_data = response.json()
            
            if 'data' not in summary_data or 'summary' not in summary_data['data']:
                logger.error("API 返回数据格式不正确")
                return
            
            summary = summary_data['data']['summary']
            logger.debug(f"找到 {len(summary)} 个设备")
            
            # 第二阶段：获取每个设备的详细信息
            devices_details = {}
            for wwn in summary.keys():
                details = self._get_device_details(wwn)
                if details:
                    devices_details[wwn] = details
            
            logger.debug(f"成功获取 {len(devices_details)} 个设备的详细信息")
            
            # 创建 metrics
            yield from self._create_device_info_metrics(summary)
            yield from self._create_smart_attributes_metrics(devices_details)
            yield from self._create_summary_metrics(devices_details)
            yield from self._create_status_metrics(summary)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 Scrutiny 数据失败: {e}")
        except Exception as e:
            logger.error(f"处理数据时出错: {e}", exc_info=True)
    
    def _get_device_details(self, device_wwn: str) -> Dict[str, Any]:
        """获取设备详细信息（带缓存）"""
        # 先检查缓存
        cached_data = self.cache.get(device_wwn)
        if cached_data:
            return cached_data
        
        # 缓存未命中，调用 API
        try:
            response = requests.get(
                f"{self.api_url}/api/device/{device_wwn}/details",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # 存入缓存
            self.cache.set(device_wwn, data)
            return data
        except Exception as e:
            logger.warning(f"获取设备 {device_wwn} 详情失败: {e}")
            return {}
    
    def _create_device_info_metrics(self, summary: Dict[str, Any]):
        """创建设备信息 metrics"""
        
        device_info = GaugeMetricFamily(
            'scrutiny_device_info',
            'Device information',
            labels=['wwn', 'device_name', 'model_name', 'serial_number', 
                   'firmware', 'protocol', 'host_id', 'form_factor']
        )
        
        device_capacity = GaugeMetricFamily(
            'scrutiny_device_capacity_bytes',
            'Device capacity in bytes',
            labels=['wwn', 'device_name', 'model_name', 'protocol', 'host_id']
        )
        
        device_status = GaugeMetricFamily(
            'scrutiny_device_status',
            'Device status (0=passed, 1=failed)',
            labels=['wwn', 'device_name', 'model_name', 'protocol', 'host_id']
        )
        
        for wwn, device_data in summary.items():
            device = device_data.get('device', {})
            device_name = device.get('device_name', '')
            model_name = device.get('model_name', '')
            protocol = device.get('device_protocol', '')
            host_id = device.get('host_id', '')
            
            device_info.add_metric(
                [
                    wwn,
                    device_name,
                    model_name,
                    device.get('serial_number', ''),
                    device.get('firmware', ''),
                    protocol,
                    host_id,
                    device.get('form_factor', '')
                ],
                1
            )
            
            capacity_labels = [wwn, device_name, model_name, protocol, host_id]
            if device.get('capacity'):
                device_capacity.add_metric(capacity_labels, device['capacity'])
            
            device_status.add_metric(capacity_labels, device.get('device_status', 0))
        
        yield device_info
        yield device_capacity
        yield device_status
    
    def _create_smart_attributes_metrics(self, devices_details: Dict[str, Any]):
        """创建完整的 SMART 属性 metrics"""
        
        gauge_metrics: Dict[str, GaugeMetricFamily] = {}
        info_metrics: Dict[str, InfoMetricFamily] = {}
        
        for wwn, device_detail in devices_details.items():
            if 'data' not in device_detail:
                continue
                
            device = device_detail['data'].get('device', {})
            smart_results = device_detail['data'].get('smart_results', [])
            
            if not smart_results:
                continue
                
            latest_result = self._select_latest_result(smart_results)
            if not latest_result:
                continue
            attrs = latest_result.get('attrs', {})
            
            device_name = device.get('device_name', '')
            model_name = device.get('model_name', '')
            protocol = device.get('device_protocol', '')
            host_id = device.get('host_id', '')
            
            for attr_id, attr_data in attrs.items():
                if not isinstance(attr_data, dict):
                    continue
                
                safe_attr_id = self._sanitize_metric_component(attr_id)
                labels = [wwn, device_name, model_name, protocol, host_id, str(attr_id)]
                
                for property_name, property_value in attr_data.items():
                    if property_value is None:
                        continue
                    
                    safe_property = self._sanitize_metric_component(property_name)
                    metric_base = f"scrutiny_smart_attr_{safe_attr_id}_{safe_property}"
                    
                    numeric_value = self._try_parse_float(property_value)
                    if numeric_value is not None:
                        if metric_base not in gauge_metrics:
                            gauge_metrics[metric_base] = GaugeMetricFamily(
                                metric_base,
                                f"SMART attribute {attr_id} {property_name}",
                                labels=['wwn', 'device_name', 'model_name', 'protocol', 'host_id', 'attribute_id']
                            )
                        gauge_metrics[metric_base].add_metric(labels, numeric_value)
                    else:
                        info_metric_name = f"{metric_base}_info"
                        if info_metric_name not in info_metrics:
                            info_metrics[info_metric_name] = InfoMetricFamily(
                                info_metric_name,
                                f"SMART attribute {attr_id} {property_name} (string)",
                                labels=['wwn', 'device_name', 'model_name', 'protocol', 'host_id', 'attribute_id']
                            )
                        info_metrics[info_metric_name].add_metric(
                            labels,
                            {'value': str(property_value)}
                        )
        
        for metric in gauge_metrics.values():
            yield metric
        for metric in info_metrics.values():
            yield metric
    
    def _create_summary_metrics(self, devices_details: Dict[str, Any]):
        """创建汇总 metrics（向后兼容）"""
        
        temperature = GaugeMetricFamily(
            'scrutiny_smart_temperature_celsius',
            'Device temperature in Celsius',
            labels=['wwn', 'device_name', 'model_name', 'protocol', 'host_id']
        )
        
        power_on_hours = GaugeMetricFamily(
            'scrutiny_smart_power_on_hours',
            'Device power on hours',
            labels=['wwn', 'device_name', 'model_name', 'protocol', 'host_id']
        )
        
        power_cycle_count = GaugeMetricFamily(
            'scrutiny_smart_power_cycle_count',
            'Device power cycle count',
            labels=['wwn', 'device_name', 'model_name', 'protocol', 'host_id']
        )
        
        collector_timestamp = GaugeMetricFamily(
            'scrutiny_smart_collector_timestamp',
            'Timestamp of last data collection',
            labels=['wwn', 'device_name', 'model_name', 'protocol', 'host_id']
        )
        
        for wwn, device_detail in devices_details.items():
            if 'data' not in device_detail:
                continue
                
            device = device_detail['data'].get('device', {})
            smart_results = device_detail['data'].get('smart_results', [])
            
            if not smart_results:
                continue
            
            latest_result = self._select_latest_result(smart_results)
            if not latest_result:
                continue
            device_name = device.get('device_name', '')
            model_name = device.get('model_name', '')
            protocol = device.get('device_protocol', '')
            host_id = device.get('host_id', '')
            
            labels = [wwn, device_name, model_name, protocol, host_id]
            
            # 温度
            temp = latest_result.get('temp')
            if temp is not None:
                temperature.add_metric(labels, float(temp))
            
            # 通电时间
            poh = latest_result.get('power_on_hours')
            if poh is not None:
                power_on_hours.add_metric(labels, float(poh))
            
            # 电源循环计数
            pcc = latest_result.get('power_cycle_count')
            if pcc is not None:
                power_cycle_count.add_metric(labels, float(pcc))
            
            # 收集时间戳（转换为毫秒用于 Grafana）
            date_str = latest_result.get('date')
            if date_str:
                try:
                    timestamp = datetime.fromisoformat(date_str.replace('Z', '+00:00')).timestamp()
                    # 转换为毫秒
                    timestamp_ms = timestamp * 1000
                    collector_timestamp.add_metric(labels, timestamp_ms)
                except Exception as e:
                    logger.debug(f"解析时间戳失败 {date_str}: {e}")
        
        yield temperature
        yield power_on_hours
        yield power_cycle_count
        yield collector_timestamp
    
    def _create_status_metrics(self, summary: Dict[str, Any]):
        """创建状态统计 metrics"""
        
        total_devices = GaugeMetricFamily(
            'scrutiny_devices_total',
            'Total number of monitored devices',
            labels=[]
        )
        total_devices.add_metric([], len(summary))
        
        protocol_count = GaugeMetricFamily(
            'scrutiny_devices_by_protocol',
            'Number of devices by protocol',
            labels=['protocol']
        )
        
        protocols = {}
        for device_data in summary.values():
            protocol = device_data.get('device', {}).get('device_protocol', 'unknown')
            protocols[protocol] = protocols.get(protocol, 0) + 1
        
        for protocol, count in protocols.items():
            protocol_count.add_metric([protocol], count)
        
        yield total_devices
        yield protocol_count

    @staticmethod
    def _sanitize_metric_component(value: Any) -> str:
        return (
            str(value)
            .strip()
            .replace(' ', '_')
            .replace('-', '_')
            .replace('.', '_')
            .lower()
        )

    @staticmethod
    def _try_parse_float(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return None
            try:
                return float(candidate)
            except ValueError:
                if candidate.startswith(('0x', '0X')):
                    try:
                        return float(int(candidate, 16))
                    except ValueError:
                        return None
        return None

    def _select_latest_result(self, smart_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not smart_results:
            return None
        latest = None
        latest_ts = None
        for result in smart_results:
            ts = self._parse_result_timestamp(result)
            if latest is None or (ts is not None and (latest_ts is None or ts > latest_ts)):
                latest = result
                latest_ts = ts
        if latest is None:
            return smart_results[-1]
        return latest

    @staticmethod
    def _parse_result_timestamp(result: Dict[str, Any]) -> Optional[float]:
        for key in ('date', 'smart_date', 'collector_date'):
            date_str = result.get(key)
            if not date_str:
                continue
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).timestamp()
            except Exception:
                continue
        return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Scrutiny Prometheus Exporter',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--api-url',
        default=os.environ.get('SCRUTINY_API_URL', 'https://smart.pve.icu'),
        help='Scrutiny API URL (env: SCRUTINY_API_URL)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.environ.get('EXPORTER_PORT', '9900')),
        help='Exporter port (env: EXPORTER_PORT)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=int(os.environ.get('API_TIMEOUT', '10')),
        help='API request timeout in seconds (env: API_TIMEOUT)'
    )
    parser.add_argument(
        '--cache-duration',
        type=int,
        default=int(os.environ.get('CACHE_DURATION', '60')),
        help='Cache device details for N seconds (env: CACHE_DURATION)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=os.environ.get('LOG_LEVEL', 'INFO').upper(),
        help='Log level (env: LOG_LEVEL)'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 注册收集器
    collector = ScrutinyCollector(args.api_url, args.timeout, args.cache_duration)
    REGISTRY.register(collector)
    
    # 启动 HTTP 服务器
    logger.info(f"启动 Prometheus exporter 在端口 {args.port}")
    logger.info(f"Scrutiny API: {args.api_url}")
    logger.info(f"缓存时间: {args.cache_duration} 秒")
    logger.info(f"Metrics endpoint: http://localhost:{args.port}/metrics")
    
    start_http_server(args.port)
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在退出...")


if __name__ == '__main__':
    main()

