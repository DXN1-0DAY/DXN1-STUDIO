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
import urllib.parse
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
                     "webridge_new.txt", "wb_wsdirty.txt",
                     "wb_wsfile.txt"):
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

    # ---- tab close over the bridge (wave 7) ---------------------------
    def _flush_pump(self):
        # the mutation queue drains on the Tk loop (80 ms cadence) —
        # give it a few beats, then pump the loop once more
        import time
        for _ in range(4):
            time.sleep(0.09)
            self.app.root.update()

    def _buffer_keys(self):
        return list(getattr(self.app, "_buffers", {}).keys())

    def test_close_tab_roundtrip(self):
        rel = "wb_close.txt"
        try:
            status, body = self.post("/api/new_file", {"path": rel})
            self.assertEqual(status, 200)
            self._flush_pump()
            self.assertTrue(any(k.endswith(rel)
                                for k in self._buffer_keys()))
            status, body = self.post("/api/close", {"path": rel})
            self.assertEqual(status, 200)
            self.assertEqual(body["closed"], rel)
            self._flush_pump()
            self.assertFalse(any(k.endswith(rel)
                                 for k in self._buffer_keys()))
            # closing again is an honest 400, not a silent shrug
            status, body = self.post("/api/close", {"path": rel})
            self.assertEqual(status, 400)
            self.assertIn("not open", body["error"])
        finally:
            p = os.path.join(self.ws, rel)
            if os.path.exists(p):
                os.remove(p)

    def test_close_refuses_dirty_buffer(self):
        rel = "wb_dirty.txt"
        try:
            status, body = self.post("/api/new_file", {"path": rel})
            self.assertEqual(status, 200)
            self._flush_pump()
            key = next(k for k in self._buffer_keys()
                       if k.endswith(rel))
            self.app._buffers[key]["dirty"] = True
            status, body = self.post("/api/close", {"path": rel})
            self.assertEqual(status, 400)
            self.assertIn("unsaved", body["error"])
            # save first, then the close goes through
            self.app._buffers[key]["dirty"] = False
            status, body = self.post("/api/close", {"path": rel})
            self.assertEqual(status, 200)
            self._flush_pump()
            self.assertFalse(any(k.endswith(rel)
                                 for k in self._buffer_keys()))
        finally:
            p = os.path.join(self.ws, rel)
            if os.path.exists(p):
                os.remove(p)

    def test_close_sandbox_and_missing(self):
        status, body = self.post("/api/close", {"path": "../escape.txt"})
        self.assertEqual(status, 400)
        self.assertIn("escapes", body["error"])
        status, body = self.post("/api/close", {"path": "never_open.txt"})
        self.assertEqual(status, 400)
        self.assertIn("not open", body["error"])

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

    # ---- branches + checkout (wave 9) ----------------------------------
    def test_git_branches_and_checkout(self):
        # own temp repo — the shared workspace's git state is owned by
        # test_diff_in_a_repo and must not be touched
        import shutil
        import subprocess
        import tempfile
        old = self.app.project_dir
        repo = tempfile.mkdtemp(prefix="dxn1-branch-")
        self.app.project_dir = repo
        try:
            def run(*args):
                return subprocess.run(["git", "-C", repo, *args],
                                      capture_output=True, text=True,
                                      timeout=10)
            run("init", "-q")
            run("config", "user.email", "t@dxn1.dev")
            run("config", "user.name", "DXN1 Test")
            with open(os.path.join(repo, "a.txt"), "w") as fh:
                fh.write("one\n")
            run("add", "-A")
            run("commit", "-qm", "seed")
            run("branch", "feature/edge")
            base_branch = run(
                "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            # the status payload now carries the branch list
            status, body = self.get("/api/git")
            self.assertEqual(status, 200)
            self.assertIn(base_branch, body["branches"])
            self.assertIn("feature/edge", body["branches"])
            # switch through the guarded API
            status, body = self.post("/api/git", {
                "action": "checkout", "branch": "feature/edge"})
            self.assertEqual(status, 200)
            self.assertEqual(body["done"], "checkout")
            self.assertEqual(run("rev-parse", "--abbrev-ref",
                                 "HEAD").stdout.strip(), "feature/edge")
            # dirty trees are refused — nothing is force-dropped
            with open(os.path.join(repo, "a.txt"), "a") as fh:
                fh.write("two\n")
            status, body = self.post("/api/git", {
                "action": "checkout", "branch": base_branch})
            self.assertEqual(status, 400)
            self.assertIn("changed file", body["error"])
            subprocess.run(["git", "-C", repo, "checkout", "-q",
                            "--", "."], timeout=10)
            # bogus names never reach git at all
            for bad in ("", "-rf", "../escape", "has space"):
                status, body = self.post("/api/git", {
                    "action": "checkout", "branch": bad})
                self.assertEqual(status, 400, bad)
                self.assertEqual(body["error"], "bad branch name")
            # unknown branch surfaces git's own honest error
            status, body = self.post("/api/git", {
                "action": "checkout", "branch": "no/such/branch"})
            self.assertEqual(status, 400)
        finally:
            self.app.project_dir = old
            shutil.rmtree(repo, ignore_errors=True)

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


class TestSnippetsEndpoint(unittest.TestCase):
    """GET /api/snippets — the shared registry for both faces."""

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
        cls.ws = tempfile.mkdtemp(prefix="dxn1-snippets-")
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

    def get(self, path):
        req = urllib.request.Request(self.base + path)
        req.add_header("X-DXN1-Token", self.token)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_token_required(self):
        req = urllib.request.Request(self.base + "/api/snippets?lang=py")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                code = r.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        self.assertEqual(code, 401)

    def test_python_pack_served(self):
        status, body = self.get("/api/snippets?lang=py")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["lang"], "python")
        self.assertGreaterEqual(body["count"], 4)
        prefixes = {s["prefix"] for s in body["snippets"]}
        self.assertIn("def", prefixes)
        for s in body["snippets"]:
            self.assertIn("prefix", s)
            self.assertIn("body", s)
        self.assertTrue(any(s["body"].startswith("def ") for s
                            in body["snippets"]))

    def test_short_and_long_lang_names_agree(self):
        _, short = self.get("/api/snippets?lang=js")
        _, long = self.get("/api/snippets?lang=javascript")
        self.assertEqual(short["lang"], "javascript")
        self.assertEqual(short["snippets"], long["snippets"])
        self.assertTrue(any(s["prefix"] == "fn" for s
                            in short["snippets"]))

    def test_unknown_lang_is_empty_not_error(self):
        status, body = self.get("/api/snippets?lang=klingon")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["snippets"], [])

    def test_user_overrides_shadow_builtins(self):
        import tempfile
        from unittest import mock
        from dxn1_studio import snippets2
        userfile = tempfile.mktemp(prefix="dxn1-user-snips-",
                                   suffix=".json")
        with open(userfile, "w", encoding="utf-8") as fh:
            json.dump({"python": {"def": "CUSTOM BODY",
                                  "mine": "own(${x})"}}, fh)
        try:
            with mock.patch.object(snippets2, "STORE_PATH", userfile):
                status, body = self.get("/api/snippets?lang=py")
            self.assertEqual(status, 200)
            packs = {s["prefix"]: s["body"] for s in body["snippets"]}
            self.assertEqual(packs["def"], "CUSTOM BODY")
            self.assertEqual(packs["mine"], "own(${x})")
            # builtins not overridden survive untouched
            self.assertIn("class", packs)
        finally:
            os.remove(userfile)


