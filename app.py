import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from database import init_db, add_idea, update_idea, get_idea, list_ideas, delete_idea, get_stats
from agent_engine import process_idea
from search_engine import search_web, batch_search

app = Flask(__name__)

# Initialize database on startup
init_db()

# ============ API Routes ============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ideas', methods=['GET'])
def api_list_ideas():
    status = request.args.get('status')
    domain = request.args.get('domain')
    decision = request.args.get('decision')
    tag = request.args.get('tag')
    ideas = list_ideas(status=status, domain=domain, decision=decision, tag=tag)
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
    # 1. Save to database
    idea_id = add_idea(content)
    # 2. Run agent analysis
    analysis = process_idea(content)
    update_idea(idea_id, **analysis)
    # 3. Return result
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
    content = idea['content']
    # 构造搜索词
    keywords = content[:50]
    results = search_web(keywords, max_results=5)
    update_idea(idea_id, search_results=json.dumps(results, ensure_ascii=False))
    return jsonify({'results': results, 'idea_id': idea_id})

@app.route('/api/search', methods=['POST'])
def api_search():
    """通用搜索"""
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': '搜索词不能为空'}), 400
    results = search_web(query, max_results=5)
    return jsonify({'results': results})

@app.route('/api/batch-search', methods=['POST'])
def api_batch_search():
    """批量搜索"""
    data = request.get_json()
    queries = data.get('queries', [])
    if not queries:
        return jsonify({'error': '搜索词列表不能为空'}), 400
    results = batch_search(queries)
    return jsonify({'results': results})

@app.route('/api/stats', methods=['GET'])
def api_stats():
    return jsonify(get_stats())

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