"""
每日复盘引擎 — 调用 DeepSeek API 进行个人反思与成长分析
"""
import os
import json
import requests

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

SYSTEM_PROMPT = """你是一位温暖而敏锐的私人复盘教练，擅长帮助用户进行每日反思与成长。

用户会告诉你今天经历的事情、产生的想法或感受，请你从以下两个维度分析：

1. 今日最大收获：从用户描述中，找出今天最值得珍视的体验、领悟或成长，说明为什么值得关注
2. 明日可以尝试的：基于今天的描述，给出1-2条明天可以尝试的小改变或新视角，要可执行

注意：
- 不要预设用户的职业或身份，完全基于用户描述的内容来理解
- 尊重用户的感受，不评判、不说教
- 如果涉及情绪或困惑，用温和的方式帮助用户梳理，而非急于给出解决方案
- 保持简洁，每条分析控制在2-3句话

请用简洁的中文回复，格式如下：
【今日最大收获】
（具体分析）

【明日可以尝试的】
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
    """从 AI 回复中提取收获和建议"""
    progress = ''
    optimization = ''

    # 按标记分割
    if '【今日最大收获】' in raw:
        parts = raw.split('【今日最大收获】', 1)
        if len(parts) > 1:
            rest = parts[1]
            if '【明日可以尝试的】' in rest:
                progress = rest.split('【明日可以尝试的】', 1)[0].strip()
                optimization = rest.split('【明日可以尝试的】', 1)[1].strip()
            else:
                progress = rest.strip()

    # 兼容旧版标记
    if not progress and '【今日最大进步】' in raw:
        parts = raw.split('【今日最大进步】', 1)
        if len(parts) > 1:
            rest = parts[1]
            if '【明日优化建议】' in rest:
                progress = rest.split('【明日优化建议】', 1)[0].strip()
                optimization = rest.split('【明日优化建议】', 1)[1].strip()
            else:
                progress = rest.strip()

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
        progress = '今天记录的内容比较简短，但愿意停下来反思本身就是一种成长。'
        optimization = '明天可以试着多写几句，记录当下的感受、想法或经历，细节越多越能看到自己的变化。'
    else:
        progress = (
            '从今天的记录来看，你花时间整理了思绪，'
            '把经历和感受写下来本身就是一种梳理，能帮你更清晰地认识自己。'
        )
        optimization = (
            '明天可以尝试：\n'
            '1. 留意今天让你感到开心或触动的瞬间，哪怕很小\n'
            '2. 如果有困惑或纠结的事，试着写下来，写的过程本身就是答案的一部分'
        )

    return {
        'progress': progress,
        'optimization': optimization,
        'raw_response': f'【今日最大收获】\n{progress}\n\n【明日可以尝试的】\n{optimization}',
        'model': 'local-fallback'
    }