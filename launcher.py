#!/usr/bin/env python3
"""新闻日报系统 - 桌面启动器
提供交互式菜单，支持一键运行、调度、查看报告等功能。
"""
import os
import sys
import subprocess
import webbrowser
from pathlib import Path


# ====== 路径处理：支持 PyInstaller 打包模式 ======
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    BASE_DIR = Path(sys._MEIPASS)
    IS_EXE = True
else:
    BASE_DIR = Path(__file__).parent
    IS_EXE = False

# 项目根目录（数据文件所在位置 = exe同目录/data）
if IS_EXE:
    PROJECT_DIR = Path(sys.executable).parent
else:
    PROJECT_DIR = BASE_DIR

DATA_DIR = PROJECT_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"


def ensure_dirs():
    """确保数据目录存在"""
    for d in [DATA_DIR, REPORTS_DIR, DATA_DIR / "news"]:
        d.mkdir(parents=True, exist_ok=True)


def check_api_key():
    """检查API Key是否可用"""
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    return bool(key)


def print_banner():
    """打印启动横幅"""
    print("""
    ╔══════════════════════════════════════════╗
    ║        🤖 AIGC 行业新闻日报系统          ║
    ║    每日时政 + AIGC行业新闻自动总结       ║
    ╚══════════════════════════════════════════╝
    """)


def print_menu():
    """打印主菜单"""
    api_status = "✅ 已配置" if check_api_key() else "⚠️  未配置（将使用降级模式）"
    print(f"  API状态: {api_status}")
    print(f"  报告目录: {REPORTS_DIR}")
    print()
    print("  ═══════════════════════════════════")
    print("  ║      🚀 生 成                     ║")
    print("  ═══════════════════════════════════")
    print("  1) 📰🤖 全部日报（时政+AI）")
    print("  2) 📰   仅时政日报")
    print("  3) 🤖   仅AI行业日报")
    print("  ═══════════════════════════════════")
    print("  ║      📂 查 看                     ║")
    print("  ═══════════════════════════════════")
    print("  4) 📊 查看最新日报")
    print("  5) 📈 查看价格走势图")
    print("  6) 🔄 每日自动调度模式（保持窗口打开）")
    print("  7) 🌐 启动HTTP报告服务器")
    print("  8) 📋 打开报告目录")
    print("  9) ❓ 使用说明")
    print("  0) 退出")
    print("  ═══════════════════════════════════")


def run_daily(mode="all"):
    """立即运行日报生成

    Args:
        mode: "all" 时政+AI, "political" 仅时政, "industry" 仅AI
    """
    mode_names = {"all": "今日新闻日报", "political": "时政日报", "industry": "AI行业日报"}
    name = mode_names.get(mode, "今日新闻日报")
    print("\n" + "=" * 50)
    print(f"  🚀 开始生成{name}...")
    print("=" * 50 + "\n")

    if IS_EXE:
        sys.path.insert(0, str(BASE_DIR))
        try:
            from price_tracker.price_tracker import PriceTracker
            tracker = PriceTracker()
            tracker.init_sample_data()
            import main
            result = main.run_daily(mode=mode)
            return result
        except Exception as e:
            print(f"[错误] 运行失败: {e}")
            return False
    else:
        from main import run_daily as _run
        return _run(mode=mode)


def open_latest_report():
    """打开最新的时政日报和AI日报"""
    if not REPORTS_DIR.exists():
        print("\n⚠️  暂无报告，请先生成")
        return

    opened = False
    # 打开最新的时政日报
    political = sorted(REPORTS_DIR.glob("*时政日报.html"), reverse=True)
    if political:
        print(f"\n📰 打开: {political[0].name}")
        webbrowser.open(str(political[0]))
        opened = True

    # 打开最新的AI日报
    industry = sorted(REPORTS_DIR.glob("*AI日报.html"), reverse=True)
    if industry:
        print(f"🤖 打开: {industry[0].name}")
        webbrowser.open(str(industry[0]))
        opened = True

    if not opened:
        print("\n⚠️  暂无报告，请先生成")


def open_price_chart():
    """打开价格走势图"""
    if not REPORTS_DIR.exists():
        print("\n⚠️  暂无图表，请先生成")
        return

    charts = sorted(REPORTS_DIR.glob("price_chart_*.png"), reverse=True)
    if not charts:
        print("\n⚠️  暂无图表，请先生成")
        return

    latest = charts[0]
    print(f"\n📊 打开: {latest.name}")
    webbrowser.open(str(latest))


