"""DataEye 短剧观察 热榜。
页面结构会变，这里的选择器需要对照真实页面校准（打开页面 → F12 → 找榜单列表的容器）。
更省事的路线：在 Network 面板里找它前端调用的 JSON 接口，把 API_URL 填上，走 parse_api()。
"""
import logging
from bs4 import BeautifulSoup
from crawler.base import BaseSource, DramaItem, render_page

log = logging.getLogger("crawler.dataeye")

RANK_URL = "https://short-drama.dataeye.com/rank"   # TODO: 核对真实榜单地址
API_URL = ""                                         # 如果抓到 JSON 接口就填这里

# TODO: 按真实页面改这三个选择器
ITEM_SEL = ".rank-list .rank-item"
TITLE_SEL = ".name"
HEAT_SEL = ".heat"


def _num(s: str) -> float:
    s = (s or "").replace(",", "").strip()
    mult = 1
    for suf, m in (("亿", 1e8), ("万", 1e4), ("w", 1e4), ("k", 1e3)):
        if s.endswith(suf):
            s, mult = s[:-len(suf)], m
            break
    try:
        return float(s) * mult
    except ValueError:
        return 0.0


class DataEyeSource(BaseSource):
    name = "dataeye"

    def fetch(self):
        if API_URL:
            yield from self.parse_api()
            return
        # 大概率是 SPA，直接用 Playwright 渲染
        html = render_page(RANK_URL, wait_selector=ITEM_SEL)
        self.fetcher.snapshot(self.name, RANK_URL, html)
        yield from self.parse_html(html)

    def parse_html(self, html: str):
        soup = BeautifulSoup(html, "lxml")
        for i, el in enumerate(soup.select(ITEM_SEL), start=1):
            title_el = el.select_one(TITLE_SEL)
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            heat_el = el.select_one(HEAT_SEL)
            link = el.select_one("a[href]")
            yield DramaItem(
                platform=self.name,
                platform_id=title,                 # 没有稳定 id 时用标题
                title=title,
                url=link["href"] if link else RANK_URL,
                heat=_num(heat_el.get_text()) if heat_el else None,
                rank=i,
                raw_tags=[t.get_text(strip=True) for t in el.select(".tag")],
            )

    def parse_api(self):
        data = self.fetcher.get_json(API_URL, snapshot_tag=self.name)
        # TODO: 按真实返回结构改字段路径
        for i, row in enumerate(data.get("data", {}).get("list", []), start=1):
            yield DramaItem(
                platform=self.name,
                platform_id=str(row.get("id") or row.get("name")),
                title=row.get("name", ""),
                synopsis=row.get("desc", ""),
                cover=row.get("cover", ""),
                producer=row.get("company", ""),
                heat=float(row.get("heat") or 0),
                rank=i,
                raw_tags=row.get("tags") or [],
            )
