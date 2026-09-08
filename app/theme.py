"""视觉系统：色板、字体、CSS、plotly 模板、几个 HTML 组件。
方向：深夜手机屏里的短剧 App —— 深夜蓝底，唯一强调色是红果式橙红，其余颜色只表达语义。
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---- tokens ----
BG = "#0F1626"        # 深夜蓝
SURFACE = "#182238"
SURFACE2 = "#1F2B47"
TEXT = "#EEF1F8"
MUTED = "#8C97B3"
LINE = "#26324F"
ACCENT = "#FF5A3C"    # 红果式橙红：唯一强调色
GOOD = "#3DDC97"      # 追
COOL = "#4CC9F0"      # 布局
WARN = "#F5B94B"      # 观望
DIM = "#5C6785"       # 衰退
VIOLET = "#B388FF"    # 新出现

ACTION_COLOR = {"追": GOOD, "布局": COOL, "回避": ACCENT, "衰退": DIM, "观望": WARN, "新出现": VIOLET}
COLORWAY = [ACCENT, COOL, GOOD, WARN, VIOLET, "#FF8FAB", "#7DD3FC", "#A3E635", "#FDBA74", "#C4B5FD"]

DISPLAY = "'Noto Serif SC', 'Noto Serif CJK SC', serif"
BODY = "'Noto Sans SC', 'Noto Sans CJK SC', -apple-system, sans-serif"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@700;900&family=Noto+Sans+SC:wght@400;500;700&display=swap');

* {{ box-sizing: border-box; }}
html, body, [class*="css"], .stApp {{ font-family: {BODY}; color: {TEXT}; }}
.stApp {{ background: radial-gradient(1200px 600px at 10% -10%, rgba(255,90,60,0.06), transparent),
                     radial-gradient(1000px 500px at 90% 0%, rgba(76,201,240,0.05), transparent), {BG}; }}
section[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {LINE}; }}
section[data-testid="stSidebar"] .stRadio label {{ font-size: 15px; padding: 7px 6px; transition: background 0.15s ease; }}
section[data-testid="stSidebar"] .stRadio [role=radiogroup] > label {{ border-radius: 7px; position: relative; }}
section[data-testid="stSidebar"] .stRadio [role=radiogroup] > label:has(input:checked) {{
  background: {SURFACE2}; box-shadow: inset 3px 0 0 {ACCENT}; }}
section[data-testid="stSidebar"] .stRadio [role=radiogroup] > label:hover {{ background: rgba(255,255,255,0.03); }}
h1, h2, h3 {{ font-family: {DISPLAY}; letter-spacing: 0.01em; }}
h1 {{ font-weight: 900; font-size: 32px !important; margin-bottom: 2px !important; }}
h2 {{ font-weight: 700; font-size: 21px !important; color: {TEXT}; margin-top: 30px !important;
      padding-bottom: 8px; border-bottom: 1px solid {LINE}; }}
h3 {{ font-weight: 700; font-size: 17px !important; }}
.stCaption, .stMarkdown p small, [data-testid="stCaptionContainer"] {{ color: {MUTED} !important; }}
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 10px; overflow: hidden;
  box-shadow: 0 4px 16px rgba(0,0,0,0.18); }}
div[data-testid="stExpander"] {{ border: 1px solid {LINE}; border-radius: 10px; background: {SURFACE};
  box-shadow: 0 2px 10px rgba(0,0,0,0.12); overflow: hidden; }}
.stSelectbox > div > div, .stMultiSelect > div > div, .stTextInput > div > div {{ background: {SURFACE}; border-color: {LINE}; border-radius: 8px; }}
hr {{ border-color: {LINE}; }}
[data-testid="stPlotlyChart"] {{ border-radius: 10px; overflow: hidden; }}

/* 顶部品牌条 */
.dr-brand {{ display:flex; align-items:center; gap:10px; padding: 4px 2px 18px; border-bottom: 1px solid {LINE}; margin-bottom: 14px; }}
.dr-brand .mark {{ width:34px; height:34px; border-radius:9px; background: linear-gradient(135deg, {ACCENT}, #ff8a5c);
  display:flex; align-items:center; justify-content:center; font-size:17px; box-shadow: 0 4px 14px rgba(255,90,60,0.35); }}
.dr-brand .name {{ font-family: {DISPLAY}; font-weight:900; font-size:17px; color:{TEXT}; line-height:1.1; }}
.dr-brand .sub {{ font-size:11px; color:{MUTED}; }}

/* 数据新鲜度徽章 */
.dr-fresh {{ display:flex; align-items:center; gap:7px; padding:9px 12px; border-radius:9px; background:{SURFACE2};
  border:1px solid {LINE}; font-size:12px; color:{MUTED}; margin-top:14px; }}
.dr-fresh .dot {{ width:7px; height:7px; border-radius:50%; background:{GOOD}; box-shadow:0 0 8px {GOOD}; flex-shrink:0; }}
.dr-fresh b {{ color:{TEXT}; font-weight:600; }}

/* 片头字卡：本周一句话 */
.dr-headline {{
  font-family: {DISPLAY}; font-weight: 900; font-size: 28px; line-height: 1.35;
  color: {TEXT}; padding: 24px 28px; margin: 10px 0 24px;
  background: linear-gradient(115deg, {SURFACE} 0%, {BG} 75%);
  border-left: 5px solid {ACCENT}; border-radius: 4px 14px 14px 4px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.03);
}}
.dr-headline small {{ display:block; font-family:{BODY}; font-weight:400; font-size:13px; color:{MUTED}; margin-top:10px; }}

/* KPI：数字当视觉，不加框，只有上沿细线做锚点 */
.dr-kpi {{ padding: 8px 0 4px; border-top: 2px solid {LINE}; transition: border-color 0.2s ease; }}
.dr-kpi .l {{ font-size: 12px; color: {MUTED}; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.04em; }}
.dr-kpi .v {{ font-family: {DISPLAY}; font-weight: 900; font-size: 32px; line-height: 1.1; color: {TEXT}; }}
.dr-kpi .d {{ font-size: 13px; font-weight: 600; margin-top: 6px; display:inline-flex; align-items:center; gap:4px; }}
.dr-kpi .d.up {{ color: {GOOD}; }} .dr-kpi .d.down {{ color: {ACCENT}; }} .dr-kpi .d.flat {{ color: {MUTED}; }}
.dr-kpi.accent {{ border-top-color: {ACCENT}; }}

/* 动作 chip */
.dr-chip {{ display:inline-flex; align-items:center; padding: 3px 11px; border-radius: 999px; font-size: 12px;
  font-weight: 700; color: {BG}; box-shadow: 0 2px 6px rgba(0,0,0,0.25); }}

/* 周报卡：轻微悬浮感 */
.dr-card {{ background: linear-gradient(160deg, {SURFACE}, {BG} 180%); border: 1px solid {LINE}; border-radius: 12px;
  padding: 18px 20px; height: 100%; box-shadow: 0 6px 18px rgba(0,0,0,0.2); transition: transform 0.15s ease, box-shadow 0.15s ease; }}
.dr-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 26px rgba(0,0,0,0.28); }}
.dr-card .t {{ font-weight: 700; font-size: 16px; margin-bottom: 8px; }}
.dr-card .n {{ font-family: {DISPLAY}; font-weight: 900; font-size: 30px; line-height: 1.1; }}
.dr-card .s {{ font-size: 13px; color: {MUTED}; margin-top: 10px; line-height: 1.55; }}
.dr-card .m {{ font-size: 13px; margin-top: 6px; color: {TEXT}; opacity: 0.85; }}
.dr-list {{ padding-left: 20px; }}
.dr-list li {{ margin-bottom: 9px; line-height: 1.6; }}
.dr-num {{ font-family: {DISPLAY}; font-weight: 900; color: {ACCENT}; }}

/* 空状态 */
.dr-empty {{ padding: 36px 20px; text-align:center; color:{MUTED}; background:{SURFACE}; border:1px dashed {LINE};
  border-radius: 12px; font-size: 14px; }}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def plotly_template():
    t = go.layout.Template()
    t.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=BODY, color=TEXT, size=13),
        title=dict(font=dict(family=DISPLAY, size=18, color=TEXT), x=0, xanchor="left"),
        colorway=COLORWAY,
        xaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE, tickcolor=LINE),
        yaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE, tickcolor=LINE),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED)),
        hoverlabel=dict(bgcolor=SURFACE2, font=dict(color=TEXT, family=BODY), bordercolor=LINE),
        margin=dict(t=40, l=40, r=20, b=40),
        coloraxis=dict(colorbar=dict(outlinewidth=0, tickfont=dict(color=MUTED))),
    )
    pio.templates["radar"] = t
    pio.templates.default = "radar"


# ---- HTML 组件 ----

def fmt_num(x, digits: int = 1) -> str:
    """大数字压成 12.3万 / 3.4M 那种紧凑格式，而不是原始浮点数。"""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    if x != x:  # NaN
        return "—"
    for unit, div in (("亿", 1e8), ("万", 1e4)):
        if abs(x) >= div:
            return f"{x/div:.{digits}f}{unit}"
    return f"{x:,.0f}"


def brand(name: str = "短剧题材雷达", sub: str = "AI 题材分析"):
    st.sidebar.markdown(
        f'<div class="dr-brand"><div class="mark">📡</div>'
        f'<div><div class="name">{name}</div><div class="sub">{sub}</div></div></div>',
        unsafe_allow_html=True)


def freshness(container, last_update: str, source_line: str):
    container.markdown(
        f'<div class="dr-fresh"><span class="dot"></span>'
        f'<span><b>{last_update}</b> 更新 · {source_line}</span></div>',
        unsafe_allow_html=True)


def empty_state(msg: str):
    st.markdown(f'<div class="dr-empty">{msg}</div>', unsafe_allow_html=True)


def headline(text: str, sub: str = ""):
    sub_html = f"<small>{sub}</small>" if sub else ""
    st.markdown(f'<div class="dr-headline">{text}{sub_html}</div>', unsafe_allow_html=True)


def kpi(col, label: str, value: str, delta: str = None, good_when_up=True, accent=False):
    cls = "flat"
    if delta and delta not in ("—", ""):
        up = not delta.strip().startswith("-")
        cls = ("up" if up else "down") if good_when_up else ("down" if up else "up")
    d = f'<div class="d {cls}">{delta}</div>' if delta else ""
    col.markdown(f'<div class="dr-kpi{" accent" if accent else ""}"><div class="l">{label}</div>'
                 f'<div class="v">{value}</div>{d}</div>', unsafe_allow_html=True)


def chip(action: str) -> str:
    return f'<span class="dr-chip" style="background:{ACTION_COLOR.get(action, MUTED)}">{action}</span>'


def card(col, title: str, number: str, meta: str = "", sub: str = "", color: str = TEXT):
    col.markdown(f'<div class="dr-card"><div class="t">{title}</div><div class="n" style="color:{color}">{number}</div>'
                 f'<div class="m">{meta}</div><div class="s">{sub}</div></div>', unsafe_allow_html=True)
