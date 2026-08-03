"""
每日复盘引擎 — 调用 DeepSeek API 分析每日工作
"""
import os
import json
import requests

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

SYSTEM_PROMPT = """你是一位资深的项目管理教练，擅长帮助氢内燃机制造项目管理者进行每日复盘。

用户会告诉你今天做了哪些工作，请你从以下两个维度分析：

1. 今日最大进步：从用户描述中，找出今天最值得肯定的一个进展或突破，说明为什么重要
2. 明日优化建议：基于今天的描述，给出1-2条明天可以改进的具体建议，要可执行

请用简洁的中文回复，格式如下：
【今日最大进步】
（具体分析）

【明日优化建议】
（具体建议）

如果用户描述的内容太少或太模糊，请友好地引导用户补充更多细节。"""


def analyze_daily_review(content):
    """调用 DeepSeek API 分析每日复盘内容"""
    if not DEEPSEEK_API_KEY:
        # 如果没有 API Key，返回本地分析结果
        return _local_analysis(content)

    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content}
                ],
                "temperature": 0.7,
                "max_tokens": 1024
            },
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data['choices'][0]['message']['content']
        progress, optimization = _parse_response(raw)
        return {
            'progress': progress,
            'optimization': optimization,
            'raw_response': raw,
            'model': DEEPSEEK_MODEL
        }
    except Exception as e:
        # 降级：使用本地分析
        result = _local_analysis(content)
        result['error'] = str(e)
        return result


def _parse_response(raw):
    """从 AI 回复中提取进步和优化建议"""
    progress = ''
    optimization = ''

    # 按标记分割
    if '【今日最大进步】' in raw:
        parts = raw.split('【今日最大进步】', 1)
        if len(parts) > 1:
            rest = parts[1]
            if '【明日优化建议】' in rest:
                progress = rest.split('【明日优化建议】', 1)[0].strip()
                optimization = rest.split('【明日优化建议】', 1)[1].strip()
            else:
                progress = rest.strip()

    # 兼容英文标记
    if not progress and '【Biggest Progress】' in raw:
        parts = raw.split('【Biggest Progress】', 1)
        if len(parts) > 1:
            rest = parts[1]
            if '【Optimization】' in rest:
                progress = rest.split('【Optimization】', 1)[0].strip()
                optimization = rest.split('【Optimization】', 1)[1].strip()

    # 如果解析失败，直接用原始内容
    if not progress:
        progress = raw[:300] if len(raw) > 300 else raw
        optimization = raw[300:600] if len(raw) > 300 else ''

    return progress, optimization


def _local_analysis(content):
    """本地分析（无 API 时的降级方案）"""
    keywords = content.replace('\n', ' ').strip()
    word_count = len(keywords)

    if word_count < 20:
        progress = '今日描述较简短，建议补充更多细节以便深入分析。'
        optimization = '明天可以尝试记录更详细的工作内容，包括具体任务、遇到的挑战和解决方案。'
    else:
        progress = (
            '从今天的记录来看，你保持了良好的工作节奏。'
            '将工作内容记录下来本身就是一种进步，有助于梳理思路和发现改进点。'
        )
        optimization = (
            '建议明天重点关注：\n'
            '1. 明确优先级最高的1-2件事，集中精力完成\n'
            '2. 记录遇到的问题和解决思路，为后续复盘积累素材'
        )

    return {
        'progress': progress,
        'optimization': optimization,
        'raw_response': f'【今日最大进步】\n{progress}\n\n【明日优化建议】\n{optimization}',
        'model': 'local-fallback'
    }