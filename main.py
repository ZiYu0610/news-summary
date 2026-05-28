#!/usr/bin/env python3
"""AI 新闻日报系统 - 主入口

每天早上9点自动运行，完成以下任务：
1. 采集昨日时政新闻和AIGC行业新闻
2. 使用Claude API进行智能总结
3. 更新行业价格数据并生成走势图
4. 生成HTML格式日报

使用方法：
  python main.py              # 立即运行一次
  python main.py --init-data  # 运行并初始化示例价格数据
  python main.py --serve      # 启动本地HTTP服务查看日报
  python main.py --schedule   # 启动内调度循环
  python main.py --install    # 注册Windows任务计划（需管理员）
"""
import argparse
import logging
import sys
from pathlib import Path

# 确保项目根目录在路径中
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config import (
    SCHEDULE_TIME, REPORTS_DIR,
    CLAUDE_API_KEY,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def run_daily():
    """执行完整的日报生成流程"""
    from collector.news_collector import collect_all, save_news
    from summarizer.summarizer import summarize_all
    from price_tracker.price_tracker import PriceTracker
    from report.report_generator import generate_report

    logger.info("=" * 50)
    logger.info("🚀 开始生成今日新闻日报")
    logger.info("=" * 50)

    # Step 1: 采集新闻
    logger.info("\n📡 [Step 1/4] 采集新闻...")
    try:
        news_data = collect_all(days=2)
        save_news(news_data)
    except Exception as e:
        logger.error(f"新闻采集失败: {e}")
        logger.warning("尝试使用已有缓存数据继续...")
        from collector.news_collector import load_today_news
        news_data = load_today_news()
        if not news_data:
            logger.error("无可用新闻数据，终止")
            return False

    # Step 2: AI总结
    logger.info("\n🤖 [Step 2/4] AI总结新闻...")
    try:
        news_summary = summarize_all(news_data)
    except Exception as e:
        logger.error(f"AI总结失败: {e}")
        # 降级：原始标题列表
        news_summary = {
            "political": "\n".join(
                f"- {a['title']}" for a in news_data.get("political", [])[:15]
            ),
            "industry": "\n".join(
                f"- {a['title']}" for a in news_data.get("industry", [])[:15]
            ),
            "combined": False,
        }

    # Step 3: 价格走势图
    logger.info("\n📊 [Step 3/4] 更新价格数据并生成图表...")
    chart_path = None
    market_analysis = ""
    try:
        tracker = PriceTracker()
        chart_file = REPORTS_DIR / f"price_chart_{Path(__file__).parent.name}.png"
        chart_path = tracker.generate_chart(chart_file)
        market_analysis = tracker.generate_market_analysis()
    except Exception as e:
        logger.warning(f"价格图表生成失败: {e}")

    # Step 4: 生成HTML日报
    logger.info("\n📝 [Step 4/4] 生成日报...")
    try:
        report_path = generate_report(
            news_summary=news_summary,
            chart_path=chart_path,
            market_analysis=market_analysis,
        )
        logger.info(f"\n✅ 日报生成完成！")
        logger.info(f"📄 文件: {report_path}")
        logger.info(f"🔗 打开方式: 浏览器打开此文件即可查看")
        return True
    except Exception as e:
        logger.error(f"日报生成失败: {e}")
        return False


def serve_reports(port: int = 8000):
    """启动本地HTTP服务查看历史日报"""
    import http.server
    import socketserver

    os.chdir(REPORTS_DIR.parent)
    handler = http.server.SimpleHTTPRequestHandler

    logger.info(f"🌐 日报查看服务已启动")
    logger.info(f"📂 报告目录: {REPORTS_DIR}")
    logger.info(f"🔗 访问地址: http://localhost:{port}")
    logger.info("按 Ctrl+C 停止")

    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(
        description="AI 新闻日报系统 - 每日9点自动生成AIGC行业日报"
    )
    parser.add_argument(
        "--init-data", action="store_true",
        help="初始化示例价格数据后运行"
    )
    parser.add_argument(
        "--serve", action="store_true",
        help="启动本地HTTP服务查看日报"
    )
    parser.add_argument(
        "--schedule", action="store_true",
        help="启动内调度循环（每隔30秒检查是否需要执行）"
    )
    parser.add_argument(
        "--install", action="store_true",
        help="注册Windows任务计划程序（需管理员权限）"
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="HTTP服务端口（默认8000）"
    )

    args = parser.parse_args()

    # 检查API Key
    if not CLAUDE_API_KEY:
        logger.warning("⚠️ ANTHROPIC_API_KEY 环境变量未设置")
        logger.warning("AI总结功能将降级为简单标题列表（不经过AI处理）")
        logger.warning("设置方式: $env:ANTHROPIC_API_KEY = 'your-key'")
        logger.warning("或将其添加到系统环境变量中")
        print()

    if args.init_data:
        from price_tracker.price_tracker import PriceTracker
        tracker = PriceTracker()
        tracker.init_sample_data()
        logger.info("示例价格数据已初始化")

    if args.serve:
        import os
        os.chdir(str(REPORTS_DIR.parent))
        from scheduler.scheduler import run_schedule_loop
        run_schedule_loop(run_daily, SCHEDULE_TIME)

    elif args.install:
        from scheduler.scheduler import install_task_scheduler
        install_task_scheduler(BASE_DIR)

    elif args.schedule:
        from scheduler.scheduler import run_schedule_loop
        run_schedule_loop(run_daily, SCHEDULE_TIME)

    else:
        # 默认：立即运行一次
        success = run_daily()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    import os  # 用于serve模式
    main()
