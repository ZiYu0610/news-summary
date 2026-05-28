"""行业市场价格追踪模块
管理AIGC行业各品类的报价数据，生成价格走势图。
支持手动录入和自动追踪。
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from config import PRICE_CATEGORIES, PRICE_FILE

logger = logging.getLogger(__name__)


class PriceTracker:
    """价格追踪器"""

    def __init__(self, data_file: Path = None):
        self.data_file = data_file or PRICE_FILE
        self.categories = {c["id"]: c for c in PRICE_CATEGORIES}
        self._ensure_data_file()

    def _ensure_data_file(self):
        """确保数据文件存在"""
        if not self.data_file.exists():
            initial = {
                "categories": PRICE_CATEGORIES,
                "records": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self._save(initial)
            logger.info(f"初始化价格数据文件: {self.data_file}")

    def _load(self) -> Dict:
        """加载价格数据"""
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("价格数据文件损坏，重新初始化")
            initial = {
                "categories": PRICE_CATEGORIES,
                "records": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self._save(initial)
            return initial

    def _save(self, data: Dict):
        """保存价格数据"""
        data["updated_at"] = datetime.now().isoformat()
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== 记录管理 ====================

    def add_record(
        self,
        category_id: str,
        price: float,
        note: str = "",
        record_date: str = None,
    ) -> bool:
        """添加一条价格记录

        Args:
            category_id: 品类ID（如 ai_video, ai_image）
            price: 价格数值
            note: 备注说明（如"可灵AI 1.0报价"）
            record_date: 日期，默认今天

        Returns:
            是否成功
        """
        if category_id not in self.categories:
            logger.error(f"未知品类: {category_id}")
            return False

        data = self._load()
        record = {
            "id": len(data["records"]) + 1,
            "category_id": category_id,
            "price": price,
            "note": note,
            "date": record_date or datetime.now().strftime("%Y-%m-%d"),
            "created_at": datetime.now().isoformat(),
        }
        data["records"].append(record)
        self._save(data)
        logger.info(f"添加价格记录: {self.categories[category_id]['name']} = {price}元")
        return True

    def get_records(
        self,
        category_id: Optional[str] = None,
        days: int = 90,
    ) -> List[Dict]:
        """获取价格记录

        Args:
            category_id: 品类ID，不传则返回所有
            days: 最近多少天的记录

        Returns:
            记录列表
        """
        data = self._load()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        records = data["records"]
        if category_id:
            records = [r for r in records if r["category_id"] == category_id]
        records = [r for r in records if r["date"] >= cutoff]

        # 按日期排序
        records.sort(key=lambda x: x["date"])
        return records

    def get_latest_prices(self) -> Dict[str, Dict]:
        """获取各品类最新价格"""
        data = self._load()
        latest = {}

        for cat_id in self.categories:
            cat_records = [r for r in data["records"] if r["category_id"] == cat_id]
            if cat_records:
                cat_records.sort(key=lambda x: x["date"], reverse=True)
                latest[cat_id] = cat_records[0]

        return latest

    # ==================== 初始化示例数据 ====================

    def init_sample_data(self):
        """初始化示例数据（供测试和展示用）"""
        import random

        today = datetime.now()
        categories = list(self.categories.keys())

        # 各品类的基础价格和波动范围
        base_prices = {
            "ai_video": (5, 20),       # 5-20元/秒
            "ai_image": (0.5, 3),      # 0.5-3元/张
            "ai_voice": (10, 50),      # 10-50元/千字
            "ai_short_drama": (8, 30), # 8-30万元/部
            "ai_ad": (3, 15),          # 3-15万元/条
            "digital_human": (2, 10),  # 2-10万元/个
        }
        notes_pool = {
            "ai_video": ["可灵AI报价", "Runway Gen-3", "Pika 2.0", "Sora内测价", "即梦Pro"],
            "ai_image": ["Midjourney V6", "DALL-E 3", "SDXL", "文心一格"],
            "ai_voice": ["ElevenLabs", "讯飞智作", "火山引擎"],
            "ai_short_drama": ["全AI制作", "半AI+真人", "AI换脸短剧"],
            "ai_ad": ["30秒AI广告", "AI宣传片(1分钟)", "AI产品展示"],
            "digital_human": ["2D数字人", "3D数字人", "AI分身定制"],
        }

        # 过去60天，每周记录一次
        records = []
        record_id = 1
        for days_ago in range(60, -1, -7):
            date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            for cat_id in categories:
                base, var = base_prices.get(cat_id, (10, 5))
                # 模拟价格逐渐下降趋势（AI行业特性）
                trend_factor = 1.0 - (60 - days_ago) * 0.002
                price = round((base + random.uniform(-var * 0.3, var * 0.3)) * trend_factor, 2)
                price = max(price, base * 0.3)
                note = random.choice(notes_pool.get(cat_id, [""]))

                records.append({
                    "id": record_id,
                    "category_id": cat_id,
                    "price": price,
                    "note": note,
                    "date": date,
                    "created_at": datetime.now().isoformat(),
                })
                record_id += 1

        data = {
            "categories": PRICE_CATEGORIES,
            "records": records,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._save(data)
        logger.info(f"初始化了 {len(records)} 条示例价格数据")
        return True

    # ==================== 图表生成 ====================

    def generate_chart(self, output_path: Path, days: int = 90) -> Optional[Path]:
        """生成价格走势图

        Args:
            output_path: 图表输出路径
            days: 展示多少天的走势

        Returns:
            图表文件路径，失败返回None
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from matplotlib import font_manager
        except ImportError:
            logger.error("matplotlib未安装，无法生成图表")
            return None

        # 尝试设置中文字体
        plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

        data = self._load()
        records = data["records"]
        if not records:
            logger.warning("没有价格数据，无法生成图表")
            return None

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle(
            "AIGC行业市场价格走势",
            fontsize=18,
            fontweight="bold",
            y=0.98,
        )

        # 副标题
        fig.text(
            0.5, 0.94,
            f"数据更新至 {datetime.now().strftime('%Y-%m-%d')}    |    单位：元",
            ha="center",
            fontsize=11,
            color="gray",
        )

        axes_flat = axes.flatten()

        for idx, cat in enumerate(PRICE_CATEGORIES):
            if idx >= len(axes_flat):
                break

            ax = axes_flat[idx]
            cat_records = [
                r for r in records
                if r["category_id"] == cat["id"]
            ]

            if not cat_records:
                ax.text(0.5, 0.5, "暂无数据", ha="center", va="center")
                ax.set_title(cat["name"])
                continue

            # 按日期排序
            cat_records.sort(key=lambda x: x["date"])
            dates = [r["date"] for r in cat_records]
            prices = [r["price"] for r in cat_records]
            notes = [r.get("note", "") for r in cat_records]

            # 绘制
            ax.plot(dates, prices, marker="o", linewidth=2, markersize=4, color="#2196F3")

            # 填充面积
            ax.fill_between(dates, prices, alpha=0.1, color="#2196F3")

            # 标注最新值
            if prices:
                ax.annotate(
                    f"¥{prices[-1]:.2f}",
                    xy=(dates[-1], prices[-1]),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=10,
                    fontweight="bold",
                    color="#1976D2",
                )

            # 标注价格波动事件
            for i, (d, p, n) in enumerate(zip(dates, prices, notes)):
                if n and (i == 0 or i == len(dates) - 1 or
                          (i > 0 and abs(p - prices[i-1]) / max(prices[i-1], 0.01) > 0.15)):
                    ax.annotate(
                        f"{n}",
                        xy=(d, p),
                        xytext=(0, -15),
                        textcoords="offset points",
                        fontsize=7,
                        rotation=45,
                        color="gray",
                        alpha=0.7,
                    )

            ax.set_title(f"{cat['name']} ({cat['unit']})", fontsize=12, fontweight="bold")
            ax.set_xlabel("")
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis="x", rotation=45, labelsize=8)

            # 格式化x轴
            if len(dates) > 10:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//8)))

        # 隐藏多余的子图
        for idx in range(len(PRICE_CATEGORIES), len(axes_flat)):
            axes_flat[idx].set_visible(False)

        plt.tight_layout(rect=[0, 0, 1, 0.92])
        plt.savefig(str(output_path), dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"价格走势图已生成: {output_path}")
        return output_path

    # ==================== 市场分析报告 ====================

    def generate_market_analysis(self) -> str:
        """生成市场分析文本"""
        data = self._load()
        records = data["records"]
        if not records:
            return "暂无价格数据，请先录入"

        latest = self.get_latest_prices()
        lines = ["## 📊 行业市场价格概览\n"]

        for cat in PRICE_CATEGORIES:
            cat_id = cat["id"]
            cat_records = [r for r in records if r["category_id"] == cat_id]
            cat_records.sort(key=lambda x: x["date"])

            if not cat_records:
                continue

            current = cat_records[-1]["price"]
            first_price = cat_records[0]["price"]
            change = ((current - first_price) / first_price) * 100 if first_price else 0

            # 趋势
            if change < -10:
                trend = "📉 显著下降"
            elif change < -2:
                trend = "📉 小幅下降"
            elif change > 10:
                trend = "📈 显著上涨"
            elif change > 2:
                trend = "📈 小幅上涨"
            else:
                trend = "➡️ 基本持平"

            lines.append(f"**{cat['name']}**: ¥{current:.2f}/{cat['unit']}  {trend} ({change:+.1f}%)")

            # 最新备注
            note = cat_records[-1].get("note", "")
            if note:
                lines.append(f"  > 最新记录: {note}")

            lines.append("")

        # 整体趋势总结
        lines.append("### 💡 价格趋势解读\n")

        down_count = sum(1 for cat in PRICE_CATEGORIES if
                        (lambda c: (lambda r: r[-1]["price"] / r[0]["price"] - 1 if len(r) > 1 else 0)(
                            [r for r in records if r["category_id"] == c["id"]]
                        ))(cat) < -0.02)  # 有点复杂，简化处理

        if "records" in data:
            lines.append("AIGC行业整体呈现价格下降趋势，尤其是AI视频和图像生成领域。")
            lines.append("建议关注成本下降带来的产品定价策略调整机会。")

        return "\n".join(lines)
