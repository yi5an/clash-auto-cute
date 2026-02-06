# 快速开始指南

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 配置 Clash

确保 Clash 的 RESTful API 已启用：

**Clash for Windows**: 默认开启，地址为 `http://127.0.0.1:9090`

**Clash Premium/Meta**: 在配置文件中添加：
```yaml
external-controller: 127.0.0.1:9090
```

## 3. 测试连接

```bash
python3 test.py
```

## 4. 启动服务

**方式一：使用启动脚本（推荐）**
```bash
./start.sh
```

**方式二：直接运行**
```bash
python3 app.py
```

## 5. 访问 Web 界面

在浏览器中打开：http://127.0.0.1:5000

## 功能说明

### 自动切换模式
1. 在 Web 界面中设置延迟阈值（默认 200ms）
2. 点击"启动检测"按钮
3. 系统会自动检测当前节点延迟
4. 超过阈值时自动切换到更好的节点

### 区域锁定
在"参数设置"中输入区域名称（如：香港、日本、新加坡），系统只在该区域内切换节点。

### 黑名单管理
1. 在节点列表中点击"拉黑"按钮将节点加入黑名单
2. 在"黑名单管理"中可以解除黑名单

### 手动控制
- 点击"切换"按钮手动切换节点
- 点击"测速"按钮测试节点延迟
- 点击"立即检测"手动触发一次延迟检测

## 配置参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 延迟阈值 | 超过此值触发切换（毫秒） | 200 |
| 检测间隔 | 每隔多少秒检测一次 | 30 |
| 锁定区域 | 只在指定区域内切换 | 空 |
| 测试URL | 用于测试延迟的地址 | http://www.gstatic.com/generate_204 |

## 注意事项

1. 配置为纯内存存储，重启后恢复默认设置
2. 确保 Clash 的 RESTful API 已开启
3. 建议根据实际网络情况调整延迟阈值
4. 首次使用建议先手动测试节点延迟

## 故障排查

**无法连接到 Clash API**
- 检查 Clash 是否正在运行
- 检查 API 地址是否正确（默认 http://127.0.0.1:9090）
- 检查 Clash 配置中是否启用了 external-controller

**节点列表为空**
- 检查 Clash 订阅是否正常
- 检查 Clash 配置文件中是否有节点

**延迟测试失败**
- 检查网络连接
- 尝试更换测试 URL

## 项目结构

```
clash-auto-switch/
├── app.py              # Flask 主应用
├── config.py           # 配置管理
├── clash_api.py        # Clash API 客户端
├── node_manager.py     # 节点管理器
├── delay_checker.py    # 延迟检测器
├── models.py           # 数据模型
├── static/             # 前端静态文件
├── templates/          # HTML 模板
├── requirements.txt    # 依赖列表
├── start.sh            # 启动脚本
├── test.py             # 测试脚本
└── README.md           # 详细说明
```
