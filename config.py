"""全局配置文件"""
import os
import sys
from pathlib import Path
from datetime import datetime

# 项目路径（支持 PyInstaller 打包模式）
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
NEWS_DIR = DATA_DIR / "news"
REPORTS_DIR = DATA_DIR / "reports"
PRICE_FILE = DATA_DIR / "prices.json"

# 报告按月分类的目录，如：data/reports/2026年5月/
MONTH_DIR = REPORTS_DIR / datetime.now().strftime("%Y年%m月")

# 确保目录存在
for d in [DATA_DIR, NEWS_DIR, REPORTS_DIR, MONTH_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ===== Claude API 配置（支持本地配置文件覆盖） =====
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN", "")
CLAUDE_API_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")
CLAUDE_API_MODEL = os.getenv("ANTHROPIC_MODEL", "deepseek-chat")

# 从本地配置文件读取覆盖（GUI设置会写入此文件）
SETTINGS_FILE = DATA_DIR / "settings.json"
if SETTINGS_FILE.exists():
    try:
        import json as _json
        _s = _json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if _s.get("api_key"):
            CLAUDE_API_KEY = _s["api_key"]
        if _s.get("base_url"):
            CLAUDE_API_BASE_URL = _s["base_url"]
        if _s.get("model"):
            CLAUDE_API_MODEL = _s["model"]
    except Exception:
        pass

# ===== 新闻采集配置 =====

# 时政新闻源（以国内权威媒体为主）
POLITICAL_NEWS_SOURCES = []  # RSS源留空，全部使用网页抓取

# 时政新闻网页源（国内主流媒体）
POLITICAL_WEB_SOURCES = [
    {
        "name": "央视新闻",
        "type": "web",
        "url": "https://news.cctv.com/",
        "category": "political",
    },
    {
        "name": "央视网",
        "type": "web",
        "url": "https://www.cctv.com/",
        "category": "political",
    },
    {
        "name": "人民日报",
        "type": "web",
        "url": "https://www.people.com.cn/",
        "category": "political",
    },
    {
        "name": "新华社",
        "type": "web",
        "url": "http://www.xinhuanet.com/",
        "category": "political",
    },
    {
        "name": "环球网",
        "type": "web",
        "url": "https://www.huanqiu.com/",
        "category": "political",
    },
    {
        "name": "中国新闻网",
        "type": "web",
        "url": "https://www.chinanews.com.cn/",
        "category": "political",
    },
    {
        "name": "央广网",
        "type": "web",
        "url": "https://www.cnr.cn/",
        "category": "political",
    },
    {
        "name": "光明网",
        "type": "web",
        "url": "https://www.gmw.cn/",
        "category": "political",
    },
    {
        "name": "中国青年网",
        "type": "web",
        "url": "https://www.youth.cn/",
        "category": "political",
    },
    {
        "name": "浙江新闻",
        "type": "web",
        "url": "https://zjnews.zjol.com.cn/",
        "category": "political",
    },
]

# AIGC 行业新闻源（AI影视传媒方向）
AIGC_NEWS_SOURCES = [
    {
        "name": "爱范儿",
        "type": "rss",
        "url": "https://www.ifanr.com/feed",
    },
    {
        "name": "TechCrunch",
        "type": "rss",
        "url": "https://techcrunch.com/feed/",
    },
    {
        "name": "ArsTechnica",
        "type": "rss",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
    },
    {
        "name": "Variety",
        "type": "rss",
        "url": "https://variety.com/feed/",
    },
    {
        "name": "The Hollywood Reporter",
        "type": "rss",
        "url": "https://www.hollywoodreporter.com/feed/",
    },
    {
        "name": "AI News",
        "type": "rss",
        "url": "https://www.artificialintelligence-news.com/feed/",
    },
    {
        "name": "Hacker News",
        "type": "rss",
        "url": "https://news.ycombinator.com/rss",
    },
]

# 网页抓取源（补充AI行业 + 政策监管信息）
WEB_SCRAPE_SOURCES = [
    # --- 政策监管（来自要求.txt） ---
    {
        "name": "国家广电总局",
        "type": "web",
        "url": "https://www.nrta.gov.cn/",
        "category": "industry_policy",
    },
    {
        "name": "广电总局网络视听节目管理司",
        "type": "web",
        "url": "https://www.nrta.gov.cn/col/col2253/index.html",
        "category": "industry_policy",
    },
    {
        "name": "中国网络视听节目服务协会",
        "type": "web",
        "url": "http://www.cnsa.cn/",
        "category": "industry_policy",
    },
    {
        "name": "国家电影局",
        "type": "web",
        "url": "https://www.chinafilm.gov.cn/",
        "category": "industry_policy",
    },
    {
        "name": "国务院政策文件库",
        "type": "web",
        "url": "https://www.gov.cn/zhengce/",
        "category": "industry_policy",
    },
    # --- 平台/创作者（部分需要登录） ---
    {
        "name": "巨量引擎",
        "type": "web",
        "url": "https://www.oceanengine.com/news",
        "category": "industry",
        "need_login": True,
    },
    {
        "name": "抖音电商学习中心",
        "type": "web",
        "url": "https://school.jinritemai.com/",
        "category": "industry",
    },
    {
        "name": "抖音创作者中心",
        "type": "web",
        "url": "https://creator.douyin.com/",
        "category": "industry",
        "need_login": True,
    },
    # --- 行业媒体 ---
    {
        "name": "36氪AI",
        "type": "web",
        "url": "https://36kr.com/search/articles/AI%E7%94%9F%E6%88%90",
        "category": "industry",
    },
    {
        "name": "1905电影网",
        "type": "web",
        "url": "https://www.1905.com/",
        "category": "industry",
    },
]

# 搜索关键词（用于AI行业过滤）
AIGC_KEYWORDS = [
    "AI漫剧", "AI短剧", "AIGC视频", "AI广告", "AI宣传片",
    "AI视频生成", "可灵AI", "Sora", "Runway", "Pika",
    "数字人", "AI配音", "AI影视", "AIGC",
]

# ===== 价格追踪配置 =====
PRICE_CATEGORIES = [
    {"id": "ai_video", "name": "AI视频生成", "unit": "元/秒", "description": "AI生成视频的行业报价"},
    {"id": "ai_image", "name": "AI图片生成", "unit": "元/张", "description": "AI生成图片的行业报价"},
    {"id": "ai_voice", "name": "AI语音合成", "unit": "元/千字", "description": "AI配音/语音合成报价"},
    {"id": "ai_short_drama", "name": "AI短剧制作", "unit": "万元/部", "description": "AI短剧全案制作成本"},
    {"id": "ai_ad", "name": "AI广告制作", "unit": "万元/条", "description": "AI广告/宣传片制作报价"},
    {"id": "digital_human", "name": "数字人定制", "unit": "万元/个", "description": "数字人克隆/定制报价"},
]

# ===== 报告配置 =====
REPORT_TITLE = "AI 行业新闻日报"
