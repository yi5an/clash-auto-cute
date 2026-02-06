"""
Clash API 客户端
封装与 Clash RESTful API 的交互
"""

import requests
import logging
from typing import Dict, List, Optional
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

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送 HTTP 请求"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=5,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.ConnectionError:
            logger.error(f"无法连接到 Clash API: {url}")
            raise ClashAPIError(f"无法连接到 Clash API: {url}")
        except requests.exceptions.Timeout:
            logger.error(f"请求 Clash API 超时: {url}")
            raise ClashAPIError(f"请求超时: {url}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Clash API 返回错误: {e.response.status_code}")
            raise ClashAPIError(f"API 错误: {e.response.status_code}")

    def get_proxies(self) -> Dict:
        """获取所有代理节点"""
        try:
            response = self._request('GET', 'proxies')
            data = response.json()
            return data.get('proxies', {})
        except ClashAPIError as e:
            logger.error(f"获取节点列表失败: {e}")
            return {}

    def get_proxy_groups(self) -> Dict:
        """获取代理组"""
        try:
            response = self._request('GET', 'proxies')
            data = response.json()
            return data.get('groups', {})
        except ClashAPIError as e:
            logger.error(f"获取代理组失败: {e}")
            return {}

    def get_current_proxy(self, group_name: str = 'PROXY') -> Optional[str]:
        """获取当前使用的节点"""
        try:
            proxies = self.get_proxies()
            if group_name in proxies:
                return proxies[group_name].get('now', '')
            return None
        except Exception as e:
            logger.error(f"获取当前节点失败: {e}")
            return None

    def switch_proxy(self, group_name: str, proxy_name: str) -> bool:
        """切换到指定节点"""
        try:
            url = f"proxies/{group_name}"
            payload = {"name": proxy_name}
            self._request('PUT', url, json=payload)
            logger.info(f"切换节点成功: {proxy_name}")
            return True
        except ClashAPIError as e:
            logger.error(f"切换节点失败: {e}")
            return False

    def get_delay(self, proxy_name: str, test_url: str = None, timeout: int = 5000) -> Optional[int]:
        """测试节点延迟"""
        try:
            if test_url is None:
                test_url = self.config.test_url

            url = f"proxies/{proxy_name}/delay"
            payload = {
                "url": test_url,
                "timeout": timeout
            }
            response = self._request('GET', url, params=payload)
            data = response.json()
            delay = data.get('delay')
            if delay is not None:
                return delay
            return None
        except ClashAPIError as e:
            logger.error(f"测试延迟失败 {proxy_name}: {e}")
            return None

    def test_multiple_delays(self, proxy_names: List[str], test_url: str = None, timeout: int = 5000) -> Dict[str, int]:
        """批量测试多个节点的延迟"""
        results = {}
        for name in proxy_names:
            delay = self.get_delay(name, test_url, timeout)
            if delay is not None:
                results[name] = delay
        return results

    def get_proxy_by_type(self, proxy_type: str = 'ALL') -> List[str]:
        """根据类型获取节点列表"""
        proxies = self.get_proxies()
        result = []
        for name, info in proxies.items():
            if proxy_type == 'ALL' or info.get('type') == proxy_type:
                result.append(name)
        return result

    def get_proxy_by_region(self, region: str) -> List[str]:
        """根据区域名称过滤节点"""
        proxies = self.get_proxies()
        result = []
        region_lower = region.lower()
        for name, info in proxies.items():
            # 检查节点名称中是否包含区域关键词
            if region_lower in name.lower():
                result.append(name)
        return result

    def is_available(self) -> bool:
        """检查 Clash API 是否可用"""
        try:
            response = self._request('GET', '')
            return response.status_code == 200
        except:
            return False
