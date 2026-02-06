# Docker 部署指南

本文档详细介绍如何使用 Docker 部署 Clash Auto Switch 服务。

## 目录

- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [部署脚本使用](#部署脚本使用)
- [Docker Compose 配置](#docker-compose-配置)
- [常见问题](#常见问题)
- [生产环境部署](#生产环境部署)

---

## 快速开始

### 1. 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 2. 一键部署

```bash
# 克隆项目
git clone git@github.com:yi5an/clash-auto-cute.git
cd clash-auto-switch

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f
```

访问: `http://localhost:5000`

---

## 配置说明

### 环境变量配置

在 `.env` 文件中配置以下变量：

```bash
# Clash API 配置
# 使用 host 网络模式（仅 Linux）
CLASH_API_URL=http://127.0.0.1:9097

CLASH_SECRET=your-secret-key
PROXY_GROUP=PROXY

# 服务配置
FLASK_PORT=5000
FLASK_HOST=0.0.0.0
FLASK_DEBUG=False

# 延迟检测配置
DELAY_THRESHOLD=200          # 延迟阈值（毫秒）
CHECK_INTERVAL=30            # 检测间隔（秒）
LOCKED_REGION=               # 锁定区域
TEST_TIMEOUT=5000            # 测试超时（毫秒）
TEST_URL=http://www.gstatic.com/generate_204
```

### 网络模式说明

#### Host 网络模式（推荐，仅 Linux）

项目默认使用 **host 网络模式**，容器直接使用宿主机网络栈：

```yaml
network_mode: host
```

**优点**:
- ✅ 直接访问宿主机 Clash API (`127.0.0.1:9097`)
- ✅ 无需额外网络配置
- ✅ 性能更好，无网络转发开销

**限制**:
- ⚠️ 仅支持 Linux 系统
- ⚠️ Mac/Windows Docker Desktop 不支持

#### Mac/Windows 用户

如果使用 Mac/Windows，需要修改 `docker-compose.yml`：

```yaml
# 移除 network_mode: host
# 添加端口映射
ports:
  - "5000:5000"

# 修改环境变量
environment:
  - CLASH_API_URL=http://host.docker.internal:9097
```

并使用 `host.docker.internal` 访问宿主机：

```bash
CLASH_API_URL=http://host.docker.internal:9097
```

#### Linux Docker (非 host 模式)

如果不想使用 host 模式，可以使用宿主机 IP：

```bash
# 获取宿主机 IP
ip addr show | grep inet

# 配置 API 地址
CLASH_API_URL=http://192.168.1.100:9097
```

或使用 host 网络模式（需修改 docker-compose.yml）：

```yaml
services:
  clash-auto-switch:
    network_mode: host
```

---

## 部署脚本使用

项目提供了便捷的部署脚本 `docker-deploy.sh`。

### 可用命令

```bash
# 显示帮助
./docker-deploy.sh help

# 构建镜像
./docker-deploy.sh build
./docker-deploy.sh build --no-cache  # 不使用缓存

# 启动服务
./docker-deploy.sh up

# 停止服务
./docker-deploy.sh down
./docker-deploy.sh stop

# 重启服务
./docker-deploy.sh restart

# 查看日志
./docker-deploy.sh logs

# 查看状态
./docker-deploy.sh status

# 进入容器
./docker-deploy.sh exec

# 清理容器和镜像
./docker-deploy.sh clean
```

### 使用示例

#### 首次部署

```bash
# 1. 构建镜像
./docker-deploy.sh build

# 2. 启动服务
./docker-deploy.sh up

# 3. 查看状态
./docker-deploy.sh status
```

#### 日常维护

```bash
# 查看实时日志
./docker-deploy.sh logs

# 重启服务
./docker-deploy.sh restart

# 进入容器调试
./docker-deploy.sh exec
```

#### 清理和重新部署

```bash
# 停止服务
./docker-deploy.sh down

# 重新构建（不使用缓存）
./docker-deploy.sh build --no-cache

# 启动服务
./docker-deploy.sh up
```

---

## Docker Compose 配置

### 基本配置

```yaml
version: '3.8'

services:
  clash-auto-switch:
    build: .
    container_name: clash-auto-switch
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - CLASH_API_URL=${CLASH_API_URL}
      - CLASH_SECRET=${CLASH_SECRET}
      # ... 其他环境变量
```

### 高级配置

#### 1. 日志持久化

```yaml
volumes:
  - ./logs:/app/logs

logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

#### 2. 资源限制

```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 256M
```

#### 3. 健康检查

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/api/state"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

---

## 常见问题

### 1. 容器无法连接到 Clash API

**问题**: 日志显示 "无法连接到 Clash API"

**解决方案**:

- Mac/Windows: 使用 `host.docker.internal`
- Linux: 使用宿主机 IP 地址
- 检查 Clash API 是否允许来自容器的连接

### 2. 端口冲突

**问题**: 启动失败，提示端口 5000 已被占用

**解决方案**:

```bash
# 修改 docker-compose.yml 中的端口映射
ports:
  - "5001:5000"  # 使用 5001 端口
```

### 3. 容器频繁重启

**问题**: 容器状态显示 Restarting

**解决方案**:

```bash
# 查看容器日志
docker compose logs -f

# 检查健康配置
docker compose ps
```

### 4. 如何更新到最新版本

```bash
# 停止服务
docker compose down

# 拉取最新代码
git pull

# 重新构建镜像
./docker-deploy.sh build --no-cache

# 启动服务
./docker-deploy.sh up
```

---

## 生产环境部署

### 1. 使用非 root 用户运行

Dockerfile 中已配置非 root 用户：

```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

### 2. 配置反向代理

使用 Nginx 作为反向代理：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. 启用 HTTPS

使用 Let's Encrypt 和 Certbot：

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com
```

### 4. 自动重启配置

在 `docker-compose.yml` 中配置：

```yaml
restart: unless-stopped
```

### 5. 日志管理

配置日志轮转：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 性能优化

### 1. 镜像优化

- 使用更小的基础镜像
- 清理不必要的文件
- 多阶段构建

### 2. 网络优化

- 使用自定义网络
- 配置 DNS

### 3. 资源优化

- 限制容器资源使用
- 配置合适的健康检查间隔

---

## 监控和调试

### 查看容器资源使用

```bash
docker stats clash-auto-switch
```

### 进入容器调试

```bash
docker compose exec clash-auto-switch /bin/bash
```

### 查看容器日志

```bash
docker compose logs -f --tail=100
```

### 实时监控

```bash
# 持续查看容器状态
watch -n 1 'docker compose ps'
```

---

## 备份和恢复

### 备份配置

```bash
# 备份 .env 文件
cp .env .env.backup

# 备份 docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup
```

### 恢复配置

```bash
# 恢复配置
cp .env.backup .env
cp docker-compose.yml.backup docker-compose.yml

# 重启服务
docker compose up -d
```

---

## 安全建议

1. **不要在镜像中包含敏感信息**
   - 使用 `.env` 文件管理密钥
   - 使用 Docker Secrets（Swarm 模式）

2. **限制容器权限**
   - 使用非 root 用户运行
   - 限制容器资源

3. **定期更新镜像**
   - 及时更新基础镜像
   - 更新依赖包

4. **网络安全**
   - 使用防火墙限制访问
   - 配置反向代理和 HTTPS

---

## 参考资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Clash 文档](https://lancellc.gitbook.io/clash/)
