"""第一档：结构化打标，批量请求版——一次 LLM 调用打一批剧，省请求次数。
python -m analysis.tagger [--all] [--batch=12]
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

TAX_CN = yaml.safe_load(config.TAXONOMY_PATH.read_text(encoding="utf-8"))
TAX_GLOBAL = yaml.safe_load(config.TAXONOMY_GLOBAL_PATH.read_text(encoding="utf-8"))
TAX = TAX_CN   # 兼容旧引用

DEFAULT_BATCH = 12


def _strip(label: str) -> str:
    """'狼人/Alpha (Werewolf, Alpha)' -> '狼人/Alpha'：库里只存中文标签"""
    return label.split(" (")[0].strip()


def taxonomy_for(market: str) -> dict:
    return TAX_GLOBAL if market == "global" else TAX_CN


def system_prompt(market: str, batch: bool = True) -> str:
    tax = taxonomy_for(market)
    intro = ("你是出海短剧（ReelShort/DramaBox/GoodShort 这类平台）的题材分析师，读者是国内做出海内容的编剧和制片。"
             "输入的剧名和简介是英文或其他语言，你输出的标签一律用中文（列表里括号内的英文只是帮助你对应海外说法）。"
             if market == "global" else
             "你是短剧行业的题材分析师。")
    fields = f"""- genre: 主题材，必须从这个列表里选一个（只输出括号前的中文部分）：{json.dumps(tax['genres'], ensure_ascii=False)}
