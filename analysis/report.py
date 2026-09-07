"""第三档：趋势周报。
数据来自 analysis/metrics.py 的确定性计算，LLM 只做解读并输出 JSON；
每条结论必须带数字。站点把 JSON 渲染成卡片，markdown 作为兜底/导出。
python -m analysis.report
"""
import json
import logging

import config
from db.session import init_db, session_scope
from db.models import Report
from analysis.llm import LLM
from analysis.cluster import week_str
from analysis import metrics

log = logging.getLogger("analysis.report")

SYSTEM = """你是短剧行业分析师，读者是编剧和制片人，他们只想知道：追什么、避什么、有什么新东西。
根据给你的数据表输出一份周报 (report)，只输出 JSON，不要 markdown 代码块，不要解释。
硬性要求：
- 每一条结论都必须引用表里的具体数字（份额、环比、负面率、剧数），不允许没有数字的判断
- 不要写"值得关注""持续观察"这类空话；要写"做/不做/等"和原因
- 上升题材只从 action 为"追"或"布局"的里选；饱和题材从"回避"或负面率/疲劳率最高的里选
- 用词直接、短句，每个 why 不超过 40 字

JSON 结构：
{
  "headline": "一句话（含至少两个数字）说明本周最大变化",
  "rising": [{"genre": "", "wow_pct": 0, "share_pct": 0, "action": "追|布局", "why": ""}],
  "saturated": [{"genre": "", "wow_pct": 0, "neg_ratio_pct": 0, "why": ""}],
  "emerging": [{"label": "", "size": 0, "verdict": "跟|再看|不跟", "why": ""}],
  "audience": [{"genre": "", "neg_ratio_pct": 0, "top_complaint": "", "insight": ""}],
  "actions": ["", "", ""],
  "markdown": "把上面内容整理成 500 字内的 markdown 周报，用于导出"
}
rising 2-3条，saturated 1-2条，emerging 只放本周新出现的簇（没有就空数组），audience 2-3条，actions 3条且每条带一个数字依据。"""


def _fallback_md(kpi: dict) -> str:
    lines = ["## 本周题材风向（自动生成）"]
    if kpi.get("top_riser"):
        r = kpi["top_riser"]; lines.append(f"- 上升最快：{r['genre']} 周环比 {r['wow']:+.0%}，份额 {r['share']:.0%}")
    if kpi.get("top_faller"):
        f = kpi["top_faller"]; lines.append(f"- 下滑最快：{f['genre']} 周环比 {f['wow']:+.0%}")
    if kpi.get("most_negative"):
        n = kpi["most_negative"]; lines.append(f"- 负面率最高：{n['genre']} {n['neg_ratio']:.0%}，主要吐槽 {n['top_complaint']}")
    return "\n".join(lines)


def run():
    init_db()
    ctx = metrics.report_context()
    kpi = metrics.kpi_summary()
    llm = LLM(model=config.REPORT_MODEL)
    data = llm.chat_json(SYSTEM, ctx, max_tokens=3000, temperature=0.3) if ctx else None
    if not isinstance(data, dict) or "headline" not in data:
        log.warning("周报 JSON 解析失败，使用兜底")
        md = _fallback_md(kpi)
        data = {"headline": md.split("\n")[1] if "\n" in md else "数据不足", "rising": [], "saturated": [],
                "emerging": [], "audience": [], "actions": [], "markdown": md}
    data["kpi"] = kpi
    md = data.get("markdown") or _fallback_md(kpi)
    with session_scope() as s:
        s.add(Report(week=week_str(), content_md=md, content_json=data, model=f"{llm.provider}/{llm.model}"))
    log.info("report written: %s", str(data.get("headline", ""))[:80])
    return data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run(), ensure_ascii=False, indent=2))
