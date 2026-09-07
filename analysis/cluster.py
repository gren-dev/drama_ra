"""第二档：聚类发现词表之外的新题材。
默认 TF-IDF(字符 n-gram) + KMeans，零依赖可跑；有 embedding 接口时把 embed() 换掉即可。
每周跑一次，把本周簇和上周簇按关键词重叠对比，标记 is_new。
python -m analysis.cluster
"""
import logging
from datetime import datetime, timedelta

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

from db.session import init_db, session_scope
from db.models import Drama, Cluster
from analysis.llm import LLM

log = logging.getLogger("analysis.cluster")

NAME_SYSTEM = """你是短剧题材分析师。下面是同一个 cluster（簇）里的几部剧的剧名和简介，它们被算法判断为题材相近。
给这个簇起一个 6 字以内的题材名（label），并用一句话描述这类剧的共同套路（description）。
只输出 JSON: {"label": "...", "description": "..."}"""


def week_str(dt: datetime = None) -> str:
    dt = dt or datetime.utcnow()
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def embed(texts: list[str]) -> np.ndarray:
    """默认字符级 TF-IDF。要换成真 embedding：
    调 OpenAI 兼容 /embeddings 或 sentence-transformers，返回 (n, dim) 矩阵即可。"""
    vec = TfidfVectorizer(analyzer="char", ngram_range=(2, 3), min_df=1, max_features=20000)
    return vec.fit_transform(texts).toarray(), vec


def top_terms(vec, centroid, k=6):
    names = np.array(vec.get_feature_names_out())
    return [str(t) for t in names[np.argsort(centroid)[::-1][:k]]]


def run(k: int = None, name_with_llm=True):
    init_db()
    wk = week_str()
    with session_scope() as s:
        dramas = s.query(Drama).filter(Drama.last_seen >= datetime.utcnow() - timedelta(days=14)).all()
        if len(dramas) < 4:
            log.warning("剧太少，跳过聚类")
            return
        texts = [f"{d.title} {d.synopsis} {' '.join(d.tags or [])}" for d in dramas]
        X, vec = embed(texts)
        k = k or max(3, min(12, int(np.sqrt(len(dramas) / 2)) + 2))
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)

        prev = s.query(Cluster).filter(Cluster.week != wk).order_by(Cluster.id.desc()).limit(50).all()
        prev_kw = [set(c.keywords or []) for c in prev]
        s.query(Cluster).filter_by(week=wk).delete()

        llm = LLM() if name_with_llm else None
        for ci in range(k):
            members = [d for d, l in zip(dramas, km.labels_) if l == ci]
            if not members:
                continue
            kws = top_terms(vec, km.cluster_centers_[ci])
            is_new = int(not any(len(set(kws) & p) >= 2 for p in prev_kw))
            label, desc = f"簇{ci}", ""
            if llm:
                sample = "\n".join(f"- {d.title}：{(d.synopsis or '')[:80]}" for d in members[:6])
                out = llm.chat_json(NAME_SYSTEM, sample, max_tokens=1000)
                if out:
                    label, desc = out.get("label", label)[:100], out.get("description", "")
            c = Cluster(week=wk, label=label, description=desc, size=len(members), keywords=kws, is_new=is_new)
            s.add(c)
            s.flush()
            for d in members:
                d.cluster_id = c.id
            log.info("cluster %s (%d) new=%d kw=%s", label, len(members), is_new, kws)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
