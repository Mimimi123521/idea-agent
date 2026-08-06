import os
import json
import sys
import traceback
from flask import Flask, request, jsonify, render_template, send_from_directory
from database import init_db, add_idea, update_idea, get_idea, list_ideas, delete_idea, get_stats
from database import search_ideas, get_today_todos, complete_todo, carry_forward_overdue, get_historical_ideas
from database import add_reminder, get_pending_reminders, get_upcoming_reminders, dismiss_reminder, dismiss_reminders_by_idea, get_reminder_count
from database import add_daily_review, get_daily_review, list_daily_reviews, delete_daily_review
from agent_engine import process_idea
from search_engine import search_web, batch_search
from review_engine import analyze_daily_review

app = Flask(__name__)

# Initialize database on startup
init_db()

# ============ No-Cache Headers ============

@app.after_request
def add_no_cache_headers(response):
    """禁止浏览器缓存 HTML 和 API 响应，确保手机端始终获取最新版本"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ============ API Routes ============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ideas', methods=['GET'])
def api_list_ideas():
    status = request.args.get('status')
    domain = request.args.get('domain')
    decision = request.args.get('decision')
    decision__in = request.args.get('decision__in')
    tag = request.args.get('tag')
    ideas = list_ideas(status=status, domain=domain, decision=decision, decision__in=decision__in, tag=tag)
    return jsonify({'ideas': ideas, 'stats': get_stats()})

@app.route('/api/ideas/<int:idea_id>', methods=['GET'])
def api_get_idea(idea_id):
    idea = get_idea(idea_id)
    if not idea:
        return jsonify({'error': 'not found'}), 404
    return jsonify(idea)

@app.route('/api/ideas', methods=['POST'])
def api_create_idea():
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': '内容不能为空'}), 400
    idea_id = add_idea(content)
    analysis = process_idea(content)
    update_idea(idea_id, **analysis)
    idea = get_idea(idea_id)
    return jsonify(idea), 201

@app.route('/api/ideas/<int:idea_id>', methods=['PUT'])
def api_update_idea(idea_id):
    data = request.get_json()
    update_idea(idea_id, **data)
    idea = get_idea(idea_id)
    return jsonify(idea)

@app.route('/api/ideas/<int:idea_id>', methods=['DELETE'])
def api_delete_idea(idea_id):
    delete_idea(idea_id)
    return jsonify({'ok': True})

@app.route('/api/ideas/<int:idea_id>/analyze', methods=['POST'])
def api_analyze_idea(idea_id):
    """重新分析灵感"""
    idea = get_idea(idea_id)
    if not idea:
        return jsonify({'error': 'not found'}), 404
    analysis = process_idea(idea['content'])
    update_idea(idea_id, **analysis)
    return jsonify(get_idea(idea_id))

@app.route('/api/ideas/<int:idea_id>/search', methods=['POST'])
def api_search_idea(idea_id):
    """为灵感搜索背景信息"""
    idea = get_idea(idea_id)
    if not idea:
        return jsonify({'error': 'not found'}), 404
    keywords = idea['content'][:50]
    results = search_web(keywords, max_results=5)
    update_idea(idea_id, search_results=json.dumps(results, ensure_ascii=False))
    return jsonify({'results': results, 'idea_id': idea_id})

@app.route('/api/version', methods=['GET'])
def api_version():
    info = {
        'version': '3.0.1',
        'search_engine': 'anysearch_http_api',
        'python': sys.version,
    }
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(__file__)
        )
        if result.returncode == 0:
            info['commit'] = result.stdout.strip()
    except Exception:
        pass
    return jsonify(info)

@app.route('/api/search', methods=['POST'])
def api_search():
    """外部搜索"""
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': '搜索词不能为空'}), 400
    try:
        results = search_web(query, max_results=5)
        return jsonify({'results': results, 'query': query})
    except Exception as e:
        return jsonify({'results': [], 'error': str(e), 'query': query})

# ============ Global Search (Local) ============

@app.route('/api/ideas/search', methods=['GET'])
def api_search_ideas():
    """全局搜索本地灵感：按关键词或日期"""
    keyword = request.args.get('keyword', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    if not keyword and not date_from and not date_to:
        return jsonify({'results': [], 'message': '请输入关键词或日期'})
    results = search_ideas(keyword=keyword or None, date_from=date_from or None, date_to=date_to or None)
    return jsonify({'results': results, 'count': len(results)})

# ============ Today's Todos ============

@app.route('/api/todos', methods=['GET'])
def api_get_todos():
    """获取今日待办列表"""
    carry_forward_overdue()  # 先顺延过期待办
    todos = get_today_todos()
    return jsonify({'todos': todos, 'count': len(todos)})

@app.route('/api/todos/<int:idea_id>/complete', methods=['POST'])
def api_complete_todo(idea_id):
    """标记待办为已完成"""
    complete_todo(idea_id)
    return jsonify({'ok': True})

# ============ Historical Memories ============

@app.route('/api/memories', methods=['GET'])
def api_memories():
    """获取上个月今日和去年今日的灵感"""
    memories = get_historical_ideas()
    return jsonify(memories)

@app.route('/api/batch-search', methods=['POST'])
def api_batch_search():
    data = request.get_json()
    queries = data.get('queries', [])
    if not queries:
        return jsonify({'error': '搜索词列表不能为空'}), 400
    results = batch_search(queries)
    return jsonify({'results': results})

@app.route('/api/stats', methods=['GET'])
def api_stats():
    return jsonify(get_stats())

# ============ Reminder Routes ============

@app.route('/api/ideas/<int:idea_id>/reminder', methods=['POST'])
def api_set_reminder(idea_id):
    idea = get_idea(idea_id)
    if not idea:
        return jsonify({'error': 'not found'}), 404
    data = request.get_json()
    remind_at = data.get('remind_at', '').strip()
    if not remind_at:
        return jsonify({'error': '提醒时间不能为空'}), 400
    title = data.get('title', '') or idea['content'][:30]
    message = data.get('message', '') or idea['content']
    reminder_id = add_reminder(idea_id, remind_at, title, message)
    return jsonify({'id': reminder_id, 'ok': True}), 201

@app.route('/api/reminders/pending', methods=['GET'])
def api_pending_reminders():
    reminders = get_pending_reminders()
    return jsonify({'reminders': reminders, 'count': len(reminders)})

@app.route('/api/reminders/upcoming', methods=['GET'])
def api_upcoming_reminders():
    reminders = get_upcoming_reminders()
    return jsonify({'reminders': reminders})

@app.route('/api/reminders/count', methods=['GET'])
def api_reminder_count():
    return jsonify({'count': get_reminder_count()})

@app.route('/api/reminders/<int:reminder_id>/dismiss', methods=['POST'])
def api_dismiss_reminder(reminder_id):
    dismiss_reminder(reminder_id)
    return jsonify({'ok': True})

@app.route('/api/ideas/<int:idea_id>/reminders/dismiss', methods=['POST'])
def api_dismiss_idea_reminders(idea_id):
    dismiss_reminders_by_idea(idea_id)
    return jsonify({'ok': True})

# ============ Daily Review Routes ============

@app.route('/api/reviews', methods=['POST'])
def api_create_review():
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': '内容不能为空'}), 400
    analysis = analyze_daily_review(content)
    review_id = add_daily_review(
        content=content,
        progress=analysis.get('progress', ''),
        optimization=analysis.get('optimization', ''),
        raw_response=analysis.get('raw_response', '')
    )
    review = get_daily_review(review_id)
    review['model'] = analysis.get('model', 'unknown')
    return jsonify(review), 201

@app.route('/api/reviews', methods=['GET'])
def api_list_reviews():
    reviews = list_daily_reviews()
    return jsonify({'reviews': reviews})

@app.route('/api/reviews/<int:review_id>', methods=['GET'])
def api_get_review(review_id):
    review = get_daily_review(review_id)
    if not review:
        return jsonify({'error': 'not found'}), 404
    return jsonify(review)

@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
def api_delete_review(review_id):
    delete_daily_review(review_id)
    return jsonify({'ok': True})

# ============ PWA Support ============

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ============ Main ============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)