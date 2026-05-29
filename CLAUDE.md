# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A local news summary system for AIGC industry (AI漫剧短剧, AI广告, AI宣传片). It collects political + AIGC industry news daily, generates HTML reports with AI summaries, and tracks AIGC market price trends with matplotlib charts. Ships as both Python source and a PyInstaller-packaged EXE.

## Architecture

```
launcher.py          → Entry point (delegates to gui.py or main.py)
main.py              → CLI: python main.py [--init-data] [--chart]
gui.py               → tkinter GUI (880x680, login → main interface)
config.py            → API keys, news sources, price categories

collector/           → News collection (RSS + web scraping)
  news_collector.py  → fetch_rss(), fetch_web(), deduplicate(), collect_all()

summarizer/          → AI summarization (Anthropic / OpenAI-compatible API)
  summarizer.py      → ClaudeClient, summarize_political(), summarize_industry()

report/              → HTML report generation
  report_generator.py → generate_political_report(), generate_industry_report()

price_tracker/       → AIGC market price tracking
  price_tracker.py   → PriceTracker class, matplotlib charts, market analysis

scheduler/           → Windows Task Scheduler + schedule library
  scheduler.py       → generate_task_xml(), run_schedule_loop()

system/              → Auth & persistence
  database.py        → SQLite (users, articles, reports, sessions, price_records)
  login_dialog.py    → tkinter LoginDialog (login/register tabs, auto-login)
```

## Data Flow

1. **Collect** → collector/news_collector.py (10 political web sources + AIGC RSS + policy/platform web scraping)
2. **Summarize** → summarizer/summarizer.py (DeepSeek/Claude API converts articles to structured summaries)
3. **Generate** → report/report_generator.py (produces HTML with source tracing via `_inject_source_links()`)
4. **Store** → SQLite via system/database.py (news_articles, daily_reports, price_records, login_sessions, users)

## Key Configuration (config.py)

- API keys read from env vars `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`, overridable via `data/settings.json`
- 10 political news sources (央视新闻, 人民日报, 新华社, etc.)
- 7 AIGC RSS feeds + 10 web scrape sources (政策监管, 平台, 行业媒体)
- 6 price categories (AI视频生成, AI图片生成, AI语音合成, AI短剧制作, AI广告制作, 数字人定制)
- DeepSeek endpoint configured as default: `api.deepseek.com/anthropic`

## GUI Entry Points

```python
# Login required → launches main GUI
python launcher.py          # shows LoginDialog first, then NewsDailyGUI
# or directly:
python gui.py               # same flow via launch_app()
```

## CLI Commands

```powershell
# Generate today's report
python main.py              # political + industry
python main.py --init-data  # with sample price data

# Price chart only
python main.py --chart

# Run daily (via batch file)
.\run_daily.bat
```

## External Site Logins (Playwright)

抖音创作者中心, 巨量引擎, 抖音电商学习中心 require browser-based login via Playwright. Session cookies are persisted in SQLite `login_sessions` table. The GUI has sidebar buttons under "站点登录" for each site.

## Report Source Tracing

`report/report_generator.py:_inject_source_links()` uses 3-tier matching:
1. `[#N]` number match (preferred)
2. Paragraph keyword overlap with article titles
3. Database source_mappings fallback

## Database

SQLite file at `data/news_summary.db`. Tables: news_articles, daily_reports, price_records, source_mappings, login_sessions, api_configs, users, auto_login_tokens. Password hashed with SHA256 + salt "NewsSummary2024!".

## EXE Build

```powershell
pyinstaller AI新闻日报.spec
```

The spec file includes all subpackages as datas. Output: `dist/AI新闻日报.exe`.

## Prompt Structure

- `POLITICAL_SUMMARY_SYSTEM`: 18-22 items, 5+ must be [AI相关] tagged, strict dedup
- `INDUSTRY_SUMMARY_SYSTEM`: AIGC-focused, strict `#N` numbering for source tracing
- Both require `[来源：XXX #N]` format at end of each summary item

## Price Tracking

- Data file: `data/prices.json`
- Chart output: `data/reports/{YYYY年MM月}/价格走势图_{YYYYMMDD}.png`
- 6 categories predefined, records stored in both JSON and SQLite
