"""LLM 提供方抽象。所有分析代码只调 chat() / chat_json()，换模型改 .env 即可。
provider:
  anthropic       -> Claude（打标用 Haiku 便宜，周报可用更强模型）
  openai_compat   -> DeepSeek / Qwen / 任何 OpenAI 兼容接口
  mock            -> 无 key 时用关键词规则打标，仅用于跑通流程
"""
import re
import json
import logging
from typing import Optional

import config

log = logging.getLogger("analysis.llm")


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


class LLM:
    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider or config.LLM_PROVIDER
        self.model = model
        if self.provider == "anthropic":
            if not config.ANTHROPIC_API_KEY:
                log.warning("ANTHROPIC_API_KEY 为空，回退到 mock")
                self.provider = "mock"
            else:
                import anthropic
                self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
                self.model = model or config.ANTHROPIC_MODEL
        elif self.provider == "openai_compat":
            if not config.OPENAI_COMPAT_API_KEY:
                log.warning("OPENAI_COMPAT_API_KEY 为空，回退到 mock")
                self.provider = "mock"
            else:
                from openai import OpenAI
                self.client = OpenAI(api_key=config.OPENAI_COMPAT_API_KEY,
                                     base_url=config.OPENAI_COMPAT_BASE_URL)
                self.model = model or config.OPENAI_COMPAT_MODEL
        if self.provider == "mock":
            self.model = "mock"

    def chat(self, system: str, user: str, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        if self.provider == "anthropic":
            r = self.client.messages.create(
                model=self.model, max_tokens=max_tokens, temperature=temperature,
                system=system, messages=[{"role": "user", "content": user}])
            return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        if self.provider == "openai_compat":
            kwargs = dict(model=self.model, max_tokens=max_tokens, temperature=temperature,
                          messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            if "json" in system.lower():
                kwargs["response_format"] = {"type": "json_object"}
            r = self.client.chat.completions.create(**kwargs)
            msg = r.choices[0].message
            text = msg.content or ""
            if not text:  # 思考型模型偶尔正文为空
                text = getattr(msg, "reasoning_content", "") or ""
            return text
        return self._mock(system, user)

    def chat_json(self, system: str, user: str, **kw) -> Optional[dict]:
        text = self.chat(system, user, **kw)
        try:
            return json.loads(_strip_fence(text))
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.S)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            log.error("JSON 解析失败: %s", text[:300])
            return None

    # ---------- mock：关键词规则，只为跑通流程 ----------
    _RULES = [
        (("战神", "龙王", "兵王", "特种兵"), "战神归来", "身份反转", "男频", "现代"),
        (("赘婿", "女婿"), "赘婿", "误会打脸", "男频", "现代"),
        (("重生", "八零", "七零", "年代"), "年代穿书", "死亡重开", "女频", "年代(60-90)"),
        (("穿书", "女配"), "年代穿书", "死亡重开", "女频", "架空"),
        (("萌宝", "龙凤胎"), "萌宝寻亲", "亲情错认", "女频", "现代"),
        (("荒岛", "求生"), "荒岛求生", "金手指觉醒", "男频", "现代"),
        (("闪婚", "替嫁", "隐婚", "契约"), "甜宠恋爱", "契约婚姻", "女频", "现代"),
        (("退婚", "离婚", "复合", "前夫"), "追妻火葬场", "身份反转", "女频", "现代"),
        (("马甲", "豪门"), "豪门虐恋", "身份反转", "女频", "现代"),
        (("民国", "上海滩", "军阀"), "民国年代", "悬念事件", "男频", "民国"),
        (("凶宅", "殡仪", "停尸", "灵异", "别回头"), "悬疑惊悚", "悬念事件", "男女通吃", "现代"),
        (("修仙", "元婴", "飞升"), "玄幻修仙", "金手指觉醒", "男频", "现代"),
        (("系统", "摆烂"), "系统金手指", "金手指觉醒", "男频", "现代"),
        (("穿越", "种田", "古代"), "穿越古代", "金手指觉醒", "女频", "古代"),
        (("首富", "劳斯莱斯"), "打脸爽剧", "身份反转", "男频", "现代"),
        (("AI", "程序员"), "都市逆袭", "金手指觉醒", "男女通吃", "现代"),
        (("军婚",), "甜宠恋爱", "契约婚姻", "女频", "年代(60-90)"),
    ]

    def _mock(self, system: str, user: str) -> str:
        if "周报" in system or "report" in system.lower():
            return json.dumps({
                "headline": "mock 周报：荒岛求生环比 +19%、份额 8% 领涨；萌宝寻亲环比 -17% 走向饱和",
                "rising": [{"genre": "荒岛求生", "wow_pct": 19, "share_pct": 8, "action": "追", "why": "mock：主流且上升"},
                           {"genre": "都市逆袭", "wow_pct": 12, "share_pct": 3, "action": "布局", "why": "mock：小众上升"}],
                "saturated": [{"genre": "萌宝寻亲", "wow_pct": -17, "neg_ratio_pct": 33, "why": "mock：主流下滑"}],
                "emerging": [{"label": "mock簇", "size": 4, "verdict": "再看", "why": "mock"}],
                "audience": [{"genre": "悬疑惊悚", "neg_ratio_pct": 50, "top_complaint": "剧情崩", "insight": "mock：结局要收住"}],
                "actions": ["mock 建议 1（+19%）", "mock 建议 2（-17%）", "mock 建议 3（50%）"],
                "markdown": "## mock 周报\n未配置 LLM key。"}, ensure_ascii=False)
        if "cluster" in system.lower() or "簇" in system:
            return json.dumps({"label": "mock簇", "description": "mock 模式下的占位描述"}, ensure_ascii=False)
        if "sentiment" in system.lower() or "情感" in system:
            out = []
            for line in user.splitlines():
                if not line.strip():
                    continue
                neg = any(k in line for k in ("烂", "假", "无聊", "老掉牙", "崩", "一般", "太慢", "能不能", "吓"))
                pos = any(k in line for k in ("爽", "好", "绝", "神", "笑死", "甜", "可以", "不错", "治愈"))
                out.append("neg" if neg and not pos else "pos" if pos else "neu")
            tags = []
            for l, line in zip(out, [x for x in user.splitlines() if x.strip()]):
                if l != "neg": tags.append(""); continue
                tags.append("套路老" if any(k in line for k in ("套路", "又是", "老", "新意")) else
                            "节奏慢" if "慢" in line else "演技差" if "演技" in line else
                            "结局烂" if any(k in line for k in ("烂尾", "崩")) else "剧情崩")
            return json.dumps({"labels": out, "tags": tags}, ensure_ascii=False)
        # 打标（批量）：system 里带 "items" 说明是批量格式
        if '"items"' in system:
            blocks = [b for b in user.split("### 第") if b.strip()]
            items = [json.loads(self._mock_single(b)) for b in blocks]
            return json.dumps({"items": items}, ensure_ascii=False)
        # 打标（单条）
        text = user
        for kws, genre, hook, aud, era in self._RULES:
            if any(k in text for k in kws):
                return json.dumps({
                    "genre": genre, "sub_genre": "/".join(k for k in kws if k in text)[:40],
                    "hook_type": hook, "audience": aud, "era": era,
                    "tags": [k for k in kws if k in text][:3],
                    "reason": "mock 规则匹配",
                }, ensure_ascii=False)
        return json.dumps({"genre": "其他", "sub_genre": "", "hook_type": "其他", "audience": "男女通吃",
                           "era": "现代", "tags": [], "reason": "mock 无匹配"}, ensure_ascii=False)

    def _mock_single(self, text: str) -> str:
        for kws, genre, hook, aud, era in self._RULES:
            if any(k in text for k in kws):
                return json.dumps({
                    "genre": genre, "sub_genre": "/".join(k for k in kws if k in text)[:40],
                    "hook_type": hook, "audience": aud, "era": era,
                    "tags": [k for k in kws if k in text][:3], "reason": "mock 规则匹配",
                }, ensure_ascii=False)
        return json.dumps({"genre": "其他", "sub_genre": "", "hook_type": "其他", "audience": "男女通吃",
                           "era": "现代", "tags": [], "reason": "mock 无匹配"}, ensure_ascii=False)
