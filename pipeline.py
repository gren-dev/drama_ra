"""一键跑流水线。当前阶段：只采集，不跑 LLM（打标/情感/聚类/周报都注释掉了）。
python pipeline.py             # 只采集
python pipeline.py --with-llm  # 采集 + 打标 + 情感 + 聚类 + 周报（等数据采集稳定后再打开）
"""
import sys
import logging
from crawler.run import crawl

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def run(with_llm=False):
    crawl()
    if with_llm:
        from analysis import tagger, sentiment, cluster, report
        tagger.tag_all()
        sentiment.run()
        cluster.run()
        report.run()


if __name__ == "__main__":
    run(with_llm="--with-llm" in sys.argv)
