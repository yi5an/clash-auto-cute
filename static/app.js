// WebSocket 连接
let socket;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initWebSocket();
    loadState();
    loadConfig();
    loadSmartConfig();
    loadNodes();
    loadBlacklist();
    loadRegions();
    updateStatusIndicator();
});

// 初始化 WebSocket
function initWebSocket() {
    socket = io();

    socket.on('connect', function() {
        console.log('已连接到服务器');
    });

    socket.on('disconnect', function() {
        console.log('与服务器断开连接');
    });

    socket.on('state_update', function(state) {
        updateStateDisplay(state);
    });
}

// 加载状态
async function loadState() {
    try {
        const response = await fetch('/api/state');
        const state = await response.json();
        updateStateDisplay(state);
    } catch (error) {
        console.error('加载状态失败:', error);
        showNotification('加载状态失败', 'error');
    }
}

// 更新状态显示
function updateStateDisplay(state) {
    // 当前节点
    const currentNodeEl = document.getElementById('currentNode');
    currentNodeEl.textContent = state.current_node || '--';
    currentNodeEl.classList.remove('delay-good', 'delay-warning', 'delay-danger');

    // 当前延迟
    const currentDelayEl = document.getElementById('currentDelay');
    if (state.current_delay) {
        currentDelayEl.textContent = state.current_delay;
        currentDelayEl.className = 'status-value ' + getDelayClass(state.current_delay);
    } else {
        currentDelayEl.textContent = '--';
        currentDelayEl.className = 'status-value';
    }

    // 系统状态
    const systemStatusEl = document.getElementById('systemStatus');
    const statusIndicatorEl = document.getElementById('statusIndicator');

    if (state.is_running) {
        systemStatusEl.innerHTML = '<span style="color: var(--accent-green);">运行中</span>';
        statusIndicatorEl.className = 'status-indicator running';
        document.getElementById('btnStart').disabled = true;
        document.getElementById('btnStop').disabled = false;
    } else {
        systemStatusEl.innerHTML = '<span style="color: var(--accent-orange);">已停止</span>';
        statusIndicatorEl.className = 'status-indicator stopped';
        document.getElementById('btnStart').disabled = false;
        document.getElementById('btnStop').disabled = true;
    }

    // 切换次数
    document.getElementById('switchCount').textContent = state.switch_count;

    // 上次检测时间
    if (state.last_check_time) {
        const lastCheck = new Date(state.last_check_time);
        document.getElementById('lastCheck').textContent = formatTime(lastCheck);
    }

    // 可用节点数
    document.getElementById('availableCount').textContent = state.available_nodes.length;

    // 更新延迟历史
    updateHistoryList(state.delay_history);

    // 更新静默期状态
    const silentPeriodEl = document.getElementById('silentPeriod');
    if (state.in_silent_period && state.silent_until) {
        const now = new Date();
        const remaining = Math.max(0, Math.ceil((state.silent_until - now) / 1000));
        silentPeriodEl.textContent = `${remaining} 分钟`;
        silentPeriodEl.className = 'status-value delay-warning';
    } else {
        silentPeriodEl.textContent = '未启用';
        silentPeriodEl.className = 'status-value';
    }

    // 更新活跃连接状态
    const activeConnectionsEl = document.getElementById('activeConnections');
    if (state.has_active_connections) {
        activeConnectionsEl.textContent = '检测到活跃';
        activeConnectionsEl.className = 'status-value delay-warning';
    } else if (state.in_silent_period) {
        activeConnectionsEl.textContent = '暂停检测';
        activeConnectionsEl.className = 'status-value';
    } else {
        activeConnectionsEl.textContent = '未启用';
        activeConnectionsEl.className = 'status-value';
    }
}

// 获取延迟状态类
function getDelayClass(delay) {
    if (delay < 150) return 'delay-good';
    if (delay < 300) return 'delay-warning';
    return 'delay-danger';
}

// 格式化时间
function formatTime(date) {
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) { // 1分钟内
        return '刚刚';
    } else if (diff < 3600000) { // 1小时内
        return Math.floor(diff / 60000) + '分钟前';
    } else if (diff < 86400000) { // 24小时内
        return Math.floor(diff / 3600000) + '小时前';
    } else {
        return date.toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// 更新状态指示器
function updateStatusIndicator() {
    // 状态指示器会在 updateStateDisplay 中更新
}

// 加载配置
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();

        document.getElementById('delayThreshold').value = config.delay_threshold;
        document.getElementById('checkInterval').value = config.check_interval;
        document.getElementById('lockedRegion').value = config.locked_region || '';
        document.getElementById('testUrl').value = config.test_url;
    } catch (error) {
        console.error('加载配置失败:', error);
        showNotification('加载配置失败', 'error');
    }
}

