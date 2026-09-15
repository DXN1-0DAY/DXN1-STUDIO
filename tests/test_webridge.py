"""Tests for the app-level HTTP bridge (dxn1_studio.webridge).

Headless: boots the studio in smoke mode, starts the bridge on a
random port, and drives it with urllib — including the security
contract (token required, workspace sandbox).
"""

import json
import os
import sys
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from dxn1_studio import webridge as wb  # noqa: E402


def _make_app():
    from dxn1_studio import config as cfgmod
    from dxn1_studio.app import DXN1Studio
    return DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)


class TestWebBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        import tkinter as tk
        try:
            cls.root = tk.Tk()
        except Exception:
            raise unittest.SkipTest("no display available")
        cls.root.withdraw()
        cls.app = _make_app()
        # a private temp workspace — file-op tests must never touch
        # the repo working tree (smoke apps boot with project_dir=None)
        cls.ws = tempfile.mkdtemp(prefix="dxn1-webridge-")
        cls.app.project_dir = cls.ws
        cls.server, cls.url, cls.token = wb.start_bridge(cls.app)
        cls.base = cls.url

    @classmethod
    def tearDownClass(cls):
        import shutil
        try:
            cls.server.shutdown()
        except Exception:
            pass
        try:
            cls.app.root.destroy()
        except Exception:
            pass
        try:
            cls.root.destroy()
        except Exception:
            pass
        shutil.rmtree(getattr(cls, "ws", ""), ignore_errors=True)

    def setUp(self):
        # idempotence: earlier failures must never poison later runs
        import shutil
        for junk in ("wb_dir", "webridge_probe.txt", "webridge_write.txt",
                     "webridge_new.txt"):
            p = os.path.join(self.ws, junk)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    # ---- helpers -----------------------------------------------------
    def get(self, path, token=True, raw=False):
        url = self.base + path
        req = urllib.request.Request(url)
        if token:
            req.add_header("X-DXN1-Token", self.token)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                body = r.read().decode("utf-8")
                return (r.status, body) if raw else \
                    (r.status, json.loads(body))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            return (exc.code, body if raw else json.loads(body))

    def post(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base + path, data=data,
                                     method="POST")
        req.add_header("X-DXN1-Token", self.token)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    # ---- static face ---------------------------------------------------
    def test_index_served_without_token(self):
        status, body = self.get("/", token=False, raw=True)
        self.assertEqual(status, 200)
        self.assertIn("DXN1", body)

    def test_app_css_and_js_served(self):
        for path, marker in (("/app.css", "--accent"),
                             ("/app.js", "X-DXN1-Token")):
            status, body = self.get(path, token=False, raw=True)
            self.assertEqual(status, 200, path)
            self.assertIn(marker, body)

    # ---- security ------------------------------------------------------
    def test_api_requires_token(self):
        status, body = self.get("/api/state", token=False)
        self.assertEqual(status, 401)
        self.assertFalse(body["ok"])

    def test_bad_token_rejected(self):
        url = self.base + "/api/state"
        req = urllib.request.Request(url)
        req.add_header("X-DXN1-Token", "wrong-token")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                code = r.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        self.assertEqual(code, 401)

    def test_token_file_written_and_private(self):
        ws = getattr(self.app, "project_dir", "") or os.getcwd()
        tok_path = os.path.join(ws, ".dxn1", "bridge_token")
        self.assertTrue(os.path.isfile(tok_path))
        with open(tok_path, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read().strip(), self.token)

    # ---- app-level API ---------------------------------------------------
    def test_state_snapshot(self):
        status, body = self.get("/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["app"], "DXN1 STUDIO")
        self.assertTrue(body["version"])
        self.assertIsInstance(body["tabs"], list)
        self.assertIn("accent", body["theme"])

    def test_commands_listed(self):
        status, body = self.get("/api/commands")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(body["commands"]), 100)
        labels = [c["label"] for c in body["commands"]]
        self.assertTrue(any("Run project" in lb for lb in labels))

    def test_bad_command_index_is_400(self):
        status, body = self.post("/api/command", {"index": 99999})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])

    def test_command_dispatches_to_palette(self):
        # "Toggle sidebar" (index-safe: find it by label)
        status, listing = self.get("/api/commands")
        idx = next(c["index"] for c in listing["commands"]
                   if c["label"] == "Toggle sidebar")
        status, body = self.post("/api/command", {"index": idx})
        self.assertEqual(status, 200)
        self.assertEqual(body["ran"], "Toggle sidebar")

    def test_tree_lists_workspace(self):
        status, body = self.get("/api/tree")
        self.assertEqual(status, 200)
        self.assertIsInstance(body["tree"], list)

    def test_file_roundtrip_and_sandbox(self):
        ws = getattr(self.app, "project_dir", "") or os.getcwd()
        probe = os.path.join(ws, "webridge_probe.txt")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("hello bridge")
        try:
            status, body = self.get("/api/file?path=webridge_probe.txt")
            self.assertEqual(status, 200)
            self.assertEqual(body["file"]["content"], "hello bridge")
            # sandbox: escapes are refused
            status, body = self.get(
                "/api/file?path=../../etc/passwd")
            self.assertEqual(status, 400)
        finally:
            try:
                os.remove(probe)
            except OSError:
                pass

    def test_file_write_schedules_reopen(self):
        ws = getattr(self.app, "project_dir", "") or os.getcwd()
        rel = "webridge_write.txt"
        try:
            status, body = self.post(
                "/api/file", {"path": rel, "content": "written by test"})
            self.assertEqual(status, 200)
            self.assertTrue(body["saved"])
            with open(os.path.join(ws, rel), "r", encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "written by test")
        finally:
            try:
                os.remove(os.path.join(ws, rel))
            except OSError:
                pass

    # ---- file ops (Phase-2 parity; reuse of bridge.Bridge engine) ----
    def test_new_file_creates_and_opens(self):
        rel = "webridge_new.txt"
        try:
            status, body = self.post("/api/new_file", {"path": rel})
            self.assertEqual(status, 200)
            self.assertEqual(body["opened"], rel)
            ws = getattr(self.app, "project_dir", "") or os.getcwd()
            self.assertTrue(os.path.isfile(os.path.join(ws, rel)))
        finally:
            try:
                os.remove(os.path.join(
                    getattr(self.app, "project_dir", "") or ".",
                    rel))
            except OSError:
                pass

    def test_new_file_refuses_workspace_escape(self):
        status, body = self.post(
            "/api/new_file", {"path": "../escape.txt"})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])

    def test_mkdir_rename_delete_roundtrip(self):
        status, body = self.post("/api/mkdir", {"path": "wb_dir"})
        self.assertEqual(status, 200)
        status, body = self.post(
            "/api/new_file", {"path": "wb_dir/inner.txt"})
        self.assertEqual(status, 200)
        status, body = self.post("/api/rename", {
            "path": "wb_dir/inner.txt", "to": "wb_dir/moved.txt"})
        self.assertEqual(status, 200)
        ws = getattr(self.app, "project_dir", "") or os.getcwd()
        self.assertTrue(os.path.isfile(
            os.path.join(ws, "wb_dir", "moved.txt")))
        # the engine refuses NON-EMPTY dirs on purpose (tested contract
        # in test_bridge.py) — empty it, then remove the dir
        status, body = self.post("/api/delete", {"path": "wb_dir"})
        self.assertEqual(status, 400)
        status, body = self.post("/api/delete", {"path": "wb_dir/moved.txt"})
        self.assertEqual(status, 200)
        status, body = self.post("/api/delete", {"path": "wb_dir"})
        self.assertEqual(status, 200)
        self.assertFalse(os.path.isdir(os.path.join(ws, "wb_dir")))

    def test_delete_root_refused(self):
        status, body = self.post("/api/delete", {"path": "."})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])

    # ---- settings over the bridge (wave 2) ----------------------------
    def test_config_get(self):
        status, body = self.get("/api/config")
        self.assertEqual(status, 200)
        self.assertIn(body["config"]["theme"], ("dark", "light"))
        self.assertIn("violet", body["config"]["accents"])

    def test_config_set_accent_recolours_snapshot(self):
        cur = self.get("/api/config")[1]["config"]["accent"]
        other = "cyan" if cur != "cyan" else "rose"
        status, body = self.post("/api/config", {"accent": other})
        self.assertEqual(status, 200)
        self.assertEqual(body["applied"]["accent"], other)
        # the live theme object re-colours → snapshot follows
        state = self.get("/api/state")[1]
        tokens = state["theme"]
        # cyan/rose dark hexes differ from violet's
        self.assertNotEqual(tokens["accent"], "#8b5cf6")
        # restore
        self.post("/api/config", {"accent": cur})

    def test_config_set_rejects_bad_values(self):
        status, body = self.post("/api/config", {"accent": "nope"})
        self.assertEqual(status, 400)
        status, body = self.post("/api/config", {"theme": "sepia"})
        self.assertEqual(status, 400)
        status, body = self.post("/api/config", {"evil_key": 1})
        self.assertEqual(status, 400)

    def test_config_set_bool_and_int(self):
        status, body = self.post("/api/config", {"word_wrap": True})
        self.assertEqual(status, 200)
        self.assertTrue(body["applied"]["word_wrap"])
        status, body = self.post("/api/config", {"word_wrap": False})
        self.assertEqual(status, 200)
        status, body = self.post("/api/config",
                                 {"editor_font_size": "not-an-int"})
        self.assertEqual(status, 400)

    # ---- git surface (wave 3) -----------------------------------------
    def test_git_status_on_plain_dir(self):
        # a fresh dir with no git init → a human error, not a crash
        # (own temp dir — unittest order is alphabetical, so a sibling
        # test may already have turned self.ws into a repo)
        import tempfile
        old = self.app.project_dir
        plain = tempfile.mkdtemp(prefix="dxn1-nogit-")
        self.app.project_dir = plain
        try:
            status, body = self.get("/api/git")
            self.assertEqual(status, 400)
            self.assertFalse(body["ok"])
        finally:
            self.app.project_dir = old

    def test_git_status_and_commit_in_a_repo(self):
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=self.ws, timeout=10)
        subprocess.run(["git", "config", "user.email", "t@dxn1.dev"],
                       cwd=self.ws, timeout=10)
        subprocess.run(["git", "config", "user.name", "DXN1 Test"],
                       cwd=self.ws, timeout=10)
        status, body = self.get("/api/git")
        self.assertEqual(status, 200)
        self.assertTrue(body["branch"])  # master or main
        self.assertEqual(body["dirty"], 0)
        self.assertEqual(body["files"], [])
        # commit flow
        with open(os.path.join(self.ws, "repo_file.txt"), "w") as fh:
            fh.write("git wave")
        status, body = self.post(
            "/api/git", {"action": "commit", "message": "wave three"})
        self.assertEqual(status, 200)
        self.assertEqual(body["done"], "commit")
        status, body = self.get("/api/git")
        self.assertEqual(status, 200)
        self.assertEqual(body["dirty"], 0)
        self.assertTrue(any("wave three" in c for c in body["commits"]))

    def test_git_action_whitelist(self):
        status, body = self.post("/api/git", {"action": "rebase"})
        self.assertEqual(status, 400)
        self.assertIn("not allowed", body["error"])
        status, body = self.post("/api/git", {"action": "commit",
                                              "message": ""})
        self.assertEqual(status, 400)

    # ---- quick-open file list (wave 4) ---------------------------------
    def test_files_flat_list_skips_internal(self):
        ws = getattr(self.app, "project_dir", "") or os.getcwd()
        os.makedirs(os.path.join(ws, "pkg"), exist_ok=True)
        for rel in ("pkg/mod.py", "top.txt"):
            with open(os.path.join(ws, rel), "w") as fh:
                fh.write("x")
        try:
            status, body = self.get("/api/files")
            self.assertEqual(status, 200)
            files = body["files"]
            self.assertIn("pkg/mod.py", files)
            self.assertIn("top.txt", files)
            # internal + hidden dirs never surface
            self.assertFalse(any(".dxn1" in f for f in files))
            self.assertFalse(any(f.startswith(".") for f in files))
        finally:
            import shutil
            shutil.rmtree(os.path.join(ws, "pkg"), ignore_errors=True)
            try:
                os.remove(os.path.join(ws, "top.txt"))
            except OSError:
                pass

    # ---- agents surface (wave 5) ---------------------------------------
    def test_state_has_agent_block(self):
        status, body = self.get("/api/state")
        self.assertEqual(status, 200)
        self.assertIn("agent", body)
        self.assertIn("transcript", body["agent"])
        self.assertIn("busy", body["agent"])

    def test_agent_send_queues_and_routes(self):
        status, body = self.post("/api/agent",
                                 {"message": "hello agents"})
        self.assertEqual(status, 200)
        self.assertTrue(body["queued"])
        status, body = self.post("/api/agent", {"message": "  "})
        self.assertEqual(status, 400)
        status, body = self.post("/api/agent", {"message": "x" * 9000})
        self.assertEqual(status, 400)

    # ---- diff + terminal input (wave 6) -------------------------------
    def test_diff_in_a_repo(self):
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=self.ws, timeout=10)
        subprocess.run(["git", "config", "user.email", "t@dxn1.dev"],
                       cwd=self.ws, timeout=10)
        subprocess.run(["git", "config", "user.name", "DXN1 Test"],
                       cwd=self.ws, timeout=10)
        # no HEAD yet → git diff HEAD fails cleanly
        status, body = self.get("/api/diff")
        self.assertEqual(status, 400)
        # seed a commit, then modify → the diff shows the change
        with open(os.path.join(self.ws, "seed.txt"), "w") as fh:
            fh.write("one\n")
        subprocess.run(["git", "add", "-A"], cwd=self.ws, timeout=10)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=self.ws,
                       timeout=10)
        with open(os.path.join(self.ws, "seed.txt"), "a") as fh:
            fh.write("two\n")
        status, body = self.get("/api/diff")
        self.assertEqual(status, 200)
        self.assertIn("seed.txt", body["diff"])
        self.assertIn("+two", body["diff"])
        # leave the tree clean for sibling tests (alphabetical order:
        # this runs before the git-status test)
        subprocess.run(["git", "checkout", "-q", "--", "."], cwd=self.ws,
                       timeout=10)

    def test_term_command_validation_and_queue(self):
        status, body = self.post("/api/term", {"command": "  "})
        self.assertEqual(status, 400)
        status, body = self.post("/api/term", {"command": "x" * 3000})
        self.assertEqual(status, 400)
        status, body = self.post("/api/term", {"command": "echo hi"})
        self.assertEqual(status, 200)
        self.assertTrue(body["queued"])


if __name__ == "__main__":
    unittest.main()
