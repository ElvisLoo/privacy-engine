# -*- coding: utf-8 -*-
"""设置持久化：回归测试。

用标准库 unittest，不引入额外依赖（这个项目只有 PyQt5 + keyboard 两个依赖，
为了测试再装 pytest 不值当）。
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import settings_store


class TestSanitize(unittest.TestCase):
    def test_defaults_on_garbage(self):
        for bad in (None, "string", 42, [1, 2], {}):
            out = settings_store.sanitize(bad)
            self.assertEqual(out["intensity"], settings_store.DEFAULTS["intensity"])
            self.assertEqual(out["mode"], "none")

    def test_intensity_clamped(self):
        self.assertEqual(settings_store.sanitize({"intensity": 999})["intensity"], 100)
        self.assertEqual(settings_store.sanitize({"intensity": -5})["intensity"], 0)

    def test_intensity_from_string(self):
        self.assertEqual(settings_store.sanitize({"intensity": "70"})["intensity"], 70)

    def test_bool_is_not_accepted_as_number(self):
        # True 是 int 的子类，若不过滤会静默变成 1
        out = settings_store.sanitize({"intensity": True})
        self.assertEqual(out["intensity"], settings_store.DEFAULTS["intensity"])

    def test_unknown_mode_rejected(self):
        self.assertEqual(settings_store.sanitize({"mode": "hack"})["mode"], "none")
        self.assertEqual(settings_store.sanitize({"mode": "circle"})["mode"], "circle")

    def test_unknown_keys_dropped(self):
        out = settings_store.sanitize({"intensity": 30, "evil": "x", "exec": "rm -rf"})
        self.assertNotIn("evil", out)
        self.assertNotIn("exec", out)

    def test_window_position(self):
        out = settings_store.sanitize({"window_x": -1920, "window_y": 300})
        self.assertEqual(out["window_x"], -1920)
        self.assertEqual(out["window_y"], 300)

    def test_absurd_window_position_rejected(self):
        out = settings_store.sanitize({"window_x": 10 ** 9})
        self.assertIsNone(out["window_x"])


class TestRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig = settings_store.config_path
        settings_store.config_path = lambda: os.path.join(self.tmpdir, "cfg.json")

    def tearDown(self):
        settings_store.config_path = self._orig
        for name in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, name))
        os.rmdir(self.tmpdir)

    def test_save_then_load(self):
        ok, err = settings_store.save({"intensity": 73, "mode": "three_zone"})
        self.assertTrue(ok, err)
        loaded = settings_store.load()
        self.assertEqual(loaded["intensity"], 73)
        self.assertEqual(loaded["mode"], "three_zone")

    def test_load_missing_returns_defaults(self):
        loaded = settings_store.load()
        self.assertEqual(loaded, settings_store.DEFAULTS)

    def test_load_corrupt_returns_defaults(self):
        with open(settings_store.config_path(), "w", encoding="utf-8") as f:
            f.write("{ this is not json ")
        loaded = settings_store.load()
        self.assertEqual(loaded["intensity"], settings_store.DEFAULTS["intensity"])

    def test_save_is_atomic(self):
        """写临时文件再 replace，中途不会留下坏 JSON"""
        settings_store.save({"intensity": 10})
        settings_store.save({"intensity": 20})
        self.assertFalse(
            os.path.exists(settings_store.config_path() + ".tmp"),
            "临时文件应已被替换掉",
        )
        with open(settings_store.config_path(), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["intensity"], 20)

    def test_save_clamps_before_writing(self):
        settings_store.save({"intensity": 500})
        with open(settings_store.config_path(), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["intensity"], 100)

    def test_save_failure_returns_false(self):
        # 把配置路径指向一个不可能创建的位置（父级是个文件）
        blocker = os.path.join(self.tmpdir, "blocker")
        with open(blocker, "w") as f:
            f.write("x")
        settings_store.config_path = lambda: os.path.join(blocker, "sub", "cfg.json")
        ok, err = settings_store.save({"intensity": 50})
        self.assertFalse(ok)
        self.assertTrue(err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
