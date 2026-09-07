"""给样例数据回填 N 周历史快照，让趋势图/环比/bump chart 有东西看。
python scripts/seed_history.py [weeks]
每个题材给一条不同的趋势（上升/下滑/平稳），方便验证四象限逻辑。
"""
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.session import init_db, session_scope
from db.models import Drama, MetricSnapshot

TREND = {  # 每周乘数：>1 上升，<1 下滑
    "悬疑惊悚": 1.25, "荒岛求生": 1.20, "系统金手指": 1.12, "都市逆袭": 1.10, "民国年代": 1.06,
    "战神归来": 0.92, "萌宝寻亲": 0.90, "豪门虐恋": 0.88, "甜宠恋爱": 0.95, "追妻火葬场": 0.93,
}


def run(weeks=5):
    init_db()
    now = datetime.utcnow()
    with session_scope() as s:
        dramas = s.query(Drama).all()
        for d in dramas:
            latest = (s.query(MetricSnapshot).filter_by(drama_id=d.id).order_by(MetricSnapshot.ts.desc()).first())
            base = latest.heat if latest and latest.heat else 1e7
            mult = TREND.get(d.genre, 1.0)
            for w in range(1, weeks + 1):
                heat_w = base / (mult ** w)           # 往回推：上升题材过去更低
                for day in (0, 3):                    # 每周两个采样点
                    ts = now - timedelta(weeks=w, days=day)
                    s.add(MetricSnapshot(drama_id=d.id, platform="sample", ts=ts,
                                         heat=heat_w * random.uniform(0.95, 1.05),
                                         rank=None, likes=int(heat_w / 50)))
            d.first_seen = min(d.first_seen or now, now - timedelta(weeks=weeks))
        print(f"seeded {weeks} weeks for {len(dramas)} dramas")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
