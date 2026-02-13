"""
数据模型定义
包含运行时状态和数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import threading


@dataclass
class Config:
    """配置参数"""
    clash_api_url: str = 'http://127.0.0.1:9090'
    clash_secret: str = ''
    proxy_group: str = 'PROXY'  # 代理组名称
    delay_threshold: int = 200  # 延迟阈值(毫秒)
    check_interval: int = 30  # 检测间隔(秒)
    locked_region: str = ''  # 锁定区域(空表示不限制)
    test_timeout: int = 5000  # 延迟测试超时(毫秒)
    test_url: str = 'http://www.gstatic.com/generate_204'  # 测试URL

    # 智能切换配置
    silent_period_minutes: int = 3  # 切换后静默期时长(分钟)，默认3分钟
    min_delay_for_switch: int = 100  # 切换前最小延迟才允许切换(ms)，避免抖动
    enable_active_detection: bool = True  # 是否启用活跃连接检测
    active_check_method: str = 'api'  # 活跃检测方法: 'api'(流量), 'traffic'(统计), 'none'(禁用)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'clash_api_url': self.clash_api_url,
            'clash_secret': self.clash_secret,
            'proxy_group': self.proxy_group,
            'delay_threshold': self.delay_threshold,
            'check_interval': self.check_interval,
            'locked_region': self.locked_region,
            'test_timeout': self.test_timeout,
            'test_url': self.test_url,
            'silent_period_minutes': self.silent_period_minutes,
            'min_delay_for_switch': self.min_delay_for_switch,
            'enable_active_detection': self.enable_active_detection,
            'active_check_method': self.active_check_method
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Config':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DelayRecord:
    """延迟记录"""
    node_name: str
    delay: int
    timestamp: datetime

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'node_name': self.node_name,
            'delay': self.delay,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class RuntimeState:
    """运行时状态"""
    current_node: str = ''
    current_delay: int = 0
    last_check_time: Optional[datetime] = None
    switch_count: int = 0
    blacklist: set = field(default_factory=set)
    available_nodes: List[str] = field(default_factory=list)
    delay_history: List[DelayRecord] = field(default_factory=list)
    is_running: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    # 智能切换相关
    in_silent_period: bool = False  # 是否在静默期内
    silent_until: Optional[datetime] = None  # 静默期结束时间
    last_switch_time: Optional[datetime] = None  # 上次切换时间
    active_detection_enabled: bool = False  # 是否启用活跃连接检测
    has_active_connections: bool = False  # 检测到活跃连接

    def to_dict(self) -> Dict:
        """转换为字典"""
        with self.lock:
            return {
                'current_node': self.current_node,
                'current_delay': self.current_delay,
                'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
                'switch_count': self.switch_count,
                'blacklist': list(self.blacklist),
                'available_nodes': self.available_nodes.copy(),
                'delay_history': [record.to_dict() for record in self.delay_history[-20:]],  # 只保留最近20条
                'is_running': self.is_running,
                # 智能切换相关
                'in_silent_period': self.in_silent_period,
                'silent_until': self.silent_until.isoformat() if self.silent_until else None,
                'last_switch_time': self.last_switch_time.isoformat() if self.last_switch_time else None,
                'active_detection_enabled': self.active_detection_enabled,
                'has_active_connections': self.has_active_connections
            }

    def add_blacklist(self, node_name: str):
        """添加黑名单"""
        with self.lock:
            self.blacklist.add(node_name)

    def remove_blacklist(self, node_name: str):
        """移除黑名单"""
        with self.lock:
            self.blacklist.discard(node_name)

    def is_blacklisted(self, node_name: str) -> bool:
        """检查是否在黑名单中"""
        with self.lock:
            return node_name in self.blacklist

    def add_delay_record(self, node_name: str, delay: int):
        """添加延迟记录"""
        with self.lock:
            record = DelayRecord(
                node_name=node_name,
                delay=delay,
                timestamp=datetime.now()
            )
            self.delay_history.append(record)
            # 只保留最近50条记录
            if len(self.delay_history) > 50:
                self.delay_history = self.delay_history[-50:]

    def increment_switch_count(self):
        """增加切换次数"""
        with self.lock:
            self.switch_count += 1
