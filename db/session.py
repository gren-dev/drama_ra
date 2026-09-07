from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import config
from db.models import Base

_url = config.DATABASE_URL
# Supabase 给的是 postgresql://，SQLAlchemy 用 psycopg2 驱动；连接池设小，Streamlit Cloud/Actions 都够用
_kw = {"future": True}
if _url.startswith("postgres"):
    _url = _url.replace("postgres://", "postgresql://", 1)
    _kw.update(pool_pre_ping=True, pool_size=3, max_overflow=2)
engine = create_engine(_url, **_kw)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db():
    Base.metadata.create_all(engine)
    _migrate()


def _migrate():
    """create_all 不会给已有表加列；这里补上新增的列（SQLite/Postgres 通用）。"""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in existing:
                    ctype = col.type.compile(engine.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{col.name}" {ctype}'))


@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
