import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ideas.db')

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            content TEXT NOT NULL,
            domain TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            feasibility INTEGER DEFAULT 0,
            priority INTEGER DEFAULT 0,
            urgency INTEGER DEFAULT 0,
            risk INTEGER DEFAULT 0,
            decision TEXT DEFAULT '',
            suggestion TEXT DEFAULT '',
            search_results TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER NOT NULL,
            remind_at TEXT NOT NULL,
            title TEXT DEFAULT '',
            message TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (idea_id) REFERENCES ideas(id)
        );

        CREATE TABLE IF NOT EXISTS daily_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            content TEXT NOT NULL,
            progress TEXT DEFAULT '',
            optimization TEXT DEFAULT '',
            raw_response TEXT DEFAULT ''
        );
    """)
    conn.commit()
    conn.close()

def add_idea(content):
    conn = get_db()
    cur = conn.execute("INSERT INTO ideas (content) VALUES (?)", (content,))
    idea_id = cur.lastrowid
    conn.commit()
    conn.close()
    return idea_id

def update_idea(idea_id, **kwargs):
    allowed = ['domain','tags','feasibility','priority','urgency','risk',
               'decision','suggestion','search_results','status','content']
    fields = {k:v for k,v in kwargs.items() if k in allowed}
    if not fields:
        return
    fields['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    set_clause = ', '.join(f"{k}=?" for k in fields)
    values = list(fields.values())
    values.append(idea_id)
    conn = get_db()
    conn.execute(f"UPDATE ideas SET {set_clause} WHERE id=?", values)
    conn.commit()
    conn.close()

def get_idea(idea_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM ideas WHERE id=?", (idea_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def list_ideas(status=None, domain=None, decision=None, decision__in=None, tag=None):
    conn = get_db()
    query = "SELECT * FROM ideas WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if domain:
        query += " AND domain=?"
        params.append(domain)
    if decision:
        query += " AND decision=?"
        params.append(decision)
    if decision__in:
        decisions = [d.strip() for d in decision__in.split(',') if d.strip()]
        if decisions:
            placeholders = ','.join(['?'] * len(decisions))
            query += f" AND decision IN ({placeholders})"
            params.extend(decisions)
    if tag:
        query += " AND tags LIKE ?"
        params.append(f'%{tag}%')
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_idea(idea_id):
    conn = get_db()
    conn.execute("DELETE FROM ideas WHERE id=?", (idea_id,))
    conn.commit()
    conn.close()

def get_stats():
    conn = get_db()
    rows = conn.execute("SELECT domain, decision, COUNT(*) as cnt FROM ideas WHERE status='active' GROUP BY domain, decision").fetchall()
    conn.close()
    stats = {'work':0, 'life':0, 'process':0, 'other':0,
             'todo_work':0, 'todo_life':0, 'stash':0, 'archive':0, 'total':0}
    for r in rows:
        d = dict(r)
        dom = d['domain']
        dec = d['decision']
        cnt = d['cnt']
        stats['total'] += cnt
        if dom == 'work':
            stats['work'] += cnt
        elif dom == 'life':
            stats['life'] += cnt
        elif dom in ('process', 'procedure', 'regulation', 'doc'):
            stats['process'] += cnt
        else:
            stats['other'] += cnt
        if dec == 'todo-work':
            stats['todo_work'] += cnt
        elif dec == 'todo-life':
            stats['todo_life'] += cnt
        elif dec == 'stash':
            stats['stash'] += cnt
        elif dec == 'archive':
            stats['archive'] += cnt
    return stats

# ============ Global Search ============

def search_ideas(keyword=None, date_from=None, date_to=None, limit=50):
    """全局搜索灵感：按关键词或日期范围"""
    conn = get_db()
    query = "SELECT * FROM ideas WHERE 1=1"
    params = []
    if keyword:
        query += " AND content LIKE ?"
        params.append(f'%{keyword}%')
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        params.append(date_to + ' 23:59:59')
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ============ Today's Todos ============

def get_today_todos():
    """获取今日待办：待办决策 + 提醒时间在今天或已过期，按提醒时间排序"""
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today = datetime.now().strftime('%Y-%m-%d')
    rows = conn.execute(
        "SELECT i.*, r.remind_at, r.id as reminder_id FROM ideas i "
        "LEFT JOIN reminders r ON i.id = r.idea_id AND r.status = 'pending' "
        "WHERE i.status = 'active' "
        "AND (i.decision = 'todo-work' OR i.decision = 'todo-life') "
        "ORDER BY CASE WHEN r.remind_at IS NULL THEN 1 ELSE 0 END, r.remind_at ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def complete_todo(idea_id):
    """标记待办为已完成"""
    conn = get_db()
    conn.execute("UPDATE ideas SET status='completed', updated_at=datetime('now','localtime') WHERE id=?", (idea_id,))
    # 同时关闭关联提醒
    conn.execute("UPDATE reminders SET status='dismissed' WHERE idea_id=? AND status='pending'", (idea_id,))
    conn.commit()
    conn.close()

def carry_forward_overdue():
    """将过期未完成的待办提醒自动顺延到今天"""
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today = datetime.now().strftime('%Y-%m-%d')
    # 找到所有过期且未完成的待办提醒
    rows = conn.execute(
        "SELECT r.id, r.remind_at FROM reminders r "
        "JOIN ideas i ON r.idea_id = i.id "
        "WHERE r.status = 'pending' AND i.status = 'active' "
        "AND r.remind_at < datetime('now','localtime')"
    ).fetchall()
    for row in rows:
        r = dict(row)
        # 顺延到明天，避免逾期通知一直触发
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        old_time = r['remind_at'].split(' ')[-1] if ' ' in r['remind_at'] else '09:00:00'
        new_remind = f"{tomorrow} {old_time}"
        conn.execute("UPDATE reminders SET remind_at = ? WHERE id = ?", (new_remind, r['id']))
    conn.commit()
    conn.close()

# ============ Historical Memories ============

def get_historical_ideas():
    """获取上个月今日和去年今日的灵感"""
    conn = get_db()
    today = datetime.now()
    results = {'last_month': [], 'last_year': []}

    # 上个月今日
    last_month = today.replace(day=1) - timedelta(days=1)
    last_month_day = last_month.replace(day=min(today.day, last_month.day))
    if last_month_day.month == last_month.month:
        date_str = last_month_day.strftime('%Y-%m-%d')
        rows = conn.execute(
            "SELECT * FROM ideas WHERE created_at >= ? AND created_at < ? ORDER BY created_at DESC",
            (date_str + ' 00:00:00', date_str + ' 23:59:59')
        ).fetchall()
        results['last_month'] = [dict(r) for r in rows]

    # 去年今日
    last_year_day = today.replace(year=today.year - 1)
    date_str = last_year_day.strftime('%Y-%m-%d')
    rows = conn.execute(
        "SELECT * FROM ideas WHERE created_at >= ? AND created_at < ? ORDER BY created_at DESC",
        (date_str + ' 00:00:00', date_str + ' 23:59:59')
    ).fetchall()
    results['last_year'] = [dict(r) for r in rows]

    conn.close()
    return results

# ============ Reminders ============

def add_reminder(idea_id, remind_at, title='', message=''):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO reminders (idea_id, remind_at, title, message) VALUES (?, ?, ?, ?)",
        (idea_id, remind_at, title, message)
    )
    reminder_id = cur.lastrowid
    conn.commit()
    conn.close()
    return reminder_id

def get_pending_reminders():
    conn = get_db()
    rows = conn.execute(
        "SELECT r.*, i.content as idea_content, i.decision FROM reminders r "
        "LEFT JOIN ideas i ON r.idea_id = i.id "
        "WHERE r.status='pending' AND r.remind_at <= datetime('now','localtime') "
        "ORDER BY r.remind_at ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_upcoming_reminders():
    conn = get_db()
    rows = conn.execute(
        "SELECT r.*, i.content as idea_content, i.decision FROM reminders r "
        "LEFT JOIN ideas i ON r.idea_id = i.id "
        "WHERE r.status='pending' "
        "ORDER BY r.remind_at ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def dismiss_reminder(reminder_id):
    conn = get_db()
    conn.execute("UPDATE reminders SET status='dismissed' WHERE id=?", (reminder_id,))
    conn.commit()
    conn.close()

def dismiss_reminders_by_idea(idea_id):
    conn = get_db()
    conn.execute("UPDATE reminders SET status='dismissed' WHERE idea_id=? AND status='pending'", (idea_id,))
    conn.commit()
    conn.close()

def get_reminder_count():
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM reminders WHERE status='pending' AND remind_at <= datetime('now','localtime')"
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0

# ============ Daily Reviews ============

def add_daily_review(content, progress='', optimization='', raw_response=''):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO daily_reviews (content, progress, optimization, raw_response) VALUES (?, ?, ?, ?)",
        (content, progress, optimization, raw_response)
    )
    review_id = cur.lastrowid
    conn.commit()
    conn.close()
    return review_id

def get_daily_review(review_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM daily_reviews WHERE id=?", (review_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def list_daily_reviews(limit=30):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM daily_reviews ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_daily_review(review_id):
    conn = get_db()
    conn.execute("DELETE FROM daily_reviews WHERE id=?", (review_id,))
    conn.commit()
    conn.close()