// 加载智能配置
async function loadSmartConfig() {
    try {
        const response = await fetch('/api/config/smart');
        const config = await response.json();

        document.getElementById('silentPeriodMinutes').value = config.silent_period_minutes;
        document.getElementById('minDelayForSwitch').value = config.min_delay_for_switch;
        document.getElementById('enableActiveDetection').value = config.enable_active_detection.toString();
        document.getElementById('activeCheckMethod').value = config.active_check_method;
    } catch (error) {
        console.error('加载智能配置失败:', error);
        showNotification('加载智能配置失败', 'error');
    }
}

// 更新基础配置
async function updateConfig() {
    const config = {
        delay_threshold: parseInt(document.getElementById('delayThreshold').value),
        check_interval: parseInt(document.getElementById('checkInterval').value),
        locked_region: document.getElementById('lockedRegion').value,
        test_url: document.getElementById('testUrl').value
    };

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const result = await response.json();

        if (result.success) {
            showNotification('配置已保存', 'success');
            loadNodes();  // 重新加载节点列表
        } else {
            showNotification('保存失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('更新配置失败:', error);
        showNotification('更新配置失败', 'error');
    }
}

// 更新智能配置
async function updateSmartConfig() {
    const config = {
        silent_period_minutes: parseInt(document.getElementById('silentPeriodMinutes').value),
        min_delay_for_switch: parseInt(document.getElementById('minDelayForSwitch').value),
        enable_active_detection: document.getElementById('enableActiveDetection').value === 'true',
        active_check_method: document.getElementById('activeCheckMethod').value
    };

    try {
        const response = await fetch('/api/config/smart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const result = await response.json();

        if (result.success) {
            showNotification('智能配置已保存', 'success');
        } else {
            showNotification('保存失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('更新智能配置失败:', error);
        showNotification('更新智能配置失败', 'error');
    }
}

// 加载节点列表
async function loadNodes() {
    const nodeListEl = document.getElementById('nodeList');
    nodeListEl.innerHTML = '<div class="loading"></div>';

    try {
        const regionFilter = document.getElementById('regionFilter').value;
        const url = regionFilter
            ? `/api/nodes?region=${encodeURIComponent(regionFilter)}`
            : '/api/nodes';

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            displayNodes(data.filtered_nodes, data.current_node);
        } else {
            nodeListEl.innerHTML = '<p class="text-center">加载失败</p>';
        }
    } catch (error) {
        console.error('加载节点列表失败:', error);
        nodeListEl.innerHTML = '<p class="text-center">加载失败</p>';
    }
}

// 显示节点列表
function displayNodes(nodes, currentNode) {
    const container = document.getElementById('nodeList');

    if (!nodes || nodes.length === 0) {
        container.innerHTML = '<p class="text-center">暂无可用节点</p>';
        return;
    }

    container.innerHTML = nodes.map((node, index) => `
        <div class="node-item" style="animation-delay: ${index * 0.05}s">
            <div class="node-name ${node === currentNode ? 'current' : ''}">${node}</div>
            <div class="node-actions">
                <button class="btn btn-sm btn-primary" onclick="switchNode('${escapeHtml(node)}')">切换</button>
                <button class="btn btn-sm btn-info" onclick="testNode('${escapeHtml(node)}')">测速</button>
                <button class="btn btn-sm btn-danger" onclick="addBlacklist('${escapeHtml(node)}')">拉黑</button>
            </div>
        </div>
    `).join('');
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 切换节点
async function switchNode(nodeName) {
    showNotification('正在切换节点...', 'info');

    try {
        const response = await fetch('/api/nodes/switch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ node_name: nodeName })
        });

        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
            loadNodes();
            loadState();  // 刷新状态
        } else {
            showNotification('切换失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('切换节点失败:', error);
        showNotification('切换节点失败', 'error');
    }
}

// 测试节点延迟
async function testNode(nodeName) {
    showNotification('正在测试延迟...', 'info');

    try {
        const response = await fetch('/api/nodes/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ node_name: nodeName })
        });

        const result = await response.json();

        if (result.success) {
            showNotification(`节点 ${nodeName} 延迟: ${result.delay}ms`, 'success');
        } else {
            showNotification('测试失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('测试节点失败:', error);
        showNotification('测试节点失败', 'error');
    }
}

// 加载黑名单
async function loadBlacklist() {
    try {
        const response = await fetch('/api/blacklist');
        const data = await response.json();

        if (data.success) {
            displayBlacklist(data.blacklist);
        }
    } catch (error) {
        console.error('加载黑名单失败:', error);
    }
}

// 显示黑名单
function displayBlacklist(blacklist) {
    const container = document.getElementById('blacklistList');

    if (!blacklist || blacklist.length === 0) {
        container.innerHTML = '<p class="text-center">黑名单为空</p>';
        return;
    }

    container.innerHTML = blacklist.map((node, index) => `
        <div class="blacklist-item" style="animation-delay: ${index * 0.05}s">
            <div class="node-name">${node}</div>
            <div class="node-actions">
                <button class="btn btn-sm btn-success" onclick="removeBlacklist('${escapeHtml(node)}')">解除</button>
            </div>
        </div>
    `).join('');
}

// 添加黑名单
async function addBlacklist(nodeName) {
    if (!confirm(`确定要将节点 "${nodeName}" 加入黑名单吗?`)) {
        return;
    }

    try {
        const response = await fetch('/api/blacklist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ node_name: nodeName })
        });

        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
            loadBlacklist();
            loadNodes();
        } else {
            showNotification('添加失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('添加黑名单失败:', error);
        showNotification('添加黑名单失败', 'error');
    }
}

// 移除黑名单
async function removeBlacklist(nodeName) {
    try {
        const response = await fetch('/api/blacklist', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ node_name: nodeName })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('已从黑名单移除', 'success');
            loadBlacklist();
            loadNodes();
        } else {
            showNotification('移除失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('移除黑名单失败:', error);
        showNotification('移除黑名单失败', 'error');
    }
}

// 加载区域列表
async function loadRegions() {
    try {
        const response = await fetch('/api/regions');
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('regionFilter');
            select.innerHTML = '<option value="">所有区域</option>' +
                data.regions.map(region => `<option value="${region}">${region}</option>`).join('');
        }
    } catch (error) {
        console.error('加载区域列表失败:', error);
    }
}

// 启动延迟检测
async function startChecker() {
    try {
        const response = await fetch('/api/checker/start', {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
        } else {
            showNotification('启动失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('启动延迟检测失败:', error);
        showNotification('启动延迟检测失败', 'error');
    }
}

// 停止延迟检测
async function stopChecker() {
    try {
        const response = await fetch('/api/checker/stop', {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
        } else {
            showNotification('停止失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('停止延迟检测失败:', error);
        showNotification('停止延迟检测失败', 'error');
    }
}

// 立即检测
async function checkNow() {
    try {
        const response = await fetch('/api/checker/check', {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
        } else {
            showNotification('检测失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('执行检测失败:', error);
        showNotification('执行检测失败', 'error');
    }
}

// 更新延迟历史
function updateHistoryList(history) {
    const container = document.getElementById('historyList');

    if (!history || history.length === 0) {
        container.innerHTML = '<p class="text-center">暂无数据</p>';
        return;
    }

    // 按时间倒序排列
    const sortedHistory = [...history].reverse();

    container.innerHTML = sortedHistory.map((record, index) => {
        const delayClass = getDelayClass(record.delay);
        const time = new Date(record.timestamp);
        const timeStr = formatTime(time);

        return `
            <div class="history-item" style="animation-delay: ${index * 0.05}s">
                <div class="history-header">
                    <div class="node-name">${record.node_name}</div>
                    <div class="delay-badge ${delayClass}">
                        <span class="status-dot ${record.delay < 300 ? 'online' : 'offline'}"></span>
                        ${record.delay} ms
                    </div>
                </div>
                <div class="history-time">${timeStr}</div>
            </div>
        `;
    }).join('');
}

// 显示通知
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--bg-card);
        border: 1px solid var(--accent-cyan);
        border-radius: 8px;
        padding: 16px 24px;
        color: var(--text-primary);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9em;
        box-shadow: 0 8px 32px rgba(0, 255, 245, 0.3);
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
        max-width: 300px;
    `;

    // 根据类型设置颜色
    if (type === 'success') {
        notification.style.borderColor = 'var(--accent-green)';
    } else if (type === 'error') {
        notification.style.borderColor = 'var(--accent-pink)';
    }

    notification.textContent = message;
    document.body.appendChild(notification);

    // 3秒后自动消失
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// 添加通知动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);
