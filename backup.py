"""
数据库备份模块 — 防止数据丢失
- 启动时自动备份
- 支持手动备份
- 支持导出为 JSON
- 保留最近 24 个备份
"""
import os
import shutil
import json
import sqlite3
import threading
import time
from datetime import datetime

BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'data', 'backups')
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ideas.db')
MAX_BACKUPS = 24
AUTO_BACKUP_INTERVAL = 3600  # 1 小时


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_database():
    """备份当前数据库到备份目录"""
    ensure_backup_dir()
    if not os.path.exists(DB_PATH):
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    try:
        # 先用 WAL checkpoint 确保数据写入主文件
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()

        shutil.copy2(DB_PATH, backup_path)
        cleanup_old_backups()
        return backup_path
    except Exception as e:
        print(f"备份失败: {e}")
        return None


def list_backups():
    """列出所有备份文件"""
    ensure_backup_dir()
    backups = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if f.endswith('.db'):
            path = os.path.join(BACKUP_DIR, f)
            size = os.path.getsize(path)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            backups.append({
                'name': f,
                'size': size,
                'size_human': _format_size(size),
                'created_at': mtime.strftime('%Y-%m-%d %H:%M:%S'),
            })
    return backups


def restore_backup(backup_name):
    """从备份恢复数据库"""
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    if not os.path.exists(backup_path):
        return False

    # 先备份当前数据库（以防万一）
    if os.path.exists(DB_PATH):
        failback = DB_PATH + '.failback'
        shutil.copy2(DB_PATH, failback)
    try:
        shutil.copy2(backup_path, DB_PATH)
        return True
    except Exception:
        return False


def export_json():
    """导出所有数据为 JSON 格式"""
    if not os.path.exists(DB_PATH):
        return {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    ideas = [dict(r) for r in conn.execute("SELECT * FROM ideas ORDER BY created_at DESC").fetchall()]
    reminders = [dict(r) for r in conn.execute("SELECT * FROM reminders ORDER BY created_at DESC").fetchall()]
    reviews = [dict(r) for r in conn.execute("SELECT * FROM daily_reviews ORDER BY created_at DESC").fetchall()]
    conn.close()

    return {
        'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ideas': ideas,
        'reminders': reminders,
        'reviews': reviews,
        'counts': {
            'ideas': len(ideas),
            'reminders': len(reminders),
            'reviews': len(reviews),
        }
    }


def get_db_info():
    """获取数据库状态信息"""
    info = {
        'db_exists': os.path.exists(DB_PATH),
        'backup_count': len(list_backups()),
        'backup_dir': BACKUP_DIR,
        'volume_mounted': os.path.exists(os.path.dirname(DB_PATH)),
    }
    if info['db_exists']:
        info['db_size'] = os.path.getsize(DB_PATH)
        info['db_size_human'] = _format_size(info['db_size'])
        conn = sqlite3.connect(DB_PATH)
        info['idea_count'] = conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
        info['reminder_count'] = conn.execute("SELECT COUNT(*) FROM reminders").fetchone()[0]
        info['review_count'] = conn.execute("SELECT COUNT(*) FROM daily_reviews").fetchone()[0]
        conn.close()
    return info


def cleanup_old_backups():
    """只保留最近 MAX_BACKUPS 个备份"""
    ensure_backup_dir()
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')])
    while len(backups) > MAX_BACKUPS:
        oldest = backups.pop(0)
        try:
            os.remove(os.path.join(BACKUP_DIR, oldest))
        except Exception:
            pass


def _format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ============ 自动备份调度 ============

_auto_backup_thread = None
_auto_backup_running = False


def _auto_backup_loop():
    """后台线程：每小时自动备份一次"""
    global _auto_backup_running
    while _auto_backup_running:
        time.sleep(AUTO_BACKUP_INTERVAL)
        if _auto_backup_running:
            try:
                result = backup_database()
                if result:
                    print(f"[AutoBackup] 备份完成: {result}")
            except Exception as e:
                print(f"[AutoBackup] 备份失败: {e}")


def start_auto_backup():
    """启动自动备份定时任务"""
    global _auto_backup_thread, _auto_backup_running
    if _auto_backup_running:
        return
    _auto_backup_running = True
    _auto_backup_thread = threading.Thread(target=_auto_backup_loop, daemon=True)
    _auto_backup_thread.start()
    print("[AutoBackup] 自动备份已启动，间隔 1 小时")


def startup_backup():
    """启动时执行：备份数据库 + 启动自动备份"""
    ensure_backup_dir()
    if os.path.exists(DB_PATH):
        result = backup_database()
        if result:
            print(f"[StartupBackup] 启动备份完成: {result}")
    start_auto_backup()