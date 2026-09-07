"""对落盘的红果页面离线跑解析，看能解析出什么。
python scripts/parse_snapshot.py data/snapshots/hongguo/20260907/xxxx.html
"""
import sys, re, json, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.INFO, format="%(message)s")
from crawler.sources.hongguo import HongguoSource, RE_ROUTER

html = Path(sys.argv[1]).read_text(encoding="utf-8")
items = HongguoSource().parse_page(html, "调试", 1)
print(f"\n解析出 {len(items)} 条")
for it in items[:5]:
    print(f"  #{it.rank} {it.title} | 热度 {it.heat} | 点赞 {it.likes} | {it.raw_tags} | {it.synopsis[:30]}")
if not items:
    m = RE_ROUTER.search(html)
    print("\n_ROUTER_DATA 存在:", bool(m))
    if m:
        raw = m.group(1)
        print("前 1500 字符：\n", raw[:1500])
    idx = html.find("series_id")
    print("\n第一个 series_id 附近的 HTML：\n", html[max(0, idx - 800): idx + 800])
