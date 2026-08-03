import json
import re
import os
import requests

ANYSEARCH_ENDPOINT = "https://api.anysearch.com/mcp"
ANYSEARCH_CLIENT = "skill/3.0.1"

def _get_api_key():
    """获取 AnySearch API Key，优先级：环境变量 > .env 文件 > 匿名"""
    key = os.environ.get("ANYSEARCH_API_KEY", "")
    if key:
        return key
    # 尝试读取 .env 文件
    for env_path in [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
    ]:
        if os.path.isfile(env_path):
            with open(env_path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    k = k.strip().lstrip("\ufeff")
                    v = v.strip().strip("\"'").strip()
                    if k == "ANYSEARCH_API_KEY" and v:
                        return v
    return ""


def _call_api(tool_name, arguments, timeout=20):
    """调用 AnySearch JSON-RPC API"""
    import sys
    headers = {
        "Content-Type": "application/json",
        "X-Anysearch-Client": ANYSEARCH_CLIENT,
    }
    api_key = _get_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    try:
        resp = requests.post(ANYSEARCH_ENDPOINT, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            error_msg = data["error"].get("message", str(data["error"]))
            print(f"AnySearch API Error: {error_msg}", file=sys.stderr)
            return None
        result = data.get("result", {})
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                return item.get("text", "")
        # 如果没有 text 类型的内容，返回整个结果
        raw = json.dumps(result, indent=2, ensure_ascii=False)
        print(f"AnySearch unexpected response format: {raw[:200]}", file=sys.stderr)
        return raw
    except requests.exceptions.Timeout:
        print("AnySearch API Timeout", file=sys.stderr)
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"AnySearch API Connection Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"AnySearch API Exception: {e}", file=sys.stderr)
        return None


def search_web(query, max_results=5):
    """使用 AnySearch HTTP API 搜索"""
    if not query or not query.strip():
        return []

    text = _call_api("search", {"query": query.strip(), "max_results": min(max_results, 10)})
    if text:
        return _parse_search_results(text, max_results)
    return []


def batch_search(queries, max_results=3):
    """批量搜索多个关键词"""
    if not queries:
        return {}

    # 构造批量查询参数
    query_items = []
    for q in queries:
        if q and q.strip():
            query_items.append({"query": q.strip(), "max_results": min(max_results, 10)})

    if not query_items:
        return {}

    # 如果只有一个查询，直接调用 search
    if len(query_items) == 1:
        results = {queries[0]: search_web(queries[0], max_results)}
        return results

    # 限制最多 5 个
    query_items = query_items[:5]

    text = _call_api("batch_search", {"queries": query_items}, timeout=30)
    if text:
        return _parse_batch_results(text, queries, max_results)

    # 降级：逐个搜索
    results = {}
    for q in queries:
        results[q] = search_web(q, max_results)
    return results


def extract_page(url):
    """提取网页全文"""
    if not url:
        return ""
    text = _call_api("extract", {"url": url}, timeout=15)
    if text:
        return text[:3000]
    return ""


def _parse_search_results(text, max_results=5):
    """解析搜索结果为结构化数据"""
    results = []

    # 匹配格式: ### N. Title
    #           - **URL**: https://...
    #           后续是摘要文本
    pattern = re.compile(
        r'###\s+\d+\.\s+(.+?)\n\s*-\s+\*\*URL\*\*\s*:\s*(\S+)\s*\n(.+?)(?=\n\s*###|\Z)',
        re.DOTALL
    )
    matches = pattern.findall(text)
    for title, url, snippet in matches:
        title = title.strip()
        snippet = _clean_snippet(snippet.strip())
        if title and url:
            results.append({
                'title': title,
                'url': url,
                'snippet': snippet[:300]
            })
        if len(results) >= max_results:
            break

    # 备用方案：正则没匹配到时，提取 URL 和标题
    if not results:
        urls = re.findall(r'https?://[^\s)\]]+', text)
        for i, url in enumerate(urls[:max_results]):
            results.append({
                'title': f'搜索结果 {i+1}',
                'url': url,
                'snippet': ''
            })

    return results[:max_results]


def _parse_batch_results(text, queries, max_results=3):
    """解析批量搜索结果"""
    results = {}
    for q in queries:
        if q and q.strip():
            results[q] = []

    # 尝试按查询分组解析
    # 批量搜索返回格式可能是多个搜索块
    sections = re.split(r'(?=##\s+搜索)', text)
    if len(sections) <= 1:
        sections = re.split(r'(?=###\s+Query)', text)

    for section in sections:
        if not section.strip():
            continue
        parsed = _parse_search_results(section, max_results)
        # 尝试匹配到对应的查询
        for q in queries:
            if q and q.strip() and q.lower() in section.lower():
                results[q] = parsed
                break
        else:
            # 无法匹配，分配给第一个空结果的查询
            for q in queries:
                if q and q.strip() and not results.get(q):
                    results[q] = parsed
                    break

    # 降级：如果都没解析出来，分配所有结果给第一个查询
    all_results = _parse_search_results(text, max_results * len(queries))
    if all_results and all(not v for v in results.values()):
        first_q = next((q for q in queries if q and q.strip()), "")
        if first_q:
            results[first_q] = all_results

    return results


def _clean_snippet(text):
    """清理摘要文本"""
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