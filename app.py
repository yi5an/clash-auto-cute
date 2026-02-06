"""
Clash Auto Switch 主应用
Flask Web 服务器
"""

import os
import logging
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from config import load_config, update_config
from models import Config, RuntimeState
from clash_api import ClashAPI
from node_manager import NodeManager
from delay_checker import DelayChecker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
app.config['SECRET_KEY'] = 'clash-auto-switch-secret-key'

# 启用 CORS
CORS(app)

# 创建 SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局对象
config: Config = load_config()
state = RuntimeState()
clash_api: ClashAPI = None
node_manager: NodeManager = None
delay_checker: DelayChecker = None


def initialize():
    """初始化服务"""
    global clash_api, node_manager, delay_checker

    try:
        # 创建 Clash API 客户端
        clash_api = ClashAPI(config)

        # 检查 Clash API 是否可用
        if not clash_api.is_available():
            logger.error("无法连接到 Clash API，请确保 Clash 正在运行")
            return False

        # 创建节点管理器
        node_manager = NodeManager(clash_api, config, state)

        # 创建延迟检测器
        delay_checker = DelayChecker(clash_api, node_manager, config, state)

        # 添加状态变化回调
        delay_checker.add_callback(notify_state_update)

        # 获取初始状态
        current_node = clash_api.get_current_proxy(config.proxy_group)
        if current_node:
            state.current_node = current_node

        available_nodes = node_manager.get_available_nodes()
        state.available_nodes = available_nodes

        logger.info("服务初始化成功")
        return True

    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        return False


def notify_state_update():
    """通知客户端状态更新"""
    try:
        socketio.emit('state_update', state.to_dict())
    except Exception as e:
        logger.error(f"发送状态更新失败: {e}")


# ========== 路由 ==========

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


# ========== API: 状态 ==========

@app.route('/api/state', methods=['GET'])
def get_state():
    """获取当前状态"""
    return jsonify(state.to_dict())


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    return jsonify(config.to_dict())


@app.route('/api/config', methods=['POST'])
def update_config_api():
    """更新配置"""
    try:
        data = request.json
        global config
        config = update_config(config, **data)

        # 如果延迟检测器正在运行，重启它以应用新配置
        if delay_checker and delay_checker.is_running():
            delay_checker.stop()
            delay_checker.start()

        return jsonify({'success': True, 'config': config.to_dict()})
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== API: 节点管理 ==========

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """获取所有节点"""
    try:
        if not node_manager:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500

        all_nodes = node_manager.get_available_nodes()
        filtered_nodes = node_manager.filter_nodes()

        return jsonify({
            'success': True,
            'all_nodes': all_nodes,
            'filtered_nodes': filtered_nodes,
            'current_node': state.current_node
        })
    except Exception as e:
        logger.error(f"获取节点列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/nodes/switch', methods=['POST'])
def switch_node():
    """手动切换节点"""
    try:
        data = request.json
        node_name = data.get('node_name')

        if not node_name:
            return jsonify({'success': False, 'error': '节点名称不能为空'}), 400

        if not node_manager:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500

        success = node_manager.switch_to_node(node_name)
        notify_state_update()

        if success:
            return jsonify({'success': True, 'message': f'已切换到节点: {node_name}'})
        else:
            return jsonify({'success': False, 'error': '切换失败'}), 500

    except Exception as e:
        logger.error(f"切换节点失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/nodes/test', methods=['POST'])
def test_node():
    """测试节点延迟"""
    try:
        data = request.json
        node_name = data.get('node_name')

        if not node_name:
            return jsonify({'success': False, 'error': '节点名称不能为空'}), 400

        if not clash_api:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500

        delay = clash_api.get_delay(
            node_name,
            test_url=config.test_url,
            timeout=config.test_timeout
        )

        if delay is not None:
            return jsonify({'success': True, 'node_name': node_name, 'delay': delay})
        else:
            return jsonify({'success': False, 'error': '测试失败'}), 500

    except Exception as e:
        logger.error(f"测试节点延迟失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== API: 黑名单 ==========

@app.route('/api/blacklist', methods=['GET'])
def get_blacklist():
    """获取黑名单"""
    return jsonify({'success': True, 'blacklist': list(state.blacklist)})


@app.route('/api/blacklist', methods=['POST'])
def add_blacklist():
    """添加黑名单"""
    try:
        data = request.json
        node_name = data.get('node_name')

        if not node_name:
            return jsonify({'success': False, 'error': '节点名称不能为空'}), 400

        success = node_manager.add_blacklist(node_name)
        notify_state_update()

        if success:
            return jsonify({'success': True, 'message': f'已添加到黑名单: {node_name}'})
        else:
            return jsonify({'success': False, 'error': '添加失败'}), 500

    except Exception as e:
        logger.error(f"添加黑名单失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/blacklist', methods=['DELETE'])
def remove_blacklist():
    """移除黑名单"""
    try:
        data = request.json
        node_name = data.get('node_name')

        if not node_name:
            return jsonify({'success': False, 'error': '节点名称不能为空'}), 400

        success = node_manager.remove_blacklist(node_name)
        notify_state_update()

        if success:
            return jsonify({'success': True, 'message': f'已从黑名单移除: {node_name}'})
        else:
            return jsonify({'success': False, 'error': '移除失败'}), 500

    except Exception as e:
        logger.error(f"移除黑名单失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== API: 延迟检测 ==========

@app.route('/api/checker/start', methods=['POST'])
def start_checker():
    """启动延迟检测"""
    try:
        if not delay_checker:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500

        delay_checker.start()
        notify_state_update()

        return jsonify({'success': True, 'message': '延迟检测已启动'})
    except Exception as e:
        logger.error(f"启动延迟检测失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/checker/stop', methods=['POST'])
def stop_checker():
    """停止延迟检测"""
    try:
        if not delay_checker:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500

        delay_checker.stop()
        notify_state_update()

        return jsonify({'success': True, 'message': '延迟检测已停止'})
    except Exception as e:
        logger.error(f"停止延迟检测失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/checker/check', methods=['POST'])
def check_now():
    """立即执行一次检测"""
    try:
        if not delay_checker:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500

        delay_checker.check_now()

        return jsonify({'success': True, 'message': '正在检测...'})
    except Exception as e:
        logger.error(f"执行检测失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== API: 区域 ==========

@app.route('/api/regions', methods=['GET'])
def get_regions():
    """获取所有区域"""
    try:
        if not node_manager:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500

        regions = node_manager.get_all_regions()
        return jsonify({'success': True, 'regions': regions})
    except Exception as e:
        logger.error(f"获取区域列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== WebSocket ==========

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')
    emit('state_update', state.to_dict())


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    logger.info('客户端已断开')


@socketio.on('subscribe')
def handle_subscribe():
    """订阅状态更新"""
    emit('state_update', state.to_dict())


# ========== 主程序 ==========

def main():
    """主函数"""
    # 初始化服务
    if not initialize():
        logger.error("初始化失败，请检查 Clash 是否正在运行")
        return

    # 自动启动延迟检测
    delay_checker.start()
    logger.info("延迟检测已自动启动")

    # 获取配置
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info(f"Web 界面: http://{host}:{port}")

    # 启动服务器
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
