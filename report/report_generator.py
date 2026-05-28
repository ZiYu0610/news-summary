"""日报报告生成模块
将新闻总结、价格图表整合为美观的HTML日报。
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from config import REPORTS_DIR

logger = logging.getLogger(__name__)


def generate_report(
    news_summary: Dict[str, str],
    chart_path: Optional[Path] = None,
    market_analysis: str = "",
    output_path: Optional[Path] = None,
) -> Path:
    """生成HTML日报

    Args:
        news_summary: 新闻总结数据，格式: {"political": "...", "industry": "...", "combined": bool}
        chart_path: 价格走势图路径（可选）
        market_analysis: 市场价格分析文本（可选）
        output_path: 输出路径，默认自动生成

    Returns:
        生成的HTML文件路径
    """
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[today.weekday()]

    if output_path is None:
        output_path = REPORTS_DIR / f"daily_report_{today.strftime('%Y%m%d')}.html"

    # 处理新闻内容
    is_combined = news_summary.get("combined", False)

    if is_combined and news_summary.get("political"):
        # 综合报告模式
        news_content = _md_to_html(news_summary["political"])
    else:
        political_content = _md_to_html(news_summary.get("political", ""))
        industry_content = _md_to_html(news_summary.get("industry", ""))
        news_content = political_content + "\n" + industry_content

    # 处理图表
    chart_html = ""
    chart_rel_path = ""
    if chart_path and chart_path.exists():
        # 计算相对于报告目录的路径
        try:
            chart_rel_path = chart_path.relative_to(REPORTS_DIR.parent).as_posix()
        except ValueError:
            # 如果不在项目目录内，复制到报告目录
            import shutil
            dest = REPORTS_DIR / chart_path.name
            shutil.copy2(chart_path, dest)
            chart_rel_path = chart_path.name

        chart_html = f"""
        <div class="section">
            <h2>📊 行业市场价格走势</h2>
            <div class="chart-container">
                <img src="../{chart_rel_path}" alt="价格走势图"
                     style="width:100%; max-width:1200px; border-radius:8px;">
            </div>
        </div>
        """

    # 市场价格分析
    market_html = ""
    if market_analysis:
        market_content = _md_to_html(market_analysis)
        market_html = f"""
        <div class="section">
            {market_content}
        </div>
        """

    # 构建完整HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{date_str} AIGC行业新闻日报</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                         "Microsoft YaHei", "Helvetica Neue", sans-serif;
            background: #f0f2f5;
            color: #333;
            line-height: 1.8;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            border-radius: 16px;
            margin-bottom: 24px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header .subtitle {{ font-size: 14px; opacity: 0.85; }}
        .header .date {{ font-size: 16px; margin-top: 12px; opacity: 0.9; }}
        .section {{
            background: white;
            border-radius: 12px;
            padding: 28px 30px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
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
            color: #444;
            margin: 16px 0 8px 0;
            padding-left: 8px;
            border-left: 3px solid #764ba2;
        }}
        .section ul {{ padding-left: 20px; }}
        .section li {{ margin-bottom: 6px; }}
        .section p {{ margin-bottom: 10px; }}
        .section blockquote {{
            border-left: 4px solid #667eea;
            padding: 10px 16px;
            margin: 12px 0;
            background: #f8f9ff;
            border-radius: 4px;
            color: #555;
            font-size: 14px;
        }}
        .section strong {{ color: #1a1a2e; }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            padding: 20px;
        }}
        .chart-container {{
            margin: 16px 0;
            text-align: center;
        }}
        .tag {{
            display: inline-block;
            background: #e8eaff;
            color: #667eea;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            margin-right: 4px;
        }}
        .insight-box {{
            background: linear-gradient(135deg, #fff3e0, #ffe0b2);
            border-radius: 8px;
            padding: 16px 20px;
            margin: 12px 0;
            border-left: 4px solid #ff9800;
        }}
        .insight-box p {{ margin-bottom: 4px; color: #e65100; }}
        @media (max-width: 600px) {{
            .container {{ padding: 10px; }}
            .section {{ padding: 16px; }}
            .header {{ padding: 24px 16px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AIGC 行业新闻日报</h1>
            <div class="date">{date_str} {weekday}</div>
            <div class="subtitle">
                覆盖时政要闻 · AIGC行业动态 · 市场价格走势
                <br>
                <span class="tag">AI漫剧短剧</span>
                <span class="tag">AI广告</span>
                <span class="tag">AI宣传片</span>
            </div>
        </div>

        <div class="section">
            {news_content}
        </div>

        {chart_html}

        {market_html}

        <div class="footer">
            <p>由 AI 自动生成 · 仅供行业参考 · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>数据来源: 公开RSS/新闻源 · 价格数据为行业估算</p>
        </div>
    </div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"日报已生成: {output_path}")

    return output_path


def _md_to_html(md_text: str) -> str:
    """简单的Markdown到HTML转换（处理日报格式）"""
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
            # 处理加粗
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f'<li>{content}</li>')

        elif line.startswith("1. ") or line.startswith("2. "):
            if not in_list:
                html_lines.append("<ol>")
                in_list = True
            content = re.sub(r'^\d+\.\s*', '', line)
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
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
            # 检查是否是启示框
            if "启示" in content or "洞察" in content:
                html_lines.append(f'<p><strong>{content}</strong></p>')
            else:
                html_lines.append(f'<p>{content}</p>')

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)
