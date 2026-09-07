"""一键跑完整流水线：采集 → 打标 → 情感 → 聚类 → 周报
python pipeline.py            # 全部
python pipeline.py --no-report
"""
import sys
import logging
from crawler.run import crawl
from analysis import tagger, sentiment, cluster, report

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def run(with_report=True):
    crawl()
    tagger.tag_all()
    sentiment.run()
    cluster.run()
    if with_report:
        report.run()


if __name__ == "__main__":
    run(with_report="--no-report" not in sys.argv)
