import sqlite3
import os
import json
from datetime import datetime

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

def list_ideas(status=None, domain=None, decision=None, tag=None):
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