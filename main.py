#!/usr/bin/env python3
"""AI 新闻日报系统 - 主入口

使用方法：
  python main.py              # 生成时政日报和AI日报
  python main.py --init-data  # 初始化示例价格数据后生成
"""
import argparse
import logging
import sys
from pathlib import Path

# 确保项目根目录在路径中
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config import CLAUDE_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def run_daily(mode: str = "all"):
    """执行日报生成流程

    Args:
        mode: "all" 时政+AI, "political" 仅时政, "industry" 仅AI
    """
    from collector.news_collector import collect_all, save_news
    from summarizer.summarizer import summarize_political, summarize_industry

    mode_label = {"all": "时政+AI", "political": "时政", "industry": "AI"}
    label = mode_label.get(mode, "时政+AI")

    logger.info("=" * 50)
    logger.info(f"开始生成今日{label}日报")
    logger.info("=" * 50)

    # Step 1: 采集新闻
    logger.info("第一步：采集新闻...")
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

    political_articles = news_data.get("political", [])
    industry_articles = news_data.get("industry", [])
    competition_articles = news_data.get("competition", [])

    # Step 2: AI总结
    logger.info("第二步：人工智能总结新闻...")

    political_summary = ""
    industry_summary = ""

    if mode in ("all", "political"):
        try:
            political_summary = summarize_political(political_articles)
        except Exception as e:
            logger.error(f"时政新闻AI总结失败: {e}")
            political_summary = "\n".join(
                f"- {a['title']}" for a in political_articles[:15]
            )

    if mode in ("all", "industry"):
        try:
            industry_summary = summarize_industry(industry_articles, competition_articles)
        except Exception as e:
            logger.error(f"行业新闻AI总结失败: {e}")
            industry_summary = "\n".join(
                f"- {a['title']}" for a in industry_articles[:15]
            )

    # Step 3: 生成HTML日报
    logger.info("第三步：生成日报...")

    from report.report_generator import generate_political_report, generate_industry_report

    results = []

    if mode in ("all", "political") and political_summary:
        try:
            path = generate_political_report(
                summary_text=political_summary,
                articles=political_articles,
            )
            logger.info(f"时政日报: {path}")
            results.append(("political", path))
        except Exception as e:
            logger.error(f"时政日报生成失败: {e}")

    if mode in ("all", "industry") and industry_summary:
        try:
            path = generate_industry_report(
                summary_text=industry_summary,
                articles=industry_articles,
            )
            logger.info(f"AI日报: {path}")
            results.append(("industry", path))
        except Exception as e:
            logger.error(f"AI日报生成失败: {e}")

    if results:
        logger.info(f"生成完成！共生成 {len(results)} 份报告")
        for t, p in results:
            logger.info(f"   {p}")
        return True
    else:
        logger.error("未生成任何报告")
        return False


def generate_chart():
    """单独生成价格走势图"""
    from price_tracker.price_tracker import PriceTracker
    from config import MONTH_DIR, REPORTS_DIR

    logger.info("开始生成价格走势图...")
    try:
        tracker = PriceTracker()
        chart_file = MONTH_DIR / f"价格走势图_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.png"
        chart_path = tracker.generate_chart(chart_file)
        market_analysis = tracker.generate_market_analysis()
        logger.info(f"价格走势图已生成: {chart_path}")
        if market_analysis:
            # 保存分析文本到同目录
            analysis_file = MONTH_DIR / f"市场价格分析_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.txt"
            analysis_file.write_text(market_analysis, encoding="utf-8")
            logger.info(f"市场价格分析已保存: {analysis_file}")
        return chart_path
    except Exception as e:
        logger.error(f"价格走势图生成失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="AI 新闻日报系统"
    )
    parser.add_argument(
        "--init-data", action="store_true",
        help="初始化示例价格数据"
    )
    parser.add_argument(
        "--chart", action="store_true",
        help="仅生成价格走势图"
    )

    args = parser.parse_args()

    if not CLAUDE_API_KEY:
        logger.warning("ANTHROPIC_API_KEY 环境变量未设置，将使用降级模式")

    if args.init_data:
        from price_tracker.price_tracker import PriceTracker
        tracker = PriceTracker()
        tracker.init_sample_data()
        logger.info("示例价格数据已初始化")

    if args.chart:
        generate_chart()
        return

    if not args.init_data:
        success = run_daily()
        sys.exit(0 if success else 1)


if __name__ == "__main__":

    main()
