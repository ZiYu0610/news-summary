"""AI新闻总结模块
使用Claude API对采集的新闻进行结构化总结和分析。
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from config import CLAUDE_API_KEY, CLAUDE_API_BASE_URL, CLAUDE_API_MODEL

logger = logging.getLogger(__name__)

# ==================== Claude API 客户端 ====================

class ClaudeClient:
    """AI API 客户端（支持 Anthropic 和 OpenAI 兼容协议自动切换）"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or CLAUDE_API_KEY
        self.model = model or CLAUDE_API_MODEL
        self.base_url = (CLAUDE_API_BASE_URL or "").rstrip("/")
        self._client = None

    def _is_anthropic(self):
        """检测是否为 Anthropic 协议"""
        return not self.base_url or "anthropic" in self.base_url.lower()

    def _ensure_client(self):
        if self._client is not None:
            return
        if self._is_anthropic():
            self._init_anthropic()
        else:
            self._init_httpx()

    def _init_anthropic(self):
        try:
            from anthropic import Anthropic
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = Anthropic(**kwargs)
        except ImportError:
            logger.error("anthropic SDK 未安装，请执行: pip install anthropic")
            raise
        except Exception as e:
            logger.error(f"初始化Anthropic客户端失败: {e}")
            raise

    def _init_httpx(self):
        self._client = "httpx"  # 标记为httpx模式

    def chat(self, system: str, messages: List[Dict], max_tokens: int = 4096) -> str:
        self._ensure_client()
        if self._is_anthropic():
            return self._chat_anthropic(system, messages, max_tokens)
        else:
            return self._chat_openai(system, messages, max_tokens)

    def _chat_anthropic(self, system, messages, max_tokens):
        try:
            resp = self._client.messages.create(
                model=self.model,
                system=system,
                max_tokens=max_tokens,
                messages=messages,
            )
            for block in resp.content:
                if hasattr(block, "text") and block.text:
                    return block.text
                if hasattr(block, "thinking") and block.thinking:
                    continue
            return str(resp.content[0])
        except Exception as e:
            logger.error(f"Anthropic API调用失败: {e}")
            raise

    def _chat_openai(self, system, messages, max_tokens):
        import httpx
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": max_tokens,
        }
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                finish = choice.get("finish_reason", "")
                msg = choice.get("message", {})
                content = msg.get("content", "")
                logger.info(f"API响应: finish={finish}, content空={not content}")
                if not content:
                    # 可能是 reasoning 模型，检查 reasoning_content
                    rc = msg.get("reasoning_content", "")
                    if rc:
                        logger.info("检测到 reasoning_content，使用推理内容")
                        return rc[:100]
                    logger.info(f"完整choice: {str(choice)[:200]}")
                    return ""
                return content
            logger.info(f"API响应结构异常: {str(data)[:200]}")
            return str(data)
        except Exception as e:
            logger.error(f"OpenAI兼容API调用失败: {e}")
            raise


# ==================== 总结 Prompt 模板 ====================

POLITICAL_SUMMARY_SYSTEM = """你是一位专业的新闻分析师。请对以下时政新闻进行总结。
所有新闻均来自国内权威媒体。严格去重——同一新闻若出现多次只保留一次。

输出格式（每条末尾加 [来源：XXX]）：

## 今日时政要闻

### 央视报道（请优先从央视新闻源中提取最重要的新闻放于此栏目）
- [标题]：一句话摘要 [来源：央视新闻]

### 要闻精选
- [标题]：一句话摘要 [来源：XXX]

### 政策与经济
- [标题]：一句话摘要 [来源：XXX]

### 社会与民生
- [标题]：一句话摘要 [来源：XXX]

要求：
1. 每条新闻控制在50字以内，末尾必须标注来源
2. 央视报道栏目置于最上方，优先展示央视新闻内容
3. 如某条新闻涉及"人工智能""AI""大模型""智能"等关键词，请在该条前加上 [AI相关] 标记
4. 按重要程度排序
5. 客观陈述，不加评论
6. 严格去重，同一新闻无论来自几个源，只保留一条
7. 优先保留央视、新华社、人民日报等国内权威来源的版本
"""

INDUSTRY_SUMMARY_SYSTEM = """你是一位专注AI影视传媒（AIGC视频/AI影视/AI广告）领域的行业分析师。
你的用户是做AI漫剧短剧、AI广告、AI宣传片方向的创业者。

请对以下行业新闻进行分析总结。每条必须标注来源！严格去重！

输出格式（每条末尾加 [来源：XXX]）：

## 🎯 AIGC行业日报

### 🔥 今日焦点
- [标题]：核心内容 + 行业影响分析 [来源：XXX]

### 🏢 大公司动态
- [公司名]：[动态简述 + 战略意义] [来源：XXX]

### 🚀 产品技术更新
（重点：AI视频生成、AI影视工具、AI广告平台、数字人、AI配音等）
- [产品/技术名]：[更新内容 + 对AI影视/广告的影响] [来源：XXX]

### 📊 市场与投融资
- [事件]：[金额/规模 + 趋势判断] [来源：XXX]

### 💡 对AI影视传媒从业者的启示
从AI漫剧短剧、AI广告、AI宣传片的角度，总结3-5条 actionable 洞察（每条末尾不加来源）

要求：
1. 每条控制在80字以内，末尾标注 [来源：XXX]
2. **重点聚焦**：AI视频生成、AI短剧、AI影视制作、AI广告投放、AI宣传片、数字人、AI配音等领域
3. 过滤掉与AI影视传媒无关的纯硬件/底层技术新闻
4. 严格去重，相同内容只保留一条，优先保留信息来源更权威的版本
5. 提供可执行的商业洞察
"""

