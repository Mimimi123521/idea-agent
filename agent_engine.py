"""
灵感管家 Agent 引擎
实现提示词 4 的归类与分析逻辑
"""
import re
from datetime import datetime

WORK_TAGS = {
    'engine-arch': '发动机架构/结构设计',
    'combustion': '燃烧/喷射/点火',
    'hydrogen-safety': '氢气安全/泄漏/防爆',
    'test-bench': '台架试验/测试方法',
    'nvh': 'NVH/振动/噪声',
    'materials': '材料/密封/耐久',
    'schedule': '进度/排期/里程碑',
    'resource': '人力/设备/预算',
    'risk': '风险识别/应对',
    'quality': '质量/标准/适航',
    'supply-chain': '供应链/采购',
}

LIFE_TAGS = {
    'daily-thought': '日常感悟/随想/反思',
    'personal-todo': '生活待办/购物/缴费',
    'health': '健康/运动/体检',
    'family': '家庭/家人相关',
    'learning': '学习/阅读/技能',
    'social': '社交/人脉/活动',
    'travel': '出行/行程安排',
    'finance': '个人财务/理财',
}

PROCESS_TAGS = {
    'procedure': '流程优化/改进',
    'regulation': '法规/标准/认证',
    'doc': '文档/报告/纪要',
}

OTHER_TAGS = {
    'idea': '初步想法，待评估',
    'question': '待确认/待研究的问题',
    'reference': '参考信息/资料',
}

ALL_TAGS = {**WORK_TAGS, **LIFE_TAGS, **PROCESS_TAGS, **OTHER_TAGS}

# 工作类关键词
WORK_KEYWORDS = [
    '发动机', '氢内燃机', '台架', '试验', '测试', '燃烧', '喷射', '点火',
    '曲轴', '活塞', '缸体', '缸盖', '涡轮', '增压', '密封', '润滑',
    'NVH', '振动', '噪声', '扭振', '耐久', '可靠性', '疲劳',
    '氢气', '泄漏', '防爆', '安全', '氢脆',
    '适航', '认证', '标准', 'GB/T', 'ISO', 'SAE', 'FAA',
    '项目管理', '进度', '里程碑', '排期', '预算', '采购',
    '供应链', '供应商', '质量', '风险', '评审',
    '台架试验', '稳态', '标定', '空燃比', '早燃', '冷热冲击',
    '水平对置', 'Boxer', '对置缸', '左右缸',
    '原型机', '样机', '装配', '调试',
    '电池', '电机', '混动', '电控',
    '项目', '团队', '开会', '会议', '纪要', '报告', '文档',
    '审批', '签字', '批准', '方案',
]

# 生活类关键词
LIFE_KEYWORDS = [
    '感悟', '随想', '反思', '想法', '心情',
    '购物', '缴费', '买菜', '水电', '物业',
    '健康', '运动', '跑步', '健身', '体检', '看病', '医院',
    '家庭', '家人', '孩子', '父母', '老婆', '老公', '爱人',
    '学习', '阅读', '读书', '课程', '技能', '培训', '考试',
    '社交', '朋友', '聚会', '饭局', '活动', '人脉',
    '旅行', '出行', '旅游', '机票', '酒店', '行程',
    '财务', '理财', '投资', '股票', '基金', '保险', '工资',
    '周末', '放假', '休息', '休假',
    '吃饭', '美食', '餐厅', '外卖',
    '电影', '音乐', '游戏', '爱好',
]

def detect_domain(content):
    """判断内容所属领域：work / life / process / other"""
    content_lower = content.lower()
    work_score = sum(1 for kw in WORK_KEYWORDS if kw in content)
    life_score = sum(1 for kw in LIFE_KEYWORDS if kw in content)
    if work_score > life_score and work_score >= 1:
        return 'work'
    elif life_score > work_score and life_score >= 1:
        return 'life'
    elif work_score == life_score and work_score > 0:
        return 'work'  # 模棱两可默认工作
    return 'other'

def suggest_tags(content, domain):
    """根据内容自动推荐标签"""
    content_lower = content.lower()
    matched = []
    if domain == 'work':
        tag_pool = WORK_TAGS
        # 特定关键词匹配
        if any(kw in content for kw in ['架构','结构','曲轴','活塞','缸体','缸盖','水平对置','Boxer','对置']):
            matched.append('engine-arch')
        if any(kw in content for kw in ['燃烧','喷射','点火','空燃比','lambda','早燃','爆震']):
            matched.append('combustion')
        if any(kw in content for kw in ['氢气','泄漏','防爆','安全','氢脆']):
            matched.append('hydrogen-safety')
        if any(kw in content for kw in ['台架','试验','测试','标定','稳态','耐久','冲击']):
            matched.append('test-bench')
        if any(kw in content for kw in ['NVH','振动','噪声','扭振','噪音']):
            matched.append('nvh')
        if any(kw in content for kw in ['材料','密封','润滑','耐久','疲劳']):
            matched.append('materials')
        if any(kw in content for kw in ['进度','排期','里程碑','时间','节点','计划']):
            matched.append('schedule')
        if any(kw in content for kw in ['资源','人力','设备','预算','采购','经费']):
            matched.append('resource')
        if any(kw in content for kw in ['风险','隐患','问题','故障','失效']):
            matched.append('risk')
        if any(kw in content for kw in ['质量','标准','适航','认证','ISO','GB/T','SAE','FAA']):
            matched.append('quality')
        if any(kw in content for kw in ['供应链','供应商','采购','外协','配套']):
            matched.append('supply-chain')
    elif domain == 'life':
        tag_pool = LIFE_TAGS
        if any(kw in content for kw in ['感悟','随想','反思','想法','心情']):
            matched.append('daily-thought')
        if any(kw in content for kw in ['购物','缴费','买菜','水电','物业','买']):
            matched.append('personal-todo')
        if any(kw in content for kw in ['健康','运动','跑步','健身','体检','看病','医院']):
            matched.append('health')
        if any(kw in content for kw in ['家庭','家人','孩子','父母','老婆','老公','爱人']):
            matched.append('family')
        if any(kw in content for kw in ['学习','阅读','读书','课程','技能','培训','考试']):
            matched.append('learning')
        if any(kw in content for kw in ['社交','朋友','聚会','饭局','活动','人脉']):
            matched.append('social')
        if any(kw in content for kw in ['旅行','出行','旅游','机票','酒店','行程']):
            matched.append('travel')
        if any(kw in content for kw in ['财务','理财','投资','股票','基金','保险','工资']):
            matched.append('finance')
    else:
        tag_pool = OTHER_TAGS
        if any(kw in content for kw in ['想法','主意','灵感','建议']):
            matched.append('idea')
        if any(kw in content for kw in ['问题','疑问','不清楚','是否','能不能','可以吗']):
            matched.append('question')
        else:
            matched.append('reference')
    return matched[:2] if matched else ['idea']

