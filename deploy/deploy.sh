#!/bin/bash
# ============================================================
# 灵感管家 (idea-agent) 一键部署脚本 — 阿里云轻量服务器
# 支持系统: Ubuntu 20.04/22.04/24.04, Debian 10+, CentOS 7/8/9, Alibaba Cloud Linux
# 用法: sudo bash deploy.sh
# ============================================================
set -e

# ---------- 颜色输出 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------- 配置（可修改） ----------
APP_DIR="/opt/idea-agent"              # 应用安装目录
DATA_DIR="${APP_DIR}/data"             # SQLite 数据目录（持久化）
APP_PORT="5000"                        # 应用监听端口（内部）
COMPILE_PY="${PYTHON_VERSION:-3.10}"   # 若需编译 Python 时的版本

# ============================================================
# 0. 检测系统类型
# ============================================================
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="$ID"
        OS_VERSION_ID="$VERSION_ID"
    else
        error "无法识别操作系统，请手动安装后在 /opt 下手动部署。"
    fi
    info "检测到系统: ${OS_ID} ${OS_VERSION_ID}"
}

# ---------- 安装通用依赖 ----------
install_basic() {
    info "安装基础工具链..."
    if command -v apt-get >/dev/null 2>&1; then
        DEBIAN_FRONTEND=noninteractive apt-get update -y
        DEBIAN_FRONTEND=noninteractive apt-get install -y curl git wget unzip \
            python3 python3-pip python3-venv build-essential libssl-dev libffi-dev 2>/dev/null || true
        # 安装 nginx（若已装则跳过）
        command -v nginx >/dev/null 2>&1 || {
            DEBIAN_FRONTEND=noninteractive apt-get install -y nginx 2>/dev/null || warn "nginx 安装失败（可后续手动装）"
        }
    elif command -v yum >/dev/null 2>&1; then
        yum install -y curl git wget unzip python3 python3-pip nginx \
            gcc gcc-c++ make openssl-devel libffi-devel 2>/dev/null || true
    else
        error "不支持的包管理器（无 apt-get/yum）"
    fi
    info "基础依赖安装完成。"
}

# ---------- 3. 配置 DeepSeek API Key ----------
configure_env() {
    ENV_FILE="${APP_DIR}/.env"
    # 尝试从已存在的 .env 读取已有 Key（多次运行不覆盖）
    if [ -f "$ENV_FILE" ] && grep -q "DEEPSEEK_API_KEY=.\+" "$ENV_FILE" 2>/dev/null; then
        info "检测到已存在 DEEPSEEK_API_KEY，跳过输入。"
        return
    fi
    echo ""
    echo "============================================================"
    echo "  需要配置 DeepSeek API Key（用于每日复盘 AI 分析）"
    echo "  说明：系统会优先使用你的 Key 调用 DeepSeek 大模型。"
    echo "  若留空则使用本地降级分析（功能仍可用，但无 AI 分析）。"
    echo "============================================================"
    read -p "请输入 DeepSeek API Key (按回车跳过): " DEEPSEEK_KEY
    echo ""
    cat > "$ENV_FILE" <<EOF
# 灵感管家环境变量
DEEPSEEK_API_KEY=${DEEPSEEK_KEY}
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
APP_PORT=${APP_PORT}
DATA_DIR=${DATA_DIR}
EOF
    chmod 600 "$ENV_FILE"
    info "环境变量已写入 ${ENV_FILE}"
}

# ---------- 4. 创建系统服务 ----------
create_service() {
    info "创建 systemd 服务..."
    cat > /etc/systemd/system/idea-agent.service <<EOF
[Unit]
Description=Idea Agent - Flask Personal Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=/usr/bin/env python3 ${APP_DIR}/venv/bin/gunicorn --bind 0.0.0.0:${APP_PORT} --workers 1 --timeout 120 --access-logfile - --error-logfile - app:app
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable idea-agent.service 2>/dev/null || true
    info "systemd 服务已创建并设为开机自启。"
}

