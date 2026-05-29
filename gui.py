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

# 确保基础目录存在
for d in [DATA_DIR, REPORTS_DIR, DATA_DIR / "news"]:
    d.mkdir(parents=True, exist_ok=True)


def _get_month_dir():
    """获取当前用户的月报告目录"""
    from config import get_user_report_dir
    return get_user_report_dir()


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
        "bg_light": "#f1f5f9",
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

    def __init__(self, root, username="default"):
        self.root = root
        self.username = username
        self.root.title("AI 新闻日报系统")
        self.root.geometry("960x720")
        self.root.minsize(800, 600)
        self.root.configure(bg=self.COLORS["bg_dark"])

        from config import get_user_report_dir
        self.month_dir = get_user_report_dir()

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
            self.root.after(0, lambda: self._log("API 未配置，请点击底部\"API 配置\"按钮进行配置"))
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
            text=f"报告目录: {self.month_dir}    |    {api_text}",
            fg=api_color,
            bg=self.COLORS["bg_dark"],
            font=("Microsoft YaHei", 9),
        ).pack()

        # -- 主体（可拖拽分割面板） --
        main = tk.PanedWindow(self.root, bg=self.COLORS["bg_dark"],
                              sashrelief=tk.RAISED, sashwidth=6, sashpad=0)
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 16))

        # 左侧面板（可滚动）
        left_container = tk.Frame(main, bg=self.COLORS["bg_card"])
        left_canvas = tk.Canvas(left_container, bg=self.COLORS["bg_card"],
                                highlightthickness=0, width=260)
        left_scroll = tk.Scrollbar(left_container, orient=tk.VERTICAL, command=left_canvas.yview)
        left_scrollable = tk.Frame(left_canvas, bg=self.COLORS["bg_card"])

        left_scrollable.bind("<Configure>", lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.create_window((0, 0), window=left_scrollable, anchor="nw", tags="inner")
        left_canvas.configure(yscrollcommand=left_scroll.set)

        # 鼠标滚轮控制左侧面板滚动
        def _on_left_scroll(event):
            left_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        left_canvas.bind("<MouseWheel>", _on_left_scroll)
        left_scrollable.bind("<MouseWheel>", _on_left_scroll)

        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_left_panel(left_scrollable)

        main.add(left_container, width=260, minsize=180)

        # 右侧日志面板
        right = tk.Frame(main, bg=self.COLORS["bg_card"])
        self._build_right_panel(right)
        main.add(right, minsize=400)

        # -- 底部状态栏 --
        self._build_statusbar()

    def _build_left_panel(self, parent):
        pad = {"padx": 14, "pady": (14, 0)}

        # 生成日报
        tk.Label(parent, text="生 成 日 报", font=("Microsoft YaHei", 11, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(**pad)
        for btn in [
            ("时政日报", self.COLORS["red"], lambda: self._run("political")),
            ("AI影视行业日报", self.COLORS["purple"], lambda: self._run("industry")),
        ]:
            self._btn(parent, *btn)

        # 分隔线
        tk.Frame(parent, bg=self.COLORS["border"], height=1).pack(fill=tk.X, padx=16, pady=10)

        # 自定义日报
        tk.Label(parent, text="自 定 义 日 报", font=("Microsoft YaHei", 11, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(**pad)
        self._btn(parent, "自定义日报", "#8b5cf6", self._open_custom_report)
        tk.Label(parent, text="⚠ 请谨慎使用，自选来源可能耗时较长",
                 font=("Microsoft YaHei", 7), fg="#e74c3c",
                 bg=self.COLORS["bg_card"]).pack(pady=(0, 6))

        # 分隔线
        tk.Frame(parent, bg=self.COLORS["border"], height=1).pack(fill=tk.X, padx=16, pady=10)

        # 查看
        tk.Label(parent, text="查 看", font=("Microsoft YaHei", 11, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(**pad)
        for btn in [
            ("查看最新日报", self.COLORS["gray"], self._open_reports),
            ("报告目录", self.COLORS["gray"], lambda: os.startfile(str(self.month_dir)) if hasattr(os, 'startfile') else None),
        ]:
            self._btn(parent, *btn)

        # 外部站点登录
        tk.Frame(parent, bg=self.COLORS["border"], height=1).pack(fill=tk.X, padx=16, pady=10)
        tk.Label(parent, text="站 点 登 录", font=("Microsoft YaHei", 11, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(**pad)
        for btn in [
            ("抖音创作者中心", "#e74c3c", lambda: self._quick_login("douyin_creator", "抖音创作者中心", "https://creator.douyin.com/")),
            ("巨量引擎", "#e67e22", lambda: self._quick_login("oceanengine", "巨量引擎", "https://ad.oceanengine.com/")),
            ("抖音电商学习中心", "#3498db", lambda: self._quick_login("douyin_school", "抖音电商学习中心", "https://school.jinritemai.com/")),
        ]:
            self._btn(parent, *btn)

    def _btn(self, parent, text, color, command):
        btn = tk.Button(
            parent, text=text, command=command,
            bg=color, fg="white", activebackground=self._lighten(color),
            activeforeground="white", relief=tk.FLAT,
            font=("Microsoft YaHei", 10), padx=16, pady=8,
            cursor="hand2", borderwidth=0,
        )
        btn.pack(anchor="center", pady=4, ipadx=24)
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

        # 进度条
        self._progress_frame = tk.Frame(parent, bg=self.COLORS["bg_card"])
        self._progress_frame.pack(fill=tk.X, padx=16, pady=(0, 4))
        # 样式设置（更大更显眼）
        s = ttk.Style()
        s.configure("TProgressbar", thickness=12)
        self._progress_bar = ttk.Progressbar(self._progress_frame, mode="determinate",
                                             length=200, style="TProgressbar")
        self._progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._progress_label = tk.Label(self._progress_frame, text="", font=("Consolas", 9, "bold"),
                                        fg=self.COLORS["primary"], bg=self.COLORS["bg_card"])
        self._progress_label.pack(side=tk.RIGHT, padx=(8, 0))
        # 默认隐藏
        self._progress_frame.pack_forget()

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

        # 鼠标滚轮滚动（DISABLED状态下也生效）
        def _on_log_wheel(event):
            self.log_text.yview_scroll(-1 * (event.delta // 120), "units")
            return "break"
        self.log_text.bind("<MouseWheel>", _on_log_wheel)
        # 触控板支持（Linux/Windows通用）
        self.log_text.bind("<Button-4>", lambda e: self.log_text.yview_scroll(-3, "units"))
        self.log_text.bind("<Button-5>", lambda e: self.log_text.yview_scroll(3, "units"))

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=self.COLORS["bg_dark"], height=36)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self._time_label = tk.Label(bar, text="",
                 fg="#94a3b8", bg=self.COLORS["bg_dark"],
                 font=("Microsoft YaHei", 9))
        self._time_label.pack(side=tk.LEFT, padx=16)
        self._update_clock()

        login_btn = tk.Button(
            bar, text="登录管理",
            command=self._open_login_manager,
            bg=self.COLORS["gray"], fg="white",
            activebackground="#475569", activeforeground="white",
            relief=tk.FLAT, font=("Microsoft YaHei", 9),
            padx=14, pady=2, cursor="hand2", borderwidth=0,
        )
        login_btn.pack(side=tk.RIGHT, padx=4)

        settings_btn = tk.Button(
            bar, text="API 配置",
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

    def _update_clock(self):
        """每秒更新状态栏时间"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._time_label.configure(text=f"{now}   |   数据目录: {DATA_DIR}")
        self.root.after(1000, self._update_clock)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    # ==================== API 配置对话框 ====================

    def _open_settings(self):
        """打开 API 配置对话框（含模型自动检测）"""
        dialog = tk.Toplevel(self.root)
        dialog.title("API 配置")
        dialog.geometry("560x420")
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

        tk.Label(dialog, text="支持 OpenAI 兼容协议及 Anthropic 协议的 API",
                 font=("Microsoft YaHei", 9),
                 fg=self.COLORS["gray"],
                 bg=self.COLORS["bg_card"]).pack(padx=20, pady=(0, 8))

        # 表单容器
        form = tk.Frame(dialog, bg=self.COLORS["bg_card"])
        form.pack(fill=tk.X, padx=20)

        # API 密钥
        tk.Label(form, text="API 密钥", anchor="w",
                 font=("Microsoft YaHei", 10), fg=self.COLORS["text_dark"],
                 bg=self.COLORS["bg_card"]).pack(fill=tk.X, pady=(8, 2))
        api_key_entry = tk.Entry(form, font=("Consolas", 10),
                                 relief=tk.SOLID, borderwidth=1, show="*")
        api_key_entry.pack(fill=tk.X, ipady=4)
        api_key_entry.insert(0, current.get("api_key", ""))

        # API 地址 + 检测按钮
        tk.Label(form, text="API 地址", anchor="w",
                 font=("Microsoft YaHei", 10), fg=self.COLORS["text_dark"],
                 bg=self.COLORS["bg_card"]).pack(fill=tk.X, pady=(8, 2))
        url_frame = tk.Frame(form, bg=self.COLORS["bg_card"])
        url_frame.pack(fill=tk.X)
        base_url_entry = tk.Entry(url_frame, font=("Consolas", 10),
                                  relief=tk.SOLID, borderwidth=1)
        base_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        base_url_entry.insert(0, current.get("base_url", ""))

        detect_btn = tk.Button(url_frame, text="检测模型",
                               font=("Microsoft YaHei", 9, "bold"),
                               bg=self.COLORS["primary"], fg="white",
                               relief=tk.FLAT, padx=14, cursor="hand2")
        detect_btn.pack(side=tk.RIGHT, padx=(6, 0))

        # 模型名称（下拉选择 + 可手动输入）
        tk.Label(form, text="模型名称", anchor="w",
                 font=("Microsoft YaHei", 10), fg=self.COLORS["text_dark"],
                 bg=self.COLORS["bg_card"]).pack(fill=tk.X, pady=(8, 2))
        model_combo = ttk.Combobox(form, font=("Consolas", 10),
                                   state="normal")  # 可手动输入
        model_combo.pack(fill=tk.X, ipady=4)
        default_model = current.get("model", "deepseek-chat")
        model_combo.set(default_model)
        model_combo["values"] = [default_model]

        # 检测状态标签
        detect_status = tk.Label(form, text="", font=("Microsoft YaHei", 9),
                                 fg=self.COLORS["gray"], bg=self.COLORS["bg_card"])
        detect_status.pack(fill=tk.X, pady=(4, 0))

        # 检测模型回调
        def on_detect():
            base_url = base_url_entry.get().strip()
            api_key = api_key_entry.get().strip()
            if not base_url:
                detect_status.configure(text="请先填写 API 地址", fg=self.COLORS["red"])
                return
            if not api_key:
                detect_status.configure(text="请先填写 API 密钥", fg=self.COLORS["red"])
                return

            detect_btn.configure(state=tk.DISABLED, text="检测中...")
            detect_status.configure(text="正在连接 API 获取模型列表...", fg=self.COLORS["gray"])
            dialog.update()

            import httpx
            try:
                url = base_url.rstrip("/") + "/models"
                resp = httpx.get(url, headers={"Authorization": f"Bearer {api_key}"},
                                 timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["id"] for m in data.get("data", []) if "id" in m]
                    if models:
                        model_combo["values"] = models
                        model_combo.set(models[0])
                        detect_status.configure(
                            text=f"检测到 {len(models)} 个模型，已选择第一个",
                            fg="#27ae60")
                    else:
                        detect_status.configure(text="API 响应正常但未获取到模型列表",
                                                fg=self.COLORS["orange"])
                elif resp.status_code == 401:
                    detect_status.configure(text="密钥无效（401），请检查 API Key",
                                            fg=self.COLORS["red"])
                elif resp.status_code == 404:
                    # 可能是 Anthropic 协议，尝试不同路径
                    try:
                        resp2 = httpx.get(base_url.rstrip("/") + "/v1/models",
                                          headers={"Authorization": f"Bearer {api_key}"},
                                          timeout=15)
                        if resp2.status_code == 200:
                            data2 = resp2.json()
                            models2 = [m["id"] for m in data2.get("data", []) if "id" in m]
                            if models2:
                                model_combo["values"] = models2
                                model_combo.set(models2[0])
                                detect_status.configure(
                                    text=f"检测到 {len(models2)} 个模型",
                                    fg="#27ae60")
                                return
                    except Exception:
                        pass
                    detect_status.configure(
                        text="该 API 不支持模型列表查询，请手动输入模型名称",
                        fg=self.COLORS["orange"])
                else:
                    detect_status.configure(
                        text=f"API 返回状态码 {resp.status_code}，请检查地址和密钥",
                        fg=self.COLORS["red"])
            except Exception as e:
                detect_status.configure(text=f"连接失败: {str(e)[:50]}",
                                        fg=self.COLORS["red"])
            finally:
                detect_btn.configure(state=tk.NORMAL, text="检测模型")

        detect_btn.configure(command=on_detect)

        def save():
            data = {
                "api_key": api_key_entry.get().strip(),
                "base_url": base_url_entry.get().strip(),
                "model": model_combo.get().strip(),
            }
            # 过滤掉空值
            data = {k: v for k, v in data.items() if v}

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
        btn_frame.pack(fill=tk.X, padx=20, pady=(12, 4))

        tk.Button(btn_frame, text="取消",
                  command=dialog.destroy,
                  font=("Microsoft YaHei", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(btn_frame, text="保存",
                  command=save,
                  bg=self.COLORS["primary"], fg="white",
                  font=("Microsoft YaHei", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT)

        tk.Label(dialog,
                 text="* 点击保存后需要重新登录系统才能使新配置生效",
                 font=("Microsoft YaHei", 9),
                 fg=self.COLORS["red"], bg=self.COLORS["bg_card"]).pack(padx=20, pady=(0, 12))

    def _open_login_manager(self):
        """打开登录管理器"""
        login_sites = [
            {"id": "douyin_creator", "name": "抖音创作者中心", "url": "https://creator.douyin.com/",
             "login_url": "https://creator.douyin.com/", "desc": "查看热门话题、创作指南"},
            {"id": "oceanengine", "name": "巨量引擎", "url": "https://www.oceanengine.com/",
             "login_url": "https://ad.oceanengine.com/", "desc": "广告投放趋势、平台政策"},
            {"id": "douyin_school", "name": "抖音电商学习中心", "url": "https://school.jinritemai.com/",
             "login_url": "https://school.jinritemai.com/", "desc": "电商运营学习课程"},
        ]

        dialog = tk.Toplevel(self.root)
        dialog.title("登录管理器")
        dialog.geometry("580x420")
        dialog.resizable(False, False)
        dialog.configure(bg=self.COLORS["bg_card"])
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="登录会话管理",
                 font=("Microsoft YaHei", 13, "bold"),
                 fg=self.COLORS["text_dark"],
                 bg=self.COLORS["bg_card"]).pack(pady=(14, 2))

        tk.Label(dialog, text="登录后自动保存Cookie，下次采集无需重复登录",
                 font=("Microsoft YaHei", 9),
                 fg=self.COLORS["gray"],
                 bg=self.COLORS["bg_card"]).pack(pady=(0, 6))

        # 可滚动的站点列表
        list_container = tk.Frame(dialog, bg=self.COLORS["bg_card"])
        list_container.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        list_canvas = tk.Canvas(list_container, bg=self.COLORS["bg_card"],
                                highlightthickness=0)
        list_scroll = tk.Scrollbar(list_container, orient=tk.VERTICAL, command=list_canvas.yview)
        list_frame = tk.Frame(list_canvas, bg=self.COLORS["bg_card"])

        list_frame.bind("<Configure>",
                        lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_canvas.create_window((0, 0), window=list_frame, anchor="nw", tags="inner")
        list_canvas.configure(yscrollcommand=list_scroll.set)

        def _on_list_scroll(event):
            list_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        list_canvas.bind("<MouseWheel>", _on_list_scroll)
        list_frame.bind("<MouseWheel>", _on_list_scroll)

        list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 从数据库读取登录状态
        session_status = {}
        try:
            from system.database import get_all_sessions
            for s in get_all_sessions():
                session_status[s["site_id"]] = s
        except Exception:
            pass

        for site in login_sites:
            sid = site["id"]
            sess = session_status.get(sid, {})
            logged_in = sess.get("is_active", False)
            logged_in_at = sess.get("logged_in_at", "")

            card = tk.Frame(list_frame, bg=self.COLORS["bg_light"], padx=12, pady=8, relief="flat", bd=0)
            card.pack(fill="x", pady=4)

            row1 = tk.Frame(card, bg=self.COLORS["bg_light"])
            row1.pack(fill="x")
            tk.Label(row1, text=site["name"], font=("Microsoft YaHei", 11, "bold"),
                     fg=self.COLORS["text_dark"], bg=self.COLORS["bg_light"]).pack(side="left")

            if logged_in:
                status_text = "✓ 已登录"
                if logged_in_at:
                    status_text += f"  ({logged_in_at[:16]})"
                status_color = "#27ae60"
            else:
                status_text = "未登录"
                status_color = "#e74c3c"
            tk.Label(row1, text=status_text, font=("Microsoft YaHei", 9),
                     fg=status_color, bg=self.COLORS["bg_light"]).pack(side="right")

            tk.Label(card, text=site["desc"], font=("Microsoft YaHei", 9),
                     fg=self.COLORS["gray"], bg=self.COLORS["bg_light"]).pack(anchor="w")

            def make_login_cmd(site_id, site_name, login_url):
                def cmd():
                    self._do_login(dialog, site_id, site_name, login_url)
                return cmd

            def make_logout_cmd(site_id):
                def cmd():
                    from system.database import get_conn
                    conn = get_conn()
                    try:
                        conn.execute("UPDATE login_sessions SET is_active=0 WHERE site_id=?", (site_id,))
                        conn.commit()
                    finally:
                        conn.close()
                    # 清除本地缓存的Cookie文件和Playwright用户数据目录
                    import shutil
                    cookie_file = DATA_DIR / "sessions" / f"{site_id}_cookies.json"
                    if cookie_file.exists():
                        cookie_file.unlink()
                    sess_dir = DATA_DIR / "sessions" / site_id
                    if sess_dir.exists():
                        shutil.rmtree(sess_dir, ignore_errors=True)
                    dialog.destroy()
                    self._log(f"{site_id} 已退出登录，Cookie已清除")
                    self._open_login_manager()
                return cmd

            btn_row = tk.Frame(card, bg=self.COLORS["bg_light"])
            btn_row.pack(fill="x", pady=(4, 0))

            tk.Button(btn_row, text="重新登录" if logged_in else "去登录",
                      command=make_login_cmd(sid, site["name"], site["login_url"]),
                      bg="#667eea", fg="white", font=("Microsoft YaHei", 9),
                      padx=12, relief="flat", cursor="hand2").pack(side="left")

            if logged_in:
                tk.Button(btn_row, text="退出登录", font=("Microsoft YaHei", 9),
                          bg="#e74c3c", fg="white", relief="flat", padx=12,
                          cursor="hand2", command=make_logout_cmd(sid)).pack(side="left", padx=(6, 0))

        tk.Button(dialog, text="关闭", command=dialog.destroy,
                  font=("Microsoft YaHei", 10), relief="flat", padx=20).pack(pady=(4, 10))

    def _quick_login(self, site_id, site_name, login_url):
        """从侧边栏快速登录"""
        self._log(f"正在打开浏览器登录 {site_name}...")
        threading.Thread(target=self._execute_login, args=(site_id, site_name, login_url), daemon=True).start()

    def _do_login(self, parent_dialog, site_id, site_name, login_url):
        """从登录管理器执行登录"""
        self._log(f"正在打开浏览器登录 {site_name}...")
        parent_dialog.destroy()
        threading.Thread(target=self._execute_login, args=(site_id, site_name, login_url), daemon=True).start()

    def _execute_login(self, site_id, site_name, login_url):
        cookie_file = DATA_DIR / "sessions" / f"{site_id}_cookies.json"

        # 尝试用 Playwright 自动登录
        try:
            import json
            import time
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                sess_dir = str(DATA_DIR / "sessions" / site_id)
                # 清除旧会话目录，确保每次登录都是全新会话（可切换账号）
                import shutil as _shutil2
                _p = Path(sess_dir)
                if _p.exists():
                    _shutil2.rmtree(_p, ignore_errors=True)
                browser = None
                for ch in ["chrome", "msedge", None]:
                    try:
                        kw = {"headless": False}
                        if ch:
                            kw["channel"] = ch
                        browser = p.chromium.launch_persistent_context(
                            user_data_dir=sess_dir, **kw,
                            viewport={"width": 1280, "height": 800}, locale="zh-CN")
                        break
                    except Exception:
                        continue

                if browser is None:
                    raise RuntimeError("no_browser")

                self._log(f"浏览器已打开，请在窗口中登录 {site_name}")
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto(login_url, wait_until="domcontentloaded")
                self._log(f"请在浏览器中登录 {site_name}，登录后关闭浏览器窗口即可")

                while True:
                    try:
                        if len(browser.pages) == 0:
                            break
                        current = browser.pages[0].url if browser.pages else ""
                        if current and "login" not in current.lower() and current != "about:blank":
                            self._log("检测到登录成功！正在保存Cookie...")
                            break
                    except Exception:
                        break
                    time.sleep(1)

                cookies = browser.cookies()
                browser.close()

                from system.database import save_login_session
                save_login_session(site_id, site_name, cookies)
                self._log(f"{site_name} 登录成功，已保存 {len(cookies)} 条Cookie")
                cookie_file.parent.mkdir(parents=True, exist_ok=True)
                cookie_file.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
                return

        except ImportError:
            pass  # Playwright 未安装，走降级方案
        except Exception as e:
            msg = str(e)
            if "no_browser" in msg:
                pass  # 没找到浏览器，走降级方案
            elif "Executable doesn't exist" in msg or "playwright" in str(type(e).__name__).lower():
                pass  # EXE中驱动不可用，走降级方案
            else:
                self._log(f"自动登录失败: {type(e).__name__}: {e}")

        # 降级方案：用默认浏览器打开 + 手动粘贴Cookie
        self._log(f"Playwright不可用，改用浏览器手动登录模式")
        self._manual_cookie_login(site_id, site_name, login_url)

    def _manual_cookie_login(self, site_id, site_name, login_url):
        """手动Cookie登录：打开默认浏览器，用户登录后粘贴Cookie"""
        import webbrowser
        webbrowser.open(login_url)

        # 弹出Cookie输入框
        dialog = tk.Toplevel(self.root)
        dialog.title(f"手动登录 - {site_name}")
        dialog.geometry("580x510")
        dialog.resizable(False, False)
        dialog.configure(bg=self.COLORS["bg_card"])
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text=f"手动登录 - {site_name}",
                 font=("Microsoft YaHei", 13, "bold"),
                 fg=self.COLORS["text_dark"], bg=self.COLORS["bg_card"]).pack(pady=(14, 6))

        instructions = (
            f"已在默认浏览器中打开 {site_name}\n\n"
            "请先在浏览器中完成登录，然后：\n"
            "1. 按 F12 打开开发者工具\n"
            "2. 切换到 Application（应用程序）标签\n"
            "3. 左侧 Storage → Cookies → 选择当前网站\n"
            "4. 复制所有Cookie，格式如下：\n"
            "   name1=value1; name2=value2\n"
            "5. 粘贴到下方输入框中，点击保存"
        )
        tk.Label(dialog, text=instructions, justify="left",
                 font=("Microsoft YaHei", 9), fg=self.COLORS["gray"],
                 bg=self.COLORS["bg_card"]).pack(padx=20, pady=(0, 8))

        cookie_entry = tk.Text(dialog, font=("Consolas", 9),
                               bg=self.COLORS["bg_light"], fg=self.COLORS["text_dark"],
                               wrap=tk.WORD, height=8, relief=tk.FLAT, borderwidth=1)
        cookie_entry.pack(fill=tk.X, padx=20, pady=(0, 8))

        status_label = tk.Label(dialog, text="", font=("Microsoft YaHei", 9),
                                fg=self.COLORS["gray"], bg=self.COLORS["bg_card"])
        status_label.pack()

        def save_manual_cookies():
            raw = cookie_entry.get("1.0", "end").strip()
            if not raw:
                status_label.configure(text="请粘贴Cookie内容", fg=self.COLORS["red"])
                return

            import json
            import re
            cookies = []
            # 解析 Cookie 字符串：name=value; name2=value2 或 JSON 数组
            if raw.startswith("["):
                try:
                    cookies = json.loads(raw)
                except json.JSONDecodeError:
                    status_label.configure(text="JSON格式错误", fg=self.COLORS["red"])
                    return
            else:
                for part in raw.split(";"):
                    part = part.strip()
                    if "=" in part:
                        name, value = part.split("=", 1)
                        cookies.append({"name": name.strip(), "value": value.strip(),
                                        "domain": "", "path": "/"})

            if not cookies:
                status_label.configure(text="未解析到有效的Cookie", fg=self.COLORS["red"])
                return

            from system.database import save_login_session
            save_login_session(site_id, site_name, cookies)
            self._log(f"{site_name} 手动登录成功，已保存 {len(cookies)} 条Cookie")

            cookie_file = DATA_DIR / "sessions" / f"{site_id}_cookies.json"
            cookie_file.parent.mkdir(parents=True, exist_ok=True)
            cookie_file.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")

            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=self.COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=20, pady=(4, 12))

        tk.Button(btn_frame, text="取消", command=dialog.destroy,
                  font=("Microsoft YaHei", 10), relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_frame, text="保存",
                  command=save_manual_cookies,
                  bg=self.COLORS["primary"], fg="white",
                  font=("Microsoft YaHei", 10),
                  relief=tk.FLAT, padx=20, cursor="hand2").pack(side=tk.RIGHT)

    # ==================== 操作 ====================

    def _set_progress(self, value: int, text: str = "", indeterminate: bool = False):
        """更新进度条（线程安全）

        value: 0-100 百分比，或 -1 表示启动加载动画
        """
        if indeterminate:
            self.root.after(0, lambda: self._progress_bar.configure(mode="indeterminate"))
            self.root.after(0, lambda: self._progress_bar.start(15))
        else:
            self.root.after(0, lambda: self._progress_bar.configure(mode="determinate"))
            self.root.after(0, lambda: self._progress_bar.stop())
            self.root.after(0, lambda: self._progress_bar.configure(value=value))
            self.root.after(0, lambda: self._progress_label.configure(text=f"{text}  {value}%"))

    def _run(self, mode):
        labels = {"political": "时政日报", "industry": "AI影视行业日报"}
        label = labels.get(mode, "日报")
        self._log(f"{'='*50}")
        self._log(f"  开始生成 {label} ...")
        self._log(f"{'='*50}")
        # 显示进度条（加载动画）
        self._progress_frame.pack(fill=tk.X, padx=16, pady=(0, 4))
        self._set_progress(0, "准备中...", indeterminate=True)
        threading.Thread(target=self._run_task, args=(mode,), daemon=True).start()

    def _run_task(self, mode):
        try:
            # Step 1: 采集新闻
            self._set_progress(5, "采集新闻中")
            from collector.news_collector import collect_all
            news_data = collect_all(days=2)
            self._set_progress(25, "新闻采集完成")

            # Step 2: AI总结（耗时长，用加载动画）
            from summarizer.summarizer import summarize_political, summarize_industry
            political_articles = news_data.get("political", [])
            industry_articles = news_data.get("industry", [])
            competition_articles = news_data.get("competition", [])

            political_summary = ""
            industry_summary = ""

            if mode in ("all", "political"):
                self._set_progress(30, "AI总结时政新闻", indeterminate=True)
                political_summary = summarize_political(political_articles)

            if mode in ("all", "industry"):
                self._set_progress(50, "AI总结行业新闻", indeterminate=True)
                industry_result = summarize_industry(industry_articles, competition_articles)
                if isinstance(industry_result, tuple):
                    industry_summary, industry_combined = industry_result
                else:
                    industry_summary = industry_result
                    industry_combined = industry_articles

            self._set_progress(80, "AI总结完成")

            # Step 3: 生成HTML报告
            from report.report_generator import generate_political_report, generate_industry_report
            if mode in ("all", "political") and political_summary:
                self._set_progress(85, "生成时政日报")
                generate_political_report(summary_text=political_summary, articles=political_articles)

            if mode in ("all", "industry") and industry_summary:
                self._set_progress(95, "生成AI行业日报")
                generate_industry_report(summary_text=industry_summary, articles=industry_combined)

            self._set_progress(100, "完成")
            self.root.after(2000, lambda: self._progress_frame.pack_forget())
            self.root.after(0, lambda: self._log("生成完成！"))
            self.root.after(500, lambda: self._open_single_report(mode))
        except Exception as e:
            self.root.after(0, lambda: self._log(f"错误: {e}"))
            import traceback
            self.root.after(0, lambda: self._log(traceback.format_exc()[:500]))

    def _open_single_report(self, mode):
        """只打开指定类型的报告"""
        pattern, icon = {
            "political": ("*时政日报.html", "时政"),
            "industry": ("*AI日报.html", "AI"),
        }.get(mode, ("*日报.html", ""))
        files = sorted(self.month_dir.glob(pattern), reverse=True)
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

    def _open_custom_report(self):
        """打开自定义日报对话框"""
        from config import POLITICAL_WEB_SOURCES, WEB_SCRAPE_SOURCES, AIGC_NEWS_SOURCES

        dialog = tk.Toplevel(self.root)
        dialog.title("自定义日报")
        dialog.geometry("620x550")
        dialog.resizable(False, False)
        dialog.configure(bg=self.COLORS["bg_card"])
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="自定义日报",
                 font=("Microsoft YaHei", 14, "bold"),
                 fg=self.COLORS["text_dark"],
                 bg=self.COLORS["bg_card"]).pack(pady=(14, 4))

        tk.Label(dialog,
                 text="勾选你想要的信息来源，点击生成即可获得专属日报",
                 font=("Microsoft YaHei", 9),
                 fg=self.COLORS["gray"],
                 bg=self.COLORS["bg_card"]).pack(pady=(0, 8))

        # 可滚动的Canvas容器
        container = tk.Frame(dialog, bg=self.COLORS["bg_card"])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 4))

        canvas = tk.Canvas(container, bg=self.COLORS["bg_card"],
                           highlightthickness=0, height=320)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.COLORS["bg_card"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_wheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")
        canvas.bind("<MouseWheel>", _on_wheel)
        inner.bind("<MouseWheel>", _on_wheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 收集所有源
        all_sources = []
        for s in POLITICAL_WEB_SOURCES:
            all_sources.append((s["name"], s["category"], "时政"))
        for s in AIGC_NEWS_SOURCES:
            cat = s.get("category", "industry")
            all_sources.append((s["name"], cat, "AI行业"))
        for s in WEB_SCRAPE_SOURCES:
            cat = s.get("category", "industry")
            all_sources.append((s["name"], cat, "AI行业/政策"))

        # 分组
        groups = {}
        for name, cat, group_label in all_sources:
            if group_label not in groups:
                groups[group_label] = []
            groups[group_label].append((name, cat))

        check_vars = {}

        for group_label, items in groups.items():
            tk.Label(inner, text=group_label,
                     font=("Microsoft YaHei", 11, "bold"),
                     fg=self.COLORS["primary"], bg=self.COLORS["bg_card"],
                     anchor="w").pack(fill=tk.X, pady=(10, 2))

            for name, cat in items:
                var = tk.BooleanVar(value=True)
                check_vars[name] = var
                cb = tk.Checkbutton(inner, text=name, variable=var,
                                    font=("Microsoft YaHei", 9),
                                    fg=self.COLORS["text_dark"],
                                    bg=self.COLORS["bg_card"],
                                    selectcolor=self.COLORS["bg_light"],
                                    activebackground=self.COLORS["bg_card"])
                cb.pack(anchor="w", padx=16)

        def select_all():
            for v in check_vars.values():
                v.set(True)

        def deselect_all():
            for v in check_vars.values():
                v.set(False)

        sel_frame = tk.Frame(inner, bg=self.COLORS["bg_card"])
        sel_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(sel_frame, text="全选", font=("Microsoft YaHei", 8),
                  bg=self.COLORS["gray"], fg="white", relief=tk.FLAT,
                  padx=8, cursor="hand2", command=select_all).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(sel_frame, text="全不选", font=("Microsoft YaHei", 8),
                  bg=self.COLORS["gray"], fg="white", relief=tk.FLAT,
                  padx=8, cursor="hand2", command=deselect_all).pack(side=tk.LEFT)

        btn_frame = tk.Frame(dialog, bg=self.COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=20, pady=(8, 14))

        tk.Button(btn_frame, text="取消",
                  command=dialog.destroy,
                  font=("Microsoft YaHei", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=(8, 0))

        def generate():
            selected = [name for name, var in check_vars.items() if var.get()]
            if not selected:
                tk.messagebox.showwarning("提示", "请至少选择一个来源", parent=dialog)
                return
            dialog.destroy()
            self._log(f"开始生成自定义日报，已选择 {len(selected)} 个来源")
            self._progress_bar.configure(value=0)
            self._progress_frame.pack(fill=tk.X, padx=16, pady=(0, 4))
            threading.Thread(target=self._custom_report_task,
                             args=(selected,), daemon=True).start()

        tk.Button(btn_frame, text="生成",
                  command=generate,
                  bg=self.COLORS["primary"], fg="white",
                  font=("Microsoft YaHei", 10),
                  relief=tk.FLAT, padx=20, cursor="hand2").pack(side=tk.RIGHT)

    def _custom_report_task(self, selected_sources):
        """后台生成自定义日报"""
        try:
            from collector.news_collector import collect_political_news, collect_industry_news
            from summarizer.summarizer import ClaudeClient, _format_articles_for_prompt

            self._set_progress(5, "按选择采集新闻中...")

            # 采集所有新闻
            all_political = collect_political_news(days=2)
            all_industry = collect_industry_news(days=2)

            # 按选中的源过滤
            selected_set = set(selected_sources)
            political_filtered = [a for a in all_political if a.get("source") in selected_set]
            industry_filtered = [a for a in all_industry if a.get("source") in selected_set]

            self._set_progress(25, f"筛选完成: 时政{len(political_filtered)}条, 行业{len(industry_filtered)}条")

            if not political_filtered and not industry_filtered:
                self.root.after(0, lambda: self._log("所选来源无可用新闻"))
                self.root.after(500, lambda: self._progress_frame.pack_forget())
                return

            # 合并为统一列表用于AI摘要
            all_filtered = political_filtered + industry_filtered
            combined_prompt = _format_articles_for_prompt(all_filtered)

            self._set_progress(30, "AI总结中...", indeterminate=True)

            SYSTEM_PROMPT = """你是专业的新闻分析师。请对以下自定义选择的新闻进行总结。
    每条新闻前标注了 [#N] 编号，你必须在末尾标注 [来源：XXX #N]。
    严格去重，按重要性排序。每条控制在60字以内，开头标注 [MM-DD] 日期。

    输出格式：
    ## 自定义日报
    ### 重点新闻（5-8条）
    - [MM-DD] [标题]：摘要 [来源：XXX #N]
    ### 其他要闻（剩余条目）
    - [MM-DD] [标题]：摘要 [来源：XXX #N]
    ### 关键洞察（2-3条）
    从业者视角的 actionable 建议"""
            client = ClaudeClient()
            prompt = f"请总结以下自定义新闻（共{len(all_filtered)}条，来源：{', '.join(selected_sources)}）：\n\n{combined_prompt}"
            summary = client.chat(SYSTEM_PROMPT, [{"role": "user", "content": prompt}])

            if not summary or not summary.strip():
                self.root.after(0, lambda: self._log("AI返回空内容"))
                self.root.after(500, lambda: self._progress_frame.pack_forget())
                return

            self._set_progress(80, "生成报告中...")

            # 生成HTML
            from report.report_generator import _summary_to_html
            today_str = datetime.now().strftime("%Y年%m月%d日")
            news_html = _summary_to_html(summary, articles=all_filtered)

            html = f"""<!DOCTYPE html>
    <html lang="zh-CN">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{today_str} 自定义日报</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
                         "Microsoft YaHei", "Noto Sans SC", sans-serif;
            background: #f0f2f5; color: #1a1a2e; line-height: 1.9;
        }}
        .container {{ max-width: 860px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white; padding: 48px 36px; border-radius: 16px; margin-bottom: 24px;
        }}
        .header h1 {{ font-size: 28px; font-weight: 700; }}
        .header .date {{ font-size: 16px; opacity: 0.8; margin-top: 8px; }}
        .header .sources {{ font-size: 12px; opacity: 0.6; margin-top: 4px; }}
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
        .section ul {{ padding-left: 20px; }}
        .section li {{ margin-bottom: 8px; font-size: 15px; }}
        .section li::marker {{ color: #667eea; }}
        .source-link {{
            display: inline-block; background: #eef0ff; color: #5b6abf;
            font-size: 12px; padding: 1px 10px; border-radius: 10px;
            margin: 0 2px; white-space: nowrap; text-decoration: none;
        }}
        .source-link:hover {{ background: #d0d5ff; text-decoration: underline; }}
        .source-tag {{
            display: inline-block; background: #eef0ff; color: #5b6abf;
            font-size: 12px; padding: 1px 10px; border-radius: 10px; margin: 0 2px;
        }}
        .footer {{ text-align: center; color: #aaa; font-size: 12px; padding: 20px; }}
    </style>
    </head>
    <body>
    <div class="container">
        <div class="header">
            <h1>自定义日报</h1>
            <div class="date">{today_str}</div>
            <div class="sources">数据来源：{', '.join(selected_sources)}</div>
        </div>
        <div class="section">{news_html}</div>
        <div class="footer">
            <p>由人工智能自动生成 · {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
        </div>
    </div>
    </body>
    </html>"""

            filename = f"{today_str}自定义日报.html"
            filepath = self.month_dir / filename
            filepath.write_text(html, encoding="utf-8")
            self._set_progress(100, "完成")

            self.root.after(0, lambda: self._log(f"自定义日报已生成: {filepath.name}"))
            self.root.after(500, lambda: webbrowser.open(str(filepath)))
            self.root.after(1500, lambda: self._progress_frame.pack_forget())
        except Exception as e:
            import traceback
            self.root.after(0, lambda: self._log(f"自定义日报生成失败: {e}"))
            self.root.after(0, lambda: self._log(traceback.format_exc()[:300]))
            self.root.after(500, lambda: self._progress_frame.pack_forget())

    def _open_reports(self):
        opened = False
        for pattern, icon in [("*时政日报.html", "时政"), ("*AI日报.html", "AI")]:
            files = sorted(self.month_dir.glob(pattern), reverse=True)
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


def launch_app():
    """启动入口：先登录，后进入主界面"""
    # 确保数据库初始化
    try:
        from system.database import init_db
        init_db()
    except Exception as e:
        print(f"数据库初始化失败: {e}")

    # 显示登录窗口
    from system.login_dialog import LoginDialog
    login = LoginDialog()
    user = login.run()
    if not user:
        # 用户关闭登录窗口
        return

    # 登录成功，设置用户专属目录
    username = user.get('username', 'default')
    from config import set_current_user
    set_current_user(username)

    # 启动主界面
    root = tk.Tk()
    app = NewsDailyGUI(root, username)
    root.title(f"AI新闻日报系统 - {username}")
    root.mainloop()


if __name__ == "__main__":
    try:
        launch_app()
    except Exception as e:
        import traceback
        try:
            crash_log = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).parent / "crash_error.log"
            crash_log.write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        raise
