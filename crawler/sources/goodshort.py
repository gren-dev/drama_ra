"""GoodShort（NewReading，出海平台）—— 分类列表页只有剧名+标签；播放量、简介、演员、集数在详情页。
两步：
1. parse_list: 10 个分类页 × 2 页，拿 剧名 + 标签（标签就是这个平台的题材体系，比通用词表细）
2. parse_detail: 对拿到简介的剧数按 DETAIL_BUDGET 增量补抓 Views / Followers / Genre / Cast / 集数 / 简介
"""
import re
import logging

from bs4 import BeautifulSoup

from crawler.base import BaseSource, DramaItem
from db.session import session_scope
from db.models import Drama, PlatformListing

log = logging.getLogger("crawler.goodshort")
BASE = "https://www.goodshort.com"
CATEGORIES = {
    "All": "/dramas/playlets",
    "Fantasy": "/dramas/fantasy-135-playlets",
    "Urban": "/dramas/urban-136-playlets",
    "Romance": "/dramas/romance-137-playlets",
    "Thriller": "/dramas/thriller-139-playlets",
    "Superpower": "/dramas/superpower-140-playlets",
    "Ancient": "/dramas/ancient-141-playlets",
    "Action": "/dramas/action-142-playlets",
    "Sci-Fi": "/dramas/sci-fi-146-playlets",
    "Suspense": "/dramas/suspense-149-playlets",
}
PAGES = 2
DETAIL_BUDGET = 60

RE_ID = re.compile(r"/drama/([a-z0-9\-]+?)-(\d{6,})", re.I)
RE_TAG = re.compile(r"/tag/([a-z0-9\-]+)-playlets-videos", re.I)
RE_GENRE_LINK = re.compile(r"/dramas/[a-z0-9\-]+-\d+-playlets", re.I)
RE_VIEWS = re.compile(r"Views\s*([\d.]+)\s*([KMB])?", re.I)
RE_FOLLOWERS = re.compile(r"Followers\s*([\d.]+)\s*([KMB])?", re.I)
RE_EPCOUNT = re.compile(r"EP\.(\d+)")
RE_ACTOR = re.compile(r"/actor/")


def _num(v: str, unit: str | None) -> float:
    return float(v) * {"K": 1e3, "M": 1e6, "B": 1e9}.get((unit or "").upper(), 1)


def _clean_title(raw: str) -> str:
    return re.split(r"-short drama", raw, flags=re.I)[0].strip()


class GoodShortSource(BaseSource):
    name = "goodshort"

    # ---------- 分类列表：剧名 + 标签 ----------
    def parse_list(self, html: str, category: str) -> list[DramaItem]:
        soup = BeautifulSoup(html, "lxml")
        out: list[DramaItem] = []
        seen: set[str] = set()
        current: DramaItem | None = None
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = RE_ID.search(href)
            if m:
                pid = m.group(2)
                if pid in seen:
                    current = None
                    continue
                title = _clean_title(a.get_text(strip=True))
                if not title:
                    img = a.find("img")
                    title = _clean_title(img.get("alt", "")) if img else ""
                if not title:
                    current = None
                    continue
                seen.add(pid)
                current = DramaItem(
                    platform=self.name, platform_id=pid, title=title, market="global",
                    url=BASE + href if href.startswith("/") else href,
                    raw_tags=[f"GoodShort:{category}"],
                    rank=len(out) + 1 if category == "All" else None,
                    heat=max(1.0, 200 - len(out) * 2) if category == "All" else None,
                )
                out.append(current)
                continue
            tm = RE_TAG.search(href)
            if tm and current is not None:
                tag = tm.group(1).replace("-", " ").title()
                if tag not in current.raw_tags:
                    current.raw_tags.append(tag)
        return out

    # ---------- 详情页：播放量/关注/简介/演员/集数 ----------
    def parse_detail(self, html: str) -> dict:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)
        out = {"synopsis": "", "views": None, "followers": None, "genre": "", "cast": [], "episodes": None, "cover": ""}

        vm = RE_VIEWS.search(text)
        if vm:
            out["views"] = _num(*vm.groups())
        fm = RE_FOLLOWERS.search(text)
        if fm:
            out["followers"] = _num(*fm.groups())
        em = RE_EPCOUNT.search(text)
        if em:
            out["episodes"] = int(em.group(1))

        glink = soup.find("a", href=RE_GENRE_LINK)
        if glink:
            out["genre"] = glink.get_text(strip=True)

        out["cast"] = [a.get_text(strip=True) for a in soup.find_all("a", href=RE_ACTOR)][:3]

        syn_head = soup.find(string=re.compile(r"^\s*Synopsis\s*$", re.I))
        if syn_head:
            p = syn_head.find_parent().find_next("p")
            if p:
                out["synopsis"] = p.get_text(strip=True)
        if not out["synopsis"]:
            md = soup.find("meta", attrs={"name": "description"})
            if md:
                m = re.search(r"telling a story of (.+?),\s*[\w\s]+ short description", md.get("content", ""))
                out["synopsis"] = (m.group(1) if m else md.get("content", "")).strip()

        img = soup.find("img", src=re.compile(r"/videobook/"))
        if img:
            out["cover"] = img.get("src", "")
        return out

    def fetch(self):
        merged: dict[str, DramaItem] = {}
        for cat, path in CATEGORIES.items():
            total = 0
            for page in range(1, PAGES + 1):
                url = BASE + path + (f"?page={page}" if page > 1 else "")
                try:
                    html = self.fetcher.get(url, snapshot_tag=self.name)
                except Exception as e:
                    log.warning("%s p%d 失败: %s", cat, page, str(e)[:100]); break
                items = self.parse_list(html, cat)
                if not items:
                    break
                total += len(items)
                for it in items:
                    if it.platform_id in merged:
                        m = merged[it.platform_id]
                        m.raw_tags = list(dict.fromkeys(m.raw_tags + it.raw_tags))
                    else:
                        merged[it.platform_id] = it
            log.info("GoodShort %s: %d 条", cat, total)

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
            d = self.parse_detail(html)
            it.synopsis = d["synopsis"]
            it.cover = d["cover"] or it.cover
            it.heat = d["views"] if d["views"] is not None else it.heat
            it.likes = int(d["followers"]) if d["followers"] is not None else it.likes
            extra = ([d["genre"]] if d["genre"] else []) + [f"主演:{c}" for c in d["cast"]]
            if d["episodes"]:
                extra.append(f"{d['episodes']}集")
            it.raw_tags = list(dict.fromkeys(it.raw_tags + extra))
            filled += 1
        log.info("GoodShort 详情补抓 %d 条，合计 %d 部", filled, len(merged))
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
