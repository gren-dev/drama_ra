"""指标层：所有"判断"都在这里用确定性计算得出，周报和站点共用。
LLM 只解读这里算出来的数字，不自己发明结论。
"""
from datetime import datetime, timedelta
import re

import numpy as np
import pandas as pd
from sqlalchemy import text

from db.session import engine

FATIGUE_PAT = re.compile(r"(?:又是|老套|套路|能不能换|看过一百遍|老掉牙|没新意|没啥新意|烂尾|崩了)")


def _q(sql: str, **params) -> pd.DataFrame:
    return pd.read_sql(text(sql), engine, params=params or None)


def week_of(ts: pd.Series) -> pd.Series:
    iso = pd.to_datetime(ts).dt.isocalendar()
    return iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)


# ---------- 题材 × 周 ----------

def genre_weekly(weeks: int = 8, platform: str | None = None, market: str | None = None) -> pd.DataFrame:
    """每题材每周：热度(每部剧取周内均值再求和)、剧数、份额、排名。
    platform: 只看某个数据源/榜单，如 'hongguo:AI剧'；None=全部。
    market: cn / global / None。global 且未指定 platform 时，各平台热度口径不同（播放量 vs 曝光分），
    先在平台内归一化成份额再合并，每个平台权重相等。"""
    df = _q("""
        select d.id drama_id, d.genre, m.platform, m.ts, m.heat
        from metric_snapshot m join drama d on d.id=m.drama_id
        where d.genre is not null and m.heat is not null and m.ts >= :since
          and (:platform is null or m.platform = :platform)
          and (:market is null or coalesce(d.market,'cn') = :market)""",
            since=datetime.utcnow() - timedelta(weeks=weeks), platform=platform, market=market)
    if df.empty:
        return df
    df["week"] = week_of(df.ts)
    if market == "global" and platform is None:
        per = df.groupby(["week", "platform", "genre", "drama_id"]).heat.mean().reset_index()
        per["heat"] = per.heat / per.groupby(["week", "platform"]).heat.transform("sum") * 1000
        per_drama = per.groupby(["week", "genre", "drama_id"]).heat.sum().reset_index()
    else:
        per_drama = df.groupby(["week", "genre", "drama_id"]).heat.mean().reset_index()
    g = per_drama.groupby(["week", "genre"]).agg(heat=("heat", "sum"), n=("drama_id", "nunique")).reset_index()
    g["share"] = g.heat / g.groupby("week").heat.transform("sum")
    g["rank"] = g.groupby("week").heat.rank(ascending=False, method="first").astype(int)
    return g.sort_values(["week", "rank"])


def genre_momentum(platform: str | None = None, market: str | None = None) -> pd.DataFrame:
    """本周 vs 上周：份额、环比、剧数变化、四象限动作建议。"""
    g = genre_weekly(8, platform, market)
    if g.empty:
        return g
    weeks = sorted(g.week.unique())
    cur = g[g.week == weeks[-1]].set_index("genre")
    if len(weeks) >= 2:
        prev = g[g.week == weeks[-2]].set_index("genre")
    else:
        prev = cur.copy()
    m = cur[["heat", "n", "share", "rank"]].join(prev[["heat", "n", "rank"]], rsuffix="_prev", how="outer").fillna(0)
    m["wow"] = np.where(m.heat_prev > 0, (m.heat - m.heat_prev) / m.heat_prev, np.nan)
    m["n_delta"] = (m.n - m.n_prev).astype(int)
    m["rank_delta"] = (m.rank_prev - m["rank"]).astype(int)   # 正数=上升
    med_share = m.share.median()

    def quadrant(r):
        if pd.isna(r.wow):
            return "新出现"
        if r.wow >= 0.10 and r.share >= med_share:
            return "追"        # 主流且上升
        if r.wow >= 0.10:
            return "布局"      # 小众但上升
        if r.wow <= -0.10 and r.share >= med_share:
            return "回避"      # 主流但下滑：饱和
        if r.wow <= -0.10:
            return "衰退"
        return "观望"
    m["action"] = m.apply(quadrant, axis=1)
    m["week"] = weeks[-1]
    m["prev_week"] = weeks[-2] if len(weeks) >= 2 else None
    return m.reset_index().sort_values("wow", ascending=False)


# ---------- 观众反馈 ----------

