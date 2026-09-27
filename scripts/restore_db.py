"""从 data/db_backup/ 恢复数据库（清空后写入）。python scripts/restore_db.py [目录]"""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import MetaData, delete, insert  # noqa: E402

from db.session import engine, init_db  # noqa: E402


def main(src: Path):
    init_db()
    md = MetaData()
    md.reflect(bind=engine)
    with engine.begin() as conn:
        for t in reversed(md.sorted_tables):
            conn.execute(delete(t))
        for t in md.sorted_tables:
            f = src / f"{t.name}.jsonl.gz"
            if not f.exists():
                continue
            rows = [json.loads(l) for l in gzip.open(f, "rt", encoding="utf-8") if l.strip()]
            for i in range(0, len(rows), 500):
                conn.execute(insert(t), rows[i:i + 500])
            print(f"{t.name}: {len(rows)} 行")
    print("恢复完成")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data" / "db_backup")
