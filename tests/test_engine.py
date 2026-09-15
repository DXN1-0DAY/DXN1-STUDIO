"""Engine tests — the brain must never break the face.

Stdlib unittest only (no pytest dependency in DS3's fresh start):
    python3 -m unittest discover -s tests -v
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from engine.server import Engine, EngineError  # noqa: E402


class EngineBase(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="dxn3-engine-")
        self.eng = Engine(self.ws)

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def req(self, cmd, args=None, rid=1):
        return self.eng.handle(json.dumps(
            {"id": rid, "cmd": cmd, "args": args or {}}))


class TestHelloAndErrors(EngineBase):
    def test_hello_names_the_studio(self):
        r = self.req("hello")
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["app"], "DXN1 STUDIO 3")
        self.assertEqual(r["result"]["workspace"], self.ws)

    def test_unknown_cmd_is_honest(self):
        r = self.req("teleport")
        self.assertFalse(r["ok"])
        self.assertIn("unknown", r["error"])

    def test_bad_json_survives(self):
        r = self.eng.handle("{not json")
        self.assertFalse(r["ok"])
        self.assertIn("bad JSON", r["error"])
        # and the engine still answers after it
        self.assertTrue(self.req("hello")["ok"])


class TestFiles(EngineBase):
    def test_write_read_roundtrip(self):
        r = self.req("write", {"path": "src/app.py",
                               "content": "print('hi')\n"})
        self.assertTrue(r["ok"])
        r = self.req("read", {"path": "src/app.py"})
        self.assertEqual(r["result"]["content"], "print('hi')\n")

    def test_write_is_atomic_and_overwrites(self):
        self.req("write", {"path": "a.txt", "content": "one"})
        self.req("write", {"path": "a.txt", "content": "two"})
        self.assertEqual(self.req("read", {"path": "a.txt"})
                         ["result"]["content"], "two")
        leftovers = [f for f in os.listdir(self.ws)
                     if f.startswith(".dxn1-tmp-")]
        self.assertEqual(leftovers, [])

    def test_path_escape_refused(self):
        r = self.req("read", {"path": "../outside.txt"})
        self.assertFalse(r["ok"])
        self.assertIn("escapes", r["error"])

    def test_stat_missing_is_not_an_error(self):
        r = self.req("stat", {"path": "nope.txt"})
        self.assertTrue(r["ok"])
        self.assertFalse(r["result"]["exists"])

    def test_rename_and_delete_guards(self):
        self.req("write", {"path": "a.txt", "content": "x"})
        self.req("write", {"path": "b.txt", "content": "y"})
        r = self.req("rename", {"from": "a.txt", "to": "b.txt"})
        self.assertFalse(r["ok"])                     # no silent overwrite
        r = self.req("rename", {"from": "a.txt", "to": "z/a.txt"})
        self.assertTrue(r["ok"])
        r = self.req("delete", {"path": "."})
        self.assertIn("refusing", r["error"])         # never the root
        r = self.req("delete", {"path": "z/a.txt"})
        self.assertTrue(r["ok"])

    def test_tree_skips_noise(self):
        os.makedirs(os.path.join(self.ws, "node_modules"))
        self.req("write", {"path": "node_modules/x.js", "content": "j"})
        self.req("write", {"path": "keep.py", "content": "k"})
        r = self.req("tree", {"depth": 2})
        names = [t["name"] for t in r["result"]["tree"]]
        self.assertNotIn("node_modules", names)
        self.assertIn("keep.py", names)


class TestScenes(EngineBase):
    def test_scene_roundtrip(self):
        scene = {"name": "t", "entities": [{"name": "player", "x": 0}]}
        r = self.req("scene_save", {"path": "scenes/t.dxn1.json",
                                    "scene": scene})
        self.assertTrue(r["ok"])
        r = self.req("scene_get", {"path": "scenes/t.dxn1.json"})
        self.assertEqual(r["result"]["scene"]["entities"][0]["name"],
                         "player")

    def test_scene_validation(self):
        self.req("write", {"path": "scenes/bad.dxn1.json",
                           "content": json.dumps({"name": "no entities"})})
        r = self.req("scene_get", {"path": "scenes/bad.dxn1.json"})
        self.assertFalse(r["ok"])
        self.assertIn("entities", r["error"])


class TestGit(EngineBase):
    """The source control bridge — real git, honest errors."""

    def setUp(self):
        super().setUp()
        self.has_git = shutil.which("git") is not None

    def _init_repo(self):
        def run(*argv):
            subprocess.run(["git", "-C", self.ws, *argv], check=True,
                           capture_output=True, text=True, timeout=20)
        run("init", "-q")
        run("config", "user.email", "studio@dxn1.test")
        run("config", "user.name", "DS3 Test")
        run("config", "commit.gpgsign", "false")

    def test_non_repo_is_honest(self):
        r = self.req("git_status")
        self.assertFalse(r["ok"])
        self.assertIn("not a git repository", r["error"])

    def test_status_branch_and_changes(self):
        if not self.has_git:
            self.skipTest("git not installed")
        self._init_repo()
        self.req("write", {"path": "a.txt", "content": "one"})
        r = self.req("git_commit", {"message": "first"})
        self.assertTrue(r["ok"])
        self.assertTrue(r["result"]["committed"])
        r = self.req("git_status")
        self.assertTrue(r["ok"])
        self.assertTrue(r["result"]["clean"])
        self.assertIn(r["result"]["branch"], ("master", "main"))
        self.req("write", {"path": "a.txt", "content": "two"})
        self.req("write", {"path": "new.txt", "content": "n"})
        r = self.req("git_status")
        files = {f["path"]: f["x"] for f in r["result"]["files"]}
        self.assertEqual(files.get("a.txt"), "M")
        self.assertEqual(files.get("new.txt"), "A")

    def test_commit_requires_message(self):
        if not self.has_git:
            self.skipTest("git not installed")
        self._init_repo()
        r = self.req("git_commit", {"message": "  "})
        self.assertFalse(r["ok"])
        self.assertIn("message required", r["error"])

    def test_nothing_to_commit_is_honest(self):
        if not self.has_git:
            self.skipTest("git not installed")
        self._init_repo()
        self.req("write", {"path": "a.txt", "content": "one"})
        self.req("git_commit", {"message": "first"})
        r = self.req("git_commit", {"message": "empty"})
        self.assertFalse(r["ok"])
        self.assertIn("nothing to commit", r["error"])

    def test_log_lists_commits(self):
        if not self.has_git:
            self.skipTest("git not installed")
        self._init_repo()
        self.req("write", {"path": "a.txt", "content": "one"})
        self.req("git_commit", {"message": "first words"})
        r = self.req("git_log")
        self.assertTrue(r["ok"])
        commits = r["result"]["commits"]
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]["subject"], "first words")
        self.assertTrue(commits[0]["hash"])

    def test_diff_modified_untracked_clean(self):
        if not self.has_git:
            self.skipTest("git not installed")
        self._init_repo()
        # untracked -> all-added diff
        self.req("write", {"path": "new.txt", "content": "l1\nl2\n"})
        r = self.req("git_diff", {"path": "new.txt"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["status"], "added")
        signs = [l["t"] for l in r["result"]["hunks"][0]["lines"]]
        self.assertEqual(signs, ["+", "+"])
        # committed then modified -> real git hunks
        self.req("git_commit", {"message": "base"})
        r = self.req("git_diff", {"path": "new.txt"})
        self.assertEqual(r["result"]["status"], "clean")
        self.assertEqual(r["result"]["hunks"], [])
        self.req("write", {"path": "new.txt", "content": "l1\nCHANGED\n"})
        r = self.req("git_diff", {"path": "new.txt"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["status"], "modified")
        flat = [l for h in r["result"]["hunks"] for l in h["lines"]]
        self.assertIn("-", [l["t"] for l in flat])
        self.assertIn("+", [l["t"] for l in flat])
        changed = [l["s"] for l in flat if l["t"] == "+"]
        self.assertIn("CHANGED", changed)
        # clean file -> zero hunks
        r = self.req("git_diff", {"path": "missing.txt"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["status"], "clean")
        # path required
        r = self.req("git_diff", {})
        self.assertFalse(r["ok"])
        self.assertIn("path required", r["error"])

    def test_branches_and_checkout(self):
        if not self.has_git:
            self.skipTest("git not installed")
        self._init_repo()
        self.req("write", {"path": "a.txt", "content": "one"})
        self.req("git_commit", {"message": "base"})
        r = self.req("git_branches")
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["current"],
                         r["result"]["branches"][0])
        base = r["result"]["current"]
        # create + switch
        r = self.req("git_checkout", {"name": "feature/x", "create": True})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"]["branch"], "feature/x")
        r = self.req("git_branches")
        self.assertEqual(r["result"]["current"], "feature/x")
        self.assertIn(base, r["result"]["branches"])
        # duplicate create refused
        r = self.req("git_checkout", {"name": "feature/x", "create": True})
        self.assertFalse(r["ok"])
        self.assertIn("already exists", r["error"])
        # switch back
        r = self.req("git_checkout", {"name": base})
        self.assertTrue(r["ok"])
        # unknown branch refused
        r = self.req("git_checkout", {"name": "ghost"})
        self.assertFalse(r["ok"])
        self.assertIn("no such branch", r["error"])
        # hostile names refused
        r = self.req("git_checkout", {"name": "-evil"})
        self.assertFalse(r["ok"])
        self.assertIn("invalid branch name", r["error"])
        r = self.req("git_checkout", {"name": "", "create": True})
        self.assertFalse(r["ok"])


class TestServeLoop(unittest.TestCase):
    def test_line_per_request(self):
        ws = tempfile.mkdtemp(prefix="dxn3-serve-")
        try:
            eng = Engine(ws)
            inbox = io.StringIO(
                '{"id":1,"cmd":"hello","args":{}}\n'
                'garbage\n'
                '{"id":2,"cmd":"write","args":{"path":"x.txt",'
                '"content":"hi"}}\n')
            out = io.StringIO()
            eng.serve_forever(inbox, out)
            lines = [json.loads(l) for l in
                     out.getvalue().strip().splitlines()]
            self.assertEqual(len(lines), 3)
            self.assertTrue(lines[0]["ok"])
            self.assertFalse(lines[1]["ok"])          # garbage answered
            self.assertTrue(lines[2]["ok"])
            self.assertTrue(os.path.isfile(os.path.join(ws, "x.txt")))
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    def test_module_boots_as_process(self):
        ws = tempfile.mkdtemp(prefix="dxn3-proc-")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "engine", ws],
                input='{"id":7,"cmd":"hello","args":{}}\n',
                capture_output=True, text=True, timeout=15,
                cwd=os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__))))
            reply = json.loads(proc.stdout.strip().splitlines()[0])
            self.assertEqual(reply["id"], 7)
            self.assertTrue(reply["ok"])
        finally:
            shutil.rmtree(ws, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
