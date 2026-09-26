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


def crawl(names=None) -> int:
    """采集所有启用的源。返回入库条数；有源失败或一条都没抓到时，命令行退出码非 0，让 Actions 变红。"""
    init_db()
    names = names or ENABLED
    total, failed = 0, []
    for n in names:
        src = SOURCES[n]()
        try:
            items = list(src.fetch())
        except Exception as e:
            log.exception("source %s failed: %s", n, e)
            failed.append(n)
            continue
        if not items:
            log.error("source %s returned 0 items（网页结构可能变了，需要检查解析器）", n)
            failed.append(n)
            continue
        with session_scope() as s:
            stats = ingest(s, items)
        total += len(items)
        log.info("%s: %d items -> %s", n, len(items), stats)
    if failed:
        log.error("采集失败的源：%s", "、".join(failed))
    return total if not failed else -total


if __name__ == "__main__":
    n = crawl(sys.argv[1:] or None)
    if n <= 0:
        sys.exit(2)          # 抓空或有源失败 → 非 0 退出，GitHub Actions 会标红并发通知
