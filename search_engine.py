import json
import re
import requests

ANYSEARCH_CLI = "/workspace/.trae/skills/anysearch/scripts/anysearch_cli.py"

def search_web(query, max_results=5):
    """使用 AnySearch CLI 搜索"""
    try:
        import subprocess
        result = subprocess.run(
            ["python3", ANYSEARCH_CLI, "search", query, "--max_results", str(max_results)],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            return _parse_cli_output(result.stdout, max_results)
    except Exception:
        pass
    return []

def batch_search(queries, max_results=3):
    """批量搜索多个关键词"""
    results = {}
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

def _parse_cli_output(text, max_results=5):
    """解析 CLI 输出为结构化结果"""
    results = []
    # Match pattern: ### N. Title stuff
    # Then - **URL**: https://...
    # Then the snippet text follows
    pattern = re.compile(
        r'###\s+\d+\.\s+(.+?)\n\s*-\s+\*\*URL\*\*\s*:\s*(\S+)\s*\n(.+?)(?=\n\s*###|\Z)',
        re.DOTALL
    )
    matches = pattern.findall(text)
    for title, url, snippet in matches:
        title = title.strip()
        # Clean up the snippet
        snippet = _clean_snippet(snippet.strip())
        if title and url:
            results.append({
                'title': title,
                'url': url,
                'snippet': snippet[:300]
            })
        if len(results) >= max_results:
            break

    # Fallback: if regex didn't match, extract URLs and titles separately
    if not results:
        urls = re.findall(r'https?://[^\s)\]]+', text)
        for i, url in enumerate(urls[:max_results]):
            results.append({'title': f'搜索结果{i+1}', 'url': url, 'snippet': ''})

    return results[:max_results]

def _clean_snippet(text):
    """Clean snippet text by removing common noise patterns"""
    # Remove lines that are just separators or metadata
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('by ') or line.startswith('by\n'):
            continue
        if line.startswith('Search Results') or line.startswith('##'):
            continue
        cleaned.append(line)
    return ' '.join(cleaned)