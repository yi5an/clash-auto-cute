// WebSocket 连接
let socket;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initWebSocket();
    loadState();
    loadConfig();
    loadNodes();
    loadBlacklist();
    loadRegions();
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
    }
}

// 更新状态显示
function updateStateDisplay(state) {
    document.getElementById('currentNode').textContent = state.current_node || '-';
    document.getElementById('currentDelay').textContent =
        state.current_delay ? state.current_delay + ' ms' : '-';

    // 运行状态
    const statusBadge = document.getElementById('runningStatus');
    if (state.is_running) {
        statusBadge.innerHTML = '<span class="badge badge-success">运行中</span>';
    } else {
        statusBadge.innerHTML = '<span class="badge badge-warning">未启动</span>';
    }

    document.getElementById('switchCount').textContent = state.switch_count;

    // 上次检测时间
    if (state.last_check_time) {
        const lastCheck = new Date(state.last_check_time);
        document.getElementById('lastCheck').textContent = lastCheck.toLocaleString();
    }

    document.getElementById('availableCount').textContent = state.available_nodes.length;

    // 更新延迟历史
    updateHistoryList(state.delay_history);
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
    }
}

// 更新配置
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
            alert('配置已保存');
            loadNodes();  // 重新加载节点列表
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (error) {
        console.error('更新配置失败:', error);
        alert('更新配置失败');
    }
}

// 加载节点列表
async function loadNodes() {
    try {
        const response = await fetch('/api/nodes');
        const data = await response.json();

        if (data.success) {
            displayNodes(data.all_nodes, data.current_node);
        }
    } catch (error) {
        console.error('加载节点列表失败:', error);
        document.getElementById('nodeList').innerHTML =
            '<p class="text-center">加载失败</p>';
    }
}

// 显示节点列表
function displayNodes(nodes, currentNode) {
    const container = document.getElementById('nodeList');

    if (!nodes || nodes.length === 0) {
        container.innerHTML = '<p class="text-center">暂无可用节点</p>';
        return;
    }

    container.innerHTML = nodes.map(node => `
        <div class="node-item">
            <div>
                <div class="node-name">${node} ${node === currentNode ? '✓' : ''}</div>
            </div>
            <div class="node-actions">
                <button class="btn btn-sm btn-primary" onclick="switchNode('${node}')">切换</button>
                <button class="btn btn-sm btn-info" onclick="testNode('${node}')">测速</button>
                <button class="btn btn-sm btn-danger" onclick="addBlacklist('${node}')">拉黑</button>
            </div>
        </div>
    `).join('');
}

// 切换节点
async function switchNode(nodeName) {
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
            alert(result.message);
            loadNodes();
        } else {
            alert('切换失败: ' + result.error);
        }
    } catch (error) {
        console.error('切换节点失败:', error);
        alert('切换节点失败');
    }
}

// 测试节点延迟
async function testNode(nodeName) {
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
            alert(`节点 ${nodeName} 延迟: ${result.delay} ms`);
        } else {
            alert('测试失败: ' + result.error);
        }
    } catch (error) {
        console.error('测试节点失败:', error);
        alert('测试节点失败');
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

    container.innerHTML = blacklist.map(node => `
        <div class="blacklist-item">
            <div class="node-name">${node}</div>
            <div class="node-actions">
                <button class="btn btn-sm btn-success" onclick="removeBlacklist('${node}')">解除</button>
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
            alert(result.message);
            loadBlacklist();
            loadNodes();
        } else {
            alert('添加失败: ' + result.error);
        }
    } catch (error) {
        console.error('添加黑名单失败:', error);
        alert('添加黑名单失败');
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
            loadBlacklist();
            loadNodes();
        } else {
            alert('移除失败: ' + result.error);
        }
    } catch (error) {
        console.error('移除黑名单失败:', error);
        alert('移除黑名单失败');
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
            alert(result.message);
        } else {
            alert('启动失败: ' + result.error);
        }
    } catch (error) {
        console.error('启动延迟检测失败:', error);
        alert('启动延迟检测失败');
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
            alert(result.message);
        } else {
            alert('停止失败: ' + result.error);
        }
    } catch (error) {
        console.error('停止延迟检测失败:', error);
        alert('停止延迟检测失败');
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
            alert(result.message);
        } else {
            alert('检测失败: ' + result.error);
        }
    } catch (error) {
        console.error('执行检测失败:', error);
        alert('执行检测失败');
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

    container.innerHTML = sortedHistory.map(record => {
        const delayClass = record.delay < 100 ? 'good' :
                          record.delay < 200 ? 'warning' : 'danger';
        const time = new Date(record.timestamp).toLocaleString();

        return `
            <div class="history-item">
                <div>
                    <div class="node-name">${record.node_name}</div>
                    <div class="node-delay ${delayClass}">${record.delay} ms</div>
                </div>
                <div style="color: #999; font-size: 0.9em;">${time}</div>
            </div>
        `;
    }).join('');
}