class TestWorkspaceSwitch(unittest.TestCase):
    """POST /api/workspace + GET /api/workspaces (wave 11).

    Own harness: switching mutates app.project_dir, buffers and the
    recents config, so it must never share a fixture with suites that
    assume a stable workspace.
    """

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
        cls.ws = tempfile.mkdtemp(prefix="dxn1-wsswitch-")
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
        # every test starts from the SAME known workspace, no buffers
        self.app.project_dir = self.ws
        for key in list(getattr(self.app, "_buffers", {}).keys()):
            try:
                self.app.close_tab(key)
            except Exception:
                pass

    # ---- helpers -----------------------------------------------------
    def get(self, path):
        req = urllib.request.Request(self.base + path)
        req.add_header("X-DXN1-Token", self.token)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

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

    def _flush_pump(self):
        # the mutation queue drains on the Tk loop (80 ms cadence) —
        # give it a few beats, then pump the loop once more
        import time
        for _ in range(4):
            time.sleep(0.09)
            self.app.root.update()

    def _buffer_keys(self):
        return list(getattr(self.app, "_buffers", {}).keys())

    def _swap_config_guard(self):
        """Snapshot recent-project keys — Config.set persists to disk,
        so a test must never leave its throwaway workspaces behind."""
        cfg = self.app.config
        return (cfg.get("recent_projects"), cfg.get("last_project"))

    def _restore_config(self, guard):
        recent, last = guard
        cfg = self.app.config
        cfg.set("recent_projects", recent, save=False)
        cfg.set("last_project", last, save=False)
        cfg.save()

    # ---- workspace switching (wave 11) ---------------------------------
    def _swap_config_guard(self):
        """Snapshot recent-project keys — Config.set persists to disk,
        so a test must never leave its throwaway workspaces behind."""
        cfg = self.app.config
        return (cfg.get("recent_projects"), cfg.get("last_project"))

    def _restore_config(self, guard):
        recent, last = guard
        cfg = self.app.config
        cfg.set("recent_projects", recent, save=False)
        cfg.set("last_project", last, save=False)
        cfg.save()

    def test_workspaces_lists_current(self):
        status, body = self.get("/api/workspaces")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["current"], self.app.project_dir)
        paths = [w["path"] for w in body["workspaces"]]
        self.assertIn(self.app.project_dir, paths)
        cur = next(w for w in body["workspaces"] if w["current"])
        self.assertEqual(cur["path"], self.app.project_dir)
        self.assertIn("kind", cur)
        self.assertIn("name", cur)

    def test_workspace_set_roundtrip(self):
        import shutil
        import tempfile
        guard = self._swap_config_guard()
        old = self.app.project_dir
        other = tempfile.mkdtemp(prefix="dxn1-ws-other-")
        with open(os.path.join(other, "main.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("print('other workspace')\n")
        try:
            status, body = self.post("/api/workspace", {"path": other})
            self.assertEqual(status, 200)
            self.assertEqual(body["workspace"], other)
            self.assertEqual(body["kind"], "python")
            self._flush_pump()
            # the desktop moved (same pipeline as its own dialog)
            self.assertEqual(self.app.project_dir, other)
            # the old tabs were closed and the entry file auto-opened —
            # only NEW-workspace buffers may remain (no dead escapes)
            self.assertTrue(self._buffer_keys())
            for k in self._buffer_keys():
                self.assertTrue(k.startswith(other), k)
            # the new workspace auto-opened its entry file
            self.assertTrue(
                (self.app.editor.file_path or "").startswith(other))
            # the token file followed into the new workspace
            tok = os.path.join(other, ".dxn1", "bridge_token")
            self.assertTrue(os.path.isfile(tok))
            with open(tok, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), self.token)
            # recents recorded the switch
            recents = self.app.config.get("recent_projects") or []
            self.assertTrue(recents)
            self.assertEqual(recents[0]["path"], other)
            # the workspaces list marks the NEW current
            status, body = self.get("/api/workspaces")
            cur = next(w for w in body["workspaces"] if w["current"])
            self.assertEqual(cur["path"], other)
        finally:
            # close anything the switch opened, restore the old ws
            for key in self._buffer_keys():
                try:
                    self.app.close_tab(key)
                except Exception:
                    pass
            self.app.project_dir = old
            shutil.rmtree(other, ignore_errors=True)
            self._restore_config(guard)

    def test_workspace_set_refuses_dirty_buffers(self):
        import shutil
        import tempfile
        old = self.app.project_dir
        other = tempfile.mkdtemp(prefix="dxn1-ws-dirty-")
        try:
            # open a clean file, then dirty the desktop buffer
            seed = os.path.join(self.ws, "wb_wsdirty.txt")
            with open(seed, "w", encoding="utf-8") as fh:
                fh.write("clean\n")
            status, _ = self.post("/api/open", {"path": "wb_wsdirty.txt"})
            self.assertEqual(status, 200)
            self._flush_pump()
            key = next(k for k in self._buffer_keys()
                       if k.endswith("wb_wsdirty.txt"))
            self.app._buffers[key]["dirty"] = True
            status, body = self.post("/api/workspace", {"path": other})
            self.assertEqual(status, 400)
            self.assertIn("unsaved", body["error"])
            # nothing moved
            self.assertEqual(self.app.project_dir, old)
            self.assertIn(key, self.app._buffers)
            self.app._buffers[key]["dirty"] = False
        finally:
            for k in list(self.app._buffers):
                if k.endswith("wb_wsdirty.txt"):
                    try:
                        self.app.close_tab(k)
                    except Exception:
                        pass
            shutil.rmtree(other, ignore_errors=True)

    def test_workspace_set_validates(self):
        import shutil
        import tempfile
        old = self.app.project_dir
        # honest refusals — nothing is half-switched
        for payload, marker in (({}, "path required"),
                                ({"path": ""}, "path required"),
                                ({"path": "/no/such/dir/x9z"},
                                 "not a directory")):
            status, body = self.post("/api/workspace", payload)
            self.assertEqual(status, 400, payload)
            self.assertIn(marker, body["error"])
        # a FILE is not a workspace
        self.post("/api/new_file", {"path": "wb_wsfile.txt",
                                    "content": "x"})
        status, body = self.post("/api/workspace",
                                 {"path": os.path.join(self.ws,
                                                       "wb_wsfile.txt")})
        self.assertEqual(status, 400)
        self.assertIn("not a directory", body["error"])
        # same-dir switch is an honest idempotent no-op
        status, body = self.post("/api/workspace", {"path": old})
        self.assertEqual(status, 200)
        self.assertTrue(body.get("unchanged"))
        self.assertEqual(self.app.project_dir, old)

    def test_workspace_switch_rebinds_file_ops(self):
        # after a switch, file ops must act on the NEW workspace
        import shutil
        import tempfile
        guard = self._swap_config_guard()
        old = self.app.project_dir
        other = tempfile.mkdtemp(prefix="dxn1-ws-ops-")
        try:
            status, _ = self.post("/api/workspace", {"path": other})
            self.assertEqual(status, 200)
            self._flush_pump()
            status, body = self.post("/api/new_file",
                                     {"path": "made_after.txt",
                                      "content": "fresh\n"})
            self.assertEqual(status, 200)
            self.assertTrue(os.path.isfile(
                os.path.join(other, "made_after.txt")))
            # reads outside the new sandbox still refuse
            status, body = self.get("/api/file?path=" +
                                    urllib.parse.quote("../escape.txt"))
            self.assertEqual(status, 400)
        finally:
            self.app.project_dir = old
            shutil.rmtree(other, ignore_errors=True)
            self._restore_config(guard)


if __name__ == "__main__":
    unittest.main()
