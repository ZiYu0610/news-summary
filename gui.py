#!/usr/bin/env python3
"""AI 新闻日报系统 - 图形界面"""
import logging
import os
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext, messagebox

# ====== 路径处理：支持 PyInstaller 打包模式 ======
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    IS_EXE = True
else:
    BASE_DIR = Path(__file__).parent
    IS_EXE = False

if IS_EXE:
    PROJECT_DIR = Path(sys.executable).parent
else:
    PROJECT_DIR = BASE_DIR

DATA_DIR = PROJECT_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"

# 确保目录存在
for d in [DATA_DIR, REPORTS_DIR, DATA_DIR / "news"]:
    d.mkdir(parents=True, exist_ok=True)


class GUILogHandler(logging.Handler):
    """将日志输出重定向到 tkinter 文本框"""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.after(0, self._append, msg + "\n")

    def _append(self, msg):
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.insert(tk.END, msg)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state=tk.DISABLED)


class NewsDailyGUI:
    """AI 新闻日报系统 主窗口"""

    COLORS = {
        "bg_dark": "#1a1a2e",
        "bg_card": "#ffffff",
        "primary": "#3b82f6",
        "success": "#10b981",
        "purple": "#8b5cf6",
        "orange": "#f59e0b",
        "red": "#ef4444",
        "gray": "#64748b",
        "text_dark": "#1e293b",
        "text_light": "#f8fafc",
        "border": "#e2e8f0",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("AI 新闻日报系统")
        self.root.geometry("880x680")
        self.root.minsize(720, 560)
        self.root.configure(bg=self.COLORS["bg_dark"])

        self._check_api()
        self._build_ui()
        self._setup_logging()

    def _check_api(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

    # ==================== UI 构建 ====================

    def _build_ui(self):
        # -- 顶部横幅 --
        header = tk.Frame(self.root, bg=self.COLORS["bg_dark"], height=90)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🤖 AIGC 行业新闻日报系统",
            fg=self.COLORS["text_light"],
            bg=self.COLORS["bg_dark"],
            font=("Microsoft YaHei", 20, "bold"),
        ).pack(pady=(16, 2))

        api_text = "✅ API 已配置" if self.api_key else "⚠️  API 未配置（将使用降级模式）"
        api_color = "#4ade80" if self.api_key else "#fbbf24"
        tk.Label(
            header,
            text=f"报告目录: {REPORTS_DIR}    |    {api_text}",
            fg=api_color,
            bg=self.COLORS["bg_dark"],
            font=("Microsoft YaHei", 9),
        ).pack()

        # -- 主体 --
        main = tk.Frame(self.root, bg=self.COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 16))
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # 左侧面板
        left = tk.Frame(main, bg=self.COLORS["bg_card"], width=260, relief=tk.FLAT, bd=0)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        left.pack_propagate(False)

        self._build_left_panel(left)

        # 右侧日志面板
        right = tk.Frame(main, bg=self.COLORS["bg_card"])
        right.grid(row=0, column=1, sticky="nsew")
        self._build_right_panel(right)

        # -- 底部状态栏 --
        self._build_statusbar()

    def _build_left_panel(self, parent):
        pad = {"padx": 14, "pady": (14, 4)}

        # 生成日报
        tk.Label(parent, text="🚀  生 成 日 报", font=("Microsoft YaHei", 11, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(**pad)
        for btn in [
            ("📰🤖  全部日报", self.COLORS["primary"], lambda: self._run("all")),
            ("📰  仅时政日报", self.COLORS["success"], lambda: self._run("political")),
            ("🤖  仅AI行业日报", self.COLORS["purple"], lambda: self._run("industry")),
        ]:
            self._btn(parent, *btn)

        # 分隔线
        tk.Frame(parent, bg=self.COLORS["border"], height=1).pack(fill=tk.X, padx=14, pady=10)

        # 查看
        tk.Label(parent, text="📂  查 看", font=("Microsoft YaHei", 11, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(**pad)
        for btn in [
            ("📊  查看最新日报", self.COLORS["gray"], self._open_reports),
            ("📈  价格走势图", self.COLORS["gray"], self._open_chart),
            ("📋  报告目录", self.COLORS["gray"], lambda: os.startfile(str(REPORTS_DIR)) if hasattr(os, 'startfile') else None),
        ]:
            self._btn(parent, *btn)

        # 分隔线
        tk.Frame(parent, bg=self.COLORS["border"], height=1).pack(fill=tk.X, padx=14, pady=10)

        # 其他
        tk.Label(parent, text="⚙️  其 他", font=("Microsoft YaHei", 11, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(**pad)
        for btn in [
            ("🔄  自动调度", self.COLORS["orange"], self._start_schedule),
            ("🌐  HTTP 服务", self.COLORS["orange"], self._start_server),
        ]:
            self._btn(parent, *btn)

    def _btn(self, parent, text, color, command):
        btn = tk.Button(
            parent, text=text, command=command,
            bg=color, fg="white", activebackground=self._lighten(color),
            activeforeground="white", relief=tk.FLAT,
            font=("Microsoft YaHei", 10), padx=12, pady=7,
            cursor="hand2", borderwidth=0,
        )
        btn.pack(fill=tk.X, padx=14, pady=3)
        btn.bind("<Enter>", lambda e, b=btn, c=color: b.configure(bg=self._lighten(c)))
        btn.bind("<Leave>", lambda e, b=btn, c=color: b.configure(bg=c))
        return btn

    def _build_right_panel(self, parent):
        # 标题栏
        title_bar = tk.Frame(parent, bg=self.COLORS["bg_card"])
        title_bar.pack(fill=tk.X, padx=16, pady=(14, 6))

        tk.Label(title_bar, text="📋  运行日志", font=("Microsoft YaHei", 12, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(side=tk.LEFT)

        tk.Button(title_bar, text="清空", command=self._clear_log,
                  font=("Microsoft YaHei", 9), relief=tk.FLAT,
                  bg=self.COLORS["border"], fg=self.COLORS["text_dark"],
                  cursor="hand2").pack(side=tk.RIGHT)

        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#1e1e2e", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            state=tk.DISABLED,
            borderwidth=0,
            highlightthickness=0,
            padx=12, pady=12,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 16))

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=self.COLORS["bg_dark"], height=36)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        tk.Label(bar, text=f"🕐 {now}   |   数据目录: {DATA_DIR}",
                 fg="#94a3b8", bg=self.COLORS["bg_dark"],
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=16)

        self.exit_btn = tk.Button(
            bar, text="退出程序",
            command=self.root.destroy,
            bg=self.COLORS["red"], fg="white",
            activebackground="#dc2626", activeforeground="white",
            relief=tk.FLAT, font=("Microsoft YaHei", 9),
            padx=14, pady=2, cursor="hand2", borderwidth=0,
        )
        self.exit_btn.pack(side=tk.RIGHT, padx=16)

    # ==================== 日志 ====================

    def _setup_logging(self):
        handler = GUILogHandler(self.log_text)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s  %(message)s", "%H:%M:%S"
        ))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        self._log("系统就绪，等待操作...")

    def _log(self, msg, level="info"):
        getattr(logging.getLogger("gui"), level)(msg)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    # ==================== 操作 ====================

    def _run(self, mode):
        labels = {"all": "全部日报", "political": "时政日报", "industry": "AI日报"}
        label = labels.get(mode, "日报")
        self._log(f"{'='*50}")
        self._log(f"  🚀 开始生成 {label} ...")
        self._log(f"{'='*50}")
        threading.Thread(target=self._run_task, args=(mode,), daemon=True).start()

    def _run_task(self, mode):
        try:
            if IS_EXE:
                sys.path.insert(0, str(BASE_DIR))
                from price_tracker.price_tracker import PriceTracker
                PriceTracker().init_sample_data()
                import main as m
                m.run_daily(mode=mode)
            else:
                from main import run_daily as _run
                _run(mode=mode)

            self.root.after(0, lambda: self._log("✅ 生成完成！"))
            self.root.after(500, self._open_reports)
        except Exception as e:
            self.root.after(0, lambda: self._log(f"❌ 错误: {e}"))

    def _open_reports(self):
        opened = False
        for pattern, icon in [("*时政日报.html", "📰"), ("*AI日报.html", "🤖")]:
            files = sorted(REPORTS_DIR.glob(pattern), reverse=True)
            if files:
                webbrowser.open(str(files[0]))
                self._log(f"{icon} 打开: {files[0].name}")
                opened = True
        if not opened:
            self._log("⚠️ 暂无报告")

    def _open_chart(self):
        charts = sorted(REPORTS_DIR.glob("price_chart_*.png"), reverse=True)
        if charts:
            webbrowser.open(str(charts[0]))
            self._log(f"📈 打开: {charts[0].name}")
        else:
            self._log("⚠️ 暂无图表")

    def _start_schedule(self):
        r = messagebox.askyesno(
            "自动调度",
            "自动调度模式将保持窗口运行，\n每天 09:00 自动生成日报。\n\n是否启动？\n（首次运行将立即执行一次）"
        )
        if not r:
            return
        self._log("🔄 启动自动调度模式（每天 09:00）...")
        self._log("📌 首次运行将立即执行一次")

        def loop():
            from scheduler.scheduler import run_schedule_loop
            from main import run_daily
            from config import SCHEDULE_TIME
            run_schedule_loop(run_daily, SCHEDULE_TIME)

        threading.Thread(target=loop, daemon=True).start()

    def _start_server(self):
        self._log("🌐 HTTP 服务启动中: http://localhost:8000/data/reports/")
        webbrowser.open("http://localhost:8000/data/reports/")

        def serve():
            import http.server
            import socketserver
            os.chdir(str(PROJECT_DIR))
            with socketserver.TCPServer(("", 8000),
                                        http.server.SimpleHTTPRequestHandler) as httpd:
                httpd.serve_forever()

        threading.Thread(target=serve, daemon=True).start()

    @staticmethod
    def _lighten(color):
        color = color.lstrip("#")
        r, g, b = int(color[:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r = min(255, int(r * 1.25))
        g = min(255, int(g * 1.25))
        b = min(255, int(b * 1.25))
        return f"#{r:02x}{g:02x}{b:02x}"


if __name__ == "__main__":
    root = tk.Tk()
    NewsDailyGUI(root)
    root.mainloop()
