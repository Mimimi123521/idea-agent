#!/bin/bash
# ============================================================
# 灵感管家 数据备份脚本
# 备份 /opt/idea-agent/data 下的 SQLite 数据库到备份目录
# 用法: sudo bash backup-data.sh [backup_dir]
# ============================================================
set -e

APP_DIR="/opt/idea-agent"
DATA_DIR="${APP_DIR}/data"
BACKUP_ROOT="${1:-${APP_DIR}/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
KEEP_DAYS=14   # 保留最近 14 天的备份

if [ ! -d "$DATA_DIR" ]; then
    echo "[ERROR] 未找到数据目录 ${DATA_DIR}"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# 先 checkpoint 确保 WAL 数据落盘
python3 - "$DATA_DIR/ideas.db" "$BACKUP_DIR" <<'PYEOF' 2>/dev/null || true
import sqlite3, sys, os, shutil
db = sys.argv[1]; dest = sys.argv[2]
if os.path.exists(db):
    try:
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
    except Exception as e:
        print("[WARN] checkpoint 失败:", e)
PYEOF

# 备份数据库文件（含 -wal/-shm 如有）
cp -f "${DATA_DIR}"/ideas.db* "$BACKUP_DIR/" 2>/dev/null || true

echo "[INFO] 备份完成: ${BACKUP_DIR}"
ls -lh "$BACKUP_DIR"

# 清理过期备份
echo "[INFO] 清理超过 ${KEEP_DAYS} 天的旧备份..."
find "$BACKUP_ROOT" -maxdepth 1 -type d -name "2*" -mtime +${KEEP_DAYS} -exec rm -rf {} \; 2>/dev/null || true

echo "[DONE] 备份完成，共 $(ls -d ${BACKUP_ROOT}/2* 2>/dev/null | wc -l) 份备份。"

# ============================================================
# 恢复方式（如需恢复，手动执行）:
#   1. 停止服务:   systemctl stop idea-agent
#   2. 覆盖数据:   cp ${BACKUP_DIR}/ideas.db* /opt/idea-agent/data/
#   3. 启动服务:   systemctl start idea-agent
# ============================================================