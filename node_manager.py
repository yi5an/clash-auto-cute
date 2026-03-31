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

    SPECIAL_PROXY_TYPES = {
        'Selector',
        'URLTest',
        'Fallback',
        'LoadBalance',
        'Relay',
        'Direct',
        'Reject',
        'RejectDrop',
        'Pass',
        'Compatible',
    }

    def __init__(self, clash_api: ClashAPI, config: Config, state: RuntimeState):
        self.clash_api = clash_api
        self.config = config
        self.state = state

    def get_available_nodes(self) -> List[str]:
        """获取可用节点列表"""
        try:
            all_proxies = self.clash_api.get_proxies()

            # 过滤掉代理组和内置特殊节点，兼容新内核返回的新协议类型
            node_list = []
            for name, info in all_proxies.items():
                proxy_type = info.get('type', '')

                if proxy_type in self.SPECIAL_PROXY_TYPES:
                    continue

                # 过滤 subscription info 这类非真实线路的说明项
                if name.startswith('剩余流量') or name.startswith('距离下次重置') or name.startswith('套餐到期'):
                    continue

                node_list.append(name)

            return node_list
        except Exception as e:
            logger.error(f"获取节点列表失败: {e}")
            return []

    def filter_nodes(self, nodes: List[str] = None) -> List[str]:
        """根据区域和黑名单过滤节点"""
        if nodes is None:
            nodes = self.get_available_nodes()
            logger.info(f"原始节点列表: {nodes}")

        # 应用区域过滤
        if self.config.locked_region:
            logger.info(f"应用区域过滤: {self.config.locked_region}")
            original_count = len(nodes)
            nodes = self._filter_by_region(nodes, self.config.locked_region)
            logger.info(f"区域过滤: {original_count} -> {len(nodes)} 个节点")
            logger.info(f"过滤后的节点列表: {nodes}")

        # 应用黑名单过滤
        original_count_after_region = len(nodes)
        nodes = [node for node in nodes if not self.state.is_blacklisted(node)]
        logger.info(f"黑名单过滤: {original_count_after_region} -> {len(nodes)} 个节点")
        if original_count_after_region != len(nodes):
            logger.info(f"被黑名单过滤的节点: {[n for n in self.state.blacklist if n in [n for n in nodes if n not in [node for node in nodes if not self.state.is_blacklisted(node)]]]}")

        return nodes

    def _filter_by_region(self, nodes: List[str], region: str) -> List[str]:
        """根据区域过滤节点"""
        region_lower = region.lower()
        filtered = []
        logger.info(f"过滤区域: '{region}' (小写: '{region_lower}')")
        logger.info(f"待过滤的节点: {nodes}")

        for node in nodes:
            node_lower = node.lower()
            # 检查是否匹配区域
            match = region_lower in node_lower
            if match:
                filtered.append(node)
                logger.debug(f"✅ '{node}' 匹配区域 '{region}' (小写匹配)")
            elif region in node:  # 精确匹配
                filtered.append(node)
                logger.debug(f"✅ '{node}' 匹配区域 '{region}' (精确匹配)")
            else:
                logger.debug(f"❌ '{node}' 不匹配区域 '{region}'")

        logger.info(f"匹配的节点: {filtered}")
        return filtered

    def select_best_node(self, nodes: List[str] = None) -> Optional[str]:
        """从可用节点中选择延迟最低的"""
        if nodes is None:
            logger.info("select_best_node: nodes为None，使用filter_nodes()")
            nodes = self.filter_nodes()
        else:
            logger.info(f"select_best_node: 使用传入的节点列表，共{len(nodes)}个: {nodes}")

        if not nodes:
            logger.warning("没有可用节点")
            return None

        # 如果只有一个节点，直接返回
        if len(nodes) == 1:
            logger.info(f"只有一个节点，直接选择: {nodes[0]}")
            return nodes[0]

        # 批量测试延迟 - 确保只测试传入的节点
        logger.info(f"开始测试 {len(nodes)} 个节点的延迟，节点列表: {nodes}")
        delays = self.clash_api.test_multiple_delays(
            nodes,
            test_url=self.config.test_url,
            timeout=self.config.test_timeout
        )

        if not delays:
            logger.warning("所有节点延迟测试失败")
            return None

        # 验证测试结果是否只包含传入的节点
        unexpected_nodes = set(delays.keys()) - set(nodes)
        if unexpected_nodes:
            logger.error(f"❌ 测试结果包含未预期的节点: {unexpected_nodes}")
            # 过滤掉未预期的节点
            delays = {k: v for k, v in delays.items() if k in nodes}
            logger.info(f"过滤后的测试结果: {delays}")

        # 详细记录测试结果
        logger.info("延迟测试结果:")
        for node, delay in sorted(delays.items(), key=lambda x: x[1]):
            logger.info(f"  {node}: {delay}ms")

        # 选择延迟最低的节点
        best_node = min(delays.items(), key=lambda x: x[1])[0]
        best_delay = delays[best_node]

        logger.info(f"选择最佳节点: {best_node} (延迟: {best_delay}ms)")

        # 再次验证选择的节点是否在传入的列表中
        if best_node not in nodes:
            logger.error(f"❌ 选择的节点 {best_node} 不在传入的列表中！列表: {nodes}")
            # 如果选择的节点不在列表中，从列表中选择延迟最低的
            best_node = min(delays.items(), key=lambda x: x[1] if x[0] in nodes else float('inf'))[0]
            logger.error(f"强制选择列表中的节点: {best_node}")

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
        logger.info(f"开始自动选择，当前配置: locked_region='{self.config.locked_region}'")
        available_nodes = self.filter_nodes()

        if not available_nodes:
            logger.warning("没有可用节点")
            return False

        logger.info(f"auto_select_and_switch中的可用节点: {available_nodes}")

        # 获取当前节点
        current_node = self.clash_api.get_current_proxy(self.config.proxy_group)
        logger.info(f"当前节点: {current_node}")

        # 如果当前节点可用且不在黑名单中，测试其延迟
        if current_node and not self.state.is_blacklisted(current_node):
            logger.info(f"测试当前节点延迟: {current_node}")
            current_delay = self.clash_api.get_delay(
                current_node,
                test_url=self.config.test_url,
                timeout=self.config.test_timeout
            )

            if current_delay is not None:
                logger.info(f"当前节点延迟: {current_delay}ms, 阈值: {self.config.delay_threshold}ms")
                if current_delay < self.config.delay_threshold:
                    logger.info(f"当前节点延迟良好: {current_node} ({current_delay}ms)")
                    self.state.current_delay = current_delay
                    self.state.add_delay_record(current_node, current_delay)
                    return True
                else:
                    logger.info(f"当前节点延迟过高，需要切换")
            else:
                logger.warning(f"当前节点延迟测试失败")
        else:
            if not current_node:
                logger.warning("无法获取当前节点")
            else:
                logger.warning(f"当前节点在黑名单中: {current_node}")

        # 需要切换，选择最佳节点
        logger.info(f"开始从 {len(available_nodes)} 个节点中选择最佳节点: {available_nodes}")
        best_node = self.select_best_node(available_nodes)
        if best_node:
            logger.info(f"选择结果: {best_node}")
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
