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
2. Python 3.8+ 或 Docker

---

### 方式一：Docker 部署（推荐）

#### 1. 使用 Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone git@github.com:yi5an/clash-auto-cute.git
cd clash-auto-cute

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 Clash API 地址和密钥
# 注意：Docker 环境下，CLASH_API_URL 需要使用 host.docker.internal 访问宿主机

# 3. 启动服务
docker compose up -d

# 4. 查看日志
docker compose logs -f

# 5. 停止服务
docker compose down
```

#### 2. 使用部署脚本（更便捷）

```bash
# 构建镜像
./docker-deploy.sh build

# 启动服务
./docker-deploy.sh up

# 查看状态
./docker-deploy.sh status

# 查看日志
./docker-deploy.sh logs

# 停止服务
./docker-deploy.sh down

# 重启服务
./docker-deploy.sh restart

# 进入容器
./docker-deploy.sh exec

# 清理容器和镜像
./docker-deploy.sh clean
```

#### Docker 配置说明

在 `.env` 文件中配置：

```bash
# Clash API 配置
# 使用 host 网络模式（默认，仅 Linux）
CLASH_API_URL=http://127.0.0.1:9097
CLASH_SECRET=your-secret
PROXY_GROUP=PROXY

# 服务配置
FLASK_PORT=5000
FLASK_HOST=0.0.0.0

# 延迟检测配置
DELAY_THRESHOLD=200
CHECK_INTERVAL=30
LOCKED_REGION=
```

**⚠️ 重要提示**:
- 默认使用 **host 网络模式**（仅 Linux 支持）
- Mac/Windows 用户需要修改 `docker-compose.yml`，详见 [DOCKER.md](DOCKER.md)

访问 Web 界面：`http://localhost:5000`

---

### 方式二：本地安装

#### 安装步骤

```bash
# 1. 克隆或下载项目
cd clash-auto-switch

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 Clash API 地址
cp .env.example .env
# 编辑 .env 文件，配置 Clash API 地址和密钥

# 5. 测试连接
python test.py

# 6. 启动服务
python app.py
```

#### 访问 Web 界面

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
├── Dockerfile             # Docker 镜像构建文件
├── docker-compose.yml     # Docker Compose 配置
├── docker-deploy.sh       # Docker 部署脚本
├── requirements.txt       # 依赖列表
├── start.sh               # 启动脚本
├── test.py                # 测试脚本
├── .env.example           # 环境变量示例
└── README.md              # 使用说明
```

## 注意事项

- 配置为纯内存存储，重启后恢复默认设置
- 确保 Clash 的 RESTful API 已开启并可访问
- 建议根据实际网络情况调整延迟阈值和检测间隔

### Docker 环境注意事项

1. **网络模式**

   - 默认使用 **host 网络模式**（仅 Linux）
   - 容器直接使用宿主机网络，可访问 `127.0.0.1:9097`
   - Mac/Windows 用户需要修改配置使用 `host.docker.internal`

2. **数据持久化**

   - 当前配置为纯内存存储，容器重启后配置会丢失
   - 可通过挂载卷实现配置持久化（需修改代码）

3. **日志管理**

   - 容器日志使用 `docker compose logs` 查看
   - 可在 docker-compose.yml 中配置日志卷挂载

## 故障排查

### Docker 环境

**容器无法连接到 Clash API**

- 检查 `.env` 中的 `CLASH_API_URL` 是否正确
- Linux（host 模式）: 使用 `http://127.0.0.1:9097`
- Mac/Windows: 使用 `http://host.docker.internal:9097`
- 确保 Clash 正在运行且 API 已启用

**容器启动失败**

- 查看日志: `docker compose logs`
- 检查端口 5000 是否被占用: `docker compose ps`
- 重新构建镜像: `./docker-deploy.sh build --no-cache`

### 本地环境

**无法连接到 Clash API**

- 检查 Clash 是否正在运行
- 检查 API 地址和密钥是否正确
- 运行 `python test.py` 进行诊断

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
