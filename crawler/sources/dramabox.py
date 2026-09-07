"""DramaBox（StoryMatrix，出海平台）—— 列表页（首页/browse）只有 剧名+集数+标签，没有简介。
简介在详情页 /drama/<id>/<slug> 的 meta description 里，按 DETAIL_BUDGET 增量补抓。
"""
import re
import logging

from bs4 import BeautifulSoup

from crawler.base import BaseSource, DramaItem
from db.session import session_scope
from db.models import Drama, PlatformListing

log = logging.getLogger("crawler.dramabox")
BASE = "https://www.dramabox.com"
PAGES = ["/", "/browse"]
DETAIL_BUDGET = 40

RE_EPS = re.compile(r"(\d+)\s*Episodes")
RE_LINK = re.compile(r"/drama/\d+/[^\s\"'?]+", re.I)


class DramaBoxSource(BaseSource):
    name = "dramabox"

    # ---------- 列表：剧名 + 集数 + 标签 ----------
    def parse(self, html: str, page: str) -> list[DramaItem]:
        soup = BeautifulSoup(html, "lxml")
        out, seen = [], set()
        for node in soup.find_all(string=RE_EPS):
            box = node.parent
            for _ in range(4):
                if box is None: break
                if box.find("img") and len(box.get_text(" ", strip=True)) > 30:
                    break
                box = box.parent
            if box is None:
                continue
            img = box.find("img")
            a = box.find("a", href=RE_LINK)
            title = (img.get("alt", "").strip() if img else "") or (a.get_text(strip=True) if a else "")
            if not title or title in seen:
                continue
            seen.add(title)
            text = box.get_text("\n", strip=True)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            eps = RE_EPS.search(text).group(1)
            tags = [l for l in lines if l != title and not RE_EPS.match(l) and 2 <= len(l) <= 30]
            url = (BASE + a["href"]) if a and a["href"].startswith("/") else (a["href"] if a else BASE)
            out.append(DramaItem(
                platform=self.name, platform_id=re.sub(r"\W+", "-", title.lower())[:80],
                title=title, market="global", url=url,
                cover=(img.get("src") or "") if img else "",
                raw_tags=[f"DramaBox:{page}", f"{eps}集"] + tags, heat=100.0,
            ))
        return out

    # ---------- 详情：简介在 meta description 里 ----------
    def parse_detail(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        return (md.get("content", "").strip() if md else "")

    def fetch(self):
        merged: dict[str, DramaItem] = {}
        for path in PAGES:
            try:
                html = self.fetcher.get(BASE + path, snapshot_tag=self.name)
            except Exception as e:
                log.info("DramaBox %s 跳过: %s", path, str(e)[:80]); continue
            items = self.parse(html, path)
            log.info("DramaBox %s: %d 条", path, len(items))
            for it in items:
                if it.platform_id in merged:
                    m = merged[it.platform_id]
                    m.raw_tags = list(dict.fromkeys(m.raw_tags + it.raw_tags))
                else:
                    merged[it.platform_id] = it

        need = self._need_detail(list(merged))
        budget = DETAIL_BUDGET
        filled = 0
        for pid in need:
            if budget <= 0:
                break
            it = merged[pid]
            try:
                html = self.fetcher.get(it.url, snapshot_tag=self.name + "_detail")
            except Exception as e:
                log.warning("详情失败 %s: %s", it.title, str(e)[:100]); continue
            budget -= 1
            it.synopsis = self.parse_detail(html)
            filled += 1
        log.info("DramaBox 详情补抓 %d 条，合计 %d 部", filled, len(merged))
        yield from merged.values()

    def _need_detail(self, pids: list[str]) -> list[str]:
        with session_scope() as s:
            have = {
                l.platform_id for l, d in s.query(PlatformListing, Drama)
                .join(Drama, Drama.id == PlatformListing.drama_id)
                .filter(PlatformListing.platform == self.name, PlatformListing.platform_id.in_(pids))
                .filter(Drama.synopsis != "")
            }
        return [p for p in pids if p not in have]
