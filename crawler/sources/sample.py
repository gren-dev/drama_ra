"""样例数据源：没有网络/选择器还没校准时，用它把整条流水线跑通。
每次运行给热度加一点随机波动，方便看趋势图。
"""
import json
import random
from pathlib import Path
from crawler.base import BaseSource, DramaItem

DATA = Path(__file__).resolve().parents[2] / "data" / "sample_dramas.json"


class SampleSource(BaseSource):
    name = "sample"

    def fetch(self):
        rows = json.loads(DATA.read_text(encoding="utf-8"))
        for i, r in enumerate(rows, start=1):
            yield DramaItem(
                platform=self.name,
                platform_id=r["id"],
                title=r["title"],
                synopsis=r["synopsis"],
                producer=r.get("producer", ""),
                raw_tags=r.get("tags", []),
                rank=i,
                heat=r["heat"] * random.uniform(0.9, 1.15),
                likes=int(r["heat"] / 50),
                comments_cnt=len(r.get("comments", [])),
                comments=[{"text": c, "likes": random.randint(0, 500)} for c in r.get("comments", [])],
            )
