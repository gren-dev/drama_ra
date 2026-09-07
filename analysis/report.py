"""第三档：趋势周报。只对变化最大的剧和簇跑一次强模型，成本可控。
python -m analysis.report
"""
import logging
from datetime import datetime, timedelta

import pandas as pd
import config
from db.session import init_db, session_scope, engine
from db.models import Report, Cluster
from analysis.llm import LLM
from analysis.cluster import week_str

log = logging.getLogger("analysis.report")

SYSTEM = """你是短剧行业分析师，读者是编剧和制片人。根据给你的数据写一份《本周题材风向周报》(report)，markdown 格式，600字以内。
结构：
1. 一句话总结本周最大变化
2. 上升题材（2-3条，每条带数据和一句为什么）
3. 下降/饱和题材（1-2条）
4. 新冒头的簇（如果有）值不值得跟
5. 观众吐槽集中点（来自评论情感）
6. 给编剧的 3 条可执行建议
不要空话，每个判断都要落到数据上。"""


def genre_trend(days=7) -> pd.DataFrame:
    q = f"""
    select d.genre, date(m.ts) as day, sum(m.heat) heat, count(distinct d.id) n
    from metric_snapshot m join drama d on d.id=m.drama_id
    where m.ts >= datetime('now','-{days*2} day') and d.genre is not null
    group by d.genre, day order by day"""
    return pd.read_sql(q, engine)


def top_movers(days=7, n=20) -> pd.DataFrame:
    q = f"""
    with cur as (select drama_id, avg(heat) h from metric_snapshot
                 where ts >= datetime('now','-{days} day') group by drama_id),
         prev as (select drama_id, avg(heat) h from metric_snapshot
                  where ts < datetime('now','-{days} day') and ts >= datetime('now','-{days*2} day') group by drama_id)
    select d.title, d.genre, d.sub_genre, cur.h cur_heat, coalesce(prev.h,0) prev_heat,
           (cur.h - coalesce(prev.h, cur.h)) delta
    from cur left join prev on prev.drama_id=cur.drama_id join drama d on d.id=cur.drama_id
    order by abs(delta) desc, cur_heat desc limit {n}"""
    return pd.read_sql(q, engine)


def complaint_summary() -> pd.DataFrame:
    q = """
    select d.genre, c.sentiment, count(*) n
    from comment c join drama d on d.id=c.drama_id
    where c.sentiment is not null group by d.genre, c.sentiment"""
    return pd.read_sql(q, engine)


def build_context() -> str:
    wk = week_str()
    parts = []
    gt = genre_trend()
    if not gt.empty:
        pivot = gt.groupby("genre").agg(heat=("heat", "sum"), dramas=("n", "max")).sort_values("heat", ascending=False)
        parts.append("## 各题材近两周总热度\n" + pivot.head(15).to_string())
    tm = top_movers()
    if not tm.empty:
        parts.append("## 热度变化最大的剧\n" + tm.to_string(index=False))
    with session_scope() as s:
        cl = s.query(Cluster).filter_by(week=wk).all()
        if cl:
            parts.append("## 本周聚类簇\n" + "\n".join(
                f"- {c.label}（{c.size}部，{'新出现' if c.is_new else '延续'}）: {c.description} | 关键词 {c.keywords}" for c in cl))
    cs = complaint_summary()
    if not cs.empty:
        parts.append("## 评论情感分布（题材 x 情感）\n" + cs.to_string(index=False))
    negs = pd.read_sql("""select d.title, c.text from comment c join drama d on d.id=c.drama_id
                          where c.sentiment='neg' order by c.likes desc limit 20""", engine)
    if not negs.empty:
        parts.append("## 高赞负面评论样本\n" + "\n".join(f"- 《{r.title}》：{r.text}" for r in negs.itertuples()))
    return "\n\n".join(parts)


def run():
    init_db()
    ctx = build_context()
    llm = LLM(model=config.REPORT_MODEL)
    md = llm.chat(SYSTEM, ctx, max_tokens=1500, temperature=0.4)
    with session_scope() as s:
        s.add(Report(week=week_str(), content_md=md, model=f"{llm.provider}/{llm.model}"))
    log.info("report written (%d chars)", len(md))
    return md


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
