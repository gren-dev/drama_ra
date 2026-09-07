"""短剧题材雷达 · Streamlit 站点
streamlit run app/dashboard.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

from db.session import engine, init_db, session_scope
from db.models import Drama, Comment, Cluster, Report

init_db()
st.set_page_config(page_title="短剧题材雷达", page_icon="📡", layout="wide")


@st.cache_data(ttl=300)
def load_dramas() -> pd.DataFrame:
    return pd.read_sql("""
        select d.*, (select heat from metric_snapshot m where m.drama_id=d.id order by ts desc limit 1) as heat
        from drama d order by heat desc nulls last""", engine)


@st.cache_data(ttl=300)
def load_trend(days: int) -> pd.DataFrame:
    return pd.read_sql(f"""
        select d.genre, date(m.ts) day, sum(m.heat) heat, count(distinct d.id) n
        from metric_snapshot m join drama d on d.id=m.drama_id
        where d.genre is not null and m.ts >= datetime('now','-{days} day')
        group by d.genre, day order by day""", engine)


@st.cache_data(ttl=300)
def load_sentiment() -> pd.DataFrame:
    return pd.read_sql("""
        select d.genre, c.sentiment, count(*) n from comment c join drama d on d.id=c.drama_id
        where c.sentiment is not null group by d.genre, c.sentiment""", engine)


df = load_dramas()
st.sidebar.title("📡 短剧题材雷达")
page = st.sidebar.radio("页面", ["题材趋势", "新兴题材", "剧集库", "AI 周报"])
st.sidebar.caption(f"库内 {len(df)} 部剧 · 已打标 {df.tagged_at.notna().sum()} 部")

# ---------------- 题材趋势 ----------------
if page == "题材趋势":
    st.title("题材热度趋势")
    days = st.select_slider("时间范围（天）", [7, 14, 30, 60, 90], value=30)
    tr = load_trend(days)
    if tr.empty:
        st.info("还没有指标数据，先跑 `python pipeline.py`")
    else:
        top = tr.groupby("genre").heat.sum().nlargest(10).index
        fig = px.line(tr[tr.genre.isin(top)], x="day", y="heat", color="genre",
                      title="各题材每日总热度", markers=True)
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            share = df.dropna(subset=["genre"]).groupby("genre").heat.sum().sort_values(ascending=False)
            st.plotly_chart(px.bar(share, title="当前热度份额（按题材）", labels={"value": "热度", "genre": ""}),
                            use_container_width=True)
        with c2:
            aud = df.dropna(subset=["audience"]).groupby(["audience", "genre"]).size().reset_index(name="n")
            st.plotly_chart(px.sunburst(aud, path=["audience", "genre"], values="n", title="男频/女频 × 题材"),
                            use_container_width=True)

        st.subheader("钩子类型分布")
        hk = df.dropna(subset=["hook_type"]).groupby("hook_type").agg(n=("id", "count"), heat=("heat", "sum"))
        st.dataframe(hk.sort_values("heat", ascending=False), use_container_width=True)

        sen = load_sentiment()
        if not sen.empty:
            st.subheader("评论情感 × 题材")
            piv = sen.pivot_table(index="genre", columns="sentiment", values="n", fill_value=0)
            piv["neg_ratio"] = piv.get("neg", 0) / piv.sum(axis=1)
            st.dataframe(piv.sort_values("neg_ratio", ascending=False).style.format({"neg_ratio": "{:.0%}"}),
                         use_container_width=True)

# ---------------- 新兴题材 ----------------
elif page == "新兴题材":
    st.title("新兴题材雷达（聚类发现）")
    with session_scope() as s:
        weeks = [w for (w,) in s.query(Cluster.week).distinct().order_by(Cluster.week.desc())]
        if not weeks:
            st.info("还没跑过聚类：`python -m analysis.cluster`")
        else:
            wk = st.selectbox("周", weeks)
            cls = s.query(Cluster).filter_by(week=wk).order_by(Cluster.is_new.desc(), Cluster.size.desc()).all()
            for c in cls:
                badge = "🆕 " if c.is_new else ""
                with st.expander(f"{badge}{c.label} · {c.size} 部", expanded=bool(c.is_new)):
                    st.write(c.description or "")
                    st.caption("关键词：" + " / ".join(c.keywords or []))
                    members = df[df.cluster_id == c.id][["title", "genre", "sub_genre", "heat"]]
                    st.dataframe(members, use_container_width=True, hide_index=True)

# ---------------- 剧集库 ----------------
elif page == "剧集库":
    st.title("剧集库")
    c1, c2, c3 = st.columns(3)
    g = c1.multiselect("题材", sorted(df.genre.dropna().unique()))
    a = c2.multiselect("受众", sorted(df.audience.dropna().unique()))
    kw = c3.text_input("搜索剧名/简介")
    view = df.copy()
    if g:
        view = view[view.genre.isin(g)]
    if a:
        view = view[view.audience.isin(a)]
    if kw:
        view = view[view.title.str.contains(kw, na=False) | view.synopsis.str.contains(kw, na=False)]
    st.dataframe(view[["title", "genre", "sub_genre", "hook_type", "audience", "era", "heat", "producer"]],
                 use_container_width=True, hide_index=True)

    pick = st.selectbox("查看详情", view.title.tolist())
    if pick:
        row = view[view.title == pick].iloc[0]
        st.subheader(row.title)
        st.write(row.synopsis)
        st.write(f"**题材** {row.genre} / {row.sub_genre} · **钩子** {row.hook_type} · "
                 f"**受众** {row.audience} · **时代** {row.era}")
        if isinstance(row.tags, list) and row.tags:
            st.write(" ".join(f"`{t}`" for t in row.tags))
        st.caption(f"判断依据：{row.tag_reason}")
        hist = pd.read_sql(f"select ts, platform, heat, rank from metric_snapshot where drama_id={int(row.id)} order by ts", engine)
        if len(hist) > 1:
            st.plotly_chart(px.line(hist, x="ts", y="heat", color="platform", title="热度曲线", markers=True),
                            use_container_width=True)
        cm = pd.read_sql(f"select text, likes, sentiment from comment where drama_id={int(row.id)} order by likes desc limit 30", engine)
        if not cm.empty:
            st.subheader("观众评论")
            st.dataframe(cm, use_container_width=True, hide_index=True)

# ---------------- AI 周报 ----------------
else:
    st.title("AI 题材风向周报")
    with session_scope() as s:
        reps = s.query(Report).order_by(Report.created_at.desc()).all()
        if not reps:
            st.info("还没生成周报：`python -m analysis.report`")
        else:
            r = st.selectbox("选择周报", reps, format_func=lambda x: f"{x.week} · {x.created_at:%m-%d %H:%M} · {x.model}")
            st.markdown(r.content_md)
