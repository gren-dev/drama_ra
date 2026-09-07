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

html, body, [class*="css"], .stApp {{ font-family: {BODY}; color: {TEXT}; }}
.stApp {{ background: {BG}; }}
section[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {LINE}; }}
section[data-testid="stSidebar"] .stRadio label {{ font-size: 15px; padding: 6px 4px; }}
section[data-testid="stSidebar"] .stRadio [role=radiogroup] > label {{ border-radius: 6px; }}
section[data-testid="stSidebar"] .stRadio [role=radiogroup] > label:has(input:checked) {{ background: {SURFACE2}; }}
h1, h2, h3 {{ font-family: {DISPLAY}; letter-spacing: 0.01em; }}
h1 {{ font-weight: 900; font-size: 34px !important; margin-bottom: 4px !important; }}
h2 {{ font-weight: 700; font-size: 22px !important; color: {TEXT}; margin-top: 28px !important; }}
h3 {{ font-weight: 700; font-size: 18px !important; }}
.stCaption, .stMarkdown p small, [data-testid="stCaptionContainer"] {{ color: {MUTED} !important; }}
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 8px; overflow: hidden; }}
div[data-testid="stExpander"] {{ border: 1px solid {LINE}; border-radius: 8px; background: {SURFACE}; }}
.stSelectbox > div > div, .stMultiSelect > div > div, .stTextInput > div > div {{ background: {SURFACE}; border-color: {LINE}; }}
hr {{ border-color: {LINE}; }}

/* 片头字卡：本周一句话 */
.dr-headline {{
  font-family: {DISPLAY}; font-weight: 900; font-size: 30px; line-height: 1.35;
  color: {TEXT}; padding: 22px 26px; margin: 8px 0 22px;
  background: linear-gradient(90deg, {SURFACE} 0%, {BG} 100%);
  border-left: 5px solid {ACCENT}; border-radius: 4px 10px 10px 4px;
}}
.dr-headline small {{ display:block; font-family:{BODY}; font-weight:400; font-size:13px; color:{MUTED}; margin-top:8px; }}

/* KPI：数字当视觉，不加框 */
.dr-kpi {{ padding: 6px 0 4px; border-top: 2px solid {LINE}; }}
.dr-kpi .l {{ font-size: 13px; color: {MUTED}; margin-bottom: 4px; }}
.dr-kpi .v {{ font-family: {DISPLAY}; font-weight: 900; font-size: 34px; line-height: 1.1; color: {TEXT}; }}
.dr-kpi .d {{ font-size: 14px; font-weight: 500; margin-top: 4px; }}
.dr-kpi .d.up {{ color: {GOOD}; }} .dr-kpi .d.down {{ color: {ACCENT}; }} .dr-kpi .d.flat {{ color: {MUTED}; }}
.dr-kpi.accent {{ border-top-color: {ACCENT}; }}

/* 动作 chip */
.dr-chip {{ display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; color: {BG}; }}

/* 周报卡 */
.dr-card {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 10px; padding: 16px 18px; height: 100%; }}
.dr-card .t {{ font-weight: 700; font-size: 16px; margin-bottom: 6px; }}
.dr-card .n {{ font-family: {DISPLAY}; font-weight: 900; font-size: 28px; line-height: 1.1; }}
.dr-card .s {{ font-size: 13px; color: {MUTED}; margin-top: 8px; line-height: 1.5; }}
.dr-card .m {{ font-size: 13px; margin-top: 4px; }}
.dr-list li {{ margin-bottom: 8px; line-height: 1.55; }}
.dr-num {{ font-family: {DISPLAY}; font-weight: 900; color: {ACCENT}; }}
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
