"""NetShort（NETSTORY，出海平台，12 种语言）—— 列表是前端渲染，用 Playwright。
/dramas/all-plots 列表：剧名 + 平台标签（如 "Rebirth ⦁ Elite"）。
首次使用：python -m playwright install chromium（Actions 里已装）。
"""
import re
import logging
from bs4 import BeautifulSoup
from crawler.base import BaseSource, DramaItem, render_page

log = logging.getLogger("crawler.netshort")
BASE = "https://netshort.com"
LIST_URL = BASE + "/dramas/all-plots"
RE_LINK = re.compile(r"/(?:drama|dramas|play|video|series)/[^\s\"']+", re.I)


class NetShortSource(BaseSource):
    name = "netshort"

    def parse(self, html: str) -> list[DramaItem]:
        soup = BeautifulSoup(html, "lxml")
        out, seen = [], set()
        # 卡片 = 含图片 + 含 "A ⦁ B" 标签文本 的最小块
        for tag_node in soup.find_all(string=re.compile(r"⦁|•|·")):
            box = tag_node.parent
            for _ in range(4):
                if box is None: break
                if box.find("img") or box.find("a", href=True):
                    break
                box = box.parent
            if box is None:
                continue
            a = box.find("a", href=True)
            img = box.find("img")
            title = ""
            for el in box.find_all(["h2", "h3", "h4", "p", "span", "div"]):
                t = el.get_text(strip=True)
                if t and not re.search(r"⦁|•", t) and 3 <= len(t) <= 80 and not el.find(True):
                    title = t; break
            if not title and img:
                title = img.get("alt", "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            tags = [t.strip() for t in re.split(r"[⦁•·]", str(tag_node)) if t.strip()]
            href = a["href"] if a else ""
            out.append(DramaItem(
                platform=self.name, platform_id=re.sub(r"\W+", "-", title.lower())[:80], title=title, market="global",
                url=(BASE + href) if href.startswith("/") else (href or LIST_URL),
                cover=(img.get("src") or "") if img else "",
                raw_tags=[f"NetShort:{t}" for t in tags], rank=len(out) + 1,
                heat=max(10.0, 120 - len(out) * 1.5),
            ))
        return out

    def fetch(self):
        try:
            html = render_page(LIST_URL, wait_selector="img", timeout_ms=45000)
        except Exception as e:
            log.warning("NetShort 渲染失败（需要 playwright install chromium）: %s", str(e)[:120]); return
        self.fetcher.snapshot(self.name, LIST_URL, html)
        items = self.parse(html)
        log.info("NetShort: %d 条", len(items))
        yield from items
