"""对落盘的 GoodShort 页面离线跑解析，看简介/标签为什么是空的。
python scripts/parse_goodshort.py data/snapshots/goodshort/20260907/xxxx.html
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bs4 import BeautifulSoup
from crawler.sources.goodshort import GoodShortSource, RE_ID, _container

html = Path(sys.argv[1]).read_text(encoding="utf-8")
items = GoodShortSource().parse_page(html, "调试", 1)
print(f"解析出 {len(items)} 条，前 3 条：")
for it in items[:3]:
    print(f"  {it.title} | synopsis={it.synopsis!r} | tags={it.raw_tags}")

print("\n---- 第一个卡片容器的完整文本 ----")
soup = BeautifulSoup(html, "lxml")
h2 = soup.find(["h2", "h3"], string=None)
for h2 in soup.find_all(["h2", "h3"]):
    a = h2.find("a", href=RE_ID) or h2.find_parent("a", href=RE_ID)
    if a:
        box = _container(h2)
        print(box.get_text("\n", strip=True)[:800])
        break
