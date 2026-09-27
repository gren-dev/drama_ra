"""打标容错：一批 LLM 调用崩了，其余批次照常，结束时有失败清单。用临时 SQLite，不联网。"""
import os
import unittest
from unittest import mock


class TestTaggerTolerance(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_URL"] = f"sqlite:///{self.tmp.name}/t.db"
        os.environ["LLM_PROVIDER"] = "mock"
        import importlib, config, db.session
        importlib.reload(config); importlib.reload(db.session)
        from db.models import Drama
        from db.session import init_db, session_scope
        init_db()
        with session_scope() as s:
            for i in range(6):
                s.add(Drama(title=f"剧{i}", market="cn"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_one_bad_batch_does_not_stop_the_rest(self):
        from analysis import tagger
        from db.models import Drama
        from db.session import session_scope
        calls = {"n": 0}

        class FakeLLM:
            provider, model = "fake", "fake"
            def chat_json(self, system, user, **kw):
                calls["n"] += 1
                if calls["n"] == 2:                      # 第二批崩
                    raise ConnectionError("网络断了")
                n = user.count("### 第")
                return {"items": [{"genre": "都市逆袭", "sub_genre": "", "hook_type": "", "audience": "", "era": "", "tags": []}] * n}
        with mock.patch.object(tagger, "LLM", FakeLLM):
            done, failed = tagger.tag_all(batch_size=2)
        self.assertEqual(done, 4)
        self.assertEqual(len(failed), 2)
        self.assertIn("ConnectionError", failed[0][1])
        with session_scope() as s:
            self.assertEqual(s.query(Drama).filter(Drama.tagged_at.isnot(None)).count(), 4)


if __name__ == "__main__":
    unittest.main()
