"""本地SQLite数据库
存储新闻、报告、价格数据、登录会话等，无需安装任何额外软件。
"""
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from config import DATA_DIR

logger = logging.getLogger(__name__)

DB_FILE = DATA_DIR / "news_summary.db"


def get_conn() -> sqlite3.Connection:
    """获取数据库连接"""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ==================== 表结构 ====================

SCHEMA = """
-- 新闻文章（原始采集）
CREATE TABLE IF NOT EXISTS news_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    content TEXT DEFAULT '',
    category TEXT DEFAULT 'industry',
    collected_at TEXT DEFAULT (datetime('now', 'localtime')),
    report_date TEXT DEFAULT (date('now'))
);

-- 日报记录
CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT NOT NULL,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    report_date TEXT DEFAULT (date('now'))
);

-- 价格记录
CREATE TABLE IF NOT EXISTS price_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id TEXT NOT NULL,
    price REAL NOT NULL,
    unit TEXT DEFAULT '',
    note TEXT DEFAULT '',
    record_date TEXT DEFAULT (date('now'))
);

-- 信息来源映射（用于溯源匹配）
CREATE TABLE IF NOT EXISTS source_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL UNIQUE,
    source_url TEXT DEFAULT '',
    category TEXT DEFAULT 'industry',
    is_active INTEGER DEFAULT 1
);

-- 登录会话
CREATE TABLE IF NOT EXISTS login_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id TEXT NOT NULL UNIQUE,
    site_name TEXT NOT NULL,
    cookies TEXT DEFAULT '[]',
    logged_in_at TEXT DEFAULT NULL,
    is_active INTEGER DEFAULT 0
);

-- API配置历史
CREATE TABLE IF NOT EXISTS api_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key_masked TEXT DEFAULT '',
    base_url TEXT DEFAULT '',
    model TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 用户账号
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    last_login TEXT DEFAULT NULL
);

-- 自动登录令牌
CREATE TABLE IF NOT EXISTS auto_login_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_articles_date ON news_articles(report_date);
CREATE INDEX IF NOT EXISTS idx_articles_source ON news_articles(source);
CREATE INDEX IF NOT EXISTS idx_reports_date ON daily_reports(report_date);
CREATE INDEX IF NOT EXISTS idx_prices_date ON price_records(record_date);
CREATE INDEX IF NOT EXISTS idx_users_name ON users(username);
CREATE INDEX IF NOT EXISTS idx_auto_login_token ON auto_login_tokens(token);
"""


# ==================== 初始化 ====================

def init_db():
    """初始化数据库，创建表"""
    conn = get_conn()
    try:
        for statement in SCHEMA.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(stmt)
        conn.commit()
        logger.info(f"数据库已初始化: {DB_FILE}")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    finally:
        conn.close()


# ==================== 新闻文章 ====================

def save_articles(articles: List[Dict], category: str = "industry"):
    """批量保存新闻文章"""
    conn = get_conn()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        for art in articles:
            conn.execute(
                """INSERT OR IGNORE INTO news_articles
                   (title, source, source_url, summary, category, collected_at, report_date)
                   VALUES (?, ?, ?, ?, ?, datetime('now','localtime'), ?)""",
                (
                    art.get("title", "")[:300],
                    art.get("source", "未知"),
                    art.get("link", ""),
                    art.get("summary", "")[:500],
                    category,
                    today,
                ),
            )
        conn.commit()
        logger.info(f"已保存 {len(articles)} 条{category}新闻到数据库")
    except Exception as e:
        logger.error(f"保存新闻失败: {e}")
    finally:
        conn.close()


def get_articles_by_date(report_date: str = None, category: str = None, limit: int = 50) -> List[Dict]:
    """按日期查询新闻"""
    conn = get_conn()
    try:
        date = report_date or datetime.now().strftime("%Y-%m-%d")
        query = "SELECT * FROM news_articles WHERE report_date = ?"
        params = [date]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ==================== 日报记录 ====================

def save_report(report_type: str, title: str, file_path: str):
    """保存日报记录"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO daily_reports (report_type, title, file_path) VALUES (?, ?, ?)",
            (report_type, title, str(file_path)),
        )
        conn.commit()
    finally:
        conn.close()


def get_reports(limit: int = 20) -> List[Dict]:
    """获取日报历史"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM daily_reports ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ==================== 价格记录 ====================

