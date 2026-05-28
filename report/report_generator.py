"""日报报告生成模块
生成时政日报和AI行业日报两个独立HTML报告，带可点击溯源链接。
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import REPORTS_DIR

logger = logging.getLogger(__name__)


def _chinese_date() -> str:
    """返回中文日期格式：2026年5月28日"""
    now = datetime.now()
    return f"{now.year}年{now.month}月{now.day}日"


def _build_sources_section(articles: List[Dict]) -> str:
    """构建可点击的新闻来源列表"""
    if not articles:
        return ""

    # 去重（按链接去重）
    seen = set()
    unique = []
    for a in articles:
        link = a.get("link", "")
        if link and link not in seen:
            seen.add(link)
            unique.append(a)
        elif not link:
            unique.append(a)

    if not unique:
        return ""

    rows = []
    for i, art in enumerate(unique[:30], 1):
        title = art.get("title", "无标题")[:60]
        source = art.get("source", "未知来源")
        link = art.get("link", "")
        if link:
            rows.append(f'''            <tr>
                <td class="src-num">{i}</td>
                <td class="src-title"><a href="{link}" target="_blank" rel="noopener">{title}</a></td>
                <td class="src-source"><span class="source-tag">{source}</span></td>
            </tr>''')
        else:
            rows.append(f'''            <tr>
                <td class="src-num">{i}</td>
                <td class="src-title">{title}</td>
                <td class="src-source"><span class="source-tag">{source}</span></td>
            </tr>''')

    return f'''
        <div class="section sources">
            <h2>📎 新闻来源（点击标题查看原文）</h2>
            <table class="source-table">
                <thead>
                    <tr><th>#</th><th>标题</th><th>来源</th></tr>
                </thead>
                <tbody>
{chr(10).join(rows)}
                </tbody>
            </table>
        </div>'''


def _summary_to_html(md_text: str) -> str:
    """将AI返回的Markdown总结转为HTML（保留链接标记）"""
    if not md_text:
        return ""

    import re

    lines = md_text.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        # 标题
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

        # 列表项
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = line[2:]
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            # 将 [来源：XXX] 转换为高亮标签
            content = re.sub(
                r'\[来源：(.+?)\]',
                r' <span class="source-badge">\1</span>',
                content,
            )
            # 将纯URL转为可点击链接
            content = re.sub(
                r'(https?://[^\s]+)',
                r'<a href="\1" target="_blank" rel="noopener" class="inline-link">\1</a>',
                content,
            )
            html_lines.append(f'<li>{content}</li>')

        elif line.startswith("1. ") or line.startswith("2. "):
            if not in_list:
                html_lines.append("<ol>")
                in_list = True
            content = re.sub(r'^\d+\.\s*', '', line)
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(
                r'\[来源：(.+?)\]',
                r' <span class="source-badge">\1</span>',
                content,
            )
            content = re.sub(
                r'(https?://[^\s]+)',
                r'<a href="\1" target="_blank" rel="noopener" class="inline-link">\1</a>',
                content,
            )
            html_lines.append(f'<li>{content}</li>')

        # 引用
        elif line.startswith("> "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line[2:])
            html_lines.append(f'<blockquote>{content}</blockquote>')

        # 分隔线
        elif line.strip() == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<hr>")

        # 空行
        elif not line.strip():
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br>")

        # 普通段落
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            content = re.sub(
                r'\[来源：(.+?)\]',
                r' <span class="source-badge">\1</span>',
                content,
            )
            content = re.sub(
                r'(https?://[^\s]+)',
                r'<a href="\1" target="_blank" rel="noopener" class="inline-link">\1</a>',
                content,
            )
            html_lines.append(f'<p>{content}</p>')

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def generate_political_report(
    summary_text: str,
    articles: List[Dict],
    output_dir: Optional[Path] = None,
) -> Path:
    """生成时政日报HTML"""
    today_str = _chinese_date()
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[datetime.now().weekday()]

    if output_dir is None:
        output_dir = REPORTS_DIR

    filename = f"{today_str}时政日报.html"
    output_path = output_dir / filename

    news_html = _summary_to_html(summary_text)
    sources_html = _build_sources_section(articles)

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
        /* 头部 */
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 48px 36px;
            border-radius: 16px;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: "📰";
            position: absolute;
            right: 24px;
            top: 12px;
            font-size: 64px;
            opacity: 0.2;
        }}
        .header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 6px; }}
        .header .date {{ font-size: 15px; opacity: 0.85; margin-top: 8px; }}
        .header .subtitle {{ font-size: 13px; opacity: 0.65; margin-top: 4px; }}
        /* 通用区块 */
        .section {{
            background: white;
            border-radius: 12px;
            padding: 28px 32px;
            margin-bottom: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        }}
        .section h2 {{
            font-size: 20px;
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 18px;
        }}
        .section h3 {{
            font-size: 16px;
            color: #2c3e50;
            margin: 18px 0 10px 0;
            padding-left: 10px;
            border-left: 3px solid #3498db;
        }}
        .section h4 {{
            font-size: 15px;
            color: #555;
            margin: 14px 0 8px 0;
        }}
        .section ul {{ padding-left: 20px; }}
        .section li {{ margin-bottom: 8px; font-size: 15px; }}
        .section li::marker {{ color: #3498db; }}
        .section p {{ margin-bottom: 10px; font-size: 15px; }}
        .section blockquote {{
            border-left: 4px solid #3498db;
            padding: 12px 18px;
            margin: 12px 0;
            background: #f8f9ff;
            border-radius: 4px;
            color: #555;
            font-size: 14px;
        }}
        .section strong {{ color: #2c3e50; }}
        .section hr {{ border: none; border-top: 1px solid #eee; margin: 16px 0; }}
        /* 来源标签（内联） */
        .source-badge {{
            display: inline-block;
            background: #e8f4fd;
            color: #2980b9;
            font-size: 12px;
            padding: 1px 10px;
            border-radius: 10px;
            margin: 0 2px;
            white-space: nowrap;
        }}
        .inline-link {{
            color: #3498db;
            text-decoration: underline;
            word-break: break-all;
            font-size: 13px;
        }}
        /* 来源表格 */
        .source-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        .source-table th {{
            text-align: left;
            padding: 8px 12px;
            background: #f0f4f8;
            color: #555;
            font-weight: 600;
            border-bottom: 2px solid #ddd;
        }}
        .source-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
        }}
        .source-table tr:hover td {{ background: #f8f9ff; }}
        .src-num {{ width: 36px; color: #999; text-align: center; }}
        .src-title a {{
            color: #2c3e50;
            text-decoration: none;
        }}
        .src-title a:hover {{
            color: #3498db;
            text-decoration: underline;
        }}
        .src-source {{ width: 100px; text-align: center; }}
        .source-tag {{
            display: inline-block;
            background: #e8f4fd;
            color: #2980b9;
            font-size: 12px;
            padding: 2px 10px;
            border-radius: 10px;
        }}
        /* 脚注 */
        .footer {{
            text-align: center;
            color: #aaa;
            font-size: 12px;
            padding: 20px;
            line-height: 1.8;
        }}
        .footer a {{ color: #3498db; text-decoration: none; }}
        @media (max-width: 600px) {{
            .container {{ padding: 10px; }}
            .section {{ padding: 16px; }}
            .header {{ padding: 28px 18px; }}
            .header::before {{ font-size: 40px; right: 12px; top: 8px; }}
            .source-table {{ font-size: 13px; }}
            .src-source {{ width: 70px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 时政日报</h1>
            <div class="date">{today_str} {weekday}</div>
            <div class="subtitle">海内外权威媒体 · 时政要闻汇总</div>
        </div>

        <div class="section">
            {news_html}
        </div>

        {sources_html}

        <div class="footer">
            <p>由 AI 自动生成 · 仅供参考 · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>数据来源: 新华社 · 人民日报 · 央视新闻 · BBC中文 · FT中文 等</p>
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
    chart_path: Optional[Path] = None,
    market_analysis: str = "",
    output_dir: Optional[Path] = None,
) -> Path:
    """生成AI行业日报HTML"""
    today_str = _chinese_date()
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[datetime.now().weekday()]

    if output_dir is None:
        output_dir = REPORTS_DIR

    filename = f"{today_str}AI日报.html"
    output_path = output_dir / filename

    news_html = _summary_to_html(summary_text)

    # 图表
    chart_html = ""
    if chart_path and chart_path.exists():
        try:
            chart_rel = chart_path.relative_to(output_dir.parent).as_posix()
        except ValueError:
            import shutil
            dest = output_dir / chart_path.name
            shutil.copy2(chart_path, dest)
            chart_rel = chart_path.name

        chart_html = f'''
        <div class="section">
            <h2>📊 行业市场价格走势</h2>
            <div class="chart-container">
                <img src="../{chart_rel}" alt="价格走势图"
                     style="width:100%; max-width:1200px; border-radius:8px;">
            </div>
        </div>'''

    # 市场分析
    market_html = ""
    if market_analysis:
        market_html = f'''
        <div class="section">
            {_summary_to_html(market_analysis)}
        </div>'''

    sources_html = _build_sources_section(articles)

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
        .container {{
            max-width: 860px;
            margin: 0 auto;
            padding: 20px;
        }}
        /* 头部 - 科技感渐变 */
        .header {{
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: white;
            padding: 48px 36px;
            border-radius: 16px;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: "🤖";
            position: absolute;
            right: 24px;
            top: 12px;
            font-size: 64px;
            opacity: 0.15;
        }}
        .header::after {{
            content: "";
            position: absolute;
            top: -50%;
            right: -20%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(102,126,234,0.15) 0%, transparent 70%);
            border-radius: 50%;
        }}
        .header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 6px; position: relative; z-index: 1; }}
        .header .date {{ font-size: 15px; opacity: 0.8; margin-top: 8px; position: relative; z-index: 1; }}
        .header .subtitle {{ font-size: 13px; opacity: 0.6; margin-top: 4px; position: relative; z-index: 1; }}
        /* 通用区块 */
        .section {{
            background: white;
            border-radius: 12px;
            padding: 28px 32px;
            margin-bottom: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        }}
        .section h2 {{
            font-size: 20px;
            color: #1a1a2e;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 18px;
        }}
        .section h3 {{
            font-size: 16px;
            color: #1a1a2e;
            margin: 18px 0 10px 0;
            padding-left: 10px;
            border-left: 3px solid #667eea;
        }}
        .section h4 {{
            font-size: 15px;
            color: #555;
            margin: 14px 0 8px 0;
        }}
        .section ul {{ padding-left: 20px; }}
        .section li {{ margin-bottom: 8px; font-size: 15px; }}
        .section li::marker {{ color: #667eea; }}
        .section p {{ margin-bottom: 10px; font-size: 15px; }}
        .section blockquote {{
            border-left: 4px solid #667eea;
            padding: 12px 18px;
            margin: 12px 0;
            background: #f8f9ff;
            border-radius: 4px;
            color: #555;
            font-size: 14px;
        }}
        .section strong {{ color: #1a1a2e; }}
        .section hr {{ border: none; border-top: 1px solid #eee; margin: 16px 0; }}
        .source-badge {{
            display: inline-block;
            background: #eef0ff;
            color: #5b6abf;
            font-size: 12px;
            padding: 1px 10px;
            border-radius: 10px;
            margin: 0 2px;
            white-space: nowrap;
        }}
        .inline-link {{
            color: #667eea;
            text-decoration: underline;
            word-break: break-all;
            font-size: 13px;
        }}
        /* 图表 */
        .chart-container {{
            margin: 16px 0;
            text-align: center;
        }}
        /* 来源表格 */
        .source-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        .source-table th {{
            text-align: left;
            padding: 8px 12px;
            background: #f0f2ff;
            color: #555;
            font-weight: 600;
            border-bottom: 2px solid #ddd;
        }}
        .source-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
        }}
        .source-table tr:hover td {{ background: #f8f9ff; }}
        .src-num {{ width: 36px; color: #999; text-align: center; }}
        .src-title a {{
            color: #1a1a2e;
            text-decoration: none;
        }}
        .src-title a:hover {{
            color: #667eea;
            text-decoration: underline;
        }}
        .src-source {{ width: 120px; text-align: center; }}
        .source-tag {{
            display: inline-block;
            background: #eef0ff;
            color: #5b6abf;
            font-size: 12px;
            padding: 2px 10px;
            border-radius: 10px;
        }}
        /* 洞察框 */
        .insight-box {{
            background: linear-gradient(135deg, #fff3e0, #ffe0b2);
            border-radius: 8px;
            padding: 16px 20px;
            margin: 12px 0;
            border-left: 4px solid #ff9800;
        }}
        .insight-box p {{ margin-bottom: 4px; color: #e65100; }}
        /* 标签 */
        .section-tag {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 2px 12px;
            border-radius: 12px;
            font-size: 12px;
            margin-right: 4px;
        }}
        /* 脚注 */
        .footer {{
            text-align: center;
            color: #aaa;
            font-size: 12px;
            padding: 20px;
            line-height: 1.8;
        }}
        .footer a {{ color: #667eea; text-decoration: none; }}
        @media (max-width: 600px) {{
            .container {{ padding: 10px; }}
            .section {{ padding: 16px; }}
            .header {{ padding: 28px 18px; }}
            .header::before {{ font-size: 40px; right: 12px; top: 8px; }}
            .source-table {{ font-size: 13px; }}
            .src-source {{ width: 80px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI 行业日报</h1>
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

        {chart_html}

        {market_html}

        {sources_html}

        <div class="footer">
            <p>由 AI 自动生成 · 仅供行业参考 · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>数据来源: TechCrunch · Variety · Hollywood Reporter · 爱范儿 · 36氪 等</p>
        </div>
    </div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"AI日报已生成: {output_path}")
    return output_path