def analyze_work(content, tags):
    """工作类四维评分分析"""
    scores = {'feasibility': 3, 'priority': 3, 'urgency': 3, 'risk': 3}
    # 可行性
    if any(kw in content for kw in ['已具备','已有','现有','成熟','有方案','可参考']):
        scores['feasibility'] = 5
    elif any(kw in content for kw in ['需要调研','需研究','探索','创新','新方案']):
        scores['feasibility'] = 2
    elif any(kw in content for kw in ['难度大','很困难','未知','挑战']):
        scores['feasibility'] = 1
    # 优先级
    high_priority = ['关键','重要','紧急','核心','瓶颈','必须','立刻','马上']
    low_priority = ['后期','以后','有空','optional','可有可无']
    if any(kw in content for kw in high_priority):
        scores['priority'] = 5
    elif any(kw in content for kw in low_priority):
        scores['priority'] = 1
    # 紧迫性
    urgent = ['今天','明天','本周','截止','deadline','马上','立刻','紧急']
    if any(kw in content for kw in urgent):
        scores['urgency'] = 5
    # 风险性
    if any(kw in content for kw in ['风险','隐患','问题','故障','失效','泄漏','爆炸']):
        scores['risk'] = 5
    elif any(kw in content for kw in ['关注','注意','监控','小心']):
        scores['risk'] = 3
    return scores

def analyze_life(content):
    """生活类简化决策"""
    urgency = 1
    feasibility = 3
    if any(kw in content for kw in ['今天','明天','到期','截止','缴费','预约','deadline']):
        urgency = 5
    elif any(kw in content for kw in ['本周','下周','最近']):
        urgency = 3
    if any(kw in content for kw in ['可以','能做','简单','容易','已经']):
        feasibility = 5
    elif any(kw in content for kw in ['想','希望','打算','有空']):
        feasibility = 3
    return {'feasibility': feasibility, 'priority': urgency, 'urgency': urgency, 'risk': 1}

def make_decision(domain, scores, tags):
    """根据评分做出待办决策"""
    if domain == 'work':
        if scores['feasibility'] >= 3 and (scores['priority'] >= 4 or scores['urgency'] >= 4):
            return 'todo-work', '建议加入工作待办，尽快落实'
        elif scores['feasibility'] >= 3:
            return 'stash', '暂存灵感库，待时机成熟再评估'
        else:
            return 'archive', '归档参考，待条件具备后再回看'
    elif domain == 'life':
        if scores['urgency'] >= 3 or scores['feasibility'] >= 4:
            return 'todo-life', '建议加入生活待办，安排时间处理'
        elif '感悟' in str(tags) or 'daily-thought' in tags:
            return 'stash', '暂存灵感库，日后再回味'
        else:
            return 'archive', '归档参考'
    else:
        return 'archive', '归档参考'

def generate_suggestion(domain, decision, content):
    """生成行动建议"""
    if decision == 'todo-work':
        return f"建议本周内制定{content[:20]}的具体执行计划，明确责任人和时间节点"
    elif decision == 'todo-life':
        return f"建议尽快安排时间处理，避免遗忘"
    elif decision == 'stash':
        return "先记录下来，等有更多信息后再评估"
    else:
        return "已归档，作为参考资料保留"

def process_idea(content):
    """完整处理一条灵感：判断领域 → 推荐标签 → 评分 → 决策"""
    domain = detect_domain(content)
    tags = suggest_tags(content, domain)
    if domain == 'work':
        scores = analyze_work(content, tags)
    elif domain == 'life':
        scores = analyze_life(content)
    else:
        scores = {'feasibility': 2, 'priority': 1, 'urgency': 1, 'risk': 1}
    decision, reason = make_decision(domain, scores, tags)
    suggestion = generate_suggestion(domain, decision, content)
    return {
        'domain': domain,
        'tags': ','.join(tags),
        'feasibility': scores['feasibility'],
        'priority': scores['priority'],
        'urgency': scores['urgency'],
        'risk': scores['risk'],
        'decision': decision,
        'suggestion': suggestion
    }