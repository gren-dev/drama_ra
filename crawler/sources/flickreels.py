"""FlickReels（FARSUN，出海平台）—— Nuxt 服务端直出。
分类页 /classify/<slug>/<id>/<page>，每页 12 条，链接 /playlist/<slug>/<id>/episode-1。
没有播放量/简介；价值在平台自己打的细粒度标签（Werewolf/Alpha/Mafia/Secret Baby/AI...）。
曝光分：出现在几个精选分类的第 1 页 + 页内位置。
"""
import re
import logging
from bs4 import BeautifulSoup
from crawler.base import BaseSource, DramaItem

log = logging.getLogger("crawler.flickreels")
BASE = "https://www.flickreels.net"
# 精选分类：题材含义强的，slug -> id（从站点导航抄的；新增分类去 /classify 页面看链接）
CATEGORIES = {
    "All": ("", ""), "AI": ("ai", "3170"), "Werewolf": ("werewolf", "1595"), "Alpha": ("alpha", "1790"),
    "Mafia": ("mafia", "1611"), "CEO/Billionaire": ("ceo-billionaire", "1579"), "Avenge": ("avenge", "1556"),
    "SecretIdentity": ("secretidentity", "1627"), "Rebirth": ("rebirth", "1830"), "TimeTravel": ("timetravel", "1798"),
    "Secret Baby": ("secret-baby", "2349"), "Cute baby": ("cute-baby", "1603"), "Flash Marriage": ("flash-marriage", "1742"),
    "Contract Love": ("contract-love", "1726"), "Vampire": ("vampire", "1587"), "Dragons": ("dragons", "4598"),
    "System": ("system", "2872"), "Xianxia": ("xianxia", "1950"), "Post-Apocalyptic": ("post-apocalyptic", "4486"),
    "Superpowers": ("superpowers", "1958"), "Suspense": ("suspense", "1524"), "Family": ("family", "1508"),
    "Ancient Asian": ("ancient-asian", "1468"), "Palace Drama": ("palace-drama", "2371"), "Teens": ("teens", "1719"),
    "Heroine": ("heroine", "1683"), "Female Awakening": ("female-awakening", "2247"), "Midlife": ("midlife", "1659"),
}
PAGES = 2
RE_PL = re.compile(r"/playlist/([a-z0-9\-]+)/(\d+)/", re.I)


class FlickReelsSource(BaseSource):
    name = "flickreels"

    def parse_page(self, html: str, category: str, page: int) -> list[DramaItem]:
        soup = BeautifulSoup(html, "lxml")
        out, seen = [], set()
        for a in soup.find_all("a", href=RE_PL):
            slug, pid = RE_PL.search(a["href"]).groups()
            if pid in seen:
                continue
            title = a.get("title") or a.get_text(strip=True)
            if not title or title.startswith("/"):
                img = a.find("img")
                title = (img.get("alt", "") if img else "").strip()
            if not title:
                continue
            seen.add(pid)
            img = a.find("img") or (a.parent.find("img") if a.parent else None)
            pos = len(out) + 1
            out.append(DramaItem(
                platform=self.name, platform_id=pid, title=title.strip(), market="global",
                url=f"{BASE}/playlist/{slug}/{pid}/episode-1",
                cover=(img.get("src") or img.get("data-src") or "") if img else "",
                raw_tags=[f"FlickReels:{category}"],
                rank=(page - 1) * 12 + pos if category == "All" else None,
                heat=max(0, 130 - (page - 1) * 12 * 4 - pos * 4),   # 第1页第1位 126，第2页末位 ~30
            ))
        return out

    def fetch(self):
        merged: dict[str, DramaItem] = {}
        for cat, (slug, cid) in CATEGORIES.items():
            n = 0
            for page in range(1, PAGES + 1):
                url = f"{BASE}/classify" if cat == "All" and page == 1 else (
                      f"{BASE}/classify/{slug}/{cid}/{page}" if cat != "All" else f"{BASE}/classify/all/0/{page}")
                try:
                    html = self.fetcher.get(url, snapshot_tag=self.name)
                except Exception as e:
                    log.warning("FlickReels %s p%d 失败: %s", cat, page, str(e)[:80]); break
                items = self.parse_page(html, cat, page)
                if not items:
                    break
                for it in items:
                    n += 1
                    if it.platform_id in merged:
                        m = merged[it.platform_id]
                        m.raw_tags = list(dict.fromkeys(m.raw_tags + it.raw_tags))
                        m.heat += it.heat * 0.5          # 多个分类里出现 → 曝光加分
                        if m.rank is None and it.rank:
                            m.rank = it.rank
                    else:
                        merged[it.platform_id] = it
            log.info("FlickReels %s: %d 条", cat, n)
        log.info("FlickReels 合并后 %d 部", len(merged))
        yield from merged.values()
