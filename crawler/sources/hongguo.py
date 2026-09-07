"""红果短剧官方网页版 hongguoduanju.com —— 服务端渲染的 SEO 榜单页，不需要逆向 App。
四个榜：红果热播榜(总榜) / 真人剧 / AI剧 / 漫剧，每榜 5 页 × 20 条。
每条自带：series_id、剧名、热度、评分、收藏、点赞、标签、新剧标记、简介、封面。
每个榜单单独记一条 listing + snapshot（platform = hongguo:<榜名>），这样 AI 剧可以单独看趋势。
解析只认 detail?series_id= 链接和文字模式，不依赖 class 名。
"""
import re
import json
import logging

from bs4 import BeautifulSoup

from crawler.base import BaseSource, DramaItem

log = logging.getLogger("crawler.hongguo")

BASE = "https://hongguoduanju.com"
BOARDS = {
    "总榜": "/rank/hot-drama",
    "真人剧": "/rank/hot-real-drama",
    "AI剧": "/rank/hot-ai-drama",
    "漫剧": "/rank/hot-comic-drama",
}
PAGES = 5

RE_SID = re.compile(r"series_id=(\d+)")
RE_HEAT = re.compile(r"([\d.]+)\s*(万|亿)?热度")
RE_SCORE = re.compile(r"评分\s*([\d.]+)")
RE_FAV = re.compile(r"([\d.]+)\s*(万|亿)?收藏")
RE_LIKE = re.compile(r"([\d.]+)\s*(万|亿)?点赞")
RE_EPS = re.compile(r"全\s*(\d+)\s*集")
RE_CJK = re.compile(r"[\u4e00-\u9fff]")
METRIC_WORDS = ("热度", "评分", "收藏", "点赞", "新剧", "播放正片")


def _num(v: str, unit: str | None) -> float:
    return float(v) * {"万": 1e4, "亿": 1e8}.get(unit or "", 1)


def _container_for(h2):
    """从 h2 往上找：只含一个 series_id 的最大祖先（这样封面图和简介都在里面）。"""
    node, best = h2, h2.parent
    for _ in range(8):
        if node is None or node.name in ("body", "html"):
            break
        sids = set(RE_SID.findall(str(node)))
        if len(sids) == 1:
            best = node
        elif len(sids) > 1:
            break
        node = node.parent
    return best


RE_ROUTER = re.compile(r"_ROUTER_DATA\s*=\s*(\{.*?\})\s*(?:;|</script>)", re.S)
KEY_TITLE = ("seriesName", "series_name", "title", "name", "bookName", "book_name")
KEY_HEAT = ("hotScore", "hot_score", "hot", "heat", "hotText", "hot_text", "popularity")
KEY_DESC = ("abstract", "desc", "description", "intro", "introduction", "summary", "seriesIntro")
KEY_SCORE = ("score", "rating", "seriesScore")
KEY_FAV = ("collectCount", "collect_count", "favorite", "favoriteCount", "collectText")
KEY_LIKE = ("diggCount", "digg_count", "likeCount", "like_count", "diggText")
KEY_TAGS = ("tags", "tagList", "tag_list", "category", "categories", "genre", "labels")
KEY_COVER = ("cover", "coverUrl", "cover_url", "thumbUrl", "poster")
KEY_EPS = ("episodeCount", "episode_count", "totalEpisode", "total_episode", "episodeCnt")


def _pick(d: dict, keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, "", [], {}):
            return d[k]
    return default


