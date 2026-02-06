#!/usr/bin/env python3
"""
测试脚本 - 验证各个模块是否正常工作
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """测试依赖导入"""
    print("=" * 50)
    print("测试依赖导入...")
    print("=" * 50)

    try:
        import flask
        print("✓ Flask")
    except ImportError as e:
        print(f"✗ Flask: {e}")
        return False

    try:
        import requests
        print("✓ Requests")
    except ImportError as e:
        print(f"✗ Requests: {e}")
        return False

    try:
        from flask_socketio import SocketIO
        print("✓ Flask-SocketIO")
    except ImportError as e:
        print(f"✗ Flask-SocketIO: {e}")
        return False

    try:
        from dotenv import load_dotenv
        print("✓ python-dotenv")
    except ImportError as e:
        print(f"✗ python-dotenv: {e}")
        return False

    print("\n所有依赖导入成功!\n")
    return True


def test_modules():
    """测试模块导入"""
    print("=" * 50)
    print("测试模块导入...")
    print("=" * 50)

    try:
        from models import Config, RuntimeState
        print("✓ models")
    except ImportError as e:
        print(f"✗ models: {e}")
        return False

    try:
        from config import load_config
        print("✓ config")
    except ImportError as e:
        print(f"✗ config: {e}")
        return False

    try:
        from clash_api import ClashAPI
        print("✓ clash_api")
    except ImportError as e:
        print(f"✗ clash_api: {e}")
        return False

    try:
        from node_manager import NodeManager
        print("✓ node_manager")
    except ImportError as e:
        print(f"✗ node_manager: {e}")
        return False

    try:
        from delay_checker import DelayChecker
        print("✓ delay_checker")
    except ImportError as e:
        print(f"✗ delay_checker: {e}")
        return False

    print("\n所有模块导入成功!\n")
    return True


def test_config():
    """测试配置加载"""
    print("=" * 50)
    print("测试配置加载...")
    print("=" * 50)

    try:
        from config import load_config
        config = load_config()

        print(f"Clash API URL: {config.clash_api_url}")
        print(f"延迟阈值: {config.delay_threshold} ms")
        print(f"检测间隔: {config.check_interval} s")
        print(f"锁定区域: {config.locked_region or '未设置'}")

        print("\n配置加载成功!\n")
        return True
    except Exception as e:
        print(f"✗ 配置加载失败: {e}\n")
        return False


def test_clash_api():
    """测试 Clash API 连接"""
    print("=" * 50)
    print("测试 Clash API 连接...")
    print("=" * 50)

    try:
        from config import load_config
        from clash_api import ClashAPI

        config = load_config()
        api = ClashAPI(config)

        if api.is_available():
            print("✓ Clash API 连接成功")

            # 获取节点列表
            proxies = api.get_proxies()
            print(f"✓ 获取到 {len(proxies)} 个代理节点/组")

            return True
        else:
            print("✗ 无法连接到 Clash API")
            print("请确保 Clash 正在运行并且 RESTful API 已启用")
            return False

    except Exception as e:
        print(f"✗ Clash API 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 48 + "╗")
    print("║" + " " * 10 + "Clash Auto Switch 测试" + " " * 14 + "║")
    print("╚" + "=" * 48 + "╝")
    print()

    results = []

    # 测试依赖导入
    results.append(("依赖导入", test_imports()))

    # 测试模块导入
    results.append(("模块导入", test_modules()))

    # 测试配置加载
    results.append(("配置加载", test_config()))

    # 测试 Clash API 连接
    results.append(("Clash API", test_clash_api()))

    # 总结
    print("=" * 50)
    print("测试总结")
    print("=" * 50)

    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")

    print()

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("🎉 所有测试通过! 可以启动服务了。")
        print("运行: ./start.sh 或 python3 app.py")
        return 0
    else:
        print("⚠ 部分测试失败，请检查错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
