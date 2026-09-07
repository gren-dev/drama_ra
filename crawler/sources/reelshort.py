"""ReelShort（Crazy Maple Studio，出海头部平台）—— Next.js 服务端渲染。
首页有：TOP 榜（排名 1-10）、New Release、十几个主题货架；每部剧带 Hot/New/Trending 标记。
没有播放量，用"曝光分"当 heat：TOP 位次 + 出现在几个货架 + 标记加权。
"""
import re
import logging
from bs4 import BeautifulSoup
from crawler.base import BaseSource, DramaItem

log = logging.getLogger("crawler.reelshort")
BASE = "https://www.reelshort.com"
RE_EP = re.compile(r"/episodes/(?:%2Fepisodes%2F)?episode-1-([a-z0-9\-]+?)-([0-9a-f]{24})-", re.I)
BADGE_SCORE = {"Hot": 150, "Trending": 150, "New": 50}


class ReelShortSource(BaseSource):
    name = "reelshort"

    def parse_home(self, html: str) -> list[DramaItem]:
        soup = BeautifulSoup(html, "lxml")
        items: dict[str, DramaItem] = {}
        shelf = "首页"
        for el in soup.find_all(["h2", "h3", "a"]):
            if el.name == "h2":                       # 货架标题
                shelf = el.get_text(strip=True).replace("View all", "").strip() or shelf
                continue
            a = el if el.name == "a" else (el.find("a", href=RE_EP) or el.find_parent("a", href=RE_EP))
            if not a or not a.get("href") or not RE_EP.search(a["href"]):
                continue
            slug, bid = RE_EP.search(a["href"]).groups()
            title = (el.get_text(strip=True) if el.name == "h3" else "") or a.get("title") or ""
            if not title:
                img = a.find("img")
                title = img.get("alt", "").strip() if img else ""
            if not title:
                continue
            it = items.get(bid)
            if it is None:
                it = DramaItem(platform=self.name, platform_id=bid, title=title, market="global",
                               url=f"{BASE}/episodes/episode-1-{slug}-{bid}", raw_tags=[], heat=0.0)
                img = a.find("img")
                if img:
                    it.cover = img.get("src", "")
                items[bid] = it
            if f"货架:{shelf}" not in it.raw_tags:
                it.raw_tags.append(f"货架:{shelf}")
                it.heat += 100
            # 标记和 TOP 排名在同一个卡片容器里：取"只含这一张卡片"的最大祖先
            box, node = a, a.parent
            for _ in range(4):
                if node is None or node.name in ("body", "html"):
                    break
                ids = set(m.group(2) for m in RE_EP.finditer(str(node)))
                if ids == {bid}:
                    box = node
                elif len(ids) > 1:
                    break
                node = node.parent
            for el in box.find_all(["span", "div", "em", "i", "b", "p"]):
                t = el.get_text(strip=True)
                if t in BADGE_SCORE and t not in it.raw_tags:
                    it.raw_tags.append(t); it.heat += BADGE_SCORE[t]
                elif shelf.upper().startswith("TOP") and t.isdigit() and 1 <= int(t) <= 10 and it.rank is None:
                    it.rank = int(t); it.heat += (11 - it.rank) * 60
            # 首页轮播里有简介和题材标签（Werewolf/Mafia...），能拿就拿
            full = a.get_text(" ", strip=True)
            if len(full) > 120 and not it.synopsis:
                it.synopsis = full[:600]
        return list(items.values())

    def fetch(self):
        try:
            html = self.fetcher.get(BASE + "/", snapshot_tag=self.name)
        except Exception as e:
            log.warning("ReelShort 首页失败: %s", e); return
        items = self.parse_home(html)
        log.info("ReelShort: %d 条（TOP %d）", len(items), sum(1 for i in items if i.rank))
        yield from items
