"""系统登录/注册窗口"""
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from config import DATA_DIR

C = {
    "bg": "#0f0c29", "card": "#1a1740", "primary": "#667eea",
    "text": "#e2e8f0", "text2": "#94a3b8", "error": "#ef4444", "success": "#27ae60",
    "entry_bg": "#2d2b55", "border": "#2d2b55",
}
TOKEN_FILE = DATA_DIR / ".auto_login"


class LoginDialog:
    def __init__(self):
        self.result = None
        self.root = tk.Tk()
        self.root.title("AI新闻日报 - 登录")
        self.root.configure(bg=C["bg"])
        self.root.resizable(False, False)
        self._mode = "login"

        self._build()
        self._center(400, 500)
        self.root.after(300, self._auto_login)

    def _center(self, w, h):
        self.root.geometry(f"{w}x{h}")
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        # 标题
        tk.Frame(self.root, bg=C["bg"], pady=28).pack(fill="x")
        tk.Label(self.root, text="AI 新闻日报系统",
                 font=("Microsoft YaHei", 18, "bold"), fg="white", bg=C["bg"]).pack()
        tk.Label(self.root, text="每日时政 · AIGC行业 · 智能总结",
                 font=("Microsoft YaHei", 9), fg=C["text2"], bg=C["bg"]).pack(pady=(2, 0))

        # 卡片
        card = tk.Frame(self.root, bg=C["card"], padx=30, pady=16,
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # Tab 切换
        tab = tk.Frame(card, bg=C["card"])
        tab.pack(fill="x")
        self._tab_login = tk.Button(tab, text="登录", font=("Microsoft YaHei", 12, "bold"),
                                     bg=C["primary"], fg="white", relief="flat", padx=20, pady=4,
                                     cursor="hand2", command=lambda: self._switch("login"))
        self._tab_login.pack(side="left", expand=True, padx=(0, 4))
        self._tab_reg = tk.Button(tab, text="注册", font=("Microsoft YaHei", 12),
                                   bg=C["card"], fg=C["text2"], relief="flat", padx=20, pady=4,
                                   cursor="hand2", command=lambda: self._switch("register"))
        self._tab_reg.pack(side="left", expand=True, padx=(4, 0))

        # 表单容器
        self._form = tk.Frame(card, bg=C["card"])
        self._form.pack(fill="both", expand=True, pady=12)

        # 错误提示
        self._err = tk.Label(self._form, text="", font=("Microsoft YaHei", 9),
                              fg=C["error"], bg=C["card"])
        self._err.pack()

        # 初始为登录表单
        self._build_login()

    # ========== 表单切换 ==========

    def _switch(self, mode):
        self._mode = mode
        for w in self._form.winfo_children():
            w.destroy()
        # Tab 样式
        active = {"bg": C["primary"], "fg": "white", "font": ("Microsoft YaHei", 12, "bold")}
        inactive = {"bg": C["card"], "fg": C["text2"], "font": ("Microsoft YaHei", 12)}
        self._tab_login.configure(**(active if mode == "login" else inactive))
        self._tab_reg.configure(**(active if mode == "register" else inactive))
        # 重新创建错误标签
        self._err = tk.Label(self._form, text="", font=("Microsoft YaHei", 9),
                              fg=C["error"], bg=C["card"])
        self._err.pack()
        if mode == "login":
            self._build_login()
        else:
            self._build_register()

    def _input(self, label, show=""):
        """创建一行输入框"""
        row = tk.Frame(self._form, bg=C["card"])
        row.pack(fill="x", pady=(6, 0))
        tk.Label(row, text=label, font=("Microsoft YaHei", 10),
                 fg=C["text"], bg=C["card"]).pack(anchor="w")
        e = tk.Entry(row, font=("Microsoft YaHei", 11), bg=C["entry_bg"],
                      fg="white", insertbackground="white", relief="flat", bd=0, show=show)
        e.pack(fill="x", ipady=6, pady=(2, 0))
        return e

    def _show_btn(self, entry):
        """密码框旁的显示/隐藏按钮"""
        btn = tk.Button(self._form, text="显示", font=("Microsoft YaHei", 8),
                         fg=C["text2"], bg=C["card"], relief="flat", cursor="hand2")
        def toggle():
            if entry.cget("show") == "*":
                entry.configure(show=""); btn.configure(text="隐藏")
            else:
                entry.configure(show="*"); btn.configure(text="显示")
        btn.configure(command=toggle)
        btn.pack(anchor="e")

    # ========== 登录表单 ==========

    def _build_login(self):
        self._u = self._input("用户名")
        self._p = self._input("密码", show="*")
        self._show_btn(self._p)

        self._rem = tk.BooleanVar(value=True)
        tk.Checkbutton(self._form, text="记住登录状态（30天免登录）",
                       variable=self._rem, font=("Microsoft YaHei", 9),
                       fg=C["text2"], bg=C["card"], selectcolor=C["card"],
                       activebackground=C["card"], cursor="hand2").pack(anchor="w", pady=(8, 2))

        tk.Button(self._form, text="登  录", font=("Microsoft YaHei", 16, "bold"),
                  bg=C["primary"], fg="white", relief="flat", pady=14, cursor="hand2",
                  command=self._do_login).pack(fill="x", pady=(6, 0))
        self.root.bind("<Return>", lambda e: self._do_login())

    def _do_login(self):
        u, p = self._u.get().strip(), self._p.get()
        if not u or not p:
            self._err.configure(text="请输入用户名和密码"); return
        from system.database import login_user, create_auto_login
        r = login_user(u, p)
        if r["success"]:
            if self._rem.get():
                t = create_auto_login(r["user_id"])
                TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
                TOKEN_FILE.write_text(t, encoding="utf-8")
            self.result = r
            self.root.destroy()
        else:
            self._err.configure(text=r["msg"])

    # ========== 注册表单 ==========

    def _build_register(self):
        self._ru = self._input("用户名")
        self._rp = self._input("密码", show="*")
        self._show_btn(self._rp)
        self._rc = self._input("确认密码", show="*")
        self._show_btn(self._rc)

        tk.Button(self._form, text="注  册", font=("Microsoft YaHei", 16, "bold"),
                  bg=C["success"], fg="white", relief="flat", pady=14, cursor="hand2",
                  command=self._do_register).pack(fill="x", pady=(10, 0))
        self.root.bind("<Return>", lambda e: self._do_register())

    def _do_register(self):
        u, p, c = self._ru.get().strip(), self._rp.get(), self._rc.get()
        if not u or not p:
            self._err.configure(text="请填写完整信息"); return
        if p != c:
            self._err.configure(text="两次密码不一致"); return
        from system.database import register_user
        r = register_user(u, p)
        if r["success"]:
            messagebox.showinfo("✅ 注册成功", f"账号 [{u}] 注册成功！\n点击确定后自动切换到登录页")
            self._switch("login")
            self._u.delete(0, "end")
            self._u.insert(0, u)
            self._p.focus()
        else:
            self._err.configure(text=r["msg"])

    # ========== 自动登录 ==========

    def _auto_login(self):
        if not TOKEN_FILE.exists():
            return
        try:
            token = TOKEN_FILE.read_text(encoding="utf-8").strip()
            if not token:
                return
            from system.database import verify_auto_login
            user = verify_auto_login(token)
            if user:
                self.result = user
                self.root.destroy()
            else:
                TOKEN_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    def run(self):
        self.root.mainloop()
        return self.result
