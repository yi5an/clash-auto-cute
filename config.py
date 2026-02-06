"""
配置管理模块
负责加载和管理应用配置
"""

import os
from dotenv import load_dotenv
from models import Config

# 加载环境变量
load_dotenv()


def load_config() -> Config:
    """从环境变量加载配置"""
    return Config(
        clash_api_url=os.getenv('CLASH_API_URL', 'http://127.0.0.1:9090'),
        clash_secret=os.getenv('CLASH_SECRET', ''),
        proxy_group=os.getenv('PROXY_GROUP', 'PROXY'),
        delay_threshold=int(os.getenv('DELAY_THRESHOLD', 200)),
        check_interval=int(os.getenv('CHECK_INTERVAL', 30)),
        locked_region=os.getenv('LOCKED_REGION', ''),
        test_timeout=int(os.getenv('TEST_TIMEOUT', 5000)),
        test_url=os.getenv('TEST_URL', 'http://www.gstatic.com/generate_204')
    )


def update_config(config: Config, **kwargs) -> Config:
    """更新配置参数"""
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config
