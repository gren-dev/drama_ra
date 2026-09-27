"""把数据库（Supabase 或本地 SQLite）逐表导出到 data/db_backup/<表>.jsonl.gz，供工作台的自动备份打包。
python scripts/backup_db.py            导出
python scripts/restore_db.py <目录>    恢复（会先清空再写入，慎用）
"""
import gzip
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import MetaData, select, text  # noqa: E402

from db.session import engine  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "db_backup"


def _json(v):
    return v.isoformat() if isinstance(v, (date, datetime)) else v


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    md = MetaData()
    md.reflect(bind=engine)
    total = 0
    with engine.connect() as conn:
        for t in md.sorted_tables:
            n = 0
            with gzip.open(OUT / f"{t.name}.jsonl.gz", "wt", encoding="utf-8") as f:
                for row in conn.execute(select(t)).mappings():
                    f.write(json.dumps({k: _json(v) for k, v in row.items()}, ensure_ascii=False) + "\n")
                    n += 1
            total += n
            print(f"{t.name}: {n} 行")
    (OUT / "manifest.json").write_text(json.dumps({"exported": datetime.now().isoformat(timespec="seconds"),
                                                   "url": str(engine.url).split("@")[-1][:40], "rows": total}, ensure_ascii=False))
    print(f"导出完成，共 {total} 行 → {OUT.name}/")


if __name__ == "__main__":
    main()
