"""新闻采集模块
支持RSS订阅源和网页抓取两种方式，收集时政新闻和AIGC行业新闻。
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

from config import (
    POLITICAL_NEWS_SOURCES, AIGC_NEWS_SOURCES,
    POLITICAL_WEB_SOURCES, WEB_SCRAPE_SOURCES, NEWS_DIR,
)

logger = logging.getLogger(__name__)

# ==================== RSS 采集 ====================

def fetch_rss(url: str, source_name: str, days: int = 2) -> List[Dict]:
    """从RSS源获取新闻条目"""
    articles = []
    try:
        logger.info(f"正在从RSS抓取: {source_name}")
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            logger.warning(f"解析RSS失败: {source_name}, 错误: {feed.bozo_exception}")
            return articles

        cutoff = datetime.now() - timedelta(days=days)

        for entry in feed.entries:
            # 解析发布时间
            pub_time = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_time = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_time = datetime(*entry.updated_parsed[:6])

            # 跳过太旧的文章
            if pub_time and pub_time < cutoff:
                continue

            article = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "published": pub_time.isoformat() if pub_time else None,
                "source": source_name,
                "collected_at": datetime.now().isoformat(),
            }
            # 清理HTML标签
            if article["summary"]:
                soup = BeautifulSoup(article["summary"], "html.parser")
                article["summary"] = soup.get_text(strip=True)[:500]

            articles.append(article)

        logger.info(f"从 {source_name} 获取了 {len(articles)} 篇文章")
    except Exception as e:
        logger.error(f"抓取RSS失败 {source_name}: {e}", exc_info=True)

    return articles


# ==================== 网页抓取 ====================

def fetch_web(url: str, source_name: str, timeout: int = 15) -> List[Dict]:
    """从新闻网站抓取文章列表（根据网站特征智能提取）"""
    articles = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        logger.info(f"正在抓取网页: {source_name} ({url})")
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        seen_links = set()
        for a_tag in soup.find_all("a", href=True):
            title = a_tag.get_text(strip=True)
            href = a_tag["href"]

            # 标题太短或含无关文本则跳过
            if len(title) < 10 or any(t in title for t in ["登录", "注册", "关于", "联系", "English"]):
                continue

            # 过滤非文章链接
            if href.startswith("#") or href.startswith("javascript:"):
                continue

            # 相对链接转绝对
            if href.startswith("/"):
                from urllib.parse import urljoin
                href = urljoin(url, href)

            # 去重
            if href in seen_links:
                continue
            seen_links.add(href)

            # 取h2/h3内的更精确的标题
            parent_heading = a_tag.find_parent(["h2", "h3", "h4"])
            if parent_heading:
                title = parent_heading.get_text(strip=True)

           # 提取摘要（周围文字）
            summary = title
            parent_p = a_tag.find_parent("p")
            if parent_p:
                summary = parent_p.get_text(strip=True)[:200]

            articles.append({
                "title": title[:100],
                "link": href,
                "summary": summary,
                "published": None,
                "source": source_name,
                "collected_at": datetime.now().isoformat(),
            })

        # 取前50条最相关的
        articles.sort(key=lambda x: len(x["title"]), reverse=True)
        articles = articles[:50]
        logger.info(f"从 {source_name} 抓取了 {len(articles)} 条内容")
    except Exception as e:
        logger.error(f"网页抓取失败 {source_name}: {e}", exc_info=True)

    return articles


# ==================== 关键词过滤 ====================

def filter_by_keywords(articles: List[Dict], keywords: List[str]) -> List[Dict]:
    """根据关键词过滤相关文章"""
    if not keywords:
        return articles
    filtered = []
    for art in articles:
        text = (art["title"] + " " + art["summary"]).lower()
        if any(kw.lower() in text for kw in keywords):
            filtered.append(art)
    return filtered


# ==================== 去重（增强版） ====================

def _normalize_title(title: str) -> str:
    """标准化标题用于去重：去空格、标点、转小写"""
    import re
    t = title.lower().strip()
    t = re.sub(r'[^\w一-鿿]', '', t)  # 去标点
    t = re.sub(r'\s+', '', t)                  # 去空格
    return t[:40]


def deduplicate(articles: List[Dict]) -> List[Dict]:
    """多维度去重：URL去重 + 标题相似度去重"""
    seen_urls = set()
    seen_titles = set()
    result = []

    for art in articles:
        # URL去重
        url = art.get("link", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)

        # 标题去重（归一化后比较）
        title_key = _normalize_title(art.get("title", ""))
        if not title_key:
            continue

        # 检查是否与已有标题高度相似
        is_dup = False
        for existing in seen_titles:
            # 简单重叠检测：一个包含另一个，或相似度很高
            if len(title_key) > 5 and len(existing) > 5:
                if title_key in existing or existing in title_key:
                    is_dup = True
                    break
                # 编辑距离检测（限于短标题）
                if len(title_key) < 30 and len(existing) < 30:
                    from difflib import SequenceMatcher
                    if SequenceMatcher(None, title_key, existing).ratio() > 0.75:
                        is_dup = True
                        break

        if not is_dup:
            seen_titles.add(title_key)
            result.append(art)

    return result


# ==================== 主采集接口 ====================

# 行业关键词（用于从英文/泛科技新闻中筛选AIGC相关内容）
AIGC_KEYWORDS = [
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "video generation", "text to video", "Sora", "Runway", "Pika", "Stable Video",
    "AIGC", "generative AI", "large language model", "LLM",
    "AI advertising", "AI video", "digital human", "AI voice",
    "diffusion model", "transformer", "multimodal",
    "AI 视频", "AI 生成", "AI 广告", "AI 短剧", "AI 宣传片",
    "人工智能", "大模型", "数字人", "视频生成",
]


def collect_political_news(days: int = 2) -> List[Dict]:
    """采集时政新闻（国内主流媒体）"""
    all_articles = []
    for source in POLITICAL_WEB_SOURCES:
        articles = fetch_web(source["url"], source["name"])
        all_articles.extend(articles)

    return deduplicate(all_articles)


def _parse_html_to_articles(html: str, source_name: str) -> List[Dict]:
    """将HTML页面解析为文章列表"""
    articles = []
    try:
        soup = BeautifulSoup(html, "lxml")
        seen_links = set()
        for a_tag in soup.find_all("a", href=True):
            title = a_tag.get_text(strip=True)
            href = a_tag["href"]
            if len(title) < 10:
                continue
            if href.startswith("#") or href.startswith("javascript:"):
                continue
            if href.startswith("/"):
                from urllib.parse import urljoin
                base = {"name": source_name, "url": ""}
                href = urljoin(f"https://{source_name}.com", href)
            if href in seen_links:
                continue
            seen_links.add(href)
            articles.append({
                "title": title[:100],
                "link": href,
                "summary": title,
                "published": None,
                "source": source_name,
                "collected_at": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return articles[:30]


def collect_industry_news(days: int = 2) -> List[Dict]:
    """采集AIGC行业新闻（RSS + 网页抓取 + 关键词过滤，支持登录态）"""
    all_articles = []
    # 1. 从AIGC新闻源采集（支持RSS和网页类型）
    for source in AIGC_NEWS_SOURCES:
        if source.get("type") == "web":
            articles = fetch_web(source["url"], source["name"])
        else:
            articles = fetch_rss(source["url"], source["name"], days)
        all_articles.extend(articles)

    # 2. 从补充网页源采集（含行业和政策源）
    for source in WEB_SCRAPE_SOURCES:
        if source.get("need_login"):
            # 登录态采集：从数据库获取cookie
            try:
                from system.database import get_login_session
                sid = source.get("site_id", source["name"])
                session = get_login_session(sid)
                if session and session.get("cookies") and len(session["cookies"]) > 0:
                    import requests as _req
                    cookies = {c.get("name", ""): c.get("value", "") for c in session["cookies"] if "name" in c}
                    try:
                        resp = _req.get(source["url"], cookies=cookies, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
                        resp.encoding = "utf-8"
                        art_list = _parse_html_to_articles(resp.text, source["name"])
                        all_articles.extend(art_list)
                        logger.info(f"使用登录态从 {source['name']} 采集到 {len(art_list)} 条")
                        continue
                    except Exception as e:
                        logger.warning(f"登录态采集 {source['name']} 失败: {e}")
                else:
                    logger.info(f"{source['name']} 需要登录，请在GUI中先登录")
                continue
            except ImportError:
                logger.warning(f"database模块不可用，跳过需要登录的 {source['name']}")
                continue
        articles = fetch_web(source["url"], source["name"])
        all_articles.extend(articles)

    # 3. 用行业关键词过滤（优先保留相关文章）
    keyword_articles = filter_by_keywords(all_articles, AIGC_KEYWORDS)

    # 如果关键词过滤结果太少（<5条），补充一些最新的泛科技新闻
    # 否则只保留关键词匹配的文章，让报告更聚焦
    if len(keyword_articles) >= 5:
        final = keyword_articles
    else:
        # 保留全部，但把关键词匹配的放在前面
        matched_ids = {id(a) for a in keyword_articles}
        rest = [a for a in all_articles if id(a) not in matched_ids]
        final = keyword_articles + rest[:20]

    return deduplicate(final)


def collect_all(days: int = 2) -> Dict[str, List[Dict]]:
    """采集所有新闻（自动保存到数据库）"""
    logger.info("=" * 40)
    logger.info("开始采集新闻...")

    political = collect_political_news(days)
    logger.info(f"时政新闻: 采集到 {len(political)} 条")

    industry = collect_industry_news(days)
    logger.info(f"行业新闻: 采集到 {len(industry)} 条")

    # 保存到数据库
    try:
        from system.database import save_articles
        save_articles(political, "political")
        save_articles(industry, "industry")
    except Exception as e:
        logger.warning(f"保存到数据库失败: {e}")

    return {
        "political": political,
        "industry": industry,
        "collected_at": datetime.now().isoformat(),
    }


def save_news(data: Dict[str, List[Dict]]) -> Path:
    """保存原始新闻到文件"""
    today = datetime.now().strftime("%Y%m%d")
    filepath = NEWS_DIR / f"news_{today}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"原始新闻已保存到: {filepath}")
    return filepath


def load_today_news() -> Optional[Dict[str, List[Dict]]]:
    """加载今天的新闻数据"""
    today = datetime.now().strftime("%Y%m%d")
    filepath = NEWS_DIR / f"news_{today}.json"
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