def start_schedule():
    """启动调度模式"""
    print("\n" + "=" * 50)
    print("  🔄 调度模式已启动（每天 09:00 自动运行）")
    print("  首次运行将立即执行一次...")
    print("  按 Ctrl+C 停止")
    print("=" * 50 + "\n")

    if IS_EXE:
        subprocess.run(
            [sys.executable, str(BASE_DIR / "main.py"), "--schedule"],
            cwd=str(PROJECT_DIR),
        )
    else:
        from scheduler.scheduler import run_schedule_loop
        from main import run_daily
        from config import SCHEDULE_TIME
        run_schedule_loop(run_daily, SCHEDULE_TIME)


def start_server():
    """启动HTTP服务"""
    import http.server
    import socketserver

    port = 8000
    os.chdir(str(PROJECT_DIR))

    print(f"\n🌐 HTTP服务已启动")
    print(f"📂 报告地址: http://localhost:{port}/data/reports/")
    print(f"按 Ctrl+C 停止\n")

    webbrowser.open(f"http://localhost:{port}/data/reports/")

    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()


def open_report_folder():
    """打开报告目录"""
    ensure_dirs()
    os.startfile(str(REPORTS_DIR))


def show_help():
    """显示使用说明"""
    print("""
    ══════════════════════════════════════════
    📖 使用说明
    ══════════════════════════════════════════

    🔑 API密钥配置
    本系统需要 Anthropic API (兼容DeepSeek) 密钥。
    已自动使用系统环境变量中的密钥。
    如未配置，总结功能将降级为标题列表模式。

    📡 新闻来源
    时政: 新华社, 人民日报, 央视新闻联播, BBC中文, FT中文,
          环球网, 中国新闻网, Solidot, Reuters
    AI行业: TechCrunch, Variety, Hollywood Reporter, 爱范儿,
            ArsTechnica, 36氪AI, 虎嗅AI, 广电总局, 1905电影网

    📊 价格追踪
    支持6个AIGC品类价格走势追踪：
      - AI视频生成 (元/秒)
      - AI图片生成 (元/张)
      - AI语音合成 (元/千字)
      - AI短剧制作 (万元/部)
      - AI广告制作 (万元/条)
      - 数字人定制 (万元/个)
    价格数据保存在 data/prices.json，可手动编辑。

    📄 双报告模式
    每次运行自动生成两份独立日报：
      - 时政日报 — 海内外权威时政要闻，带可点击溯源链接
      - AI日报 — AIGC影视传媒行业动态，含价格走势图表
    文件名格式: "2026年5月28日时政日报.html"（每天新建，不覆盖）

    ⏰ 每日自动运行
    方式1: 选"4) 每日自动调度" — 保持窗口打开即可
    方式2: 用Windows任务计划程序设置每天9:00执行
           → 在项目目录执行: python main.py --install

    💾 数据位置
    日报: data/reports/
    新闻缓存: data/news/
    价格数据: data/prices.json
    """)


def main():
    ensure_dirs()

    while True:
        print_banner()
        print_menu()
        choice = input("\n  请输入选项 [0-9]: ").strip()

        if choice == "1":
            print("\n" + "-" * 50)
            success = run_daily("all")
            print("-" * 50)
            if success:
                print("\n  ✅ 日报生成完成！正在打开...")
                open_latest_report()
            print("\n  按回车键返回菜单...", end="")
            input()

        elif choice == "2":
            print("\n" + "-" * 50)
            success = run_daily("political")
            print("-" * 50)
            if success:
                political = sorted(REPORTS_DIR.glob("*时政日报.html"), reverse=True)
                if political:
                    print(f"\n  ✅ 时政日报生成完成！正在打开...")
                    webbrowser.open(str(political[0]))
            print("\n  按回车键返回菜单...", end="")
            input()

        elif choice == "3":
            print("\n" + "-" * 50)
            success = run_daily("industry")
            print("-" * 50)
            if success:
                industry = sorted(REPORTS_DIR.glob("*AI日报.html"), reverse=True)
                if industry:
                    print(f"\n  ✅ AI日报生成完成！正在打开...")
                    webbrowser.open(str(industry[0]))
            print("\n  按回车键返回菜单...", end="")
            input()

        elif choice == "4":
            open_latest_report()
            print("\n  按回车键返回菜单...", end="")
            input()

        elif choice == "5":
            open_price_chart()
            print("\n  按回车键返回菜单...", end="")
            input()

        elif choice == "6":
            start_schedule()
            print("\n  调度已停止。按回车键返回菜单...", end="")
            input()

        elif choice == "7":
            start_server()

        elif choice == "8":
            open_report_folder()
            print("\n  按回车键返回菜单...", end="")
            input()

        elif choice == "9":
            show_help()
            print("\n  按回车键返回菜单...", end="")
            input()

        elif choice == "0":
            print("\n  感谢使用，再见！\n")
            sys.exit(0)

        else:
            print("\n  ❌ 无效选项，请重新选择")
            import time
            time.sleep(1)


if __name__ == "__main__":
    main()
