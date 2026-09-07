"""评论情感：批量送给 LLM，一次 30 条，输出 pos/neg/neu。
python -m analysis.sentiment
"""
import json
import logging
from db.session import init_db, session_scope
from db.models import Comment
from analysis.llm import LLM

log = logging.getLogger("analysis.sentiment")
SYSTEM = """对下面每条短剧观众评论做情感判断（sentiment）。
逐行对应，输出 JSON: {"labels": ["pos"|"neg"|"neu", ...]}，数量必须和评论行数一致。
"催更""看了三遍"算 pos；"老套但爱看"算 pos；"能不能换个套路"算 neg。不要输出别的内容。"""

BATCH = 30


def run():
    init_db()
    llm = LLM()
    with session_scope() as s:
        rows = s.query(Comment).filter(Comment.sentiment.is_(None)).all()
        for i in range(0, len(rows), BATCH):
            batch = rows[i:i + BATCH]
            out = llm.chat_json(SYSTEM, "\n".join(c.text.replace("\n", " ") for c in batch), max_tokens=2000)
            labels = (out or {}).get("labels") or []
            if len(labels) != len(batch):
                log.warning("label count mismatch %d vs %d", len(labels), len(batch))
                continue
            for c, l in zip(batch, labels):
                c.sentiment = l if l in ("pos", "neg", "neu") else "neu"
            s.commit()
        log.info("sentiment done: %d comments", len(rows))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
