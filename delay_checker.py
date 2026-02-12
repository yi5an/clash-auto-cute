"""
延迟检测器
定时检测节点延迟并触发切换
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional
from clash_api import ClashAPI
from node_manager import NodeManager
from models import Config, RuntimeState

logger = logging.getLogger(__name__)


class DelayChecker:
    """延迟检测器"""

    def __init__(self, clash_api: ClashAPI, node_manager: NodeManager,
                 config: Config, state: RuntimeState):
        self.clash_api = clash_api
        self.node_manager = node_manager
        self.config = config
        self.state = state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 回调函数列表
        self._callbacks = []

    def add_callback(self, callback: Callable):
        """添加状态变化回调"""
        self._callbacks.append(callback)

    def is_running(self) -> bool:
        """检测器是否正在运行"""
        return self._running

    def _check_active_connections(self) -> bool:
        """检测代理是否有活跃连接

        检测方法：
        1. 'api' - 通过 Clash API 检测（如果支持）
        2. 'traffic' - 通过流量统计检测
        3. 'none' - 禁用检测

        Returns:
            bool: 是否检测到活跃连接
        """
        method = self.config.active_check_method

        if method == 'none':
            logger.debug("活跃连接检测已禁用")
            return False

        try:
            # 方法1: 通过 Clash API 检测连接数
            if method == 'api':
                # 尝试获取连接信息（某些 Clash 版本支持）
                # 注意：不是所有 Clash 都支持这个端点
                result = self._check_active_via_api()
                if result:
                    logger.info("通过 API 检测到活跃连接")
                    return True

            # 方法2: 通过流量统计判断
            if method == 'traffic':
                # 检查最近是否有流量记录
                result = self._check_active_via_traffic()
                if result:
                    logger.info("通过流量统计检测到活跃连接")
                    return True

            logger.warning("活跃连接检测未发现活跃连接")
            return False

        except Exception as e:
            logger.error(f"活跃连接检测异常: {e}")
            return False

    def _check_active_via_api(self) -> bool:
        """通过 Clash API 检测活跃连接"""
        try:
            # 尝试获取连接信息（部分 Clash 版本支持 /connections 端点）
            response = self.clash_api._request('GET', 'connections', max_retries=1)

            if response.status_code == 200:
                data = response.json()
                connections = data.get('connections', {})

                # 检查是否有活跃的 SOCKS5/HTTP 连接
                active_count = len([c for c in connections.values() if c.get('alive', False)])

                logger.debug(f"API 返回的连接数: {active_count}")
                return active_count > 0
            else:
                logger.debug("Clash API 不支持 /connections 端点")
                return False

        except Exception as e:
            logger.debug(f"API 检测失败: {e}")
            return False

    def _check_active_via_traffic(self) -> bool:
        """通过流量统计判断是否有活跃使用"""
        # 检查延迟历史中最近的测试记录
        # 如果最近30秒内有成功的延迟测试，说明可能有活跃使用
        if not self.state.delay_history:
            return False

        now = datetime.now()
        recent_records = [
            r for r in self.state.delay_history
            if (now - r.timestamp).total_seconds() < 30
        ]

        # 如果有最近的成功测试记录，认为可能有活跃使用
        has_recent_activity = len(recent_records) > 0

        if has_recent_activity:
            logger.debug(f"最近30秒内有 {len(recent_records)} 次延迟测试，可能有活跃使用")
        else:
            logger.debug("最近30秒内无延迟测试记录")

        return has_recent_activity

    def _notify_callbacks(self):
        """通知所有回调函数"""
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"回调函数执行失败: {e}")

    def start(self):
        """启动延迟检测"""
        if self._running:
            logger.warning("延迟检测器已在运行")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()

        self.state.is_running = True
        logger.info("延迟检测器已启动")

    def stop(self):
        """停止延迟检测"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        self.state.is_running = False
        logger.info("延迟检测器已停止")

    def _check_loop(self):
        """延迟检测循环"""
        while self._running:
            try:
                # 执行一次延迟检测
                self._check_and_switch()

                # 等待指定的检测间隔
                self._stop_event.wait(self.config.check_interval)

            except Exception as e:
                logger.error(f"延迟检测出错: {e}")
                # 出错后等待一段时间再继续
                self._stop_event.wait(10)

    def _check_and_switch(self):
        """检测当前节点并判断是否需要切换（智能版）"""
        try:
            # 检查是否在静默期内
            if self.state.in_silent_period and self.state.silent_until:
                now = datetime.now()
                if now < self.state.silent_until:
                    remaining = (self.state.silent_until - now).total_seconds()
                    logger.info(f"静默期内，剩余 {remaining} 秒，跳过检测")
                    self._notify_callbacks()
                    return  # 静默期内不检测

            # 静默期结束
            if self.state.in_silent_period and self.state.silent_until and datetime.now() >= self.state.silent_until:
                logger.info("静默期结束，恢复检测")
                self.state.in_silent_period = False
                self.state.silent_until = None

            # 获取当前节点
            current_node = self.clash_api.get_current_proxy(self.config.proxy_group)

            if not current_node:
                logger.warning("无法获取当前节点")
                return

            # 测试当前节点延迟
            delay = self.clash_api.get_delay(
                current_node,
                test_url=self.config.test_url,
                timeout=self.config.test_timeout
            )

            # 更新状态
            self.state.current_node = current_node
            self.state.current_delay = delay if delay else 0
            self.state.last_check_time = datetime.now()

            # 记录延迟历史
            if delay is not None:
                self.state.add_delay_record(current_node, delay)

            # 判断是否需要切换
            need_switch = False

            if delay is None:
                logger.warning(f"节点延迟测试失败: {current_node}")
                need_switch = True
            elif delay > self.config.delay_threshold:
                logger.warning(
                    f"节点延迟超过阈值: {current_node} "
                    f"({delay}ms > {self.config.delay_threshold}ms)"
                )
                need_switch = True
            else:
                logger.info(f"节点延迟正常: {current_node} ({delay}ms)")

            # 智能判断：是否允许切换
            allow_switch = True

            if need_switch:
                # 检查1：最小延迟保护 - 避免频繁切换
                if delay and delay < self.config.min_delay_for_switch:
                    logger.info(f"延迟虽超阈值但过低 ({delay}ms < {self.config.min_delay_for_switch}ms)，跳过切换以避免抖动")
                    allow_switch = False

                # 检查2：活跃连接检测（如果启用）
                if allow_switch and self.config.enable_active_detection:
                    has_active = self._check_active_connections()
                    if has_active:
                        logger.info("检测到活跃连接，暂停切换")
                        allow_switch = False
                        # 可选：延长静默期
                        if self.config.active_check_method != 'none':
                            silent_minutes = self.config.silent_period_minutes + 2  # 额外2分钟
                            self.state.silent_until = datetime.now() + timedelta(minutes=silent_minutes)
                            self.state.in_silent_period = True
                            logger.info(f"设置静默期 {silent_minutes} 分钟")
                    else:
                        logger.debug("未检测到活跃连接")

            # 需要切换时，自动选择并切换到最佳节点
            if allow_switch and need_switch:
                logger.info("触发自动切换...")
                success = self.node_manager.auto_select_and_switch()

                if success:
                    logger.info("自动切换成功")
                    # 记录切换时间并进入静默期
                    self.state.last_switch_time = datetime.now()
                    self.state.switch_count += 1

                    # 设置静默期
                    silent_minutes = self.config.silent_period_minutes
                    self.state.silent_until = datetime.now() + timedelta(minutes=silent_minutes)
                    self.state.in_silent_period = True
                    logger.info(f"切换后进入 {silent_minutes} 分钟静默期")
                else:
                    logger.warning("自动切换失败")

            # 通知回调函数
            self._notify_callbacks()

        except Exception as e:
            logger.error(f"检测过程出错: {e}")

    def check_now(self):
        """立即执行一次检测（手动触发）"""
        def _manual_check():
            self._check_and_switch()

        thread = threading.Thread(target=_manual_check, daemon=True)
        thread.start()

    def is_running(self) -> bool:
        """检测器是否正在运行"""
        return self._running
