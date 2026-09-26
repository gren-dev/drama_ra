"""片场工作台设计系统。工作台、Script Studio、雷达共用同一套色板、字体、组件和图表模板。

用法（Streamlit 应用）：
    from dramakit import theme
    theme.inject("drama_radar")          # 紧跟 st.set_page_config 之后；参数是应用 id，决定身份色
    theme.plotly_template("drama_radar") # 用到 plotly 时
    theme.headline("本周一眼看", "副标题")
    theme.kpi(col, "总热度周环比", "+12%", delta="+3.1%")
    theme.empty_state("还没有数据")

方向：浅色、克制、专业。白色面板、石墨文字、极细分割线；每个应用只有一个身份色，其余颜色只表达语义。
"""
from __future__ import annotations

# ---- 基础色板（与工作台 index.html 的 :root 一致） ----
BG = "#f4f4f2"
SURFACE = "#ffffff"
SURFACE2 = "#f0f0ee"
TEXT = "#151617"
TEXT2 = "#4b4e52"
MUTED = "#8a8d92"
LINE = "#e6e6e2"
LINE2 = "#d3d3ce"

# 语义色（浅底可读版本）
GOOD = "#2e8b57"
WARN = "#c47a12"
BAD = "#c0392b"
COOL = "#2f6f8f"
VIOLET = "#7c5cbf"
DIM = "#9aa0a6"

# 应用身份色（与 hub/apps/*.json 里的 color 一致）
ACCENTS = {"adcut": "#d8342b", "script_studio": "#2f6f8f", "drama_radar": "#c47a12", "hub": "#151617"}

FONT = ("-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Segoe UI', "
        "'Microsoft YaHei', Inter, sans-serif")
MONO = "'SF Mono', Menlo, Consolas, monospace"


def accent(app: str) -> str:
    return ACCENTS.get(app, ACCENTS["hub"])


def action_colors(accent_color: str) -> dict:
    """雷达四象限动作 → 颜色。"""
    return {"追": GOOD, "布局": COOL, "回避": accent_color, "衰退": DIM, "观望": WARN, "新出现": VIOLET}


def colorway(app: str) -> list[str]:
    return [accent(app), COOL, GOOD, WARN, VIOLET, "#d9748f", "#5fa8d3", "#8bb174", "#e0a458", "#a58fd9"]


