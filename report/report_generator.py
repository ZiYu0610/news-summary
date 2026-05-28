"""日报报告生成模块
生成时政日报和AI行业日报，来源链接直接嵌入摘要正文。
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import MONTH_DIR

logger = logging.getLogger(__name__)


def _chinese_date() -> str:
    now = datetime.now()
    return f"{now.year}年{now.month}月{now.day}日"


def _inject_source_links(html_text: str, articles: List[Dict]) -> str:
    """将正文中的 [来源：XXX] 或 [来源：XXX #N] 替换为可点击的超链接

    匹配优先级：
    1. [#N] 编号精确定位
    2. 段落文本匹配标题关键词
    3. 来源名 + 数据库映射
    4. 来源名顺序匹配
    """
    import re

    # 建立标题索引（用于模糊匹配）
    title_index = {}
    for i, art in enumerate(articles):
        t = art.get("title", "").strip()[:30].lower()
        if t:
            # 提取标题中的关键信息词
            import re as _re
            words = _re.findall(r'[\w一-鿿]{2,}', t)
            for w in words:
                if w not in title_index:
                    title_index[w] = []
                title_index[w].append((i, art))

    def _find_by_source_name(source_name: str, line_text: str = "") -> str:
        """查找来源链接，多种策略"""
        # 策略1: 段落中找标题关键词匹配
        if line_text:
            line_lower = line_text.lower()
            # 找段落中所有出现的文章标题词
            candidates = set()
            for i, art in enumerate(articles):
                t = art.get("title", "").strip().lower()[:30]
                # 检查段落是否包含标题中的关键词
                t_words = set(re.findall(r'[\w一-鿿]{2,}', t))
                match_count = sum(1 for w in t_words if w in line_lower and len(w) >= 2)
                if match_count >= 2 and art.get("link"):  # 至少匹配2个词
                    candidates.add((match_count, i, art))

            if candidates:
                best = max(candidates, key=lambda x: x[0])
                return f'<a href="{best[2]["link"]}" target="_blank" rel="noopener" class="source-link">{source_name}</a>'

        # 策略2: 数据库来源映射
        try:
            from system.database import get_source_url
            db_url = get_source_url(source_name)
            if db_url:
                return f'<a href="{db_url}" target="_blank" rel="noopener" class="source-link">{source_name}</a>'
        except Exception:
            pass

        # 策略3: 按来源名顺序匹配第一个有链接的
        for art in articles:
            if art.get("source") == source_name and art.get("link"):
                return f'<a href="{art["link"]}" target="_blank" rel="noopener" class="source-link">{source_name}</a>'

        return f'<span class="source-tag">{source_name}</span>'

    def replace_func(match):
        source_name = match.group(1).strip()
        raw_num = match.group(2)  # 可能为 None

        if raw_num:
            # 编号模式 [来源：XXX #N] — 直接精确定位
            idx = int(raw_num) - 1
            if 0 <= idx < len(articles):
                link = articles[idx].get("link", "")
                if link:
                    return f'<a href="{link}" target="_blank" rel="noopener" class="source-link">{source_name}</a>'
                return f'<span class="source-tag">{source_name}</span>'
            # 编号越界，走降级
            return _find_by_source_name(source_name)

        # 无编号模式：提取段落上下文辅助匹配
        full_text = match.string
        line_start = full_text.rfind("\n", 0, match.start()) + 1
        line_end = full_text.find("\n", match.end())
        if line_end == -1:
            line_end = len(full_text)
        line_text = full_text[line_start:line_end]
        return _find_by_source_name(source_name, line_text)

    # 先匹配带编号的 [来源：XXX #N]，再匹配不带编号的 [来源：XXX]
    result = re.sub(r'\[来源：(.+?)\s+#(\d+)\]', replace_func, html_text)
    result = re.sub(r'\[来源：(.+?)\]', replace_func, result)
    return result


def _mark_ai_red(html_text: str) -> str:
    import re
    ai_keywords = [
        "人工智能", "AI", "大模型", "智能",
        "人工智慧", "深度学习", "机器学习",
        "AGI", "AIGC", "生成式",
    ]
    for kw in ai_keywords:
        pattern = re.compile(
            r'(<li>)(.*?' + re.escape(kw) + r'.*?</li>)',
            re.IGNORECASE,
        )
        html_text = pattern.sub(
            r'\1<span class="ai-highlight">\2</span>',
            html_text,
        )
    html_text = html_text.replace(
        '<span class="ai-highlight"><span class="ai-highlight">',
        '<span class="ai-highlight">',
    ).replace(
        '</span></span>', '</span>',
    )
    return html_text


def _summary_to_html(md_text: str, articles: List[Dict] = None,
                     mark_ai: bool = False) -> str:
    """将Markdown总结转为HTML，并注入可点击的溯源链接"""
    if not md_text:
        return ""

    import re

    lines = md_text.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        if line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h2>{line[3:]}</h2>')

        elif line.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h3>{line[4:]}</h3>')

        elif line.startswith("#### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h4>{line[5:]}</h4>')

        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = line[2:]
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(
                r'(https?://[^\s]+)',
                r'<a href="\1" target="_blank" rel="noopener">\1</a>',
                content,
            )
            if mark_ai:
                html_lines.append(f'<li><span class="ai-check">{content}</span></li>')
            else:
                html_lines.append(f'<li>{content}</li>')

        elif line.startswith("1. ") or line.startswith("2. "):
            if not in_list:
                html_lines.append("<ol>")
                in_list = True
            content = re.sub(r'^\d+\.\s*', '', line)
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(
                r'(https?://[^\s]+)',
                r'<a href="\1" target="_blank" rel="noopener">\1</a>',
                content,
            )
            html_lines.append(f'<li>{content}</li>')

        elif line.startswith("> "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line[2:])
            html_lines.append(f'<blockquote>{content}</blockquote>')

        elif line.strip() == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<hr>")

        elif not line.strip():
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br>")

        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            content = re.sub(
                r'(https?://[^\s]+)',
                r'<a href="\1" target="_blank" rel="noopener">\1</a>',
                content,
            )
            html_lines.append(f'<p>{content}</p>')

    if in_list:
        html_lines.append("</ul>")

    result = "\n".join(html_lines)

    # 注入可点击的溯源链接
    if articles:
        result = _inject_source_links(result, articles)

    if mark_ai:
        result = _mark_ai_red(result)

    return result


def generate_political_report(
    summary_text: str,
    articles: List[Dict],
    hangzhou_policy_summary: str = "",
    hangzhou_policy_articles: List[Dict] = None,
) -> Path:
    """生成时政日报HTML"""
    today_str = _chinese_date()
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[datetime.now().weekday()]

    filename = f"{today_str}时政日报.html"
    output_path = MONTH_DIR / filename

    news_html = _summary_to_html(summary_text, articles=articles, mark_ai=True)

    policy_html = ""
    if hangzhou_policy_summary:
        policy_html = f'''
        <div class="section policy-section">
            <h2>杭州市创业扶持政策动态</h2>
            <div class="policy-content">
                {_summary_to_html(hangzhou_policy_summary, articles=hangzhou_policy_articles)}
            </div>
        </div>'''

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{today_str} 时政日报</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
                         "Microsoft YaHei", "Noto Sans SC", sans-serif;
            background: #f5f6fa;
            color: #2d3436;
            line-height: 1.9;
        }}
        .container {{
            max-width: 860px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #8b0000 0%, #cc0000 50%, #ff4444 100%);
            color: white;
            padding: 48px 36px;
            border-radius: 16px;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: "新闻联播";
            position: absolute;
            right: 20px;
            top: 10px;
            font-size: 80px;
            opacity: 0.1;
            font-weight: bold;
            letter-spacing: 8px;
        }}
        .header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 6px; }}
        .header .date {{ font-size: 16px; opacity: 0.9; margin-top: 8px; }}
        .header .subtitle {{ font-size: 13px; opacity: 0.7; margin-top: 4px; }}
        .section {{
            background: white;
            border-radius: 12px;
            padding: 28px 32px;
            margin-bottom: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        }}
        .section h2 {{
            font-size: 20px;
            color: #8b0000;
            border-bottom: 3px solid #cc0000;
            padding-bottom: 10px;
            margin-bottom: 18px;
        }}
        .section h3 {{
            font-size: 16px;
            color: #2d3436;
            margin: 18px 0 10px 0;
            padding-left: 10px;
            border-left: 3px solid #cc0000;
        }}
        .section h4 {{ font-size: 15px; color: #555; margin: 14px 0 8px 0; }}
        .section ul {{ padding-left: 20px; }}
        .section li {{ margin-bottom: 8px; font-size: 15px; }}
        .section li::marker {{ color: #cc0000; }}
        .section p {{ margin-bottom: 10px; font-size: 15px; }}
        .section blockquote {{
            border-left: 4px solid #cc0000; padding: 12px 18px; margin: 12px 0;
            background: #fef2f2; border-radius: 4px; color: #555; font-size: 14px;
        }}
        .section strong {{ color: #2d3436; }}
        .section hr {{ border: none; border-top: 1px solid #eee; margin: 16px 0; }}
        .ai-highlight {{ color: #cc0000; font-weight: bold; }}
        .policy-section {{ border-left: 4px solid #e67e22; }}
        .policy-section h2 {{ color: #e67e22; border-bottom-color: #e67e22; }}
        .policy-content {{ background: #fffaf0; border-radius: 8px; padding: 12px 16px; }}
        .source-link {{
            display: inline-block;
            background: #fef2f2;
            color: #cc0000;
            font-size: 12px;
            padding: 1px 10px;
            border-radius: 10px;
            margin: 0 2px;
            white-space: nowrap;
            text-decoration: none;
            transition: background 0.2s;
        }}
        .source-link:hover {{
            background: #fecaca;
            text-decoration: underline;
        }}
        .source-tag {{
            display: inline-block;
            background: #fef2f2;
            color: #cc0000;
            font-size: 12px;
            padding: 1px 10px;
            border-radius: 10px;
            margin: 0 2px;
            white-space: nowrap;
        }}
        .footer {{
            text-align: center; color: #aaa; font-size: 12px;
            padding: 20px; line-height: 1.8;
        }}
        @media (max-width: 600px) {{
            .container {{ padding: 10px; }}
            .section {{ padding: 16px; }}
            .header {{ padding: 28px 18px; }}
            .header::before {{ font-size: 40px; right: 10px; top: 6px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>时政日报</h1>
            <div class="date">{today_str} {weekday}</div>
            <div class="subtitle">央视新闻 · 人民日报 · 新华社 · 国内权威媒体</div>
        </div>

        <div class="section">
            {news_html}
        </div>

        {policy_html}

        <div class="footer">
            <p>由人工智能自动生成 · 仅供参考 · {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
            <p>数据来源：央视新闻 · 人民日报 · 新华社 · 环球网 · 中国新闻网 · 央广网 · 光明网 等</p>
        </div>
    </div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"时政日报已生成: {output_path}")
    return output_path


def generate_industry_report(
    summary_text: str,
    articles: List[Dict],
) -> Path:
    """生成AI行业日报HTML"""
    today_str = _chinese_date()
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[datetime.now().weekday()]

    filename = f"{today_str}AI日报.html"
    output_path = MONTH_DIR / filename

    news_html = _summary_to_html(summary_text, articles=articles)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{today_str} AI日报</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
                         "Microsoft YaHei", "Noto Sans SC", sans-serif;
            background: #f0f2f5;
            color: #1a1a2e;
            line-height: 1.9;
        }}
        .container {{ max-width: 860px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: white; padding: 48px 36px; border-radius: 16px;
            margin-bottom: 24px; position: relative; overflow: hidden;
        }}
        .header::after {{
            content: ""; position: absolute; top: -50%; right: -20%;
            width: 300px; height: 300px;
            background: radial-gradient(circle, rgba(102,126,234,0.15) 0%, transparent 70%);
            border-radius: 50%;
        }}
        .header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 6px; position: relative; z-index: 1; }}
        .header .date {{ font-size: 16px; opacity: 0.8; margin-top: 8px; position: relative; z-index: 1; }}
        .header .subtitle {{ font-size: 13px; opacity: 0.6; margin-top: 4px; position: relative; z-index: 1; }}
        .section {{
            background: white; border-radius: 12px; padding: 28px 32px;
            margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        }}
        .section h2 {{
            font-size: 20px; color: #1a1a2e;
            border-bottom: 3px solid #667eea; padding-bottom: 10px; margin-bottom: 18px;
        }}
        .section h3 {{
            font-size: 16px; color: #1a1a2e;
            margin: 18px 0 10px 0; padding-left: 10px; border-left: 3px solid #667eea;
        }}
        .section h4 {{ font-size: 15px; color: #555; margin: 14px 0 8px 0; }}
        .section ul {{ padding-left: 20px; }}
        .section li {{ margin-bottom: 8px; font-size: 15px; }}
        .section li::marker {{ color: #667eea; }}
        .section p {{ margin-bottom: 10px; font-size: 15px; }}
        .section blockquote {{
            border-left: 4px solid #667eea; padding: 12px 18px; margin: 12px 0;
            background: #f8f9ff; border-radius: 4px; color: #555; font-size: 14px;
        }}
        .section strong {{ color: #1a1a2e; }}
        .section hr {{ border: none; border-top: 1px solid #eee; margin: 16px 0; }}
        .source-link {{
            display: inline-block; background: #eef0ff; color: #5b6abf;
            font-size: 12px; padding: 1px 10px; border-radius: 10px;
            margin: 0 2px; white-space: nowrap; text-decoration: none;
            transition: background 0.2s;
        }}
        .source-link:hover {{ background: #d0d5ff; text-decoration: underline; }}
        .source-tag {{
            display: inline-block; background: #eef0ff; color: #5b6abf;
            font-size: 12px; padding: 1px 10px; border-radius: 10px;
            margin: 0 2px; white-space: nowrap;
        }}
        .section-tag {{
            display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2);
            color: white; padding: 2px 12px; border-radius: 12px;
            font-size: 12px; margin-right: 4px;
        }}
        .footer {{ text-align: center; color: #aaa; font-size: 12px; padding: 20px; line-height: 1.8; }}
        @media (max-width: 600px) {{
            .container {{ padding: 10px; }}
            .section {{ padding: 16px; }}
            .header {{ padding: 28px 18px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI 行业日报</h1>
            <div class="date">{today_str} {weekday}</div>
            <div class="subtitle">
                AIGC影视传媒 · 大模型动态 · 行业趋势
                <br>
                <span class="section-tag">AI视频</span>
                <span class="section-tag">AI短剧</span>
                <span class="section-tag">AI广告</span>
                <span class="section-tag">数字人</span>
            </div>
        </div>

        <div class="section">
            {news_html}
        </div>

        <div class="footer">
            <p>由人工智能自动生成 · 仅供行业参考 · {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
            <p>数据来源：TechCrunch · Variety · Hollywood Reporter · 爱范儿 · 36氪 等</p>
        </div>
    </div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"AI日报已生成: {output_path}")
    return output_path
