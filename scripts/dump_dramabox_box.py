"""打印 DramaBox 页面里第一个卡片容器的完整文本，看简介到底在哪。
python scripts/dump_dramabox_box.py data/snapshots/dramabox/xxx.html
"""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bs4 import BeautifulSoup
from crawler.sources.dramabox import RE_EPS

html = Path(sys.argv[1]).read_text(encoding="utf-8")
soup = BeautifulSoup(html, "lxml")
count = 0
for node in soup.find_all(string=RE_EPS):
    box = node.parent
    for _ in range(4):
        if box is None: break
        if box.find("img") and len(box.get_text(" ", strip=True)) > 60:
            break
        box = box.parent
    if box is None:
        continue
    print(f"==== 卡片 {count+1} ====")
    print(repr(box.get_text("\n", strip=True))[:1000])
    print()
    count += 1
    if count >= 3:
        break
