"""
节点管理器
负责节点过滤、选择和管理
"""

import logging
from typing import List, Optional, Dict, Tuple
from clash_api import ClashAPI
from models import Config, RuntimeState

logger = logging.getLogger(__name__)


class NodeManager:
    """节点管理器"""

    def __init__(self, clash_api: ClashAPI, config: Config, state: RuntimeState):
        self.clash_api = clash_api
        self.config = config
        self.state = state

    def get_available_nodes(self) -> List[str]:
        """获取可用节点列表"""
        try:
            all_proxies = self.clash_api.get_proxies()

            # 过滤掉代理组和特殊节点
            node_list = []
            for name, info in all_proxies.items():
                # 跳过代理组（如 PROXY, DIRECT 等）
                if info.get('type') in ['Selector', 'URLTest', 'Fallback', 'LoadBalance']:
                    continue
                # 只保留实际节点（SS, SSR, V2Ray, Trojan 等）
                if info.get('type') in ['Shadowsocks', 'ShadowsocksR', 'V2Ray', 'Trojan', 'Snell']:
                    node_list.append(name)

            return node_list
        except Exception as e:
            logger.error(f"获取节点列表失败: {e}")
            return []

    def filter_nodes(self, nodes: List[str] = None) -> List[str]:
        """根据区域和黑名单过滤节点"""
        if nodes is None:
            nodes = self.get_available_nodes()

        # 应用区域过滤
        if self.config.locked_region:
            nodes = self._filter_by_region(nodes, self.config.locked_region)

        # 应用黑名单过滤
        nodes = [node for node in nodes if not self.state.is_blacklisted(node)]

        return nodes

    def _filter_by_region(self, nodes: List[str], region: str) -> List[str]:
        """根据区域过滤节点"""
        region_lower = region.lower()
        filtered = []
        for node in nodes:
            if region_lower in node.lower():
                filtered.append(node)
        return filtered

    def select_best_node(self, nodes: List[str] = None) -> Optional[str]:
        """从可用节点中选择延迟最低的"""
        if nodes is None:
            nodes = self.filter_nodes()

        if not nodes:
            logger.warning("没有可用节点")
            return None

        # 如果只有一个节点，直接返回
        if len(nodes) == 1:
            return nodes[0]

        # 批量测试延迟
        logger.info(f"测试 {len(nodes)} 个节点的延迟...")
        delays = self.clash_api.test_multiple_delays(
            nodes,
            test_url=self.config.test_url,
            timeout=self.config.test_timeout
        )

        if not delays:
            logger.warning("所有节点延迟测试失败")
            return None

        # 选择延迟最低的节点
        best_node = min(delays.items(), key=lambda x: x[1])[0]
        best_delay = delays[best_node]

        logger.info(f"选择最佳节点: {best_node} (延迟: {best_delay}ms)")
        return best_node

    def get_node_info(self, node_name: str) -> Optional[Dict]:
        """获取节点信息"""
        try:
            proxies = self.clash_api.get_proxies()
            if node_name in proxies:
                return proxies[node_name]
            return None
        except Exception as e:
            logger.error(f"获取节点信息失败: {e}")
            return None

    def switch_to_node(self, node_name: str, group_name: str = None) -> bool:
        """切换到指定节点"""
        if not node_name:
            logger.error("节点名称为空")
            return False

        if group_name is None:
            group_name = self.config.proxy_group

        # 检查节点是否在黑名单中
        if self.state.is_blacklisted(node_name):
            logger.warning(f"节点在黑名单中: {node_name}")
            return False

        success = self.clash_api.switch_proxy(group_name, node_name)
        if success:
            self.state.current_node = node_name
            self.state.increment_switch_count()
            logger.info(f"成功切换到节点: {node_name}")
        else:
            logger.error(f"切换到节点失败: {node_name}")

        return success

    def auto_select_and_switch(self) -> bool:
        """自动选择最佳节点并切换"""
        available_nodes = self.filter_nodes()

        if not available_nodes:
            logger.warning("没有可用节点")
            return False

        # 获取当前节点
        current_node = self.clash_api.get_current_proxy(self.config.proxy_group)

        # 如果当前节点可用且不在黑名单中，测试其延迟
        if current_node and not self.state.is_blacklisted(current_node):
            current_delay = self.clash_api.get_delay(
                current_node,
                test_url=self.config.test_url,
                timeout=self.config.test_timeout
            )

            if current_delay is not None and current_delay < self.config.delay_threshold:
                logger.info(f"当前节点延迟良好: {current_node} ({current_delay}ms)")
                self.state.current_delay = current_delay
                self.state.add_delay_record(current_node, current_delay)
                return True

        # 需要切换，选择最佳节点
        best_node = self.select_best_node(available_nodes)
        if best_node:
            return self.switch_to_node(best_node)

        return False

    def add_blacklist(self, node_name: str) -> bool:
        """添加黑名单"""
        if not node_name:
            return False

        self.state.add_blacklist(node_name)
        logger.info(f"添加黑名单: {node_name}")
        return True

    def remove_blacklist(self, node_name: str) -> bool:
        """移除黑名单"""
        if not node_name:
            return False

        self.state.remove_blacklist(node_name)
        logger.info(f"移除黑名单: {node_name}")
        return True

    def get_all_regions(self) -> List[str]:
        """从节点名称中提取所有区域"""
        nodes = self.get_available_nodes()
        regions = set()

        # 常见的区域关键词
        region_keywords = [
            '香港', 'HK', 'Hong Kong',
            '日本', 'JP', 'Japan', '东京', '大阪',
            '新加坡', 'SG', 'Singapore',
            '美国', 'US', 'USA', 'United States',
            '韩国', 'KR', 'Korea',
            '台湾', 'TW', 'Taiwan',
            '英国', 'UK', 'GB', 'United Kingdom',
            '德国', 'DE', 'Germany',
            '加拿大', 'CA', 'Canada'
        ]

        for node in nodes:
            for keyword in region_keywords:
                if keyword.lower() in node.lower():
                    regions.add(keyword)
                    break

        return sorted(list(regions))