def _to_num(v) -> float | None:
    """'5948万热度' / '60.1万' / 59480000 / '5948万' -> float"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"([\d.]+)\s*(万|亿)?", str(v))
    return _num(m.group(1), m.group(2)) if m else None


def _walk(obj, found: dict):
    """递归找所有带 seriesId/series_id 且有标题的 dict。"""
    if isinstance(obj, dict):
        sid = obj.get("seriesId") or obj.get("series_id") or obj.get("id")
        if sid and _pick(obj, KEY_TITLE) and str(sid).isdigit() and len(str(sid)) > 10:
            found.setdefault(str(sid), obj)
        for v in obj.values():
            _walk(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _walk(v, found)


class HongguoSource(BaseSource):
    name = "hongguo"

    def parse_router_data(self, html: str, board: str, page: int) -> list[DramaItem]:
        m = RE_ROUTER.search(html)
        if not m:
            return []
        raw = m.group(1)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # 有时 JSON 后面还跟别的脚本，逐步截短找到合法结尾
            for cut in range(len(raw), max(len(raw) - 5000, 0), -1):
                if raw[cut - 1] == "}":
                    try:
                        data = json.loads(raw[:cut]); break
                    except json.JSONDecodeError:
                        continue
            else:
                log.warning("_ROUTER_DATA JSON 解析失败")
                return []
        found: dict = {}
        _walk(data, found)
        if not found:
            log.warning("_ROUTER_DATA 里没找到剧集对象，顶层键: %s", list(data)[:20] if isinstance(data, dict) else type(data))
            return []
        sample = next(iter(found.values()))
        log.info("剧集对象字段: %s", list(sample)[:40])
        out = []
        for i, (sid, d) in enumerate(found.items(), start=1):
            title = str(_pick(d, KEY_TITLE, "")).strip()
            tags = _pick(d, KEY_TAGS, [])
            if isinstance(tags, str):
                tags = [t for t in re.split(r"[,，/、\s]+", tags) if t]
            tags = [str(t.get("name", t) if isinstance(t, dict) else t) for t in tags][:8]
            score = _pick(d, KEY_SCORE)
            fav, like = _to_num(_pick(d, KEY_FAV)), _to_num(_pick(d, KEY_LIKE))
            raw_tags = [f"红果{board}"] + tags
            if score not in (None, "", 0, "0"):
                raw_tags.append(f"评分{score}")
            if fav is not None:
                raw_tags.append(f"收藏:{int(fav)}")
            if (e := _pick(d, KEY_EPS)):
                raw_tags.append(f"{e}集")
            out.append(DramaItem(
                platform=f"{self.name}:{board}", platform_id=sid, title=title,
                url=f"{BASE}/detail?series_id={sid}",
                synopsis=str(_pick(d, KEY_DESC, "")).strip(),
                cover=str(_pick(d, KEY_COVER, "") or ""),
                raw_tags=raw_tags,
                rank=(page - 1) * 20 + i,
                heat=_to_num(_pick(d, KEY_HEAT)),
                likes=int(like) if like is not None else None,
            ))
        return out

    def parse_page(self, html: str, board: str, page: int) -> list[DramaItem]:
        items = self.parse_router_data(html, board, page)
        if items:
            return items
        return self.parse_html(html, board, page)

    def parse_html(self, html: str, board: str, page: int) -> list[DramaItem]:
        soup = BeautifulSoup(html, "lxml")
        out, seen = [], set()
        for h2 in soup.find_all(["h2", "h3", "h4"]):
            a = h2.find("a", href=RE_SID) or h2.find_parent("a", href=RE_SID)
            if not a:
                continue
            sid = RE_SID.search(a["href"]).group(1)
            if sid in seen:
                continue
            title = h2.get_text(strip=True)
            if not title:
                continue
            seen.add(sid)
            box = _container_for(h2)
            text = box.get_text(" ", strip=True)
            lines = [l.strip() for l in box.get_text("\n", strip=True).split("\n") if l.strip()]

            heat = _num(*RE_HEAT.search(text).groups()) if RE_HEAT.search(text) else None
            fav = _num(*RE_FAV.search(text).groups()) if RE_FAV.search(text) else None
            like = _num(*RE_LIKE.search(text).groups()) if RE_LIKE.search(text) else None
            score = RE_SCORE.search(text).group(1) if RE_SCORE.search(text) else None
            is_new = "新剧" in text

            # 简介：容器里最长的一段（>=40字）
            synopsis = max((l for l in lines if len(l) >= 40), key=len, default="")
            # 标签：优先 class 含 tag 的元素；否则取指标行之后、简介之前的短行
            tag_els = box.select('[class*="tag"], [class*="label"], [class*="category"]')
            tags = [t.get_text(strip=True) for t in tag_els
                    if not t.find(True) and 1 < len(t.get_text(strip=True)) <= 8 and RE_CJK.search(t.get_text())]
            if not tags:
                for l in lines:
                    if l == title or l == synopsis or any(w in l for w in METRIC_WORDS) or not RE_CJK.search(l):
                        continue
                    if 2 <= len(l) <= 14:
                        tags.append(re.sub(r"\d+$", "", l))
                        break
            img = box.find("img", alt=lambda s: s and "封面" in s) or box.find("img")
            cover = img.get("src", "") if img else ""

            raw_tags = [f"红果{board}"] + [t for t in tags if t]
            if score:
                raw_tags.append(f"评分{score}")
            if fav is not None:
                raw_tags.append(f"收藏:{int(fav)}")
            if is_new:
                raw_tags.append("新剧")
            if (e := RE_EPS.search(text)):
                raw_tags.append(f"{e.group(1)}集")

            out.append(DramaItem(
                platform=f"{self.name}:{board}",
                platform_id=sid,
                title=title,
                url=f"{BASE}/detail?series_id={sid}",
                synopsis=synopsis,
                cover=cover,
                raw_tags=raw_tags,
                rank=(page - 1) * 20 + len(out) + 1,
                heat=heat,
                likes=int(like) if like is not None else None,
            ))
        return out

    def fetch(self):
        for board, path in BOARDS.items():
            total = 0
            for page in range(1, PAGES + 1):
                url = BASE + path + (f"?page={page}" if page > 1 else "")
                try:
                    html = self.fetcher.get(url, snapshot_tag=self.name)
                except Exception as e:
                    log.warning("%s 第%d页失败: %s", board, page, e)
                    break
                items = self.parse_page(html, board, page)
                if not items:
                    break
                total += len(items)
                yield from items
            log.info("红果%s: %d 条", board, total)
