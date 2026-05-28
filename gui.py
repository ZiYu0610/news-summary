#!/usr/bin/env python3
"""AI 新闻日报系统 - 图形界面"""
import json
import logging
import os
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk

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

# 确保能导入项目模块（PyInstaller 环境下需要）
sys.path.insert(0, str(BASE_DIR))

DATA_DIR = PROJECT_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"
MONTH_DIR = REPORTS_DIR / datetime.now().strftime("%Y年%m月")

# 确保目录存在
for d in [DATA_DIR, REPORTS_DIR, MONTH_DIR, DATA_DIR / "news"]:
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
        "red": "#cc0000",
        "orange": "#f59e0b",
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
        # 启动后异步验证API连接
        threading.Thread(target=self._verify_api_connection, daemon=True).start()

    def _check_api(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        # 同时从本地配置读取
        sf = DATA_DIR / "settings.json"
        if not self.api_key and sf.exists():
            try:
                s = json.loads(sf.read_text(encoding="utf-8"))
                self.api_key = s.get("api_key", "")
            except Exception:
                pass

    def _verify_api_connection(self):
        """启动后异步验证API连接"""
        if not self.api_key:
            self.root.after(0, lambda: self._log("API 未配置，请点击底部\"设置\"按钮进行配置"))
            return

        settings_path = DATA_DIR / "settings.json"
        base_url = "https://api.deepseek.com"
        user_model = "deepseek-chat"
        if settings_path.exists():
            try:
                s = json.loads(settings_path.read_text(encoding="utf-8"))
                if s.get("base_url"):
                    base_url = s["base_url"]
                if s.get("model"):
                    user_model = s["model"]
            except Exception:
                pass

        base_url = base_url.rstrip("/")
        self.root.after(0, lambda: self._log(f"正在验证 API 连接（{base_url}）..."))

        import httpx

        # 第一步：验证 API 地址和密钥是否有效（列出模型）
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["id"] for m in data.get("data", []) if "id" in m]
                    if models:
                        self.root.after(0, lambda: self._log(f"API 连接成功，可用模型: {', '.join(models[:5])}..."))
                    else:
                        self.root.after(0, lambda: self._log("API 连接成功（地址和密钥有效）"))
                elif resp.status_code == 401:
                    self.root.after(0, lambda: self._log("API 验证失败：密钥无效"))
                    return
                elif resp.status_code == 404:
                    self.root.after(0, lambda: self._log(f"API 连接成功（{base_url} 地址有效）"))
                else:
                    self.root.after(0, lambda: self._log(f"API 返回状态码: {resp.status_code}"))
                    return
        except Exception as e:
            err = str(e).lower()
            if "connect" in err or "timeout" in err or "name or service" in err:
                self.root.after(0, lambda: self._log(f"API 连接失败：无法连接到 {base_url}"))
            else:
                self.root.after(0, lambda: self._log(f"API 连接测试失败: {str(e)[:60]}"))
            return

        # 第二步：用 deepseek-chat 发一条测试消息
        self.root.after(0, lambda: self._log("测试对话（模型: deepseek-chat）..."))
        try:
            from summarizer.summarizer import ClaudeClient
            client = ClaudeClient(api_key=self.api_key, model="deepseek-chat")
            client.base_url = base_url
            resp = client.chat(
                "请简短回复 ping ok",
                [{"role": "user", "content": "ping"}],
                max_tokens=20,
            )
            if resp and resp.strip():
                self.root.after(0, lambda: self._log(f"对话测试通过。你设置的模型名 \"{user_model}\" 可能需要确认是否正确"))
            else:
                self.root.after(0, lambda: self._log(f"对话测试返回空，请检查模型名 \"{user_model}\" 是否正确"))
        except Exception as e:
            self.root.after(0, lambda: self._log(f"对话测试失败: {str(e)[:60]}"))

    # ==================== UI 构建 ====================

    def _build_ui(self):
        # -- 顶部横幅 --
        header = tk.Frame(self.root, bg=self.COLORS["bg_dark"], height=90)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="AI 新闻日报系统",
            fg=self.COLORS["text_light"],
            bg=self.COLORS["bg_dark"],
            font=("Microsoft YaHei", 20, "bold"),
        ).pack(pady=(16, 2))

        api_text = "API 已配置" if self.api_key else "API 未配置（将使用降级模式）"
        api_color = "#4ade80" if self.api_key else "#fbbf24"
        tk.Label(
            header,
            text=f"报告目录: {MONTH_DIR}    |    {api_text}",
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
        tk.Label(parent, text="生 成 日 报", font=("Microsoft YaHei", 11, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(**pad)
        for btn in [
            ("时政日报", self.COLORS["red"], lambda: self._run("political")),
            ("AI影视行业日报", self.COLORS["purple"], lambda: self._run("industry")),
        ]:
            self._btn(parent, *btn)

        # 分隔线
        tk.Frame(parent, bg=self.COLORS["border"], height=1).pack(fill=tk.X, padx=14, pady=10)

        # 查看
        tk.Label(parent, text="查 看", font=("Microsoft YaHei", 11, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(**pad)
        for btn in [
            ("查看最新日报", self.COLORS["gray"], self._open_reports),
            ("价格走势图", self.COLORS["orange"], self._generate_and_open_chart),
            ("报告目录", self.COLORS["gray"], lambda: os.startfile(str(MONTH_DIR)) if hasattr(os, 'startfile') else None),
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

        tk.Label(title_bar, text="运 行 日 志", font=("Microsoft YaHei", 12, "bold"),
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
        tk.Label(bar, text=f"{now}   |   数据目录: {DATA_DIR}",
                 fg="#94a3b8", bg=self.COLORS["bg_dark"],
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=16)

        settings_btn = tk.Button(
            bar, text="设置",
            command=self._open_settings,
            bg=self.COLORS["gray"], fg="white",
            activebackground="#475569", activeforeground="white",
            relief=tk.FLAT, font=("Microsoft YaHei", 9),
            padx=14, pady=2, cursor="hand2", borderwidth=0,
        )
        settings_btn.pack(side=tk.RIGHT, padx=4)

        self.exit_btn = tk.Button(
            bar, text="退出程序",
            command=self.root.destroy,
            bg=self.COLORS["gray"], fg="white",
            activebackground="#475569", activeforeground="white",
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

    # ==================== 设置对话框 ====================

    def _open_settings(self):
        """打开API设置对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("API 设置")
        dialog.geometry("520x350")
        dialog.resizable(False, False)
        dialog.configure(bg=self.COLORS["bg_card"])
        dialog.transient(self.root)
        dialog.grab_set()

        # 读取当前配置
        settings_path = DATA_DIR / "settings.json"
        current = {}
        if settings_path.exists():
            try:
                current = json.loads(settings_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        pad = {"padx": 20, "pady": (12, 4)}

        tk.Label(dialog, text="API 配置",
                 font=("Microsoft YaHei", 13, "bold"),
                 fg=self.COLORS["text_dark"],
                 bg=self.COLORS["bg_card"]).pack(**pad)

        tk.Label(dialog, text="支持 Anthropic 协议兼容的 API（如 DeepSeek、Claude 等）",
                 font=("Microsoft YaHei", 9),
                 fg=self.COLORS["gray"],
                 bg=self.COLORS["bg_card"]).pack(padx=20, pady=(0, 8))

        fields = [
            ("api_key", "API 密钥 *", "输入您的 API Key", True),
            ("base_url", "API 地址", "https://api.deepseek.com", False),
            ("model", "模型名称", "deepseek-chat", False),
        ]

        entries = {}
        for key, label, placeholder, required in fields:
            frame = tk.Frame(dialog, bg=self.COLORS["bg_card"])
            frame.pack(fill=tk.X, padx=20, pady=4)

            tk.Label(frame, text=label, width=12, anchor="e",
                     font=("Microsoft YaHei", 10),
                     fg=self.COLORS["text_dark"],
                     bg=self.COLORS["bg_card"]).pack(side=tk.LEFT, padx=(0, 8))

            show_char = "*" if key == "api_key" else ""
            entry = tk.Entry(frame, font=("Consolas", 10),
                             relief=tk.SOLID, borderwidth=1,
                             show=show_char)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # 填入保存的值
            entry.insert(0, current.get(key, ""))
            if not current.get(key) and placeholder and key == "model":
                entry.insert(0, "deepseek-chat")

            entries[key] = entry

        def save():
            data = {}
            for key in fields:
                val = entries[key[0]].get().strip()
                if val:
                    data[key[0]] = val

            if not data.get("api_key"):
                messagebox.showwarning("提示", "请输入 API 密钥", parent=dialog)
                return

            # 保存到文件
            settings_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            # 同步到环境变量（当前进程生效）
            os.environ["ANTHROPIC_API_KEY"] = data["api_key"]
            if data.get("base_url"):
                os.environ["ANTHROPIC_BASE_URL"] = data["base_url"]
            if data.get("model"):
                os.environ["ANTHROPIC_MODEL"] = data["model"]

            dialog.destroy()
            # 询问是否重启应用
            restart = messagebox.askyesno(
                "配置已保存",
                "API 配置已保存。\n是否立即重启应用使配置生效？",
                parent=self.root,
            )
            if restart:
                self.root.destroy()
                if IS_EXE:
                    os.startfile(sys.executable)
                else:
                    os.startfile(sys.argv[0])

        btn_frame = tk.Frame(dialog, bg=self.COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=20, pady=(16, 12))

        tk.Button(btn_frame, text="取消",
                  command=dialog.destroy,
                  font=("Microsoft YaHei", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(btn_frame, text="保存",
                  command=save,
                  bg=self.COLORS["primary"], fg="white",
                  font=("Microsoft YaHei", 10),
                  relief=tk.FLAT, padx=20,
                  cursor="hand2").pack(side=tk.RIGHT)

    # ==================== 操作 ====================

    def _run(self, mode):
        labels = {"political": "时政日报", "industry": "AI影视行业日报"}
        label = labels.get(mode, "日报")
        self._log(f"{'='*50}")
        self._log(f"  开始生成 {label} ...")
        self._log(f"{'='*50}")
        threading.Thread(target=self._run_task, args=(mode,), daemon=True).start()

    def _run_task(self, mode):
        try:
            if IS_EXE:
                sys.path.insert(0, str(BASE_DIR))
                import main as m
                m.run_daily(mode=mode)
            else:
                from main import run_daily as _run
                _run(mode=mode)

            self.root.after(0, lambda: self._log("生成完成！"))
            # 只打开刚生成的报告，不打开其他类型的报告
            self.root.after(500, lambda: self._open_single_report(mode))
        except Exception as e:
            self.root.after(0, lambda: self._log(f"错误: {e}"))

    def _open_single_report(self, mode):
        """只打开指定类型的报告"""
        pattern, icon = {
            "political": ("*时政日报.html", "时政"),
            "industry": ("*AI日报.html", "AI"),
        }.get(mode, ("*日报.html", ""))
        files = sorted(MONTH_DIR.glob(pattern), reverse=True)
        if files:
            webbrowser.open(str(files[0]))
            self._log(f"{icon}日报: {files[0].name}")
        else:
            self._log("暂无报告")

    def _generate_and_open_chart(self):
        """单独生成并打开价格走势图"""
        self._log("开始生成价格走势图...")
        threading.Thread(target=self._chart_task, daemon=True).start()

    def _chart_task(self):
        try:
            if IS_EXE:
                sys.path.insert(0, str(BASE_DIR))
                import main as m
                chart_path = m.generate_chart()
            else:
                from main import generate_chart
                chart_path = generate_chart()

            if chart_path:
                self.root.after(0, lambda: webbrowser.open(str(chart_path)))
                self.root.after(0, lambda: self._log(f"价格走势图已生成并打开"))
            else:
                self.root.after(0, lambda: self._log("价格走势图生成失败"))
        except Exception as e:
            self.root.after(0, lambda: self._log(f"错误: {e}"))

    def _open_reports(self):
        opened = False
        for pattern, icon in [("*时政日报.html", "时政"), ("*AI日报.html", "AI")]:
            files = sorted(MONTH_DIR.glob(pattern), reverse=True)
            if files:
                webbrowser.open(str(files[0]))
                self._log(f"{icon}日报: {files[0].name}")
                opened = True
        if not opened:
            self._log("暂无报告")

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