def save_price_record(category_id: str, price: float, unit: str = "", note: str = ""):
    """保存价格记录"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO price_records (category_id, price, unit, note) VALUES (?, ?, ?, ?)",
            (category_id, price, unit, note),
        )
        conn.commit()
    finally:
        conn.close()


def get_price_history(category_id: str = None, days: int = 90) -> List[Dict]:
    """获取价格历史"""
    conn = get_conn()
    try:
        if category_id:
            rows = conn.execute(
                "SELECT * FROM price_records WHERE category_id = ? AND record_date >= date('now', ?) ORDER BY record_date",
                (category_id, f"-{days} days"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM price_records WHERE record_date >= date('now', ?) ORDER BY record_date",
                (f"-{days} days",),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ==================== 来源映射 ====================

def init_source_mappings():
    """初始化信息来源映射表"""
    mappings = [
        # 政策监管
        ("国家广电总局", "https://www.nrta.gov.cn/", "industry_policy"),
        ("中国网络视听节目服务协会", "http://www.cnsa.cn/", "industry_policy"),
        ("国家电影局", "https://www.chinafilm.gov.cn/", "industry_policy"),
        ("国务院政策文件库", "https://www.gov.cn/zhengce/", "industry_policy"),
        # 平台
        ("巨量引擎", "https://www.oceanengine.com/", "industry"),
        ("抖音电商学习中心", "https://school.jinritemai.com/", "industry"),
        ("抖音创作者中心", "https://creator.douyin.com/", "industry"),
        ("红果短剧", "https://www.hongguo.com/", "industry"),
        # 行业媒体
        ("TechCrunch", "https://techcrunch.com/", "industry"),
        ("ArsTechnica", "https://arstechnica.com/", "industry"),
        ("Variety", "https://variety.com/", "industry"),
        ("The Hollywood Reporter", "https://www.hollywoodreporter.com/", "industry"),
        ("爱范儿", "https://www.ifanr.com/", "industry"),
        ("36氪", "https://36kr.com/", "industry"),
        ("AI News", "https://www.artificialintelligence-news.com/", "industry"),
        ("Hacker News", "https://news.ycombinator.com/", "industry"),
        ("1905电影网", "https://www.1905.com/", "industry"),
        # 时政
        ("央视新闻", "https://news.cctv.com/", "political"),
        ("人民日报", "https://www.people.com.cn/", "political"),
        ("新华社", "http://www.xinhuanet.com/", "political"),
        ("环球网", "https://www.huanqiu.com/", "political"),
        ("中国新闻网", "https://www.chinanews.com.cn/", "political"),
        ("光明网", "https://www.gmw.cn/", "political"),
    ]
    conn = get_conn()
    try:
        for name, url, cat in mappings:
            conn.execute(
                "INSERT OR IGNORE INTO source_mappings (source_name, source_url, category) VALUES (?, ?, ?)",
                (name, url, cat),
            )
        conn.commit()
        logger.info(f"来源映射表已初始化 ({len(mappings)} 条)")
    finally:
        conn.close()


def get_source_url(source_name: str) -> str:
    """根据来源名称获取官网URL"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT source_url FROM source_mappings WHERE source_name = ?", (source_name,)
        ).fetchone()
        return row["source_url"] if row else ""
    finally:
        conn.close()


# ==================== 登录会话 ====================

def save_login_session(site_id: str, site_name: str, cookies: list):
    """保存登录会话"""
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO login_sessions (site_id, site_name, cookies, logged_in_at, is_active)
               VALUES (?, ?, ?, datetime('now','localtime'), 1)
               ON CONFLICT(site_id) DO UPDATE SET cookies=?, logged_in_at=datetime('now','localtime'), is_active=1""",
            (site_id, site_name, json.dumps(cookies, ensure_ascii=False), json.dumps(cookies, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def get_login_session(site_id: str) -> Optional[Dict]:
    """获取登录会话"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM login_sessions WHERE site_id = ? AND is_active = 1", (site_id,)
        ).fetchone()
        if row:
            result = dict(row)
            result["cookies"] = json.loads(result.get("cookies", "[]"))
            return result
        return None
    finally:
        conn.close()


