"""番茄小说 榜单：红果大量剧改编自番茄，小说榜是题材的先行指标。
番茄网页版 https://fanqienovel.com 是 SPA，数据来自接口；先用 Playwright 渲染榜单页，
稳定后可以换成它的 JSON 接口（Network 面板里能看到）。
"""
import logging
from bs4 import BeautifulSoup
from crawler.base import BaseSource, DramaItem, render_page

log = logging.getLogger("crawler.fanqie")

RANK_URLS = {
    "男频热榜": "https://fanqienovel.com/rank/1_1_1",   # TODO: 核对真实榜单地址
    "女频热榜": "https://fanqienovel.com/rank/1_2_1",
}
ITEM_SEL = ".rank-book-item"     # TODO: 按真实页面改
TITLE_SEL = ".book-name"
DESC_SEL = ".book-desc"


class FanqieSource(BaseSource):
    name = "fanqie"

    def fetch(self):
        for board, url in RANK_URLS.items():
            try:
                html = render_page(url, wait_selector=ITEM_SEL)
            except Exception as e:
                log.warning("fanqie %s failed: %s", board, e)
                continue
            self.fetcher.snapshot(self.name, url, html)
            soup = BeautifulSoup(html, "lxml")
            for i, el in enumerate(soup.select(ITEM_SEL), start=1):
                t = el.select_one(TITLE_SEL)
                if not t:
                    continue
                d = el.select_one(DESC_SEL)
                link = el.select_one("a[href]")
                yield DramaItem(
                    platform=self.name,
                    platform_id=(link["href"] if link else t.get_text(strip=True)),
                    title=t.get_text(strip=True),
                    url=link["href"] if link else url,
                    synopsis=d.get_text(strip=True) if d else "",
                    rank=i,
                    raw_tags=[board] + [x.get_text(strip=True) for x in el.select(".tag")],
                )
