"""评论情感：批量送给 LLM，一次 30 条，输出 pos/neg/neu。
python -m analysis.sentiment
"""
import json
import logging
from db.session import init_db, session_scope
from db.models import Comment
from analysis.llm import LLM

log = logging.getLogger("analysis.sentiment")
SYSTEM = """对下面每条短剧观众评论做情感判断（sentiment）并给负面评论标一个吐槽点。
逐行对应，输出 JSON: {"labels": ["pos"|"neg"|"neu", ...], "tags": ["", ...]}
- labels 和 tags 的数量都必须和评论行数一致
- tags：负面评论填一个吐槽点，从这些里选或自拟（4字内）：套路老、演技差、节奏慢、剧情崩、结局烂、制作差、人设崩、逻辑硬伤；非负面填空字符串
"催更""看了三遍"算 pos；"老套但爱看"算 pos；"能不能换个套路"算 neg（套路老）。不要输出别的内容。"""

BATCH = 30


def run():
    init_db()
    llm = LLM()
    with session_scope() as s:
        ids = [i for (i,) in s.query(Comment.id).filter(Comment.sentiment.is_(None)).order_by(Comment.id)]
    total = 0
    for i in range(0, len(ids), BATCH):
        batch_ids = ids[i:i + BATCH]
        with session_scope() as s:
            texts = [c.text.replace("\n", " ") for c in s.query(Comment).filter(Comment.id.in_(batch_ids)).order_by(Comment.id)]
        out = llm.chat_json(SYSTEM, "\n".join(texts), max_tokens=2000)
        labels = (out or {}).get("labels") or []
        tags = (out or {}).get("tags") or [""] * len(labels)
        if len(labels) != len(batch_ids):
            log.warning("label count mismatch %d vs %d", len(labels), len(batch_ids))
            continue
        if len(tags) != len(batch_ids):
            tags = [""] * len(batch_ids)
        with session_scope() as s:
            rows = s.query(Comment).filter(Comment.id.in_(batch_ids)).order_by(Comment.id).all()
            for c, l, t in zip(rows, labels, tags):
                c.sentiment = l if l in ("pos", "neg", "neu") else "neu"
                c.complaint_tag = (str(t) or "")[:50] if c.sentiment == "neg" else None
        total += len(batch_ids)
    log.info("sentiment done: %d comments", total)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
