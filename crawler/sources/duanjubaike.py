"""短剧百科 duanjubaike.net —— 聚合番茄/红果/河马/点众等平台的短剧热度榜，每日更新，服务端直出 HTML。
榜单页：每条是 <a href="/duanju/info-{id}.html" title="短剧《名字》">，内部文字形如
  "短剧 5862万热度全 88 集 他深情侵入评分9.5 / 61.2万收藏 / 104万次点赞第1季 / 爱情 / 王小亿 / 沉思"
详情页：剧情介绍、分类标签、出品方、上映时间、评分、播放/热度/收藏。
解析只认链接和文字模式，不依赖 class 名，改版不容易断。
"""
import re
import logging
from datetime import datetime

from bs4 import BeautifulSoup

from crawler.base import BaseSource, DramaItem
from db.session import session_scope
from db.models import Drama, PlatformListing

log = logging.getLogger("crawler.duanjubaike")

BASE = "https://www.duanjubaike.net"
BOARDS = {                       # 榜单名 -> 路径；rank 只取热播榜的，其它榜只补 raw_tags
    "热播榜": "/paihang/rebo.html",
    "新剧榜": "/paihang/xinju.html",
    "热搜榜": "/paihang/reso.html",
    "收藏榜": "/paihang/shoucang.html",
}
DETAIL_BUDGET = 60               # 每次运行最多补抓多少个详情页（首轮之后每天只有新剧需要）

RE_ID = re.compile(r"/duanju/info-(\d+)\.html")
RE_TITLE = re.compile(r"《(.+?)》")
RE_HEAT = re.compile(r"([\d.]+)\s*(万|亿)?热度")
RE_EPS = re.compile(r"全\s*(\d+)\s*集")
RE_SCORE = re.compile(r"评分\s*([\d.]+)")
RE_FAV = re.compile(r"([\d.]+)\s*(万|亿)?收藏")
RE_LIKE = re.compile(r"([\d.]+)\s*(万|亿)?次点赞")
RE_TAIL = re.compile(r"点赞\s*(.+)$")          # 点赞后面是 "第1季 / 爱情 / 演员 / 演员"
RE_SEASON = re.compile(r"^第\d+季$")


def _num(v: str, unit: str | None) -> float:
    x = float(v)
    return x * {"万": 1e4, "亿": 1e8}.get(unit or "", 1)


class DuanjubaikeSource(BaseSource):
    name = "duanjubaike"

    # ---------- 榜单 ----------
    def parse_board(self, html: str, board: str) -> dict[str, DramaItem]:
        soup = BeautifulSoup(html, "lxml")
        items: dict[str, DramaItem] = {}
        rank = 0
        for a in soup.select('a[href*="/duanju/info-"]'):
            m = RE_ID.search(a.get("href", ""))
            if not m:
                continue
            pid = m.group(1)
            if pid in items:
                continue
            title_attr = a.get("title", "")
            tm = RE_TITLE.search(title_attr)
            text = " ".join(a.get_text(" ", strip=True).split())
            title = tm.group(1) if tm else ""
            if not title:
                continue
            rank += 1
            heat = fav = like = None
            if (h := RE_HEAT.search(text)):
                heat = _num(h.group(1), h.group(2))
            if (f := RE_FAV.search(text)):
                fav = _num(f.group(1), f.group(2))
            if (l := RE_LIKE.search(text)):
                like = _num(l.group(1), l.group(2))
            tags = [board]
            if (t := RE_TAIL.search(text)):
                parts = [p.strip() for p in t.group(1).split("/") if p.strip()]
                # 结构：[第X季] / 题材 / 演员 / 演员 —— 题材是第一个不是"第X季"的
                genre_parts = [p for p in parts if not RE_SEASON.match(p)]
                if genre_parts:
                    tags.append(genre_parts[0])
                    actors = genre_parts[1:3]
                else:
                    actors = []
            else:
                actors = []
            if (e := RE_EPS.search(text)):
                tags.append(f"{e.group(1)}集")
            if (s := RE_SCORE.search(text)):
                tags.append(f"评分{s.group(1)}")
            items[pid] = DramaItem(
                platform=self.name, platform_id=pid, title=title,
                url=f"{BASE}/duanju/info-{pid}.html",
                raw_tags=tags + [f"主演:{x}" for x in actors],
                rank=rank if board == "热播榜" else None,
                heat=heat if board == "热播榜" else None,
                likes=int(like) if like is not None and board == "热播榜" else None,
                comments_cnt=None,
            )
            if fav is not None and board == "热播榜":
                items[pid].raw_tags.append(f"收藏:{int(fav)}")
        return items

    # ---------- 详情 ----------
    def parse_detail(self, html: str) -> dict:
        soup = BeautifulSoup(html, "lxml")
        out = {"synopsis": "", "tags": [], "producer": "", "cover": "", "release": ""}
        # 剧情介绍：找含"剧情介绍"的标题，取其后第一段有内容的文字
        for h in soup.find_all(["h2", "h3", "h4", "div", "p"]):
            if "剧情介绍" in h.get_text() and len(h.get_text(strip=True)) < 60:
                nxt = h.find_next(string=lambda s: s and len(s.strip()) > 30)
                if nxt:
                    out["synopsis"] = nxt.strip()
                break
        if not out["synopsis"]:
            md = soup.find("meta", attrs={"name": "description"})
            if md:
                out["synopsis"] = md.get("content", "").strip()
        out["tags"] = [a.get_text(strip=True) for a in soup.select('a[href*="/tags?id="]')][:10]
        prod = soup.select_one('a[href*="/gongsi/info-"]')
        if prod:
            out["producer"] = prod.get_text(strip=True)
        img = soup.find("img", alt=lambda s: s and "海报" in s)
        if img:
            out["cover"] = img.get("src", "")
        rm = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)\s*上线", soup.get_text(" "))
        if rm:
            out["release"] = rm.group(1)
        return out

    # ---------- 主流程 ----------
    def fetch(self):
        merged: dict[str, DramaItem] = {}
        for board, path in BOARDS.items():
            try:
                html = self.fetcher.get(BASE + path, snapshot_tag=self.name)
            except Exception as e:
                log.warning("%s 抓取失败: %s", board, e)
                continue
            got = self.parse_board(html, board)
            log.info("%s: %d 条", board, len(got))
            for pid, it in got.items():
                if pid in merged:
                    m = merged[pid]
                    m.raw_tags = list(dict.fromkeys(m.raw_tags + it.raw_tags))
                    if m.heat is None and it.heat is not None:
                        m.heat, m.rank, m.likes = it.heat, it.rank, it.likes
                else:
                    merged[pid] = it

        # 只给库里还没有简介的剧补详情，控制请求量
        need = self._need_detail(list(merged))
        budget = DETAIL_BUDGET
        for pid in need:
            if budget <= 0:
                break
            it = merged[pid]
            try:
                html = self.fetcher.get(it.url, snapshot_tag=self.name + "_detail")
            except Exception as e:
                log.warning("详情失败 %s: %s", it.title, e)
                continue
            budget -= 1
            d = self.parse_detail(html)
            it.synopsis = d["synopsis"]
            it.producer = d["producer"]
            it.cover = d["cover"]
            it.raw_tags = list(dict.fromkeys(it.raw_tags + d["tags"] + ([f"上线:{d['release']}"] if d["release"] else [])))
        log.info("详情补抓 %d 条", DETAIL_BUDGET - budget)
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
