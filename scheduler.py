"""常驻调度：每 N 小时采集+打标，每周一早上聚类+周报。
python scheduler.py
"""
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
import config
from crawler.run import crawl
from analysis import tagger, sentiment, cluster, report

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def hourly():
    crawl()
    tagger.tag_all()
    sentiment.run()


def weekly():
    cluster.run()
    report.run()


if __name__ == "__main__":
    sch = BlockingScheduler(timezone="Asia/Shanghai")
    sch.add_job(hourly, "interval", hours=config.CRAWL_INTERVAL_HOURS, next_run_time=None)
    sch.add_job(weekly, "cron", day_of_week="mon", hour=8)
    logging.info("scheduler started, crawl every %dh", config.CRAWL_INTERVAL_HOURS)
    sch.start()
