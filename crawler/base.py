"""采集层公共部分：
- Fetcher: 带重试/随机UA/限速/原始快照的 HTTP 客户端
- DramaItem: 各数据源统一输出的数据结构
- ingest(): 把 DramaItem 写入库，同名剧跨平台合并
"""
import re
import json
import time
import random
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config
from db.models import Drama, PlatformListing, MetricSnapshot, Comment

log = logging.getLogger("crawler")


# ---------- 统一数据结构 ----------

@dataclass
class DramaItem:
    platform: str
    platform_id: str
    title: str
    url: str = ""
    synopsis: str = ""
    cover: str = ""
    producer: str = ""
    raw_tags: list = field(default_factory=list)
    rank: Optional[int] = None
    heat: Optional[float] = None
    likes: Optional[int] = None
    comments_cnt: Optional[int] = None
    comments: list = field(default_factory=list)   # [{"text":..., "likes":...}]


def normalize_title(t: str) -> str:
    """去重键：去书名号/空白/标点/“第X季”等后缀，统一小写。"""
    t = t.strip()
    t = re.sub(r"[《》【】\[\]（）()\s]", "", t)
    t = re.sub(r"(第[一二三四五六七八九十\d]+[季部集]|完结篇|全集|短剧)$", "", t)
    t = re.sub(r"[:：\-—_·,，。!！?？]", "", t)
    return t.lower()


# ---------- HTTP ----------

class Fetcher:
    def __init__(self, min_delay=1.5, max_delay=4.0, timeout=20):
        self.min_delay, self.max_delay = min_delay, max_delay
        self.client = httpx.Client(
            timeout=timeout,
            proxy=config.HTTP_PROXY,
            follow_redirects=True,
            headers={"Accept-Language": "zh-CN,zh;q=0.9"},
        )
        self._last = 0.0

    def _throttle(self):
        wait = random.uniform(self.min_delay, self.max_delay) - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=2, min=2, max=20),
           retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)))
    def get(self, url: str, *, params=None, headers=None, snapshot_tag: str = None) -> str:
        self._throttle()
        h = {"User-Agent": random.choice(config.USER_AGENTS)}
        if headers:
            h.update(headers)
        r = self.client.get(url, params=params, headers=h)
        if r.status_code in (403, 429, 503):
            log.warning("blocked %s %s", r.status_code, url)
            raise httpx.HTTPStatusError("blocked", request=r.request, response=r)
        r.raise_for_status()
        if snapshot_tag:
            self.snapshot(snapshot_tag, url, r.text)
        return r.text

    def get_json(self, url: str, **kw):
        return json.loads(self.get(url, **kw))

    @staticmethod
    def snapshot(tag: str, url: str, body: str):
        """原始页面落盘：反爬改版后可以离线重解析，不用再请求。"""
        d = config.SNAPSHOT_DIR / tag / datetime.utcnow().strftime("%Y%m%d")
        d.mkdir(parents=True, exist_ok=True)
        name = hashlib.md5(url.encode()).hexdigest()[:10] + "_" + datetime.utcnow().strftime("%H%M%S")
        (d / f"{name}.html").write_text(body, encoding="utf-8")


def render_page(url: str, wait_selector: str = None, timeout_ms=30000) -> str:
    """需要 JS 渲染时用 Playwright。首次使用需 `playwright install chromium`。"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": config.HTTP_PROXY} if config.HTTP_PROXY else None)
        ctx = browser.new_context(user_agent=random.choice(config.USER_AGENTS), locale="zh-CN")
        page = ctx.new_page()
        page.goto(url, timeout=timeout_ms)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=timeout_ms)
        html = page.content()
        browser.close()
    return html


# ---------- 数据源接口 ----------

class BaseSource:
    name = "base"

    def __init__(self):
        self.fetcher = Fetcher()

    def fetch(self) -> Iterable[DramaItem]:
        raise NotImplementedError


# ---------- 入库 ----------

def ingest(session, items: Iterable[DramaItem]) -> dict:
    stats = {"new": 0, "merged": 0, "snapshots": 0, "comments": 0}
    now = datetime.utcnow()
    for it in items:
        if not it.title:
            continue
        key = normalize_title(it.title)
        drama = session.query(Drama).filter_by(norm_title=key).one_or_none()
        if drama is None:
            drama = Drama(norm_title=key, title=it.title.strip(), synopsis=it.synopsis,
                          cover=it.cover, producer=it.producer, first_seen=now)
            session.add(drama)
            session.flush()
            stats["new"] += 1
        else:
            stats["merged"] += 1
            # 补全缺失字段，不覆盖已有的
            if not drama.synopsis and it.synopsis:
                drama.synopsis = it.synopsis
            if not drama.cover and it.cover:
                drama.cover = it.cover
            if not drama.producer and it.producer:
                drama.producer = it.producer
        drama.last_seen = now

        listing = session.query(PlatformListing).filter_by(
            platform=it.platform, platform_id=it.platform_id).one_or_none()
        if listing is None:
            session.add(PlatformListing(drama_id=drama.id, platform=it.platform,
                                        platform_id=it.platform_id, url=it.url, raw_tags=it.raw_tags))
        elif it.raw_tags:
            listing.raw_tags = it.raw_tags

        if any(v is not None for v in (it.rank, it.heat, it.likes, it.comments_cnt)):
            session.add(MetricSnapshot(drama_id=drama.id, platform=it.platform, ts=now,
                                       rank=it.rank, heat=it.heat, likes=it.likes,
                                       comments_cnt=it.comments_cnt))
            stats["snapshots"] += 1

        for c in it.comments:
            text = (c.get("text") or "").strip()
            if not text:
                continue
            exists = session.query(Comment.id).filter_by(drama_id=drama.id, text=text).first()
            if not exists:
                session.add(Comment(drama_id=drama.id, platform=it.platform,
                                    text=text, likes=c.get("likes", 0)))
                stats["comments"] += 1
    return stats