def genre_sentiment() -> pd.DataFrame:
    df = _q("""select d.genre, c.sentiment, c."text" as text, c.likes, c.complaint_tag
               from comment c join drama d on d.id=c.drama_id
               where d.genre is not null and c.sentiment is not null""")
    if df.empty:
        return df
    df["fatigue"] = df.text.str.contains(FATIGUE_PAT)
    out = df.groupby("genre").agg(
        comments=("text", "count"),
        neg=("sentiment", lambda s: (s == "neg").sum()),
        pos=("sentiment", lambda s: (s == "pos").sum()),
        fatigue=("fatigue", "sum"),
    )
    out["neg_ratio"] = out.neg / out.comments
    out["fatigue_ratio"] = out.fatigue / out.comments
    top_tag = (df[df.sentiment == "neg"].dropna(subset=["complaint_tag"])
               .groupby("genre").complaint_tag.agg(lambda s: s.value_counts().index[0] if len(s) else ""))
    out["top_complaint"] = top_tag
    return out.reset_index().sort_values("neg_ratio", ascending=False)


def complaint_tags(limit: int = 20) -> pd.DataFrame:
    df = _q("""select complaint_tag tag, count(*) n, sum(likes) likes from comment
               where sentiment='neg' and complaint_tag is not null and complaint_tag<>''
               group by complaint_tag order by n desc""")
    return df.head(limit)


# ---------- 矩阵 ----------

def hook_genre_matrix(market: str | None = None) -> pd.DataFrame:
    df = _q("""select genre, hook_type from drama where genre is not null and hook_type is not null
               and (:market is null or coalesce(market,'cn') = :market)""", market=market)
    return df.pivot_table(index="genre", columns="hook_type", aggfunc="size", fill_value=0) if not df.empty else df


def producer_genre_matrix(min_dramas: int = 1, market: str | None = None) -> pd.DataFrame:
    df = _q("""select d.producer, d.genre,
                      (select heat from metric_snapshot m where m.drama_id=d.id order by ts desc limit 1) heat
               from drama d where d.genre is not null and d.producer is not null and d.producer<>''
               and (:market is null or coalesce(d.market,'cn') = :market)""", market=market)
    if df.empty:
        return df
    keep = df.producer.value_counts()
    df = df[df.producer.isin(keep[keep >= min_dramas].index)]
    return df.pivot_table(index="producer", columns="genre", values="heat", aggfunc="sum", fill_value=0)


# ---------- 剧 ----------

def top_movers(days: int = 7, n: int = 15) -> pd.DataFrame:
    t1, t2 = datetime.utcnow() - timedelta(days=days), datetime.utcnow() - timedelta(days=days * 2)
    df = _q("""
        with cur as (select drama_id, avg(heat) h from metric_snapshot where ts >= :t1 group by drama_id),
             prev as (select drama_id, avg(heat) h from metric_snapshot where ts < :t1 and ts >= :t2 group by drama_id)
        select d.title, d.genre, d.sub_genre, d.producer, cur.h cur_heat, prev.h prev_heat
        from cur left join prev on prev.drama_id=cur.drama_id join drama d on d.id=cur.drama_id""", t1=t1, t2=t2)
    if df.empty:
        return df
    df["delta_pct"] = np.where(df.prev_heat > 0, (df.cur_heat - df.prev_heat) / df.prev_heat, np.nan)
    return df.sort_values("delta_pct", ascending=False, na_position="last").head(n)


def platforms(market: str | None = None) -> list[str]:
    df = _q("""select distinct m.platform from metric_snapshot m join drama d on d.id=m.drama_id
               where (:market is null or coalesce(d.market,'cn') = :market) order by m.platform""", market=market)
    return df.platform.tolist() if not df.empty else []