def css(app: str) -> str:
    a = accent(app)
    return f"""
<style>
/* ---- 隐藏 Streamlit 自带的壳：嵌在工作台里时不该看到另一个程序的顶栏 ---- */
header[data-testid="stHeader"], #MainMenu, footer, .stDeployButton, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {{ display: none !important; }}
.block-container, [data-testid="stMainBlockContainer"] {{ padding-top: 1.4rem !important; padding-bottom: 3rem !important; max-width: 1180px; }}
[data-testid="stSidebarHeader"], [data-testid="stLogoSpacer"], [data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
[data-testid="stSidebarUserContent"] {{ padding-top: 1.4rem !important; }}

/* ---- 基础 ---- */
html, body, .stApp, [class*="css"] {{ font-family: {FONT}; color: {TEXT}; font-variant-numeric: tabular-nums;
  -webkit-font-smoothing: antialiased; }}
.stApp {{ background: {BG}; }}
h1, h2, h3 {{ font-family: {FONT}; letter-spacing: -0.01em; color: {TEXT}; }}
h1 {{ font-weight: 600 !important; font-size: 26px !important; line-height: 1.2 !important; margin: 0 0 4px !important; }}
h2 {{ font-weight: 600 !important; font-size: 18px !important; margin-top: 28px !important; padding-bottom: 8px;
      border-bottom: 1px solid {LINE}; }}
h3 {{ font-weight: 600 !important; font-size: 15px !important; }}
p, li {{ line-height: 1.6; }}
a {{ color: {a}; }}
hr {{ border-color: {LINE}; }}
.stCaption, [data-testid="stCaptionContainer"], .stMarkdown p small {{ color: {MUTED} !important; font-size: 12.5px; }}

/* ---- 侧边栏：与工作台导航同一语言 ---- */
section[data-testid="stSidebar"] {{ background: {BG}; border-right: 1px solid {LINE}; }}
section[data-testid="stSidebar"] > div {{ padding-top: 1.2rem; }}
section[data-testid="stSidebar"] [role=radiogroup] {{ gap: 2px; display: flex; flex-direction: column; align-items: stretch; }}
section[data-testid="stSidebar"] [role=radiogroup] > * {{ width: 100%; }}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] {{ border-radius: 8px; padding: 7px 10px; margin: 0;
  font-size: 14.5px; color: {TEXT2}; transition: background .12s; width: 100% !important; display: flex !important; }}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"]:hover {{ background: {SURFACE2}; }}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] {{
  background: {SURFACE}; color: {TEXT}; box-shadow: 0 0 0 1px {LINE}; font-weight: 500; }}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child {{ display: none !important; }}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] p {{ margin: 0; font-size: 14.5px; }}

/* ---- 控件 ---- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius: 8px; border: 1px solid {LINE2}; background: {SURFACE}; color: {TEXT}; font-weight: 500;
  padding: 6px 14px; box-shadow: none; transition: background .12s, border-color .12s; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ background: {SURFACE2}; border-color: {LINE2}; color: {TEXT}; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
  background: {a}; border-color: {a}; color: #fff; }}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{ filter: brightness(.94); background: {a}; }}
.stTextInput > div > div, .stTextArea > div > div, .stSelectbox > div > div, .stMultiSelect > div > div,
.stNumberInput > div > div {{ background: {SURFACE}; border: 1px solid {LINE2}; border-radius: 8px; }}
.stTextInput > div > div:focus-within, .stTextArea > div > div:focus-within, .stSelectbox > div > div:focus-within {{
  border-color: {TEXT}; box-shadow: none; }}
[data-testid="stFileUploader"] section {{ background: {SURFACE}; border: 1px dashed {LINE2}; border-radius: 12px; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ padding: 8px 12px; color: {MUTED}; font-weight: 500; }}
.stTabs [aria-selected="true"] {{ color: {TEXT}; border-bottom: 2px solid {TEXT}; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}
div[data-testid="stExpander"] {{ border: 1px solid {LINE}; border-radius: 12px; background: {SURFACE}; box-shadow: none; }}
[data-testid="stDataFrame"], [data-testid="stTable"] {{ border: 1px solid {LINE}; border-radius: 12px; overflow: hidden; }}
[data-testid="stMetric"] {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 12px; padding: 14px 16px; }}
[data-testid="stMetricLabel"] {{ color: {MUTED}; font-size: 12.5px; }}
[data-testid="stMetricValue"] {{ font-size: 24px; font-weight: 600; }}
[data-testid="stPlotlyChart"] {{ border-radius: 12px; overflow: hidden; }}
.stAlert {{ border-radius: 10px; }}
[data-testid="stStatusWidget"] {{ display: none; }}
div[data-testid="stStatus"] {{ border: 1px solid {LINE}; border-radius: 12px; background: {SURFACE}; }}
.stProgress > div > div {{ background: {a}; }}
code {{ font-family: {MONO}; font-size: 12.5px; }}

/* ---- 组件 ---- */
.dk-brand {{ display:flex; align-items:center; gap:10px; padding: 2px 4px 16px; border-bottom: 1px solid {LINE}; margin-bottom: 12px; }}
.dk-brand .mark {{ width:32px; height:32px; border-radius:9px; background:{a}; color:#fff; display:flex; align-items:center;
  justify-content:center; font-size:16px; flex:none; }}
.dk-brand .name {{ font-weight:600; font-size:15px; color:{TEXT}; line-height:1.15; }}
.dk-brand .sub {{ font-size:12px; color:{MUTED}; }}
.dk-fresh {{ display:flex; align-items:center; gap:8px; padding:8px 12px; border-radius:8px; background:{SURFACE};
  border:1px solid {LINE}; font-size:12.5px; color:{MUTED}; margin-top:12px; }}
.dk-fresh .dot {{ width:7px; height:7px; border-radius:50%; background:{GOOD}; flex:none; }}
.dk-fresh b {{ color:{TEXT}; font-weight:500; }}
.dk-headline {{ font-weight:600; font-size:24px; line-height:1.35; letter-spacing:-0.01em; color:{TEXT};
  padding:20px 24px; margin:8px 0 22px; background:{SURFACE}; border:1px solid {LINE}; border-left:4px solid {a}; border-radius:12px; }}
.dk-headline small {{ display:block; font-weight:400; font-size:13px; color:{MUTED}; margin-top:8px; }}
.dk-kpi {{ padding:14px 16px; background:{SURFACE}; border:1px solid {LINE}; border-radius:12px; }}
.dk-kpi .l {{ font-size:12.5px; color:{MUTED}; margin-bottom:6px; }}
.dk-kpi .v {{ font-weight:600; font-size:26px; line-height:1.1; color:{TEXT}; letter-spacing:-0.01em; }}
.dk-kpi .d {{ font-size:13px; font-weight:500; margin-top:6px; }}
.dk-kpi .d.up {{ color:{GOOD}; }} .dk-kpi .d.down {{ color:{BAD}; }} .dk-kpi .d.flat {{ color:{MUTED}; }}
.dk-kpi.accent {{ border-color:{a}; }}
.dk-chip {{ display:inline-flex; align-items:center; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; color:#fff; }}
.dk-card {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:12px; padding:16px 18px; height:100%; }}
.dk-card .t {{ font-weight:600; font-size:14px; color:{TEXT2}; margin-bottom:6px; }}
.dk-card .n {{ font-weight:600; font-size:26px; line-height:1.1; letter-spacing:-0.01em; }}
.dk-card .s {{ font-size:13px; color:{MUTED}; margin-top:8px; line-height:1.55; }}
.dk-card .m {{ font-size:13px; margin-top:6px; color:{TEXT2}; }}
.dk-list {{ padding-left:20px; }} .dk-list li {{ margin-bottom:8px; line-height:1.6; }}
.dk-num {{ font-weight:600; color:{a}; }}
.dk-empty {{ padding:30px 20px; text-align:center; color:{MUTED}; background:{SURFACE}; border:1px dashed {LINE2}; border-radius:12px; font-size:14px; }}
/* 旧类名兼容（雷达） */
.dr-brand{{}} .dr-list {{ padding-left:20px; }} .dr-list li {{ margin-bottom:8px; line-height:1.6; }} .dr-num {{ font-weight:600; color:{a}; }}
</style>
"""


