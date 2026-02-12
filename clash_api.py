"""
Clash API 客户端
封装与 Clash RESTful API 的交互
"""

import requests
import logging
import time
from typing import Dict, List, Optional
from urllib.parse import quote
from models import Config

logger = logging.getLogger(__name__)


class ClashAPIError(Exception):
    """Clash API 错误"""
    pass


class ClashAPI:
    """Clash API 客户端"""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.clash_api_url.rstrip('/')
        self.secret = config.clash_secret
        self.headers = {}
        if self.secret:
            self.headers['Authorization'] = f'Bearer {self.secret}'

        logger.info(f"初始化 Clash API 客户端: {self.base_url}")
        logger.debug(f"代理组: {config.proxy_group}, 测试URL: {config.test_url}")

    def _request(self, method: str, endpoint: str, max_retries: int = 3, **kwargs) -> requests.Response:
        """发送 HTTP 请求，支持重试机制"""
        url = f"{self.base_url}/{endpoint}"
        start_time = time.time()

        # 记录请求详情
        json_data = kwargs.get('json')
        params = kwargs.get('params')
        logger.debug(f"API 请求: {method} {url}")
        if json_data:
            logger.debug(f"  请求体: {json_data}")
        if params:
            logger.debug(f"  查询参数: {params}")

        last_error = None
        for attempt in range(max_retries):
            try:
                attempt_start = time.time()
                response = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=(15, 60),  # (连接超时, 读取超时) - 增加以适应慢速 API
                    **kwargs
                )
                attempt_time = time.time() - attempt_start

                # 记录成功响应
                logger.debug(f"  响应: 状态码={response.status_code}, 耗时={attempt_time:.2f}s")

                response.raise_for_status()

                # 记录总耗时
                total_time = time.time() - start_time
                if total_time > 3:
                    logger.warning(f"API 响应较慢: {method} {endpoint} 总耗时 {total_time:.2f}s (重试 {attempt + 1} 次)")

                return response

            except requests.exceptions.ConnectionError as e:
                last_error = e
                attempt_time = time.time() - start_time
                logger.warning(f"  连接失败 (尝试 {attempt + 1}/{max_retries}, 耗时 {attempt_time:.2f}s): {str(e)[:100]}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # 重试前等待1秒
                    continue
                logger.error(f"无法连接到 Clash API: {url}")
                raise ClashAPIError(f"无法连接到 Clash API: {url}")

            except requests.exceptions.Timeout as e:
                last_error = e
                attempt_time = time.time() - start_time
                logger.warning(f"  请求超时 (尝试 {attempt + 1}/{max_retries}, 耗时 {attempt_time:.2f}s)")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 超时后等待更长时间
                    continue
                logger.error(f"请求 Clash API 超时: {url}")
                raise ClashAPIError(f"请求超时: {url}")

            except requests.exceptions.HTTPError as e:
                last_error = e
                attempt_time = time.time() - start_time
                response_text = e.response.text[:200] if hasattr(e, 'response') and e.response else 'N/A'
                logger.error(f"  HTTP 错误 (尝试 {attempt + 1}/{max_retries}, 耗时 {attempt_time:.2f}s): "
                           f"状态码={e.response.status_code}, 响应={response_text}")
                raise ClashAPIError(f"API 错误: {e.response.status_code}")

    def get_proxies(self) -> Dict:
        """获取所有代理节点"""
        try:
            logger.debug("获取所有代理节点")
            response = self._request('GET', 'proxies')
            data = response.json()
            proxies = data.get('proxies', {})
            logger.info(f"成功获取代理节点: 共 {len(proxies)} 个")
            return proxies
        except ClashAPIError as e:
            logger.error(f"获取节点列表失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"获取节点列表异常: {type(e).__name__}: {e}")
            return {}

    def get_proxy_groups(self) -> Dict:
        """获取代理组"""
        try:
            logger.debug("获取代理组")
            response = self._request('GET', 'proxies')
            data = response.json()
            groups = data.get('groups', {})
            logger.info(f"成功获取代理组: 共 {len(groups)} 个")
            return groups
        except ClashAPIError as e:
            logger.error(f"获取代理组失败: {e}")
            return {}

    def get_current_proxy(self, group_name: str = 'PROXY') -> Optional[str]:
        """获取当前使用的节点"""
        try:
            logger.debug(f"获取当前节点: 组名={group_name}")
            proxies = self.get_proxies()

            if group_name in proxies:
                current = proxies[group_name].get('now', '')
                logger.info(f"当前使用节点: {current} (组: {group_name})")
                return current
            else:
                available_groups = [k for k, v in proxies.items() if v.get('type') in ['Selector', 'URLTest']]
                logger.error(f"代理组 '{group_name}' 不存在, 可用的代理组: {available_groups[:5]}...")
                return None
        except Exception as e:
            logger.error(f"获取当前节点失败: {type(e).__name__}: {e}")
            return None

    def switch_proxy(self, group_name: str, proxy_name: str) -> bool:
        """切换到指定节点"""
        try:
            logger.info(f"准备切换节点: 组={group_name}, 节点={proxy_name}")

            # URL 编码以支持中文代理组名
            encoded_group_name = quote(group_name, safe='')
            url = f"proxies/{encoded_group_name}"
            logger.debug(f"  编码后的URL: {url}")

            payload = {"name": proxy_name}
            self._request('PUT', url, json=payload)
            logger.info(f"✅ 切换节点成功: {proxy_name}")
            return True
        except ClashAPIError as e:
            logger.error(f"❌ 切换节点失败: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 切换节点异常: {type(e).__name__}: {e}")
            return False

    def get_delay(self, proxy_name: str, test_url: str = None, timeout: int = 5000) -> Optional[int]:
        """测试节点延迟"""
        try:
            if test_url is None:
                test_url = self.config.test_url

            logger.debug(f"测试节点延迟: 节点={proxy_name}, URL={test_url}, 超时={timeout}ms")

            # URL 编码以支持中文节点名
            encoded_proxy_name = quote(proxy_name, safe='')
            url = f"proxies/{encoded_proxy_name}/delay"

            payload = {
                "url": test_url,
                "timeout": timeout
            }

            response = self._request('GET', url, params=payload)
            data = response.json()
            delay = data.get('delay')

            if delay is not None:
                logger.debug(f"  延迟结果: {delay}ms")
                if delay > 1000:
                    logger.warning(f"节点延迟较高: {proxy_name} ({delay}ms)")
                return delay
            else:
                logger.warning(f"延迟测试未返回结果: {proxy_name}")
                return None
        except ClashAPIError as e:
            logger.error(f"测试延迟失败 {proxy_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"测试延迟异常 {proxy_name}: {type(e).__name__}: {e}")
            return None

    def test_multiple_delays(self, proxy_names: List[str], test_url: str = None, timeout: int = 5000) -> Dict[str, int]:
        """批量测试多个节点的延迟"""
        logger.info(f"开始批量测试 {len(proxy_names)} 个节点的延迟")
        results = {}
        for i, name in enumerate(proxy_names, 1):
            logger.debug(f"  [{i}/{len(proxy_names)}] 测试 {name}")
            delay = self.get_delay(name, test_url, timeout)
            if delay is not None:
                results[name] = delay
        logger.info(f"批量测试完成: 成功 {len(results)}/{len(proxy_names)} 个节点")
        return results

    def get_proxy_by_type(self, proxy_type: str = 'ALL') -> List[str]:
        """根据类型获取节点列表"""
        logger.debug(f"按类型获取节点: 类型={proxy_type}")
        proxies = self.get_proxies()
        result = []
        for name, info in proxies.items():
            if proxy_type == 'ALL' or info.get('type') == proxy_type:
                result.append(name)
        logger.debug(f"  找到 {len(result)} 个节点")
        return result

    def get_proxy_by_region(self, region: str) -> List[str]:
        """根据区域名称过滤节点"""
        logger.debug(f"按区域获取节点: 区域={region}")
        proxies = self.get_proxies()
        result = []
        region_lower = region.lower()
        for name, info in proxies.items():
            # 检查节点名称中是否包含区域关键词
            if region_lower in name.lower():
                result.append(name)
        logger.debug(f"  找到 {len(result)} 个节点")
        return result

    def is_available(self) -> bool:
        """检查 Clash API 是否可用"""
        try:
            logger.debug(f"检查 Clash API 可用性: {self.base_url}")
            response = self._request('GET', '')
            available = response.status_code == 200
            logger.info(f"Clash API 状态: {'✅ 可用' if available else '❌ 不可用'}")
            return available
        except Exception as e:
            logger.error(f"Clash API 不可用: {type(e).__name__}: {e}")
            return False
