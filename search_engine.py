import json
import requests

ANYSEARCH_API = "https://api.anysearch.com/mcp"
ANYSEARCH_CLI = "/workspace/.trae/skills/anysearch/scripts/anysearch_cli.py"

def search_web(query, max_results=5):
    """使用 AnySearch API 搜索，优先调用本地 CLI，失败则回退到 HTTP API"""
    try:
        import subprocess
        result = subprocess.run(
            ["python3", ANYSEARCH_CLI, "search", query, "--max_results", str(max_results)],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return _parse_cli_output(result.stdout)
    except Exception:
        pass
    # Fallback to HTTP API
    try:
        resp = requests.post(
            ANYSEARCH_API,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": query, "max_results": max_results}
                },
                "id": 1
            },
            timeout=10
        )
        if resp.ok:
            data = resp.json()
            return _parse_api_response(data)
    except Exception:
        pass
    return []

def batch_search(queries, max_results=3):
    """批量搜索多个关键词"""
    results = {}
    try:
        import subprocess
        q_json = json.dumps([{"query": q, "max_results": max_results} for q in queries])
        result = subprocess.run(
            ["python3", ANYSEARCH_CLI, "batch_search", "--queries", q_json],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return _parse_cli_output(result.stdout)
    except Exception:
        pass
    # Fallback: sequential
    for q in queries:
        results[q] = search_web(q, max_results)
    return results

def extract_page(url):
    """提取网页全文"""
    try:
        import subprocess
        result = subprocess.run(
            ["python3", ANYSEARCH_CLI, "extract", url],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return result.stdout[:3000]
    except Exception:
        pass
    return ""

def _parse_cli_output(text):
    """解析 CLI 输出为结构化结果"""
    results = []
    lines = text.split('\n')
    current = {}
    for line in lines:
        line = line.strip()
        if line.startswith('###'):
            if current.get('title') and current.get('url'):
                results.append(current)
            current = {'title': '', 'url': '', 'snippet': ''}
        elif line.startswith('- **URL**'):
            current['url'] = line.replace('- **URL**:', '').strip()
        elif line.startswith('- by') or line.startswith('by'):
            if current:
                current['snippet'] = line
        elif line and current and not current.get('snippet'):
            current['snippet'] = line[:200]
    if current and current.get('title'):
        results.append(current)
    # 如果没有解析到结果，尝试从文本中提取URL
    if not results:
        import re
        urls = re.findall(r'https?://[^\s)]+', text)
        for i, url in enumerate(urls[:max_results]):
            results.append({'title': f'结果{i+1}', 'url': url, 'snippet': ''})
    return results[:max_results]

def _parse_api_response(data):
    """解析 API 响应"""
    results = []
    try:
        items = data.get('result', {}).get('content', [])
        for item in items[:5]:
            results.append({
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'snippet': item.get('snippet', '')[:200]
            })
    except Exception:
        pass
    return results