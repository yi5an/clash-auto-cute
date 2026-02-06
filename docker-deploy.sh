#!/bin/bash

# Clash Auto Switch - Docker 部署脚本
# 支持快速部署、管理和维护

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF

Clash Auto Switch - Docker 部署脚本

用法: ./docker-deploy.sh [命令] [选项]

命令:
  build       构建 Docker 镜像
  up          启动服务 (docker-compose)
  down        停止服务
  restart     重启服务
  logs        查看日志
  status      查看服务状态
  exec        进入容器
  clean       清理容器和镜像
  help        显示此帮助信息

选项:
  --no-cache  构建时不使用缓存
  --force     强制执行

示例:
  ./docker-deploy.sh build          # 构建镜像
  ./docker-deploy.sh up             # 启动服务
  ./docker-deploy.sh logs           # 查看日志
  ./docker-deploy.sh exec           # 进入容器
  ./docker-deploy.sh clean          # 清理

EOF
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    print_success "Docker 环境检查通过"
}

# 构建 Docker 镜像
build_image() {
    print_info "构建 Docker 镜像..."

    if [ "$1" = "--no-cache" ]; then
        docker compose build --no-cache
    else
        docker compose build
    fi

    print_success "镜像构建完成"
}

# 启动服务
start_service() {
    print_info "启动服务..."

    # 检查 .env 文件
    if [ ! -f .env ]; then
        print_warning ".env 文件不存在，从 .env.example 复制..."
        if [ -f .env.example ]; then
            cp .env.example .env
            print_info "请编辑 .env 文件配置 Clash API 地址和密钥"
            print_warning "配置完成后重新运行: ./docker-deploy.sh up"
            exit 0
        else
            print_error ".env.example 文件不存在"
            exit 1
        fi
    fi

    docker compose up -d

    print_success "服务启动成功"
    print_info "Web 界面: http://localhost:5000"
    print_info "查看日志: ./docker-deploy.sh logs"
}

# 停止服务
stop_service() {
    print_info "停止服务..."
    docker compose down
    print_success "服务已停止"
}

# 重启服务
restart_service() {
    print_info "重启服务..."
    docker compose restart
    print_success "服务已重启"
}

# 查看日志
view_logs() {
    docker compose logs -f --tail=100
}

# 查看状态
view_status() {
    print_info "容器状态:"
    docker compose ps

    echo ""
    print_info "容器健康状态:"
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
}

# 进入容器
exec_container() {
    print_info "进入容器..."
    docker compose exec clash-auto-switch /bin/bash
}

# 清理
clean_up() {
    print_warning "这将删除所有容器和镜像，确定吗? (y/n)"
    read -r confirm

    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        print_info "停止并删除容器..."
        docker compose down

        print_info "删除镜像..."
        docker rmi clash-auto-switch-clash-auto-switch 2>/dev/null || true

        print_success "清理完成"
    else
        print_info "已取消"
    fi
}

# 主函数
main() {
    case "$1" in
        build)
            check_docker
            build_image "$2"
            ;;
        up)
            check_docker
            start_service
            ;;
        down|stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        logs)
            view_logs
            ;;
        status)
            view_status
            ;;
        exec)
            exec_container
            ;;
        clean)
            clean_up
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

main "$@"
