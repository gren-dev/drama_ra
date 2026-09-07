"""通用离线调试：对任意源落盘的 HTML 跑一遍它自己的 parse 方法，不用重新联网请求。
python scripts/parse_snapshot2.py goodshort data/snapshots/goodshort/20260907/xxxx.html
python scripts/parse_snapshot2.py reelshort data/snapshots/reelshort/20260907/xxxx.html
python scripts/parse_snapshot2.py dramabox data/snapshots/dramabox/20260907/xxxx.html
python scripts/parse_snapshot2.py flickreels data/snapshots/flickreels/20260907/xxxx.html
"""
import sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.INFO, format="%(message)s")

name, path = sys.argv[1], sys.argv[2]
html = Path(path).read_text(encoding="utf-8")

if name == "goodshort":
    from crawler.sources.goodshort import GoodShortSource
    src = GoodShortSource()
    if "/drama/" in path and "_detail" not in path and False:
        pass
    if "_detail" in path or Path(path).parent.parent.name == "goodshort_detail":
        print(src.parse_detail(html))
    else:
        items = src.parse_list(html, "调试")
        print(f"解析出 {len(items)} 条\n")
        for it in items[:8]:
            print(f"  {it.title} | tags={it.raw_tags}")
elif name == "reelshort":
    from crawler.sources.reelshort import ReelShortSource
    items = ReelShortSource().parse_home(html)
    print(f"解析出 {len(items)} 条\n")
    for it in items[:10]:
        print(f"  {it.title} | rank={it.rank} heat={it.heat} tags={it.raw_tags} | {it.synopsis[:60]!r}")
elif name == "dramabox":
    from crawler.sources.dramabox import DramaBoxSource
    items = DramaBoxSource().parse(html, "/")
    print(f"解析出 {len(items)} 条\n")
    for it in items[:10]:
        print(f"  {it.title} | tags={it.raw_tags} | {it.synopsis[:60]!r}")
elif name == "flickreels":
    from crawler.sources.flickreels import FlickReelsSource
    items = FlickReelsSource().parse_page(html, "调试", 1)
    print(f"解析出 {len(items)} 条\n")
    for it in items[:10]:
        print(f"  {it.title} | heat={it.heat} tags={it.raw_tags}")
elif name == "netshort":
    from crawler.sources.netshort import NetShortSource
    items = NetShortSource().parse(html)
    print(f"解析出 {len(items)} 条\n")
    for it in items[:10]:
        print(f"  {it.title} | tags={it.raw_tags} url={it.url}")
else:
    print("unknown source name")
