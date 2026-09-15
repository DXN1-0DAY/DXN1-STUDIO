"""Tests for the Electron bridge (dxn1_studio.bridge) — no Tk needed."""

import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dxn1_studio import bridge as br  # noqa: E402


class BridgeBase(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.ws = tempfile.mkdtemp(prefix="dxn1-bridge-")
        self.b = br.Bridge(self.workspace() if False else self.ws)

    def workspace(self):  # pragma: no cover — clarity helper
        return self.ws

    def tearDown(self):
        import shutil
        shutil.rmtree(self.ws, ignore_errors=True)

    def req(self, cmd, args=None, rid=1):
        return self.b.handle(json.dumps({"id": rid, "cmd": cmd,
                                         "args": args or {}}))


class TestBridgeBasics(BridgeBase):
    def test_hello_reports_version_and_workspace(self):
        r = self.req("hello")
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["workspace"], self.ws)
        self.assertTrue(r["result"]["version"])

    def test_unknown_command_is_graceful(self):
        r = self.req("definitely_not_a_cmd")
        self.assertFalse(r["ok"])
        self.assertIn("unknown command", r["error"])

    def test_bad_json_never_crashes(self):
        r = self.b.handle("{not json")
        self.assertFalse(r["ok"])
        self.assertIn("bad json", r["error"])

    def test_path_escape_is_refused(self):
        r = self.req("read_file", {"path": "../../etc/passwd"})
        self.assertFalse(r["ok"])
        self.assertIn("escapes", r["error"])


class TestBridgeFiles(BridgeBase):
    def test_write_then_read_roundtrip(self):
        w = self.req("write_file", {"path": "src/main.py",
                                    "content": "print('hi')\n"})
        self.assertTrue(w["ok"], w)
        self.assertEqual(w["result"]["size"], 12)
        rd = self.req("read_file", {"path": "src/main.py"})
        self.assertTrue(rd["ok"])
        self.assertEqual(rd["result"]["content"], "print('hi')\n")

    def test_write_creates_parent_dirs(self):
        r = self.req("write_file", {"path": "a/b/c/deep.txt",
                                    "content": "x"})
        self.assertTrue(r["ok"])

    def test_overwrite_is_atomic_no_tmp_left(self):
        self.req("write_file", {"path": "f.txt", "content": "one"})
        self.req("write_file", {"path": "f.txt", "content": "two"})
        rd = self.req("read_file", {"path": "f.txt"})
        self.assertEqual(rd["result"]["content"], "two")
        self.assertFalse(os.path.exists(os.path.join(self.ws,
                                                     "f.txt.dxn1-tmp")))

    def test_tree_lists_files_not_hidden_or_junk(self):
        os.makedirs(os.path.join(self.ws, "pkg"))
        open(os.path.join(self.ws, "pkg", "mod.py"), "w").write("x")
        open(os.path.join(self.ws, ".secret"), "w").write("x")
        os.makedirs(os.path.join(self.ws, "__pycache__"), exist_ok=True)
        open(os.path.join(self.ws, "__pycache__", "m.pyc"), "w").write("x")
        r = self.req("tree")
        paths = [e["path"] for e in r["result"]["entries"]]
        self.assertIn("pkg/mod.py", paths)
        self.assertNotIn(".secret", paths)
        self.assertFalse(any("__pycache__" in p for p in paths))

    def test_tree_truncates_at_limit(self):
        for i in range(12):
            open(os.path.join(self.ws, f"f{i}.txt"), "w").write("x")
        r = self.req("tree", {"limit": 5})
        self.assertTrue(r["result"]["truncated"])
        self.assertEqual(len(r["result"]["entries"]), 5)

    def test_rename_and_delete(self):
        self.req("write_file", {"path": "old.txt", "content": "x"})
        self.assertTrue(self.req("rename_path",
                                 {"from": "old.txt",
                                  "to": "new.txt"})["ok"])
        self.assertFalse(os.path.exists(os.path.join(self.ws, "old.txt")))
        self.assertTrue(self.req("delete_path",
                                 {"path": "new.txt"})["ok"])
        st = self.req("stat", {"path": "new.txt"})
        self.assertFalse(st["result"]["exists"])

    def test_delete_refuses_workspace_root(self):
        r = self.req("delete_path", {"path": "."})
        self.assertFalse(r["ok"])
        self.assertIn("refusing", r["error"])

    def test_delete_refuses_nonempty_dir(self):
        self.req("write_file", {"path": "d/x.txt", "content": "x"})
        r = self.req("delete_path", {"path": "d"})
        self.assertFalse(r["ok"])

    def test_rename_to_existing_fails(self):
        self.req("write_file", {"path": "a.txt", "content": "a"})
        self.req("write_file", {"path": "b.txt", "content": "b"})
        r = self.req("rename_path", {"from": "a.txt", "to": "b.txt"})
        self.assertFalse(r["ok"])
        self.assertIn("exists", r["error"])

    def test_make_dir(self):
        self.assertTrue(self.req("make_dir", {"path": "x/y"})["ok"])
        self.assertTrue(os.path.isdir(os.path.join(self.ws, "x/y")))

    def test_read_missing_file_errors_cleanly(self):
        r = self.req("read_file", {"path": "ghost.txt"})
        self.assertFalse(r["ok"])
        self.assertIn("not found", r["error"])

    def test_stat_roundtrip(self):
        self.req("write_file", {"path": "s.txt", "content": "12345"})
        st = self.req("stat", {"path": "s.txt"})
        self.assertTrue(st["result"]["exists"])
        self.assertEqual(st["result"]["size"], 5)
        self.assertFalse(st["result"]["is_dir"])

    def test_workspace_set_validates(self):
        r = self.req("workspace_set", {"workspace": "/definitely/missing"})
        self.assertFalse(r["ok"])
        r = self.req("workspace_set", {"workspace": self.ws})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["workspace"], self.ws)

    def test_open_external_refuses_non_http(self):
        r = self.req("open_external", {"url": "file:///etc/passwd"})
        self.assertFalse(r["ok"])


class TestBridgeServeLoop(BridgeBase):
    def test_serve_forever_replies_line_per_request(self):
        import io
        inp = io.StringIO(json.dumps({"id": 1, "cmd": "hello"}) + "\n" +
                          json.dumps({"id": 2, "cmd": "stat",
                                      "args": {"path": "nope"}}) + "\n")
        out = io.StringIO()
        b = br.Bridge(self.ws, stdin=inp, stdout=out)
        b.serve_forever()
        lines = [json.loads(x) for x in
                 out.getvalue().strip().splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0]["ok"])
        self.assertEqual(lines[0]["result"]["workspace"], self.ws)
        self.assertTrue(lines[1]["ok"])          # stat answers, not errors
        self.assertFalse(lines[1]["result"]["exists"])

    def test_serve_stops_on_closed_stdin(self):
        import io
        b = br.Bridge(self.ws, stdin=io.StringIO(""),
                      stdout=io.StringIO())
        b.serve_forever()          # returns, does not hang
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
