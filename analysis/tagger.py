"""第一档：结构化打标。用小模型跑全量，词表来自 taxonomy.yaml，保证标签口径一致。
python -m analysis.tagger [--all]   默认只打未打标或简介更新过的剧
"""
import sys
import json
import logging
from datetime import datetime

import yaml
import config
from db.session import init_db, session_scope
from db.models import Drama, Comment
from analysis.llm import LLM

log = logging.getLogger("analysis.tagger")

TAX = yaml.safe_load(config.TAXONOMY_PATH.read_text(encoding="utf-8"))

SYSTEM = f"""你是短剧行业的题材分析师。根据剧名、简介、平台标签和观众评论，给这部剧打标签。
只输出一个 JSON 对象，不要任何解释、不要 markdown 代码块。字段：
- genre: 主题材，必须从这个列表里选一个：{json.dumps(TAX['genres'], ensure_ascii=False)}
- sub_genre: 子题材，自由填写，10字以内，尽量具体（如"军婚年代"、"荒岛系统流"）
- hook_type: 第一集的钩子类型，从列表选：{json.dumps(TAX['hook_types'], ensure_ascii=False)}
- audience: {json.dumps(TAX['audience'], ensure_ascii=False)} 三选一
- era: {json.dumps(TAX['eras'], ensure_ascii=False)} 选一
- tags: 3-5个爽点/看点标签，短词，如 ["打脸","掉马","团宠"]
- reason: 一句话说明为什么这样判断（30字内）"""


def build_prompt(d: Drama, comments: list[str]) -> str:
    plat_tags = sorted({t for l in d.listings for t in (l.raw_tags or [])})
    parts = [f"剧名：{d.title}", f"简介：{d.synopsis or '（无）'}"]
    if plat_tags:
        parts.append(f"平台标签：{'、'.join(plat_tags)}")
    if comments:
        parts.append("观众评论：\n" + "\n".join(f"- {c}" for c in comments[:8]))
    return "\n".join(parts)


def tag_all(force=False, limit=None):
    init_db()
    llm = LLM()
    log.info("tagger provider=%s model=%s", llm.provider, llm.model)
    with session_scope() as s:
        q = s.query(Drama)
        if not force:
            q = q.filter(Drama.tagged_at.is_(None))
        dramas = q.all()
        if limit:
            dramas = dramas[:limit]
        for i, d in enumerate(dramas, 1):
            comments = [c.text for c in s.query(Comment).filter_by(drama_id=d.id)
                        .order_by(Comment.likes.desc()).limit(8)]
            out = llm.chat_json(SYSTEM, build_prompt(d, comments), max_tokens=2000)
            if not out:
                continue
            d.genre = out.get("genre") if out.get("genre") in TAX["genres"] else "其他"
            d.sub_genre = (out.get("sub_genre") or "")[:100]
            d.hook_type = out.get("hook_type") if out.get("hook_type") in TAX["hook_types"] else "其他"
            d.audience = out.get("audience") if out.get("audience") in TAX["audience"] else "男女通吃"
            d.era = out.get("era") if out.get("era") in TAX["eras"] else "现代"
            d.tags = [str(t)[:20] for t in (out.get("tags") or [])][:6]
            d.tag_reason = (out.get("reason") or "")[:300]
            d.tagged_at = datetime.utcnow()
            if i % 10 == 0:
                s.commit()
                log.info("tagged %d/%d", i, len(dramas))
        log.info("done: %d dramas", len(dramas))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tag_all(force="--all" in sys.argv)
