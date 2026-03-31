#!/usr/bin/env python3
"""
回归测试：兼容新版 Clash 节点类型与代理组回退逻辑
"""

from models import Config, RuntimeState
from clash_api import ClashAPI
from node_manager import NodeManager


class FakeClashAPI(ClashAPI):
    def __init__(self, config: Config, proxies):
        super().__init__(config)
        self._fake_proxies = proxies

    def get_proxies(self):
        return self._fake_proxies


def test_anytls_nodes_are_available():
    config = Config(proxy_group='PROXY')
    proxies = {
        'DIRECT': {'type': 'Direct'},
        '自动选择': {'type': 'URLTest', 'all': ['香港1']},
        '贝贝云': {'type': 'Selector', 'all': ['自动选择', '香港1', '美国1']},
        '剩余流量：63.73 GB': {'type': 'AnyTLS'},
        '香港1': {'type': 'AnyTLS'},
        '美国1': {'type': 'Trojan'},
    }
    api = FakeClashAPI(config, proxies)
    manager = NodeManager(api, config, RuntimeState())

    nodes = manager.get_available_nodes()

    assert '香港1' in nodes
    assert '美国1' in nodes
    assert 'DIRECT' not in nodes
    assert '剩余流量：63.73 GB' not in nodes


def test_proxy_group_falls_back_to_existing_selector():
    config = Config(proxy_group='PROXY')
    proxies = {
        'DIRECT': {'type': 'Direct'},
        '自动选择': {'type': 'URLTest', 'all': ['香港1'], 'now': '香港1'},
        '贝贝云': {'type': 'Selector', 'all': ['自动选择', '香港1'], 'now': '自动选择'},
        '香港1': {'type': 'AnyTLS'},
    }
    api = FakeClashAPI(config, proxies)

    resolved = api.resolve_proxy_group(config.proxy_group, proxies)

    assert resolved == '贝贝云'


if __name__ == '__main__':
    test_anytls_nodes_are_available()
    test_proxy_group_falls_back_to_existing_selector()
    print('ok')
