"""短剧题材雷达 · Streamlit 站点
streamlit run app/dashboard.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

from db.session import engine, init_db, session_scope
from db.models import Cluster, Report
from analysis import metrics
from app import theme
from app.theme import ACTION_COLOR, ACCENT, GOOD, COOL, MUTED, LINE, TEXT, SURFACE2

init_db()
st.set_page_config(page_title="短剧题材雷达", page_icon="📡", layout="wide")
theme.inject()
theme.plotly_template()


@st.cache_data(ttl=300)
def load_dramas() -> pd.DataFrame:
    df = pd.read_sql("""
        select d.*, (select heat from metric_snapshot m where m.drama_id=d.id order by ts desc limit 1) as heat
        from drama d""", engine)
    return df.sort_values("heat", ascending=False, na_position="last").reset_index(drop=True)


@st.cache_data(ttl=300)
def m_weekly(platform=None): return metrics.genre_weekly(8, platform)
@st.cache_data(ttl=300)
def m_momentum(platform=None): return metrics.genre_momentum(platform)
@st.cache_data(ttl=300)
def m_platforms(): return metrics.platforms()
@st.cache_data(ttl=300)
def m_sent(): return metrics.genre_sentiment()
@st.cache_data(ttl=300)
def m_tags(): return metrics.complaint_tags(15)
@st.cache_data(ttl=300)
def m_hook(): return metrics.hook_genre_matrix()
@st.cache_data(ttl=300)
def m_producer(): return metrics.producer_genre_matrix()
@st.cache_data(ttl=300)
def m_movers(): return metrics.top_movers()
@st.cache_data(ttl=300)
def m_clusters(): return metrics.cluster_history()


def pct(x, signed=False):
    if x is None or pd.isna(x):
        return "—"
    return f"{x:+.0%}" if signed else f"{x:.0%}"


def latest_report():
    with session_scope() as s:
        r = s.query(Report).order_by(Report.created_at.desc()).first()
        return (r.content_json or {}) if r else {}


def quadrant_chart(m: pd.DataFrame):
    m = m.dropna(subset=["wow"]).copy() if "wow" in m.columns else pd.DataFrame()
    if m.empty:
        st.info("需要至少两周数据才能算环比。样例数据可跑 `python scripts/seed_history.py`。")
        return
    m["wow_pct"], m["share_pct"] = m.wow * 100, m.share * 100
    fig = px.scatter(m, x="share_pct", y="wow_pct", size="n", color="action", text="genre",
                     color_discrete_map=ACTION_COLOR, size_max=48,
                     labels={"share_pct": "热度份额 %", "wow_pct": "周环比 %", "n": "剧数"},
                     hover_data={"genre": True, "n": True, "rank_delta": True, "share_pct": ":.1f", "wow_pct": ":.0f"})
    fig.update_traces(textposition="top center", textfont=dict(size=12, color=TEXT),
                      marker=dict(opacity=0.9, line=dict(width=1.5, color="rgba(255,255,255,0.35)")))
    xmed = m.share_pct.median()
    xmax, ymax, ymin = m.share_pct.max() * 1.18, max(m.wow_pct.max() * 1.25, 5), min(m.wow_pct.min() * 1.25, -5)
    # 象限底色：只给"追"和"回避"两个决策象限上色
    fig.add_shape(type="rect", x0=xmed, x1=xmax, y0=0, y1=ymax, fillcolor=GOOD, opacity=0.07, line_width=0, layer="below")
    fig.add_shape(type="rect", x0=xmed, x1=xmax, y0=ymin, y1=0, fillcolor=ACCENT, opacity=0.08, line_width=0, layer="below")
    fig.add_hline(y=0, line_color=MUTED, line_width=1)
    fig.add_vline(x=xmed, line_dash="dot", line_color=MUTED, line_width=1)
    for txt, x, y, col in (("追 · 主流且上升", xmax, ymax, GOOD), ("布局 · 小众上升", 0, ymax, COOL),
                           ("回避 · 主流下滑", xmax, ymin, ACCENT), ("衰退", 0, ymin, MUTED)):
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False, font=dict(size=12, color=col),
                           xanchor="right" if x else "left", yanchor="top" if y > 0 else "bottom")
    fig.update_layout(height=540, showlegend=False, xaxis=dict(range=[0, xmax], showgrid=False),
                      yaxis=dict(range=[ymin, ymax], showgrid=False, ticksuffix="%"), margin=dict(t=10, l=50, r=20, b=50))
    st.plotly_chart(fig, width="stretch")


def bump_chart(g: pd.DataFrame, top=10):
    if g.empty or g.week.nunique() < 2:
        return
    latest = g[g.week == g.week.max()].nsmallest(top, "rank").genre
    d = g[g.genre.isin(latest)]
    fig = px.line(d, x="week", y="rank", color="genre", markers=True, title="题材排名变化")
    fig.update_traces(line=dict(width=2.5), marker=dict(size=8))
    fig.update_yaxes(autorange="reversed", dtick=1, title="", showgrid=False)
    fig.update_xaxes(title="", showgrid=False)
    fig.update_layout(height=420, legend=dict(orientation="h", y=-0.12))
    st.plotly_chart(fig, width="stretch")


def share_area(g: pd.DataFrame, top=8):
    if g.empty:
        return
    latest = g[g.week == g.week.max()].nsmallest(top, "rank").genre
    d = g.copy(); d["genre"] = d.genre.where(d.genre.isin(latest), "其他")
    d = d.groupby(["week", "genre"]).share.sum().reset_index()
    fig = px.area(d, x="week", y="share", color="genre", title="热度份额演变", groupnorm="fraction", line_shape="spline")
    fig.update_traces(line=dict(width=0.5))
    fig.update_yaxes(tickformat=".0%", title="", showgrid=False)
    fig.update_xaxes(title="", showgrid=False)
    fig.update_layout(height=380, legend=dict(orientation="h", y=-0.12))
    st.plotly_chart(fig, width="stretch")


df = load_dramas()
st.sidebar.title("📡 短剧题材雷达")
page = st.sidebar.radio("页面", ["总览", "题材趋势", "观众反馈", "新兴题材", "出品方", "剧集库", "AI 周报"])
_plats = m_platforms()
_labels = {None: "全部数据源"} | {p: p.replace("hongguo:", "红果·").replace("duanjubaike", "短剧百科").replace("sample", "样例") for p in _plats}
scope = st.sidebar.selectbox("数据范围", list(_labels), format_func=lambda x: _labels[x],
                             help="选一个榜单只看它，例如「红果·AI剧」只看 AI 短剧的题材动量")
st.sidebar.caption(f"库内 {len(df)} 部剧 · 已打标 {df.tagged_at.notna().sum()} 部")

# ================= 总览 =================
if page == "总览":
    m, s, rep = m_momentum(scope), m_sent(), latest_report()
    kpi = (rep.get("kpi") if scope is None else None) or metrics.kpi_summary()
    if scope is not None and not m.empty:
        # 切了范围就现算 KPI，不用周报里的全局值
        valid = m.dropna(subset=["wow"])
        kpi = {"week": m.week.iloc[0] if not m.empty else "",
               "total_wow": float((m.heat.sum() - m.heat_prev.sum()) / m.heat_prev.sum()) if not m.empty and m.heat_prev.sum() else None,
               "top_riser": {"genre": valid.iloc[0].genre, "wow": float(valid.iloc[0].wow)} if not valid.empty else {},
               "top_faller": {"genre": valid.iloc[-1].genre, "wow": float(valid.iloc[-1].wow)} if not valid.empty else {},
               "most_negative": kpi.get("most_negative") or {}}
    st.title("本周一眼看")
    if rep.get("headline") and scope is None:
        theme.headline(rep["headline"], f"{kpi.get('week', '')} · 数据来自 {len(df)} 部剧的热度与评论")
    elif scope is not None:
        theme.headline(f"{_labels[scope]} · 题材动量", f"{kpi.get('week', '')} · 只统计该榜单的热度")

    c1, c2, c3, c4 = st.columns(4)
    theme.kpi(c1, "总热度周环比", pct(kpi.get("total_wow"), True))
    r = kpi.get("top_riser") or {}
    theme.kpi(c2, "上升最快", r.get("genre", "—"), pct(r.get("wow"), True), accent=True)
    f = kpi.get("top_faller") or {}
    theme.kpi(c3, "下滑最快", f.get("genre", "—"), pct(f.get("wow"), True), good_when_up=False)
    n = kpi.get("most_negative") or {}
    theme.kpi(c4, "负面率最高", n.get("genre", "—"), f"{pct(n.get('neg_ratio'))} · {n.get('top_complaint', '')}", good_when_up=False)

    st.subheader("题材动量")
    st.caption("横轴=当前热度份额，纵轴=周环比，气泡=剧数。右上绿区追，右下红区回避。")
    quadrant_chart(m)

    if not m.empty and "wow" in m.columns:
        l, rgt = st.columns(2)
        with l:
            st.subheader("动作清单")
            t = m.dropna(subset=["wow"]).copy()
            order = {"追": 0, "布局": 1, "回避": 2, "衰退": 3, "观望": 4, "新出现": 5}
            t = t.sort_values("action", key=lambda c: c.map(order))
            rows = "".join(
                f'<tr><td>{theme.chip(x.action)}</td><td style="font-weight:500">{x.genre}</td>'
                f'<td>{pct(x.share)}</td><td style="color:{GOOD if x.wow >= 0 else ACCENT}">{pct(x.wow, True)}</td>'
                f'<td>{int(x.n)}</td><td style="color:{MUTED}">{int(x.rank_delta):+d}</td></tr>'
                for x in t.itertuples())
            st.markdown(f"""<table style="width:100%;border-collapse:collapse;font-size:14px">
                <thead><tr style="color:{MUTED};font-size:12px;text-align:left">
                <th style="padding:6px 8px">动作</th><th>题材</th><th>份额</th><th>周环比</th><th>剧数</th><th>排名</th></tr></thead>
                <tbody>{rows}</tbody></table>
                <style>.stMarkdown table td{{padding:7px 8px;border-bottom:1px solid {LINE}}}</style>""",
                unsafe_allow_html=True)
        with rgt:
            st.subheader("本周编剧建议")
            acts = rep.get("actions") or []
            if acts:
                st.markdown('<ol class="dr-list">' + "".join(f"<li>{a}</li>" for a in acts) + "</ol>", unsafe_allow_html=True)
            else:
                st.caption("还没生成周报：`python -m analysis.report`")

# ================= 题材趋势 =================
elif page == "题材趋势":
    st.title("题材热度趋势")
    g = m_weekly(scope)
    if g.empty:
        st.info("还没有指标数据，先跑 `python pipeline.py`")
    else:
        share_area(g)
        bump_chart(g)
        st.subheader("热度变化最大的剧（近 7 天 vs 前 7 天）")
        tm = m_movers()
        if not tm.empty:
            t = tm.copy(); t["delta_pct"] = t.delta_pct.map(lambda x: pct(x, True))
            t["cur_heat"] = t.cur_heat.map(lambda x: f"{x/1e4:.0f}万")
            st.dataframe(t[["title", "genre", "sub_genre", "producer", "cur_heat", "delta_pct"]]
                         .rename(columns={"title": "剧名", "genre": "题材", "sub_genre": "子题材", "producer": "出品",
                                          "cur_heat": "当前热度", "delta_pct": "环比"}), width="stretch", hide_index=True)
        st.subheader("钩子 × 题材")
        hk = m_hook()
        if not hk.empty:
            st.plotly_chart(px.imshow(hk, text_auto=True, aspect="auto", color_continuous_scale=[[0, "#182238"], [1, COOL]],
                                      labels=dict(color="剧数")).update_layout(height=420), width="stretch")

# ================= 观众反馈 =================
elif page == "观众反馈":
    st.title("观众在吐槽什么")
    s = m_sent()
    if s.empty:
        st.info("还没有评论情感数据：`python -m analysis.sentiment`")
    else:
        c1, c2 = st.columns(2)
        with c1:
            d = s.sort_values("neg_ratio")
            fig = go.Figure()
            fig.add_bar(y=d.genre, x=d.neg_ratio, orientation="h", name="负面率", marker_color=ACCENT)
            fig.add_bar(y=d.genre, x=d.fatigue_ratio, orientation="h", name="套路疲劳率", marker_color="#F5B94B")
            fig.update_layout(barmode="group", title="负面率 / 套路疲劳率", xaxis_tickformat=".0%", height=460,
                              yaxis=dict(showgrid=False), xaxis=dict(showgrid=False), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig, width="stretch")
            st.caption("套路疲劳率 = 评论里出现“又是/老套/能不能换”类表达的比例，是题材饱和的先行信号。")
        with c2:
            ct = m_tags()
            if not ct.empty:
                fig2 = px.bar(ct.sort_values("n"), x="n", y="tag", orientation="h", title="吐槽点排行",
                              labels={"n": "差评数", "tag": ""}, text="n")
                fig2.update_traces(marker_color=SURFACE2, marker_line_color=ACCENT, marker_line_width=1.5, textposition="outside")
                fig2.update_layout(height=460, xaxis=dict(showgrid=False, visible=False), yaxis=dict(showgrid=False))
                st.plotly_chart(fig2, width="stretch")
        t = s[["genre", "comments", "neg_ratio", "fatigue_ratio", "top_complaint"]].copy()
        t["neg_ratio"], t["fatigue_ratio"] = t.neg_ratio.map(pct), t.fatigue_ratio.map(pct)
        t.columns = ["题材", "评论数", "负面率", "疲劳率", "主要吐槽"]
        st.dataframe(t, width="stretch", hide_index=True)

# ================= 新兴题材 =================
elif page == "新兴题材":
    st.title("新兴题材雷达（聚类发现）")
    cl = m_clusters()
    if cl.empty:
        st.info("还没跑过聚类：`python -m analysis.cluster`")
    else:
        if cl.week.nunique() > 1:
            st.plotly_chart(px.line(cl, x="week", y="size", color="label", markers=True, title="各簇规模变化")
                            .update_layout(height=360, margin=dict(t=40)), width="stretch")
        wk = st.selectbox("周", sorted(cl.week.unique(), reverse=True))
        with session_scope() as s:
            for c in s.query(Cluster).filter_by(week=wk).order_by(Cluster.is_new.desc(), Cluster.size.desc()):
                badge = "🆕 " if c.is_new else ""
                with st.expander(f"{badge}{c.label} · {c.size} 部", expanded=bool(c.is_new)):
                    st.write(c.description or "")
                    st.caption("关键词：" + " / ".join(c.keywords or []))
                    st.dataframe(df[df.cluster_id == c.id][["title", "genre", "sub_genre", "heat"]],
                                 width="stretch", hide_index=True)

# ================= 出品方 =================
elif page == "出品方":
    st.title("谁在押什么题材")
    pm = m_producer()
    if pm.empty:
        st.info("没有出品方数据")
    else:
        st.plotly_chart(px.imshow(pm / 1e4, text_auto=".0f", aspect="auto", color_continuous_scale=[[0, "#182238"], [1, ACCENT]],
                                  labels=dict(color="热度(万)")).update_layout(height=max(320, 40 * len(pm))),
                        width="stretch")
        st.caption("行=出品方，列=题材，格子=该出品方在该题材的当前热度合计。看空白格子找差异化机会。")

# ================= 剧集库 =================
elif page == "剧集库":
    st.title("剧集库")
    c1, c2, c3 = st.columns(3)
    g = c1.multiselect("题材", sorted(df.genre.dropna().unique()))
    a = c2.multiselect("受众", sorted(df.audience.dropna().unique()))
    kw = c3.text_input("搜索剧名/简介")
    view = df.copy()
    if g: view = view[view.genre.isin(g)]
    if a: view = view[view.audience.isin(a)]
    if kw: view = view[view.title.str.contains(kw, na=False) | view.synopsis.str.contains(kw, na=False)]
    st.dataframe(view[["title", "genre", "sub_genre", "hook_type", "audience", "era", "heat", "producer"]],
                 width="stretch", hide_index=True)
    pick = st.selectbox("查看详情", view.title.tolist())
    if pick:
        row = view[view.title == pick].iloc[0]
        st.subheader(row.title)
        st.write(row.synopsis)
        st.write(f"**题材** {row.genre} / {row.sub_genre} · **钩子** {row.hook_type} · **受众** {row.audience} · **时代** {row.era}")
        if isinstance(row.tags, list) and row.tags:
            st.write(" ".join(f"`{t}`" for t in row.tags))
        st.caption(f"判断依据：{row.tag_reason}")
        hist = pd.read_sql(text('select ts, platform, heat, "rank" as rank from metric_snapshot where drama_id=:i order by ts'),
                           engine, params={"i": int(row.id)})
        if len(hist) > 1:
            st.plotly_chart(px.line(hist, x="ts", y="heat", color="platform", title="热度曲线", markers=True), width="stretch")
        cm = pd.read_sql(text('select "text" as text, likes, sentiment, complaint_tag from comment where drama_id=:i order by likes desc limit 30'),
                         engine, params={"i": int(row.id)})
        if not cm.empty:
            st.subheader("观众评论")
            st.dataframe(cm, width="stretch", hide_index=True)

# ================= AI 周报 =================
else:
    st.title("AI 题材风向周报")
    with session_scope() as s:
        reps = s.query(Report).order_by(Report.created_at.desc()).all()
        if not reps:
            st.info("还没生成周报：`python -m analysis.report`")
        else:
            r = st.selectbox("选择周报", reps, format_func=lambda x: f"{x.week} · {x.created_at:%m-%d %H:%M} · {x.model}")
            j = r.content_json or {}
            if j.get("headline"):
                theme.headline(j["headline"], f"{r.week} · {r.model}")
            if j.get("rising"):
                st.subheader("上升 · 追 / 布局")
                cols = st.columns(max(len(j["rising"]), 1))
                for c, x in zip(cols, j["rising"]):
                    theme.card(c, f"{theme.chip(x.get('action', ''))}&nbsp; {x.get('genre', '')}",
                               f"{x.get('wow_pct', 0):+.0f}%", f"周环比 · 份额 {x.get('share_pct', 0):.0f}%",
                               x.get("why", ""), color=GOOD)
            if j.get("saturated"):
                st.subheader("饱和 · 回避")
                cols = st.columns(max(len(j["saturated"]), 1))
                for c, x in zip(cols, j["saturated"]):
                    theme.card(c, f"{theme.chip('回避')}&nbsp; {x.get('genre', '')}",
                               f"{x.get('wow_pct', 0):+.0f}%", f"周环比 · 负面率 {x.get('neg_ratio_pct', 0):.0f}%",
                               x.get("why", ""), color=ACCENT)
            if j.get("emerging"):
                st.subheader("新冒头")
                cols = st.columns(max(len(j["emerging"]), 1))
                for c, x in zip(cols, j["emerging"]):
                    theme.card(c, x.get("label", ""), f"{x.get('size', 0)} 部", f"判断：{x.get('verdict', '')}", x.get("why", ""), color=theme.VIOLET)
            if j.get("audience"):
                st.subheader("观众吐槽集中点")
                st.markdown('<ul class="dr-list">' + "".join(
                    f'<li><b>{x.get("genre", "")}</b> 负面率 <span class="dr-num">{x.get("neg_ratio_pct", 0):.0f}%</span>，'
                    f'主要是「{x.get("top_complaint", "")}」：{x.get("insight", "")}</li>' for x in j["audience"]) + "</ul>",
                    unsafe_allow_html=True)
            if j.get("actions"):
                st.subheader("给编剧的三件事")
                st.markdown('<ol class="dr-list">' + "".join(f"<li>{a}</li>" for a in j["actions"]) + "</ol>", unsafe_allow_html=True)
            with st.expander("Markdown 版（可复制导出）"):
                st.markdown(r.content_md or "")
                st.download_button("下载 .md", r.content_md or "", file_name=f"drama-radar-{r.week}.md")