COMBINED_SUMMARY_SYSTEM = """你是一位专业的新闻分析师和AI影视传媒行业专家。
请综合时政新闻和行业新闻，生成一份完整的日报。

**核心要求：**
1. 每条总结末尾必须标注来源，格式：[来源：XXX]
2. 严格去重，同一新闻无论从几个渠道来，只保留一条
3. 重点聚焦与AI影视传媒（AI视频生成、AI短剧、AI广告、AI宣传片、数字人等）相关的内容
4. 过滤掉纯硬件/底层技术新闻（除非对AI影视行业有直接影响）

输出格式：

## 📰 今日时政要闻
（提取最重要的3-5条，每条一句话 + [来源：XXX]）

## 🎯 AIGC行业日报

### 🔥 今日焦点
（2-3条最重要的行业新闻，含行业影响分析 + [来源：XXX]）

### 🏢 大公司动态
（大厂在AI影视/AIGC领域的最新动作 + [来源：XXX]）

### 🚀 产品技术更新
（AI视频生成、AI短剧、AI广告、AI宣传片、数字人、AI配音等领域的技术和产品更新 + [来源：XXX]）

### 📊 市场与投融资
（投融资事件、价格变化、市场趋势 + [来源：XXX]）

### 💡 对AI影视传媒从业者的启示
（3-5条 actionable 商业洞察，针对AI漫剧短剧、AI广告、AI宣传片方向。**这部分不加来源**）

## 🌐 舆论风向
（社交媒体或行业讨论热点，如有则带来源）

要求：语言简洁有力，重在 actionable 的信息。每条新闻总结必须带 [来源：XXX] 标注。"""


# ==================== 总结函数 ====================

def _format_articles_for_prompt(articles: List[Dict], max_count: int = 30) -> str:
    """将文章列表格式化为prompt文本（含来源链接）"""
    lines = []
    for i, art in enumerate(articles[:max_count], 1):
        title = art.get("title", "无标题")
        summary = art.get("summary", "")
        source = art.get("source", "未知来源")
        link = art.get("link", "")
        lines.append(f"{i}. [{source}] {title}")
        if link:
            lines.append(f"   链接: {link}")
        if summary:
            lines.append(f"   摘要: {summary[:200]}")
    return "\n".join(lines)


def summarize_political(news_list: List[Dict], client: Optional[ClaudeClient] = None) -> str:
    """总结时政新闻"""
    if not news_list:
        return "## 📰 今日时政要闻\n\n暂无时政新闻数据。"

    if client is None:
        client = ClaudeClient()

    content = _format_articles_for_prompt(news_list)
    prompt = f"请总结以下时政新闻（今天是{datetime.now().strftime('%Y年%m月%d日')}）：\n\n{content}"

    try:
        return client.chat(POLITICAL_SUMMARY_SYSTEM, [{"role": "user", "content": prompt}])
    except Exception as e:
        logger.error(f"时政新闻总结失败: {e}")
        return _fallback_summary(news_list, "时政要闻")


def summarize_industry(news_list: List[Dict], client: Optional[ClaudeClient] = None) -> str:
    """总结AIGC行业新闻"""
    if not news_list:
        return "## 🎯 AIGC行业日报\n\n暂无行业新闻数据。"

    if client is None:
        client = ClaudeClient()

    content = _format_articles_for_prompt(news_list)
    prompt = f"请分析总结以下AIGC行业新闻（今天是{datetime.now().strftime('%Y年%m月%d日')}）：\n\n{content}"

    try:
        return client.chat(INDUSTRY_SUMMARY_SYSTEM, [{"role": "user", "content": prompt}])
    except Exception as e:
        logger.error(f"行业新闻总结失败: {e}")
        return _fallback_summary(news_list, "AIGC行业")


def summarize_all(news_data: Dict[str, List[Dict]], client: Optional[ClaudeClient] = None) -> Dict[str, str]:
    """综合总结所有新闻"""
    result = {}

    if client is None:
        try:
            client = ClaudeClient()
        except Exception as e:
            logger.warning(f"Claude客户端初始化失败: {e}，使用备用总结模式")
            for category in ["political", "industry"]:
                items = news_data.get(category, [])
                result[category] = _fallback_summary(items, category)
            return result

    political_list = news_data.get("political", [])
    industry_list = news_data.get("industry", [])

    if political_list and industry_list:
        # 综合模式
        combined = "=== 时政新闻 ===\n"
        combined += _format_articles_for_prompt(political_list)
        combined += "\n\n=== AIGC行业新闻 ===\n"
        combined += _format_articles_for_prompt(industry_list)
        combined += "\n\n【要求】每条总结末尾标注来源名称。[来源：XXX]"
        prompt = f"请生成今日综合日报（{datetime.now().strftime('%Y年%m月%d日')}）：\n\n{combined}"
        try:
            full = client.chat(COMBINED_SUMMARY_SYSTEM, [{"role": "user", "content": prompt}])
            result["political"] = full  # 综合报告放在political字段
            result["industry"] = ""  # industry不需要再单独生成
            result["combined"] = True
            return result
        except Exception as e:
            logger.error(f"综合总结失败: {e}，降级到分别总结")

    # 分别总结
    result["political"] = summarize_political(political_list, client)
    result["industry"] = summarize_industry(industry_list, client)
    result["combined"] = False
    return result


def _fallback_summary(news_list: List[Dict], category: str) -> str:
    """联网API不可用时的备用总结（简单排序输出）"""
    if not news_list:
        return f"## {category}\n\n暂无数据。"

    lines = [f"## {category}（自动摘要）\n"]
    for i, art in enumerate(news_list[:15], 1):
        title = art.get("title", "无标题")
        source = art.get("source", "未知")
        lines.append(f"{i}. [{source}] {title}")
    return "\n".join(lines)
