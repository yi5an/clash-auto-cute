"""
延迟检测器
定时检测节点延迟并触发切换
"""

import time
import threading
import logging
from datetime import datetime
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
        """检测当前节点并判断是否需要切换"""
        try:
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

            # 需要切换时，自动选择并切换到最佳节点
            if need_switch:
                logger.info("触发自动切换...")
                success = self.node_manager.auto_select_and_switch()
                if success:
                    logger.info("自动切换成功")
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
