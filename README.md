# Clash Auto Switch

Clash VPN 节点自动切换服务 - 根据延迟自动切换节点，支持区域锁定和黑名单管理。

## 功能特性

- ✅ 自动延迟检测与节点切换
- ✅ 区域锁定功能（只切换指定区域的节点）
- ✅ 黑名单管理（手动添加不使用的节点）
- ✅ Web 管理界面（实时监控、手动控制、参数配置）
- ✅ 实时状态监控

## 安装

### 前置要求

1. 已安装 Clash（Clash for Windows / Clash Premium / Clash.Meta）
2. Python 3.8+

### 安装步骤

```bash
# 1. 克隆或下载项目
cd clash-auto-switch

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 Clash API 地址（可选，默认为 http://127.0.0.1:9090）
cp .env.example .env
# 编辑 .env 文件，配置 Clash API 地址和密钥

# 4. 启动服务
python app.py
```

### 访问 Web 界面

启动成功后，在浏览器中访问：
```
http://localhost:5000
```

## 配置说明

### Clash API 设置

确保 Clash 的 RESTful API 已启用：

**Clash for Windows**: 默认开启，地址为 `http://127.0.0.1:9090`

**Clash Premium/Meta**: 在配置文件中添加：
```yaml
external-controller: 127.0.0.1:9090
secret: your-secret  # 可选
```

### Web 界面配置

在 Web 界面中可以配置：
- **延迟阈值**: 超过此值触发切换（毫秒）
- **检测间隔**: 每隔多少秒检测一次延迟
- **锁定区域**: 只在指定区域内切换节点
- **测试超时**: 延迟测试超时时间

## 使用说明

### 自动切换模式

1. 启动服务后，延迟检测器自动运行
2. 每隔设定的检测间隔，测试当前节点延迟
3. 延迟超过阈值时，自动切换到延迟更低且不在黑名单的节点
4. 如果设置了区域锁定，只在指定区域内选择节点

### 手动控制

1. 在 Web 界面的"节点列表"中查看所有可用节点
2. 点击"切换"按钮手动切换到指定节点
3. 在"黑名单管理"中添加/移除黑名单节点

### 区域锁定

1. 在"参数设置"中输入要锁定的区域名称（如：香港、日本、新加坡）
2. 系统只会在该区域的节点中进行切换
3. 清空区域名称则取消锁定

## 项目结构

```
clash-auto-switch/
├── app.py                 # Flask 主应用
├── config.py              # 配置管理
├── clash_api.py           # Clash API 客户端
├── node_manager.py        # 节点管理器
├── delay_checker.py       # 延迟检测器
├── models.py              # 数据模型
├── static/                # 前端静态文件
│   ├── index.html
│   ├── style.css
│   └── app.js
├── templates/             # HTML 模板
├── requirements.txt       # 依赖列表
├── .env.example           # 环境变量示例
└── README.md              # 使用说明
```

## 注意事项

- 配置为纯内存存储，重启后恢复默认设置
- 确保 Clash 的 RESTful API 已开启并可访问
- 建议根据实际网络情况调整延迟阈值和检测间隔

## 许可证

MIT License
