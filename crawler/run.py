"""采集入口：python -m crawler.run [source ...]
不带参数则跑 SOURCES 里启用的全部。
"""
import sys
import logging
from db.session import init_db, session_scope
from crawler.base import ingest
from crawler.sources.sample import SampleSource
from crawler.sources.dataeye import DataEyeSource
from crawler.sources.fanqie import FanqieSource
from crawler.sources.duanjubaike import DuanjubaikeSource
from crawler.sources.hongguo import HongguoSource
from crawler.sources.goodshort import GoodShortSource
from crawler.sources.reelshort import ReelShortSource
from crawler.sources.dramabox import DramaBoxSource
from crawler.sources.flickreels import FlickReelsSource
from crawler.sources.netshort import NetShortSource

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("crawler.run")

SOURCES = {
    "sample": SampleSource,
    "dataeye": DataEyeSource,
    "fanqie": FanqieSource,
    "duanjubaike": DuanjubaikeSource,
    "hongguo": HongguoSource,
    "goodshort": GoodShortSource,
    "reelshort": ReelShortSource,
    "dramabox": DramaBoxSource,
    "flickreels": FlickReelsSource,
    "netshort": NetShortSource,
}
ENABLED = ["goodshort"]  # 目前只做 GoodShort；其他源代码都在，想加回来把名字加进这个列表即可   # 真实源。想用样例数据跑通流程：python -m crawler.run sample


def crawl(names=None):
    init_db()
    names = names or ENABLED
    for n in names:
        src = SOURCES[n]()
        try:
            items = list(src.fetch())
        except Exception as e:
            log.exception("source %s failed: %s", n, e)
            continue
        with session_scope() as s:
            stats = ingest(s, items)
        log.info("%s: %d items -> %s", n, len(items), stats)


if __name__ == "__main__":
    crawl(sys.argv[1:] or None)