def get_all_sessions() -> List[Dict]:
    """获取所有登录会话"""
    conn = get_conn()
    try:
        rows = conn.execute("SELECT site_id, site_name, is_active, logged_in_at FROM login_sessions").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ==================== 设置 ====================

def save_api_config(api_key: str, base_url: str, model: str):
    """保存API配置"""
    conn = get_conn()
    try:
        # 先标记旧的为非活跃
        conn.execute("UPDATE api_configs SET is_active = 0")
        masked = api_key[:8] + "..." if len(api_key) > 8 else ""
        conn.execute(
            "INSERT INTO api_configs (api_key_masked, base_url, model) VALUES (?, ?, ?)",
            (masked, base_url, model),
        )
        conn.commit()
    finally:
        conn.close()


def get_active_api_config() -> Optional[Dict]:
    """获取当前API配置"""
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM api_configs WHERE is_active = 1 ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ==================== 用户认证 ====================

import hashlib
import secrets


def _hash_password(password: str) -> str:
    """密码哈希"""
    salt = "NewsSummary2024!"
    return hashlib.sha256((password + salt).encode()).hexdigest()


def register_user(username: str, password: str) -> Dict:
    """注册新用户"""
    conn = get_conn()
    try:
        # 检查用户名是否已存在
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return {"success": False, "msg": "用户名已存在"}
        if len(username) < 2:
            return {"success": False, "msg": "用户名至少2个字符"}
        if len(password) < 4:
            return {"success": False, "msg": "密码至少4个字符"}
        pwd_hash = _hash_password(password)
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pwd_hash))
        conn.commit()
        user_id = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()["id"]
        return {"success": True, "msg": "注册成功", "user_id": user_id, "username": username}
    except Exception as e:
        return {"success": False, "msg": f"注册失败: {e}"}
    finally:
        conn.close()


def login_user(username: str, password: str) -> Dict:
    """用户登录验证"""
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            return {"success": False, "msg": "用户名或密码错误"}
        pwd_hash = _hash_password(password)
        if row["password_hash"] != pwd_hash:
            return {"success": False, "msg": "用户名或密码错误"}
        # 更新最后登录时间
        conn.execute("UPDATE users SET last_login = datetime('now','localtime') WHERE id = ?", (row["id"],))
        conn.commit()
        return {"success": True, "msg": "登录成功", "user_id": row["id"], "username": row["username"]}
    except Exception as e:
        return {"success": False, "msg": f"登录失败: {e}"}
    finally:
        conn.close()


def create_auto_login(user_id: int) -> str:
    """创建自动登录令牌（30天有效）"""
    conn = get_conn()
    try:
        # 清除旧令牌
        conn.execute("DELETE FROM auto_login_tokens WHERE user_id = ?", (user_id,))
        token = secrets.token_hex(32)
        conn.execute(
            "INSERT INTO auto_login_tokens (user_id, token, expires_at) VALUES (?, ?, datetime('now','+30 days'))",
            (user_id, token),
        )
        conn.commit()
        return token
    except Exception as e:
        logger.error(f"创建自动登录令牌失败: {e}")
        return ""
    finally:
        conn.close()


def verify_auto_login(token: str) -> Optional[Dict]:
    """验证自动登录令牌"""
    conn = get_conn()
    try:
        row = conn.execute(
            """SELECT u.id, u.username FROM auto_login_tokens t
               JOIN users u ON t.user_id = u.id
               WHERE t.token = ? AND t.expires_at > datetime('now','localtime')""",
            (token,),
        ).fetchone()
        if row:
            return {"user_id": row["id"], "username": row["username"]}
        return None
    finally:
        conn.close()


def remove_auto_login(token: str):
    """删除自动登录令牌"""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM auto_login_tokens WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


# ==================== 工具函数 ====================

def get_db_stats() -> Dict:
    """获取数据库统计信息"""
    conn = get_conn()
    try:
        stats = {}
        for table in ["news_articles", "daily_reports", "price_records", "login_sessions"]:
            row = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
            stats[table] = row["cnt"] if row else 0
        # 数据库文件大小
        stats["db_size_mb"] = round(DB_FILE.stat().st_size / 1024 / 1024, 2) if DB_FILE.exists() else 0
        return stats
    finally:
        conn.close()


def export_to_json(table: str) -> str:
    """导出表数据为JSON"""
    conn = get_conn()
    try:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 100").fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2)
    finally:
        conn.close()
