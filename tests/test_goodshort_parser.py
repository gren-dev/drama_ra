"""GoodShort 解析器：用真实页面快照做基准。网页结构一变，这里先红。

快照来自 data/snapshots/goodshort*/（2026-09-07）。更新快照时把断言里的数字一起更新。
运行：python -m pytest tests -q
"""
import unittest

from crawler.sources.goodshort import GoodShortSource
from tests.conftest import read_fixture

src = GoodShortSource.__new__(GoodShortSource)     # 不走 __init__，不需要网络和数据库


class TestListPage(unittest.TestCase):
    def test_all_page_has_ranked_items(self):
        items = src.parse_list(read_fixture("goodshort", "list_all_p1.html"), "All")
        self.assertGreaterEqual(len(items), 20)
        first = items[0]
        self.assertEqual(first.title, "Blood and Bones of the Disowned Daughter")
        self.assertEqual(first.rank, 1)
        self.assertEqual(first.market, "global")
        self.assertTrue(first.url.startswith("https://www.goodshort.com/drama/"))
        self.assertRegex(first.platform_id, r"^\d{6,}$")
        self.assertIn("GoodShort:All", first.raw_tags)
        self.assertIn("Family", first.raw_tags)
        self.assertEqual(len({i.platform_id for i in items}), len(items), "同一页不应有重复剧")
        self.assertTrue(all(i.title for i in items))
        self.assertTrue(all(i.heat and i.heat > 0 for i in items), "All 榜单每条都应有位置热度")

    def test_category_page2_no_rank(self):
        items = src.parse_list(read_fixture("goodshort", "list_scifi_p2.html"), "Sci-Fi")
        self.assertGreaterEqual(len(items), 8)
        self.assertIn("GoodShort:Sci-Fi", items[0].raw_tags)
        self.assertIsNone(items[0].rank)
        self.assertIsNone(items[0].heat)

    def test_garbage_html_gives_empty(self):
        self.assertEqual(src.parse_list("<html><body>nothing</body></html>", "All"), [])


class TestDetailPage(unittest.TestCase):
    def test_full_detail(self):
        d = src.parse_detail(read_fixture("goodshort", "detail_canary.html"))
        self.assertEqual(d["genre"], "Romance", "分类必须来自面包屑，不是导航菜单的第一项")
        self.assertEqual(d["views"], 3_300_000)
        self.assertEqual(d["followers"], 383_900)
        self.assertEqual(d["episodes"], 55)
        self.assertEqual(d["cast"], ["Clara Carlo", "David Lovio"])
        self.assertTrue(d["synopsis"].startswith("Valentina"))
        self.assertIn("/videobook/", d["cover"])
        self.assertIn("Mafia", d["tags"])
        self.assertGreaterEqual(len(d["tags"]), 8)

    def test_small_drama_units(self):
        d = src.parse_detail(read_fixture("goodshort", "detail_small.html"))
        self.assertEqual(d["views"], 292)             # 没有 K/M 单位
        self.assertEqual(d["followers"], 1600)        # 1.6K
        self.assertEqual(d["genre"], "Romance")     # 旧代码这里会错成 Fantasy（导航菜单第一项）
        self.assertEqual(d["cast"], [])

    def test_garbage_html_gives_defaults(self):
        d = src.parse_detail("<html></html>")
        self.assertEqual(d["genre"], "")
        self.assertIsNone(d["views"])
        self.assertEqual(d["tags"], [])


if __name__ == "__main__":
    unittest.main()