def genre_platform_share(market: str = "global") -> pd.DataFrame:
    """题材 × 平台：各平台内的热度份额（本周），跨平台对比用。"""
    df = _q("""
        select d.genre, split_part(m.platform, ':', 1) as platform, m.heat, d.id drama_id
        from metric_snapshot m join drama d on d.id=m.drama_id
        where d.genre is not null and m.heat is not null and m.ts >= :since
          and coalesce(d.market,'cn') = :market""",
            since=datetime.utcnow() - timedelta(days=7), market=market) if engine.dialect.name == "postgresql" else _q("""
        select d.genre, substr(m.platform, 1, case when instr(m.platform, ':')>0 then instr(m.platform, ':')-1 else length(m.platform) end) as platform,
               m.heat, d.id drama_id
        from metric_snapshot m join drama d on d.id=m.drama_id
        where d.genre is not null and m.heat is not null and m.ts >= :since
          and coalesce(d.market,'cn') = :market""",
            since=datetime.utcnow() - timedelta(days=7), market=market)
    if df.empty:
        return df
    per = df.groupby(["platform", "genre", "drama_id"]).heat.mean().reset_index()
    g = per.groupby(["platform", "genre"]).heat.sum().reset_index()
    g["share"] = g.heat / g.groupby("platform").heat.transform("sum")
    return g.pivot_table(index="genre", columns="platform", values="share", fill_value=0)


def cluster_history() -> pd.DataFrame:
    return _q("select week, label, size, is_new, description, keywords from cluster order by week")


# ---------- 汇总给周报 ----------

def kpi_summary(market: str | None = None) -> dict:
    m = genre_momentum(market=market)
    s = genre_sentiment()
    cl = cluster_history()
    out = {}
    if not m.empty:
        total_now, total_prev = m.heat.sum(), m.heat_prev.sum()
        out["week"] = m.week.iloc[0]
        out["total_heat"] = float(total_now)
        out["total_wow"] = float((total_now - total_prev) / total_prev) if total_prev else None
        valid = m.dropna(subset=["wow"])
        if not valid.empty:
            r, f = valid.iloc[0], valid.iloc[-1]
            out["top_riser"] = {"genre": r.genre, "wow": float(r.wow), "share": float(r.share)}
            out["top_faller"] = {"genre": f.genre, "wow": float(f.wow), "share": float(f.share)}
        out["leader"] = {"genre": m.sort_values("share").iloc[-1].genre,
                         "share": float(m.share.max())}
    if not s.empty:
        w = s.iloc[0]
        out["most_negative"] = {"genre": w.genre, "neg_ratio": float(w.neg_ratio),
                                "top_complaint": w.top_complaint or ""}
        out["fatigue_leader"] = {"genre": s.sort_values("fatigue_ratio").iloc[-1].genre,
                                 "fatigue_ratio": float(s.fatigue_ratio.max())}
    if not cl.empty:
        latest = cl[cl.week == cl.week.max()]
        out["new_clusters"] = int(latest.is_new.sum())
    return out


def report_context(market: str | None = None) -> str:
    """给 LLM 的紧凑数据包：全是数字表，不带任何解读。"""
    parts = []
    m = genre_momentum(market=market)
    if not m.empty:
        t = m[["genre", "share", "wow", "n", "n_delta", "rank", "rank_delta", "action"]].copy()
        t["share"] = (t.share * 100).round(1); t["wow"] = (t.wow * 100).round(1)
        parts.append(f"## 题材动量（本周 {m.week.iloc[0]} vs 上周）\n份额share和环比wow单位%，n=剧数，rank_delta正数=排名上升\n"
                     + t.to_string(index=False))
    s = genre_sentiment()
    if not s.empty:
        t = s[["genre", "comments", "neg_ratio", "fatigue_ratio", "top_complaint"]].copy()
        t["neg_ratio"] = (t.neg_ratio * 100).round(0); t["fatigue_ratio"] = (t.fatigue_ratio * 100).round(0)
        parts.append("## 观众反馈（neg_ratio负面率%，fatigue_ratio套路疲劳率%）\n" + t.to_string(index=False))
    tm = top_movers()
    if not tm.empty:
        t = tm.copy(); t["delta_pct"] = (t.delta_pct * 100).round(0)
        parts.append("## 热度变化最大的剧（delta_pct 周环比%）\n" + t[["title", "genre", "sub_genre", "delta_pct"]].to_string(index=False))
    cl = cluster_history()
    if not cl.empty:
        latest = cl[cl.week == cl.week.max()]
        parts.append("## 本周聚类簇\n" + "\n".join(
            f"- {r.label}（{r.size}部，{'新出现' if r.is_new else '延续'}）：{r.description}" for r in latest.itertuples()))
    ct = complaint_tags(10)
    if not ct.empty:
        parts.append("## 吐槽点排行\n" + ct.to_string(index=False))
    return "\n\n".join(parts)
