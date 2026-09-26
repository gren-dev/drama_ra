"""雷达视觉层：直接使用片场工作台的设计系统（dramakit.theme），本地和 Cloud 长得一样。

本地工作台装了 dramakit 就用它；Streamlit Cloud 没有共享包时用随仓库带的副本 app/_dk_theme.py。
（副本由 dramakit/theme.py 复制而来，升级设计系统时一起覆盖。）
对外保留旧接口：inject / plotly_template / brand / freshness / empty_state / headline / kpi / chip / card / fmt_num
以及 ACTION_COLOR / ACCENT / GOOD / COOL / WARN / DIM / VIOLET / MUTED / LINE / TEXT / SURFACE / SURFACE2 / BG。
"""
try:
    from dramakit import theme as _t
except ImportError:
    from app import _dk_theme as _t

APP = "drama_radar"

BG, SURFACE, SURFACE2, TEXT, MUTED, LINE = _t.BG, _t.SURFACE, _t.SURFACE2, _t.TEXT, _t.MUTED, _t.LINE
GOOD, COOL, WARN, DIM, VIOLET = _t.GOOD, _t.COOL, _t.WARN, _t.DIM, _t.VIOLET
ACCENT = _t.accent(APP)
ACTION_COLOR = _t.action_colors(ACCENT)
COLORWAY = _t.colorway(APP)
DISPLAY = BODY = _t.FONT


def inject():
    _t.inject(APP)


def plotly_template():
    _t.plotly_template(APP)


def brand(name: str = "短剧题材雷达", sub: str = "AI 题材分析"):
    _t.brand(name, sub, icon="📡")


freshness = _t.freshness
empty_state = _t.empty_state
headline = _t.headline
kpi = _t.kpi
card = _t.card


def chip(action: str) -> str:
    return _t.chip(action, APP)


def fmt_num(x, digits: int = 1) -> str:
    """大数字压成 12.3万 / 1.2亿。"""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    if x != x:
        return "—"
    for unit, div in (("亿", 1e8), ("万", 1e4)):
        if abs(x) >= div:
            return f"{x/div:.{digits}f}{unit}"
    return f"{x:,.0f}"