- sub_genre: 子题材，中文自由填写，10字以内，尽量具体（如"军婚年代"、"Alpha 拒绝 Luna"）
- hook_type: 第一集的钩子类型，从列表选（只输出括号前的中文）：{json.dumps(tax['hook_types'], ensure_ascii=False)}
- audience: {json.dumps(tax['audience'], ensure_ascii=False)} 三选一
- era: {json.dumps(tax['eras'], ensure_ascii=False)} 选一
- tags: 3-5个爽点/看点标签，中文短词，如 ["打脸","掉马","命定伴侣"]
- reason: 一句中文说明为什么这样判断（30字内）"""
    no_think = "直接输出最终 JSON，不要输出任何分析过程、推理文字、中间思考或解释——第一个字符就必须是 {。"
    if not batch:
        return f"{intro}根据剧名、简介、平台标签和观众评论，给这部剧打标签。\n{no_think}\n只输出一个 JSON 对象，不要 markdown 代码块。字段：\n{fields}"
    return f"""{intro}下面会给你一批剧（每部有编号），根据剧名、简介、平台标签和观众评论，给每一部打标签。
{no_think}
只输出一个 JSON 对象：{{"items": [ {{...第1部的标签...}}, {{...第2部的标签...}}, ... ]}}
items 数组长度必须和输入的剧数量完全一致，顺序一一对应，不要合并、不要跳过、不要多输出。不要 markdown 代码块。
每部剧的标签字段：
{fields}"""


def build_prompt(d: Drama, comments: list[str]) -> str:
    plat_tags = sorted({t for l in d.listings for t in (l.raw_tags or [])})
    parts = [f"剧名：{d.title}", f"简介：{d.synopsis or '（无）'}"]
    if plat_tags:
        parts.append(f"平台标签：{'、'.join(plat_tags[:15])}")
    if comments:
        parts.append("观众评论：\n" + "\n".join(f"- {c}" for c in comments[:8]))
    return "\n".join(parts)


def build_batch_prompt(entries: list[tuple[Drama, list[str]]]) -> str:
    blocks = []
    for i, (d, comments) in enumerate(entries, 1):
        blocks.append(f"### 第{i}部\n" + build_prompt(d, comments))
    return "\n\n".join(blocks)


_DEFAULT_TAG_RESULT = {"genre": "其他", "sub_genre": "", "hook_type": "其他",
                       "audience": "男女通吃", "era": "现代", "tags": [], "reason": ""}


def _apply_tag(session, drama_id: int, out: dict, tax: dict):
    genres = {_strip(g) for g in tax["genres"]}
    hooks = {_strip(h) for h in tax["hook_types"]}
    d = session.get(Drama, drama_id)
    if d is None:
        return
    g = _strip(str(out.get("genre") or ""))
    d.genre = g if g in genres else "其他"
    d.sub_genre = (out.get("sub_genre") or "")[:100]
    h = _strip(str(out.get("hook_type") or ""))
    d.hook_type = h if h in hooks else "其他"
    d.audience = out.get("audience") if out.get("audience") in tax["audience"] else "男女通吃"
    d.era = out.get("era") if out.get("era") in tax["eras"] else "现代"
    d.tags = [str(t)[:20] for t in (out.get("tags") or [])][:6]
    d.tag_reason = (out.get("reason") or "")[:300]
    d.tagged_at = datetime.utcnow()


def tag_all(force=False, limit=None, batch_size=DEFAULT_BATCH):
    init_db()
    llm = LLM()
    log.info("tagger provider=%s model=%s batch_size=%d", llm.provider, llm.model, batch_size)

    with session_scope() as s:
        q = s.query(Drama.id, Drama.market)
        if not force:
            q = q.filter(Drama.tagged_at.is_(None))
        rows = q.order_by(Drama.id).all()
    if limit:
        rows = rows[:limit]
    log.info("待打标 %d 部", len(rows))

    by_market: dict[str, list[int]] = {}
    for did, market in rows:
        by_market.setdefault(market or "cn", []).append(did)

    total_done = 0
    total_calls = 0
    for market, ids in by_market.items():
        tax = taxonomy_for(market)
        sys_prompt = system_prompt(market, batch=True)
        for i in range(0, len(ids), batch_size):
            chunk = ids[i:i + batch_size]
            with session_scope() as s:
                dramas = s.query(Drama).filter(Drama.id.in_(chunk)).order_by(Drama.id).all()
                entries = []
                for d in dramas:
                    comments = [c.text for c in s.query(Comment).filter_by(drama_id=d.id)
                               .order_by(Comment.likes.desc()).limit(5)]
                    entries.append((d, comments))
                prompt = build_batch_prompt(entries)
                chunk_ids = [d.id for d in dramas]

            out = llm.chat_json(sys_prompt, prompt, max_tokens=min(600 * len(chunk_ids) + 300, 8000))
            total_calls += 1
            items = (out or {}).get("items") if isinstance(out, dict) else None

            if items is not None and len(items) == len(chunk_ids):
                with session_scope() as s:
                    for did, item in zip(chunk_ids, items):
                        _apply_tag(s, did, item or _DEFAULT_TAG_RESULT, tax)
                total_done += len(chunk_ids)
            else:
                # 批量返回对不上，逐个兜底重试，不整批丢弃
                log.warning("批量结果数量不符（期望%d，实际%s），逐个重试本批", len(chunk_ids),
                           len(items) if items is not None else "解析失败")
                single_sys = system_prompt(market, batch=False)
                for did in chunk_ids:
                    with session_scope() as s:
                        d = s.get(Drama, did)
                        comments = [c.text for c in s.query(Comment).filter_by(drama_id=d.id)
                                   .order_by(Comment.likes.desc()).limit(5)]
                        p = build_prompt(d, comments)
                    single_out = llm.chat_json(single_sys, p, max_tokens=1500)
                    total_calls += 1
                    if not single_out:
                        continue
                    with session_scope() as s:
                        _apply_tag(s, did, single_out, tax)
                    total_done += 1

            if total_done and total_done % (batch_size * 5) < batch_size:
                log.info("tagged %d/%d（已用 %d 次调用）", total_done, len(rows), total_calls)

    log.info("done: %d dramas tagged, %d LLM calls total", total_done, total_calls)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bs = DEFAULT_BATCH
    for a in sys.argv[1:]:
        if a.startswith("--batch="):
            bs = int(a.split("=")[1])
    tag_all(force="--all" in sys.argv, batch_size=bs)
