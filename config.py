"""全局配置文件"""
import os
from pathlib import Path

# 项目路径
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
NEWS_DIR = DATA_DIR / "news"
REPORTS_DIR = DATA_DIR / "reports"
PRICE_FILE = DATA_DIR / "prices.json"

# 确保目录存在
for d in [DATA_DIR, NEWS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ===== Claude API 配置 =====
# 支持 ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN
# 如果用了兼容DeepSeek或其他第三方API，请设置 ANTHROPIC_BASE_URL
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN", "")
CLAUDE_API_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")
CLAUDE_API_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6-20250514")

# ===== 新闻采集配置 =====

# ===== 新闻采集配置 =====

# 时政新闻源（已验证可用的RSS）
POLITICAL_NEWS_SOURCES = [
    {
        "name": "BBC中文",
        "type": "rss",
        "url": "https://www.bbc.com/zhongwen/simp/index.xml",
    },
    {
        "name": "FT中文",
        "type": "rss",
        "url": "https://www.ftchinese.com/rss/news",
    },
    {
        "name": "Solidot",
        "type": "rss",
        "url": "https://www.solidot.org/index.rss",
    },
]

# 时政新闻网页源（补充RSS，覆盖央视等国内主流媒体）
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
]

# AIGC 行业新闻源（已验证可用的RSS）
# 重点覆盖 AI影视传媒（AI视频/AI短剧/AI广告/AI宣传片）方向
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
        "name": "AI News",
        "type": "rss",
        "url": "https://www.artificialintelligence-news.com/feed/",
    },
    {
        "name": "ArsTechnica",
        "type": "rss",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
    },
    {
        "name": "Hacker News",
        "type": "rss",
        "url": "https://news.ycombinator.com/rss",
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
]

# 网页抓取源（补充RSS，重点覆盖AI影视传媒方向）
WEB_SCRAPE_SOURCES = [
    {
        "name": "36氪",
        "type": "web",
        "url": "https://36kr.com/search/articles/AI%E7%94%9F%E6%88%90",
        "category": "industry",
    },
    {
        "name": "虎嗅AI",
        "type": "web",
        "url": "https://www.huxiu.com/channel/AI.html",
        "category": "industry",
    },
    {
        "name": "国家广电总局",
        "type": "web",
        "url": "https://www.nrta.gov.cn/",
        "category": "industry_policy",
    },
    {
        "name": "1905电影网",
        "type": "web",
        "url": "https://www.1905.com/",
        "category": "industry",
    },
]

# 搜索关键词（用于补充采集）
AIGC_KEYWORDS = [
    "AI漫剧", "AI短剧", "AIGC视频", "AI广告", "AI宣传片",
    "AI视频生成", "可灵AI", "Sora", "Runway", "Pika",
    "数字人", "AI配音", "AI影视", "AIGC",
]

# ===== 价格追踪配置 =====
PRICE_CATEGORIES = [
    {
        "id": "ai_video",
        "name": "AI视频生成",
        "unit": "元/秒",
        "description": "AI生成视频的行业报价",
    },
    {
        "id": "ai_image",
        "name": "AI图片生成",
        "unit": "元/张",
        "description": "AI生成图片的行业报价",
    },
    {
        "id": "ai_voice",
        "name": "AI语音合成",
        "unit": "元/千字",
        "description": "AI配音/语音合成报价",
    },
    {
        "id": "ai_short_drama",
        "name": "AI短剧制作",
        "unit": "万元/部",
        "description": "AI短剧全案制作成本",
    },
    {
        "id": "ai_ad",
        "name": "AI广告制作",
        "unit": "万元/条",
        "description": "AI广告/宣传片制作报价",
    },
    {
        "id": "digital_human",
        "name": "数字人定制",
        "unit": "万元/个",
        "description": "数字人克隆/定制报价",
    },
]

# ===== 报告配置 =====
REPORT_TITLE = "AI 行业新闻日报"
REPORT_LANGUAGE = "zh-CN"

# ===== 调度配置 =====
SCHEDULE_TIME = "09:00"  # 每天早上9点运行