# ---------- 5. 配置 Nginx ----------
configure_nginx() {
    if ! command -v nginx >/dev/null 2>&1; then
        warn "未检测到 nginx，跳过反向代理配置（可直接访问 http://公网IP:5000）。"
        return
    fi
    cat > /etc/nginx/sites-available/idea-agent <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    # 兼容不同发行版的分支配置目录
    if [ -d /etc/nginx/sites-enabled ]; then
        ln -sf /etc/nginx/sites-available/idea-agent /etc/nginx/sites-enabled/idea-agent
        rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    else
        # CentOS/RHEL 风格：写入 conf.d
        cat > /etc/nginx/conf.d/idea-agent.conf <<EOF
server {
    listen 80;
    server_name _;
    client_max_body_size 10m;
    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    fi
    nginx -t 2>/dev/null && { systemctl restart nginx 2>/dev/null || service nginx restart 2>/dev/null; info "Nginx 已配置并重启。"; } \
        || warn "Nginx 配置校验失败，请手动检查 /etc/nginx/ 配置。"
}

# ---------- 6. 系统防火墙开放端口 ----------
open_ports() {
    info "开放 80/5000 端口（防火墙/安全组）..."
    # 使用 firewalld
    if command -v firewall-cmd >/dev/null 2>&1; then
        firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=${APP_PORT}/tcp 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
    fi
    # 使用 ufw (Debian/Ubuntu)
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 80/tcp 2>/dev/null || true
        ufw allow ${APP_PORT}/tcp 2>/dev/null || true
    fi
    info "防火墙端口配置完成。（阿里云控制台安全组也需放行 80 端口！）"
}

# ---------- 主流程 ----------
main() {
    if [ "$(id -u)" != "0" ]; then
        error "请使用 root 运行: sudo bash deploy.sh"
    fi
    detect_os

    info "=========== 步骤 1/6: 安装基础依赖 ==========="
    install_basic

    info "=========== 步骤 2/6: 部署应用代码 ==========="
    mkdir -p "$APP_DIR"
    # 若 deploy.sh 与项目同目录，直接拷贝；否则提示手动放置
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    if [ -f "$SCRIPT_DIR/app.py" ]; then
        info "从本地目录同步代码到 ${APP_DIR}..."
        # 拷贝整个项目（排除 deploy 自身和备份目录）
        rsync -a --exclude='deploy' --exclude='data' "$SCRIPT_DIR/" "$APP_DIR/" 2>/dev/null || \
            cp -r "$SCRIPT_DIR"/. "$APP_DIR/"
    else
        warn "未检测到项目文件，跳过代码拷贝（请手动将项目放到 ${APP_DIR}）。"
    fi
    mkdir -p "$DATA_DIR"
    chmod -R 755 "$APP_DIR"

    info "=========== 步骤 3/6: 配置环境变量 ==========="
    configure_env

    info "=========== 步骤 4/6: 创建虚拟环境并安装依赖 ==========="
    python3 -m venv "$APP_DIR/venv" 2>/dev/null || error "无法创建 Python 虚拟环境，请确认已安装 python3-venv"
    "$APP_DIR/venv/bin/pip" install --upgrade pip -q
    "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q
    info "依赖安装完成。"

    info "=========== 步骤 5/6: 创建并启动系统服务 ==========="
    create_service
    systemctl restart idea-agent.service || warn "服务启动失败，请检查日志: journalctl -u idea-agent -f"

    info "=========== 步骤 6/6: 配置 Nginx 反向代理 ==========="
    configure_nginx
    open_ports

    echo ""
    echo "============================================================"
    echo "  部署完成！"
    echo "  服务状态: $(systemctl is-active idea-agent.service)"
    echo "  访问地址: http://<你的公网IP>   (Nginx 已配置则走 80 端口)"
    echo "  若未配 Nginx，可访问: http://<公网IP>:${APP_PORT}"
    echo ""
    echo "  注意: 请到阿里云控制台【轻量应用服务器】→【防火墙】"
    echo "        放行 80 端口（TCP 入方向）"
    echo ""
    echo "  常用命令:"
    echo "    查看日志  : journalctl -u idea-agent -f"
    echo "    重启服务  : systemctl restart idea-agent"
    echo "    停止服务  : systemctl stop idea-agent"
    echo "============================================================"
}

main "$@"