# ---- Streamlit 组件 ----

def inject(app: str = "hub") -> None:
    import streamlit as st
    st.markdown(css(app), unsafe_allow_html=True)


def plotly_template(app: str = "hub") -> None:
    import plotly.graph_objects as go
    import plotly.io as pio
    t = go.layout.Template()
    t.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=TEXT2, size=13),
        title=dict(font=dict(family=FONT, size=16, color=TEXT), x=0, xanchor="left"),
        colorway=colorway(app),
        xaxis=dict(gridcolor=LINE, zerolinecolor=LINE2, linecolor=LINE2, tickcolor=LINE2),
        yaxis=dict(gridcolor=LINE, zerolinecolor=LINE2, linecolor=LINE2, tickcolor=LINE2),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED)),
        hoverlabel=dict(bgcolor=SURFACE, font=dict(color=TEXT, family=FONT), bordercolor=LINE2),
        margin=dict(t=40, l=40, r=20, b=40),
        coloraxis=dict(colorbar=dict(outlinewidth=0, tickfont=dict(color=MUTED))),
    )
    pio.templates["dramakit"] = t
    pio.templates.default = "dramakit"


def brand(name: str, sub: str = "", icon: str = "◼") -> None:
    import streamlit as st
    st.sidebar.markdown(f'<div class="dk-brand"><div class="mark">{icon}</div>'
                        f'<div><div class="name">{name}</div><div class="sub">{sub}</div></div></div>',
                        unsafe_allow_html=True)


def freshness(container, last_update: str, source_line: str) -> None:
    container.markdown(f'<div class="dk-fresh"><span class="dot"></span><span><b>{last_update}</b> 更新 · {source_line}</span></div>',
                       unsafe_allow_html=True)


def empty_state(msg: str) -> None:
    import streamlit as st
    st.markdown(f'<div class="dk-empty">{msg}</div>', unsafe_allow_html=True)


def headline(text: str, sub: str = "") -> None:
    import streamlit as st
    st.markdown(f'<div class="dk-headline">{text}{f"<small>{sub}</small>" if sub else ""}</div>', unsafe_allow_html=True)


def kpi(col, label: str, value: str, delta: str | None = None, good_when_up: bool = True, accent: bool = False) -> None:
    cls = "flat"
    if delta and delta not in ("—", ""):
        up = not delta.strip().startswith("-")
        cls = ("up" if up else "down") if good_when_up else ("down" if up else "up")
    d = f'<div class="d {cls}">{delta}</div>' if delta else ""
    col.markdown(f'<div class="dk-kpi{" accent" if accent else ""}"><div class="l">{label}</div><div class="v">{value}</div>{d}</div>',
                 unsafe_allow_html=True)


def chip(action: str, app: str = "hub") -> str:
    return f'<span class="dk-chip" style="background:{action_colors(accent(app)).get(action, MUTED)}">{action}</span>'


def card(col, title: str, number: str, meta: str = "", sub: str = "", color: str = TEXT) -> None:
    col.markdown(f'<div class="dk-card"><div class="t">{title}</div><div class="n" style="color:{color}">{number}</div>'
                 f'<div class="m">{meta}</div><div class="s">{sub}</div></div>', unsafe_allow_html=True)


STREAMLIT_CONFIG = """[theme]
base = "light"
primaryColor = "{accent}"
backgroundColor = "#f4f4f2"
secondaryBackgroundColor = "#ffffff"
textColor = "#151617"
font = "sans serif"

[client]
toolbarMode = "minimal"

[browser]
gatherUsageStats = false
"""


def streamlit_config(app: str) -> str:
    """各应用 .streamlit/config.toml 的内容（Streamlit 原生主题只能从这里改）。"""
    return STREAMLIT_CONFIG.replace("{accent}", accent(app))
