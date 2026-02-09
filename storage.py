"""
数据持久化模块
负责保存和加载配置、黑名单等数据到文件
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from models import Config, RuntimeState

logger = logging.getLogger(__name__)

# 数据存储目录
DATA_DIR = Path('/app/data')
CONFIG_FILE = DATA_DIR / 'config.json'
BLACKLIST_FILE = DATA_DIR / 'blacklist.json'


class StorageManager:
    """数据持久化管理器"""

    def __init__(self):
        # 确保数据目录存在
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def save_config(self, config: Config) -> bool:
        """保存配置到文件"""
        try:
            config_data = {
                'delay_threshold': config.delay_threshold,
                'check_interval': config.check_interval,
                'locked_region': config.locked_region,
                'test_timeout': config.test_timeout,
                'test_url': config.test_url
            }

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            logger.info("配置已保存")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def load_config(self) -> Optional[Dict]:
        """从文件加载配置"""
        try:
            if not CONFIG_FILE.exists():
                logger.info("配置文件不存在，使用默认配置")
                return None

            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            logger.info(f"配置已加载: {config_data}")
            return config_data
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return None

    def save_blacklist(self, blacklist: set) -> bool:
        """保存黑名单到文件"""
        try:
            blacklist_data = {
                'blacklist': list(blacklist)
            }

            with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(blacklist_data, f, ensure_ascii=False, indent=2)

            logger.info(f"黑名单已保存，共 {len(blacklist)} 个节点")
            return True
        except Exception as e:
            logger.error(f"保存黑名单失败: {e}")
            return False

    def load_blacklist(self) -> set:
        """从文件加载黑名单"""
        try:
            if not BLACKLIST_FILE.exists():
                logger.info("黑名单文件不存在")
                return set()

            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                blacklist = set(data.get('blacklist', []))

            logger.info(f"黑名单已加载，共 {len(blacklist)} 个节点")
            return blacklist
        except Exception as e:
            logger.error(f"加载黑名单失败: {e}")
            return set()

    def save_state(self, state: RuntimeState) -> bool:
        """保存运行时状态（黑名单部分）"""
        return self.save_blacklist(state.blacklist)

    def load_state_to_config(self, config: Config) -> Config:
        """从文件加载配置并应用到 Config 对象"""
        config_data = self.load_config()
        if config_data:
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        return config


# 全局存储管理器实例
storage = StorageManager()
