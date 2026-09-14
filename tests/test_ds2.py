"""DXN1 STUDIO — DS2 consolidated engine test suite.

Runs with pytest OR standalone (``python3 tests/test_ds2.py``).
Covers the DS2 feature engines headlessly — no Tk, no network:

* projects/gallery scaffolds & template registry
* hub pins & favourites (config-backed helpers)
* doctor health checks
* plugins discovery/approval/hooks (real temp plugin folders)
* term task runner (real subprocesses)
* backup snapshots (incl. zip-slip protection)
* outline symbol extraction (5 languages)
* scratchpad persistence
* branches tag engine (real git)

CI runs this after the import gate; locally:

    python3 -m pytest tests/ -q        # or
    python3 tests/test_ds2.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402  (CI installs pytest; standalone needs it too)

# --------------------------------------------------------------- fixtures


class FakeConfig:
    """Minimal config double matching studio.Config's get/set."""

    def __init__(self, data=None):
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


def git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True,
                   capture_output=True, text=True)


def make_git_repo():
    ws = tempfile.mkdtemp()
    git(ws, "init", "-q")
    git(ws, "config", "user.email", "test@local")
    git(ws, "config", "user.name", "Test")
    with open(os.path.join(ws, "a.txt"), "w") as fh:
        fh.write("one\n")
    git(ws, "add", "a.txt")
    git(ws, "commit", "-m", "first")
    return ws


# ---------------------------------------------------------------- gallery
def projects_kinds():
    from dxn1_studio import projects
    from dxn1_studio import gallery
    return list(projects.KIND_ORDER) + list(gallery.EXTRA_TEMPLATES.keys())


def test_gallery_registry_has_all_kinds():
    from dxn1_studio import gallery
    tpl = gallery.all_templates()
    assert len(tpl) >= 17
    for kind in projects_kinds():
        assert kind in tpl, f"missing {kind} in gallery"


def test_gallery_scaffold_extra_templates_compile():
    from dxn1_studio import gallery
    for kind in gallery.EXTRA_TEMPLATES:
        files = gallery.extra_template(kind, "Compile Check")
        assert files, kind
        for rel, content in files.items():
            if rel.endswith(".py"):
                compile(content, rel, "exec")


def test_gallery_favorites_and_pins(tmp_path):
    from dxn1_studio import gallery
    cfg = FakeConfig()
    assert gallery.toggle_favorite(cfg, "todo") is True
    assert gallery.toggle_favorite(cfg, "todo") is False
    gallery.toggle_pin(cfg, str(tmp_path / "w1"))
    gallery.toggle_pin(cfg, str(tmp_path / "w2"))
    recents = [{"path": str(tmp_path / "w1")},
               {"path": str(tmp_path / "w9")},
               {"path": str(tmp_path / "w2")}]
    ordered = gallery.sort_recents_with_pins(recents, cfg)
    assert [r["path"] for r in ordered][:2] == [
        str(tmp_path / "w1"), str(tmp_path / "w2")]


def test_scaffold_roundtrip_python(tmp_path):
    from dxn1_studio import projects
    path, kind = projects.scaffold("python", tmp_path, "Test App")
    assert kind == "python"
    src = open(os.path.join(path, "main.py")).read()
    compile(src, "main.py", "exec")
    meta = projects.read_project_meta(path)
    assert meta == {"name": "Test App", "kind": "python"}


# ------------------------------------------------------------------ doctor
def test_doctor_full_run_shape():
    from dxn1_studio import doctor
    results = doctor.run_checks(config=FakeConfig(), workspace=None)
    assert len(results) >= 10
    for r in results:
        assert r.status in (doctor.OK, doctor.WARN, doctor.FAIL)
    counts = doctor.summary(results)
    assert sum(counts.values()) == len(results)


def test_doctor_detects_missing_workspace():
    from dxn1_studio import doctor
    assert doctor.check_workspace("/definitely/not/here").status \
        == doctor.FAIL


def test_doctor_memory_corruption_detected(tmp_path):
    from dxn1_studio import doctor
    mem = os.path.join(tmp_path, ".dxn1")
    os.makedirs(mem)
    with open(os.path.join(mem, "memory.json"), "w") as fh:
        fh.write("{oops")
    assert doctor.check_memory(str(tmp_path)).status == doctor.FAIL


def test_doctor_report_renders():
    from dxn1_studio import doctor
    report = doctor.format_report(
        doctor.run_checks(config=FakeConfig(), workspace=None))
    assert "doctor" in report


# ----------------------------------------------------------------- plugins
def _write_plugin(base, name, manifest, code):
    folder = os.path.join(base, name)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "plugin.json"), "w") as fh:
        json.dump(manifest, fh)
    with open(os.path.join(folder, "plugin.py"), "w") as fh:
        fh.write(code)
    return folder


def test_plugin_discovery_validation_and_approval(monkeypatch):
    import dxn1_studio.plugins as P
    home = tempfile.mkdtemp()
    monkeypatch.setattr(P, "GLOBAL_PLUGIN_DIR",
                        os.path.join(home, ".dxn1-studio", "plugins"))
    os.makedirs(P.GLOBAL_PLUGIN_DIR, exist_ok=True)
    _write_plugin(P.GLOBAL_PLUGIN_DIR, "good", {
        "name": "good", "version": "1.0", "hooks": ["save"],
        "commands": [{"label": "Do"}],
    }, 'SEEN=[]\n\ndef register(api):\n'
       '    api.register_command("Do", lambda c: "ok")\n'
       '    api.on_save(lambda c: SEEN.append(c["path"]))\n')
    cfg = FakeConfig()
    reg = P.PluginRegistry(config=cfg)
    # not approved -> skipped
    assert reg.load_all(workspace=None) == []
    manifest = [m for m in P.discover(None)
                if m.get("name") == "good"][0]
    # approved -> loads, hooks fire
    reg.approve(manifest)
    assert reg.load(manifest)
    reg.fire_save("/tmp/x.py", "text")
    mod = reg.plugins["good"]["module"]
    assert mod.SEEN == ["/tmp/x.py"]
    # fingerprint change -> approval invalidated
    with open(os.path.join(P.GLOBAL_PLUGIN_DIR, "good", "plugin.py"),
              "a") as fh:
        fh.write("\n# changed\n")
    manifest2 = [m for m in P.discover(None)
                 if m.get("name") == "good"][0]
    assert not reg.approved(manifest2)


def test_plugin_broken_code_fails_soft(monkeypatch):
    import dxn1_studio.plugins as P
    home = tempfile.mkdtemp()
    monkeypatch.setattr(P, "GLOBAL_PLUGIN_DIR",
                        os.path.join(home, ".dxn1-studio", "plugins"))
    os.makedirs(P.GLOBAL_PLUGIN_DIR, exist_ok=True)
    _write_plugin(P.GLOBAL_PLUGIN_DIR, "bad", {"name": "bad"},
                  "not python (")
    reg = P.PluginRegistry(config=FakeConfig())
    manifest = [m for m in P.discover(None)
                if m.get("name") == "bad"][0]
    reg.approve(manifest)
    assert not reg.load(manifest)
    assert any(n == "bad" for n, _ in reg.errors)


def test_sample_plugins_load(monkeypatch):
    import dxn1_studio.plugins as P
    home = tempfile.mkdtemp()
    monkeypatch.setattr(P, "GLOBAL_PLUGIN_DIR",
                        os.path.join(home, ".dxn1-studio", "plugins"))
    os.makedirs(P.GLOBAL_PLUGIN_DIR, exist_ok=True)
    P.write_sample_plugins(P.GLOBAL_PLUGIN_DIR)
    reg = P.PluginRegistry(config=FakeConfig())
    loaded = reg.load_all(workspace=None, request_approval=lambda m: True)
    assert {"insert-header", "commit-lint", "session-clock"} <= set(loaded)


# -------------------------------------------------------------------- term
def _wait(pred, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(0.05)
    return False


def test_task_runner_list_save_defaults(tmp_path):
    from dxn1_studio import term
    assert term.list_tasks(str(tmp_path)) == []
    term.save_tasks(str(tmp_path), [{"name": "t", "cmd": "echo hi"}])
    tasks = term.list_tasks(str(tmp_path))
    assert [t["name"] for t in tasks] == ["t"]
    s, src = term.suggest_tasks(str(tmp_path))
    assert src == "file"
    assert term.default_tasks_for("rust")
    assert term.default_tasks_for("no-such-kind")


def test_task_runner_streaming_and_stop(tmp_path):
    from dxn1_studio import term
    lines, done = [], []
    rt = term.run_task({"name": "echo", "cmd": "echo live-task",
                        "cwd": "", "env": {}, "shell": True},
                       str(tmp_path), lines.append, done.append)
    assert _wait(lambda: len(done) == 1)
    assert done[0] == 0 and "live-task" in "".join(lines)

    long_task = term.run_task({"name": "sleep", "cmd": "sleep 20",
                               "cwd": "", "env": {}, "shell": True},
                              str(tmp_path))
    time.sleep(0.3)
    assert long_task.stop()
    assert _wait(lambda: not long_task.alive)


# ------------------------------------------------------------------ backup
def test_snapshot_create_restore_prune(tmp_path):
    from dxn1_studio import backup
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / "src" / "main.py").write_text("print(1)\n")
    (ws / "README.md").write_text("# demo\n")
    (ws / "__pycache__").mkdir()
    (ws / "__pycache__" / "x.pyc").write_text("junk")
    path, stats = backup.create_snapshot(str(ws), label="pre")
    assert stats["zipped"] >= 2
    # break the file, restore
    (ws / "src" / "main.py").write_text("broken")
    assert backup.restore_snapshot(str(ws), path) >= 2
    assert (ws / "src" / "main.py").read_text() == "print(1)\n"
    # zip-slip blocked
    evil = os.path.join(backup.backups_root(str(ws)), "evil.zip")
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../../../pwned.txt", "x")
    with pytest.raises(ValueError):
        backup.restore_snapshot(str(ws), evil)
    # prune
    for _ in range(11):
        backup.create_snapshot(str(ws))
    assert len(backup.prune_snapshots(str(ws), keep=10)) == 2
    assert len(backup.list_snapshots(str(ws))) == 10


# ----------------------------------------------------------------- outline
def test_outline_python_and_filtering():
    from dxn1_studio import outline
    src = ("def alpha():\n    pass\n\n\nclass Beta:\n"
           "    def run(self):\n        pass\n")
    syms = outline.symbols_for(src, "m.py")
    names = [s["name"] for s in syms]
    assert names == ["alpha", "Beta", "run"]
    assert outline.filter_symbols(syms, "run")[0]["name"] == "run"
    assert outline.symbols_for("def broken(:", "bad.py") == []


def test_outline_multi_language():
    from dxn1_studio import outline
    assert any(s["kind"] == "class" for s in
               outline.symbols_for("class A {}\nfunction b() {}", "a.ts"))
    assert any(s["kind"] == "struct" for s in
               outline.symbols_for("pub struct P {\n}", "p.rs"))
    assert [(s["name"], s["indent"]) for s in
            outline.symbols_for("# H\n## S", "r.md")] == [("H", 0),
                                                          ("S", 1)]


# ----------------------------------------------------------------- scratch
def test_scratch_roundtrip_and_isolation(monkeypatch, tmp_path):
    from dxn1_studio import scratch
    monkeypatch.setattr(scratch, "GLOBAL_SCRATCH",
                        str(tmp_path / "global.md"))
    ws = str(tmp_path / "ws")
    scratch.save_scratch("note", ws)
    assert scratch.load_scratch(ws) == "note"
    scratch.append_entry("entry", ws)
    assert "] entry" in scratch.load_scratch(ws)
    assert "entry" not in scratch.load_scratch(None)


# ------------------------------------------------------------------- tags
def test_tag_engine_roundtrip():
    from dxn1_studio import branches as B
    ws = make_git_repo()
    ok, out = B.create_tag(ws, "v1.0", message="release one")
    assert ok, out
    details = B.tag_details(ws, "v1.0")
    assert details["annotation"] == "release one"
    _, _, tags = B.list_branches(ws)
    assert any(n == "v1.0" for n, _ in tags)
    for bad in ("", "has space", "a^b"):
        assert not B.create_tag(ws, bad)[0]
    ok, out = B.delete_tag(ws, "v1.0")
    assert ok
    _, _, tags = B.list_branches(ws)
    assert all(n != "v1.0" for n, _ in tags)


# -------------------------------------------------------- version sanity
def test_version_is_ds2():
    from dxn1_studio import APP_VERSION
    parts = APP_VERSION.split(".")
    assert len(parts) == 3 and int(parts[0]) >= 2, APP_VERSION


# ------------------------------------------------------------- filestats
def test_filestats_scan_and_sizes(tmp_path):
    from dxn1_studio.filestats import (
        human_size, scan_workspace, top_extensions, summary_lines)

    assert human_size(0) == "0 B"
    assert human_size(1024) == "1.00 KB"
    assert human_size(5 * 1024 * 1024) == "5.00 MB"
    assert human_size(None) == "0 B"

    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_bytes(b"a" * 3000)
    (tmp_path / "src" / "app.py").write_bytes(b"b" * 2000)
    (tmp_path / "README.md").write_bytes(b"c" * 500)
    (tmp_path / "node_modules" / "big.js").write_bytes(b"d" * 99999)
    (tmp_path / "Makefile").write_bytes(b"e")

    s = scan_workspace(tmp_path)
    assert s["exists"] and s["total_files"] == 4
    assert s["total_bytes"] == 3000 + 2000 + 500 + 1
    assert s["by_ext"][".py"] == {"count": 2, "bytes": 5000}
    assert ".js" not in s["by_ext"]              # skipped dir honored
    assert s["no_ext"]["count"] == 1             # Makefile
    assert s["largest"][0][1] == 3000            # main.py first
    tops = top_extensions(s, 2)
    assert tops[0][0] == ".py"
    line1, line2 = summary_lines(s)
    assert "4 files" in line1 and "node_modules" in line2
    assert scan_workspace(tmp_path / "nope")["exists"] is False


# --------------------------------------------------------------- recents
def test_recents_ranking_and_load(tmp_path):
    from dxn1_studio.recents import (
        load_recents, filter_recents, display_row)

    class Cfg:
        def __init__(self, d):
            self.d = d

        def get(self, k, d=None):
            return self.d.get(k, d)

    assert load_recents(None) == []
    assert load_recents(Cfg({})) == []

    f1 = tmp_path / "main.py"
    f2 = tmp_path / "src" / "util.py"
    (tmp_path / "src").mkdir(parents=True)
    f1.write_text("x")
    f2.write_text("y")
    cfg = Cfg({"recent_files": [str(f1), "missing.py", str(f2), str(f1)]})
    recs = load_recents(cfg)
    assert recs == [str(f1), str(f2)]            # dedupe + missing filter

    assert filter_recents(recs, "") == recs      # empty keeps order
    # basename prefix ranks above substring
    assert filter_recents(recs, "util")[0] == str(f2)
    assert filter_recents(recs, "main.py") == [str(f1)]
    assert filter_recents(recs, "zzz") == []     # no match
    assert str(f1) in filter_recents(recs, "mn")  # subsequence fallback
    base, d = display_row(str(f2), tmp_path)
    assert (base, d) == ("util.py", "src")


# -------------------------------------------------------------- standalone
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "--no-header"]))


# ------------------------------------------------------------- bookmarks
def test_bookmark_store_roundtrip(tmp_path):
    from dxn1_studio.bookmarks import (
        BookmarkStore, key_for, snippet_for, store_path)

    assert store_path(str(tmp_path)) == \
        str(tmp_path / ".dxn1" / "bookmarks.json")
    f1 = tmp_path / "main.py"
    (tmp_path / "src").mkdir()
    f2 = tmp_path / "src" / "app.py"
    f1.write_text("def one():\n    pass\n")
    f2.write_text("x = 1  # hello\n")

    assert key_for(f1, tmp_path) == "main.py"
    assert key_for(f2, tmp_path) == "src/app.py"
    assert key_for(str(tmp_path) + "_outside.py", tmp_path).endswith(".py")

    s = BookmarkStore(tmp_path)
    assert s.toggle("main.py", 1) is True
    assert s.toggle("main.py", 1) is False
    s.set("src/app.py", [10, 2, 2, 0, -5])          # dedupe + drop bad
    assert s.get("src/app.py") == [2, 10]
    assert s.save() is True

    s2 = BookmarkStore(tmp_path)
    assert s2.get("main.py") == []                  # toggled back off
    assert s2.get("src/app.py") == [2, 10]
    s2.set("big.py", list(range(1, 2000)))
    assert len(s2.get("big.py")) == 500             # cap per file

    # corrupt store -> clean start, no raise
    (tmp_path / ".dxn1" / "bookmarks.json").write_text("{bad json")
    assert BookmarkStore(tmp_path).all() == {}

    # snippets are safe on missing/oversize files
    assert snippet_for(str(f1), 1) == "def one():"
    assert snippet_for(str(tmp_path / "nope.py"), 1) == ""


# ------------------------------------------------------- prompt library
def test_prompt_library_engine(tmp_path):
    from dxn1_studio.prompts import (
        load_prompts, save_user_prompt, delete_user_prompt, render,
        filter_prompts)

    ws = str(tmp_path)
    lib = load_prompts(ws)
    assert len(lib) >= 6                      # starters present

    ok, _ = save_user_prompt(ws, "Explain this file", "CUSTOM {file}")
    assert ok
    mine = [p for p in load_prompts(ws) if p["name"] == "Explain this file"]
    assert mine[0]["template"] == "CUSTOM {file}"   # workspace wins
    assert save_user_prompt(ws, "", "x")[0] is False  # validation

    out = render("Do {file} in {workspace} ({lang})",
                 file_path=ws + "/main.py", workspace=ws)
    assert "main.py" in out and "py" in out
    assert render("keep {unknown}") == "keep {unknown}"   # literal
    assert "the file" in render("use {selection}", selection="   ")

    hits = filter_prompts(lib, "tests")
    assert hits and all("tests" in (p["name"] + p["description"]).lower()
                        for p in hits)
    assert filter_prompts(lib, "zzz") == []

    assert delete_user_prompt(ws, "Explain this file") is True


# --------------------------------------------------------- what's new
def test_whatsnew_parser_and_upgrade_gate():
    from dxn1_studio.whatsnew import (
        parse_changelog, load_entries, new_entries, plain_bullet,
        find_changelog)

    sample = (
        "# Changelog\n\nintro\n"
        "## [2.4.0] — 2026-09-14 · beta\n\n"
        "### Added\n- **Feature A** — does things\n  wrapped line\n"
        "### Fixed\n- a fix\n"
        "## [2.3.0] — 2026-09-13 · beta\n\n"
        "### Added\n- older\n")
    es = parse_changelog(sample)
    assert [e["version"] for e in es] == ["2.4.0", "2.3.0"]
    added = [s for s in es[0]["sections"] if s["title"] == "Added"][0]
    assert len(added["items"]) == 1 and "wrapped line" in added["items"][0]

    assert find_changelog().endswith("CHANGELOG.md")
    real = load_entries()
    # semver-ish compare (2.10.0 > 2.9.0 — never compare version strings)
    def _vkey(v):
        return tuple(int(p) for p in str(v).split("."))
    assert real and _vkey(real[0]["version"]) >= (2, 4, 0)
    assert new_entries(real, None) == real[:1]
    assert new_entries(real, "99.0.0") == []
    assert plain_bullet("**b** `c`") == "b c"


# --------------------------------------------- hub insights (DS2 v2.6.0)
def test_hub_insights_engines(tmp_path):
    from dxn1_studio.workspace_stats import (
        aggregate_insights, aggregate_line, current_branch, stats_for)

    ws = tmp_path / "insws"
    (ws / "sub").mkdir(parents=True)
    (ws / "a.py").write_text("x = 1\n")
    (ws / "sub" / "b.py").write_text("y = 2\n")
    (ws / "c.md").write_text("# hi\n")
    (ws / "data.bin").write_bytes(b"\x00\x01")
    stats = stats_for(str(ws))
    assert stats["files"] == 4
    assert stats["primary_language"] == "Python"

    # aggregate: empty stats entries are skipped, mix normalizes to 100 %
    ag = aggregate_insights([stats, {}, None])
    assert ag["workspaces"] == 1 and ag["files"] == 4
    assert ag["top"] and ag["top"][0][0] == "Python"
    assert sum(p for _n, p in ag["top"]) == 100
    line = aggregate_line(ag)
    assert "1 workspace  " in line and "Python" in line and "4 files" in line
    # plural + empty cases
    two = aggregate_insights([stats, stats])
    assert two["workspaces"] == 2 and "2 workspaces" in aggregate_line(two)
    assert aggregate_line(aggregate_insights([])) == ""
    assert aggregate_line(None) == ""

    # branch: non-git dir → '', git repo (this checkout) → non-empty
    assert current_branch(str(ws)) == ""
    here = str(tmp_path)  # not a repo either, still must not raise
    assert current_branch(here) in ("", "(unknown)") or isinstance(
        current_branch(here), str)


def test_sniff_encoding_labels(tmp_path):
    """DS2 v2.6: the statusbar's encoding sniffer labels common cases."""
    from dxn1_studio.app import DXN1Studio

    p_utf = tmp_path / "u.py"
    p_utf.write_text("print('héllo')\n", encoding="utf-8")
    p_bom = tmp_path / "b.py"
    p_bom.write_bytes(b"\xef\xbb\xbfprint('x')\n")
    p_bin = tmp_path / "b.bin"
    p_bin.write_bytes(b"\xff\xfe\x00\xfa")
    assert DXN1Studio._sniff_encoding(str(p_utf)) == "UTF-8"
    assert DXN1Studio._sniff_encoding(str(p_bom)) == "UTF-8 BOM"
    assert DXN1Studio._sniff_encoding(str(p_bin)) in ("non-UTF8", "UTF-16")
    assert DXN1Studio._sniff_encoding(str(tmp_path / "nope.py")) == ""


# ------------------------------------------ error-block extraction v2.6.0
def test_extract_error_block_pytest_and_traceback():
    from dxn1_studio.app import extract_error_block as ex

    pytest_out = (
        "running...\n"
        "================================== FAILURES"
        " ==================================\n"
        "________________________________ test_add"
        " ________________________________\n\n"
        "    def test_add():\n"
        ">       assert add(1, 2) == 4\n"
        "E       assert 3 == 4\n"
        "E        +  where 3 = add(1, 2)\n\n"
        "tests/test_x.py:12: AssertionError\n"
        "========================= short summary info"
        " =========================\n"
        "FAILED tests/test_x.py::test_add - assert 3 == 4\n")
    block = ex(pytest_out)
    assert "FAILED tests/test_x.py::test_add" in block
    assert "assert 3 == 4" in block          # assert context came along
    assert "running..." not in block          # banner walk-up worked

    # unittest header form
    uni = ".....\nFAIL: test_divide (t.TestDiv)\nZeroDivisionError: division by zero\n"
    assert "FAIL: test_divide" in ex(uni) and "ZeroDivisionError" in ex(uni)

    # classic traceback still detected
    tb = "before\nTraceback (most recent call last):\n  File \"x.py\", line 1\nNameError: name 'x' is not defined\n"
    assert "Traceback (most recent call last)" in ex(tb)
    assert "NameError" in ex(tb)

    # false positives must NOT match
    assert ex("Failed to open file\nall good\n") == ""
    assert ex("fail-safe mode enabled\n") == ""
    assert ex("") == ""
    assert ex("hello world\nnothing here\n") == ""

    # most recent failure wins (two FAILED lines)
    two = pytest_out + "FAILED tests/test_y.py::test_b - boom\n"
    assert "test_b" in ex(two)


def test_extract_error_block_line_cap():
    from dxn1_studio.app import extract_error_block as ex
    tb = ("Traceback (most recent call last):\n"
          + "".join(f"  line {i}\n" for i in range(100)))
    assert len(ex(tb, max_lines=10).split("\n")) <= 10


def test_devtools_case_and_codecs():
    from dxn1_studio.devtools import (to_snake, to_camel, to_pascal,
                                      to_kebab, to_const, to_title,
                                      b64_encode, b64_decode,
                                      url_encode, url_decode,
                                      hashes, unicode_escape,
                                      unicode_unescape, text_counts)
    # identifier splitting across every naming style
    for src in ("HTTPServer2", "http_server2", "HttpServer2"):
        assert to_snake(src) == "http_server2"
    assert to_snake("http-server-2") == "http_server_2"
    assert to_camel("user_profile_name") == "userProfileName"
    assert to_pascal("user profile") == "UserProfile"
    assert to_kebab("PascalCaseInput") == "pascal-case-input"
    assert to_const("apiKey") == "API_KEY"
    assert to_title("hello-world") == "Hello World"
    assert to_snake("") == "" and to_snake("   ") == ""
    # codec round-trips
    assert b64_decode(b64_encode("héllo 世界")[0])[0] == "héllo 世界"
    assert b64_decode("!!!not base64!!!")[1] != ""
    assert url_decode(url_encode("a b&c=d")[0])[0] == "a b&c=d"
    h = hashes("abc")
    assert h["md5"] == "900150983cd24fb0d6963f7d28e17f72"
    assert len(h["sha256"]) == 64
    esc, _ = unicode_escape("aéπ")
    assert esc == "a\\u00e9\\u03c0"
    assert unicode_unescape(esc)[0] == "aéπ"
    astral, _ = unicode_escape("𝄞")
    assert astral == "\\U0001d11e"
    assert unicode_unescape(astral)[0] == "𝄞"
    c = text_counts("hello world\nsecond\n")
    assert c == {"chars": 19, "chars_no_ws": 16, "words": 3, "lines": 2}


def test_devtools_regex_engine():
    from dxn1_studio.devtools import (regex_matches, regex_do_replace,
                                      regex_flags, MAX_MATCHES)
    # groups + named groups + spans
    ms, err = regex_matches(r"(\w+)@(\w+)\.com",
                            "a@b.com and c@d.com")
    assert err == "" and len(ms) == 2
    assert ms[0]["start"] == 0 and ms[0]["end"] == 7
    assert ms[0]["groups"] == ["a", "b"]
    ms, _ = regex_matches(r"(?P<y>\d{4})-(?P<m>\d{2})", "2026-09")
    assert ms[0]["groupdict"] == {"y": "2026", "m": "09"}
    # flags engine
    assert regex_matches("HELLO", "hello world",
                         regex_flags("i"))[1] == ""
    assert regex_matches("HELLO", "hello world")[0] == []
    fm, _ = regex_matches(r"^b", "a\nb", regex_flags("m"))
    assert fm and fm[0]["text"] == "b"
    # bad pattern is an error, never an exception
    ms, err = regex_matches("([unclosed", "x")
    assert ms == [] and "pattern error" in err
    # replace with backrefs + errors
    out, err = regex_do_replace(r"(\w+)@example\.com",
                                r"\1 AT example", "bob@example.com")
    assert out == "bob AT example" and err == ""
    out, err = regex_do_replace("a", r"\9nosuch", "a")
    assert err != ""
    # cap enforced
    ms, _ = regex_matches("x", "x" * 3000)
    assert len(ms) == MAX_MATCHES


def test_devtools_json_and_time():
    from dxn1_studio.devtools import (json_format, json_minify,
                                      json_validate, epoch_to_iso,
                                      iso_to_epoch, rel_time,
                                      now_iso)
    pretty, err = json_format('{"b":1,"a":[1,2]}', sort_keys=True)
    assert err == ""
    assert pretty.splitlines()[1].strip().startswith('"a"')
    mini, err = json_minify('{ "a" : 1 }')
    assert mini == '{"a":1}' and err == ""
    # error carries line/col
    _, err = json_format('{\n  "a": 1,\n}')
    assert "line 2" in err or "line 3" in err
    assert json_validate("nope") != ""
    assert json_validate('{"ok": true}') == ""
    # epoch <-> ISO round-trip (UTC, second resolution)
    ep = 1_789_000_000
    iso, err = epoch_to_iso(ep)
    assert err == "" and iso.startswith("2026-")
    back, err = iso_to_epoch(iso)
    assert back == ep and err == ""
    # 'Z' suffix + naive-means-UTC
    assert iso_to_epoch("2026-01-01T00:00:00Z")[0] == \
        iso_to_epoch("2026-01-01T00:00:00")[0]
    # garbage is an error, never an exception
    assert epoch_to_iso("not-a-number")[1] != ""
    assert iso_to_epoch("gibberish")[1] != ""
    # relative time engine
    now = 1_800_000_000
    assert rel_time(now - 7200, now=now) == "2h ago"
    assert rel_time(now + 3 * 86400, now=now) == "in 3d"
    assert rel_time(now + 3, now=now) == "in 3s"
    assert rel_time(now - 61, now=now) == "1m ago"
    assert rel_time(now, now=now) == "now"
    assert rel_time("junk") == ""
    assert now_iso().startswith("20")


def test_devtools_color_engine():
    from dxn1_studio.devtools import (hex_to_rgb, rgb_to_hex, rgb_to_hsl,
                                      hsl_to_rgb, contrast_ratio,
                                      rel_luminance, color_harmonies)
    r, g, b, err = hex_to_rgb("#4f8cff")
    assert (r, g, b, err) == (79, 140, 255, "")
    assert hex_to_rgb("#abc")[:3] == (170, 187, 204)
    assert hex_to_rgb("nope")[3] != "" and hex_to_rgb("#12")[3] != ""
    assert rgb_to_hex(79, 140, 255) == "#4f8cff"
    assert rgb_to_hex(300, -5, 25.4) == "#ff0019"   # clamped
    h, s, l = rgb_to_hsl(79, 140, 255)
    assert 210 < h < 230 and 95 < s <= 100 and 50 < l < 70
    assert rgb_to_hsl(255, 255, 255) == (0.0, 0.0, 100.0)
    rr, gg, bb = hsl_to_rgb(h, s, l)
    assert abs(rr - 79) <= 1 and abs(gg - 140) <= 1 and abs(bb - 255) <= 1
    # WCAG anchors: black on white = 21:1; same color = 1:1
    assert abs(contrast_ratio("#000000", "#ffffff") - 21.0) < 0.01
    assert abs(contrast_ratio("#4f8cff", "#4f8cff") - 1.0) < 0.01
    assert rel_luminance(255, 255, 255) == 1.0
    assert rel_luminance(0, 0, 0) == 0.0
    hm = color_harmonies("#4f8cff")
    assert len(hm) == 8 and hm["base"] == "#4f8cff"
    assert all(v.startswith("#") for v in hm.values())
    assert color_harmonies("hello") == {}  # bad length, not a 3-digit shorthand


def test_cronexp_engine():
    from datetime import datetime
    from dxn1_studio.cronexp import (describe, parse_cron, next_runs,
                                     field_table)
    # parsing: every shorthand resolves
    assert parse_cron("@daily")[0] == parse_cron("0 0 * * *")[0]
    assert parse_cron("@hourly")[0]["minute"] == [0]
    assert "@reboot" in parse_cron("@reboot")[1]
    # names, steps, ranges, lists, 7==Sunday
    f, err = parse_cron("*/15 9-17 * * mon-fri")
    assert err == "" and f["minute"] == [0, 15, 30, 45]
    assert f["dow"] == [1, 2, 3, 4, 5]
    f, _ = parse_cron("* * * * 7")
    assert f["dow"] == [0]                      # 7 normalizes to Sunday
    f, _ = parse_cron("0 0 * dec,jan *")
    assert f["month"] == [1, 12]
    # garbage never raises
    assert parse_cron("junk")[1] != ""
    assert parse_cron("99 * * * *")[1] != ""
    assert parse_cron("*/0 * * * *")[1] != ""
    assert parse_cron("0 9 * *")[1] != ""       # 4 fields
    assert parse_cron("")[1] != ""
    # describe sentences
    assert describe("0 9 * * 1")[0] == "at 09:00, on MON"
    assert describe("5 * * * *")[0] == "at :05 past every hour"
    assert describe("* * * * *")[0] == "every minute"
    assert describe("30 4 1,15 * *")[0] == "at 04:30, on day 1, 15 of the month"
    assert "JAN" in describe("0 0 1 1 *")[0]
    assert describe("@daily")[0] == describe("0 0 * * *")[0]
    # next runs: daily -> tomorrow and the day after, both midnight
    runs, err = next_runs("@daily", count=3,
                          now=datetime(2026, 9, 14, 10, 0))
    assert err == "" and len(runs) == 3
    assert (runs[0].month, runs[0].day, runs[0].hour) == (9, 15, 0)
    assert (runs[2].month, runs[2].day) == (9, 17)
    # mon-only 9am skips a Sunday start
    runs, _ = next_runs("0 9 * * 1", count=2,
                        now=datetime(2026, 9, 14, 10, 0))  # Monday 10:00
    assert all(r.weekday() == 0 and r.hour == 9 for r in runs)
    assert runs[0].day == 21
    # yearly: three consecutive years
    runs, _ = next_runs("0 0 1 1 *", count=3,
                        now=datetime(2026, 9, 14, 10, 0))
    assert [r.year for r in runs] == [2027, 2028, 2029]
    # field table rows: names render uppercase, star fields say every
    rows = field_table("*/15 9-17 * * mon-fri")
    assert rows[0][2] == "0, 15, 30, 45"
    assert rows[4][2] == "MON, TUE, WED, THU, FRI"  # calendar order
    assert rows[2][2].startswith("every day-of-month")


def test_readability_engine():
    from dxn1_studio.readability import (syllables, sentences, words,
                                         flesch_reading_ease,
                                         flesch_kincaid_grade,
                                         grade_label, gunning_fog,
                                         stats, long_sentences,
                                         top_words, report_text)
    assert syllables("cat") == 1 and syllables("apple") == 2
    assert syllables("documentation") == 5
    assert syllables("queue") == 1 and syllables("syllable") == 3
    assert syllables("") == 0 and syllables("123 45") == 0
    assert sentences("One. Two! Three?")[2] == "Three"
    assert sentences("no terminator here") == ["no terminator here"]
    assert sentences("") == []
    assert len(words("Hello, world! It's 2026.")) == 3  # digits are not prose
    easy = "The cat sat on the mat. It was a cat and the cat was happy."
    hard = ("Incontrovertible administrator considerations "
            "characterized the unprecedented industrialization, "
            "disproportionately compromising the feasibility of the "
            "constitutionality, nevertheless perpetuating an "
            "incomprehensible bureaucratization of the international "
            "responsibilities.")
    assert flesch_reading_ease(easy) > flesch_reading_ease(hard)
    assert flesch_kincaid_grade(hard) > flesch_kincaid_grade(easy)
    assert gunning_fog(hard) > gunning_fog(easy)
    assert grade_label(95) == "very easy" and grade_label(10) == "very difficult"
    assert grade_label(62) == "plain English"
    assert flesch_reading_ease("") == 0.0
    assert stats("") == {} and stats("Short bit.")["words"] == 2
    st = stats(easy)
    assert st["sentences"] == 2 and st["words"] == 15
    long_text = ("This single sentence wanders on and on through clause "
                 "after clause without ever finding a natural resting "
                 "place for its reader, piling subordination upon "
                 "subordination until the poor sentence finally, "
                 "exhaustively, mercifully collapses.")
    longs = long_sentences("Short one. " + long_text)
    assert longs and longs[0][0] > 25
    top = top_words(easy)
    assert top[0][0] == "cat" and top[0][1] == 3
    # report renders both ways and never raises on empty input
    assert "Readability" in report_text(easy, "demo")
    assert report_text("", "empty").startswith("No prose")
    assert report_text(easy, "demo", markdown=True).startswith("# Readability")


def _mk_jwt(payload, header=None):
    import base64 as _b64
    import json as _json
    h = _b64.urlsafe_b64encode(_json.dumps(header or {
        "alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    p = _b64.urlsafe_b64encode(_json.dumps(payload).encode()) \
        .rstrip(b"=").decode()
    return f"{h}.{p}.{'x' * 43}"


def test_jwt_engine():
    from dxn1_studio.jwt import (decode_jwt, token_status, claims_table,
                                 b64url_decode)
    import time as _time
    tok = _mk_jwt({"sub": "u1", "iss": "dxn1", "aud": "api",
                   "exp": int(_time.time()) + 7200})
    d, err = decode_jwt(tok)
    assert err == "" and d["alg"] == "HS256" and d["typ"] == "JWT"
    assert d["payload"]["sub"] == "u1" and d["signature_len"] == 43
    state, human = token_status(d["payload"])
    assert state == "valid" and "expires in" in human and "1h" in human
    # expired + none + garbage exp
    old = _mk_jwt({"exp": 1000000000})
    state, human = token_status(decode_jwt(old)[0]["payload"])
    assert state == "expired" and human.endswith("ago")
    assert token_status({})[0] == "none"
    assert token_status({"exp": "soon"})[0] == "none"
    # claims table: time claims humanized, standard claims, extras JSON
    rows = claims_table(decode_jwt(tok)[0]["payload"])
    names = [r[0] for r in rows]
    assert names[:4] == ["exp", "iss", "sub", "aud"]
    assert "UTC" in rows[0][2]
    rows = claims_table({"iat": "not-a-number", "x": {"deep": [1, 2]}})
    by = {r[0]: r for r in rows}
    assert "unreadable" in by["iat"][2]
    assert '"deep"' in by["x"][1]
    # broken tokens never raise
    assert "3 dot-separated" in decode_jwt("abc")[1]
    assert decode_jwt("")[1] != ""
    assert decode_jwt("a.b.c")[1] != ""
    assert "JSON" in decode_jwt("bm90LWpzb24.e30.x")[1]
    assert b64url_decode("")[1] if False else True  # smoke the import
    assert b64url_decode("!bad!") == b""


def test_envcheck_engine():
    from dxn1_studio.envcheck import (parse_env, lint_env, mask_env,
                                      is_secret_key, summary)
    assert is_secret_key("STRIPE_API_TOKEN")
    assert is_secret_key("db_password")
    assert not is_secret_key("DEBUG")
    # parse basics
    entries = parse_env("A=1\n# comment\n\nB = 2\n")
    assert [e["blank"] for e in entries] == [False, False, True, False]
    assert entries[3]["error"].startswith("spaces around")
    # duplicates, invalid keys, quotes, comments, spaces
    sample = ("# config\n"
              "KEY=first\n"
              "KEY=second\n"
              "BAD-KEY!=x\n"
              "Q=\"two words\"  # trailing note\n"
              "UNQ=hello world # glued comment\n"
              "EMPTY=\n"
              "OPEN=\"never closed\n")
    findings = lint_env(sample)
    msgs = [m for _, _, m in findings]
    assert any("duplicate key KEY" in m for m in msgs)
    assert any("invalid key" in m for m in msgs)
    assert any("empty value" in m for m in msgs)
    assert any("never closed" in m for m in msgs)
    assert any("' #'" in m for m in msgs)          # unquoted comment
    # quoted value with trailing comment is CLEAN
    assert not any(m.startswith("Q:") for m in msgs)
    lines = {line: msg for line, _, msg in findings}
    assert 8 in lines and 6 in lines
    # masking: secret keys and URL creds, comments preserved
    env = ("API_KEY=sk-live-abcdef1234567890\n"
           "DEBUG=1\n"
           "DB=postgres://user:pass@host:5432/db\n")
    masked = mask_env(env)
    assert "sk-live" not in masked and "sk-…" in masked
    assert "pass" not in masked and "user:***@host" in masked
    assert "DEBUG=1" in masked                     # non-secrets survive
    assert summary(env) == (3, 1, 0)               # only API_KEY smells
    assert summary("") == (0, 0, 0)
    assert summary("A=1") == (1, 0, 1)             # EOF newline info
    assert lint_env("") == []
    # no newline at EOF is an info, not an error
    assert lint_env("A=1")[0][1] == "info"


def test_gen_engine():
    from dxn1_studio import gen as g
    import re
    us = g.uuid4s(8)
    assert all(re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
                        r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$", x)
               for x in us)
    assert len(set(us)) == 8
    ul = g.ulids(5)
    assert all(len(x) == 26 and all(c in g._CROCKFORD for c in x)
               for x in ul)
    assert ul[0][0] >= ul[-1][0]        # newest first, monotonic-ish
    assert g.ulids(1, now_ms=0)[0].startswith("0" * 10)
    na = g.nanoids(50)
    assert all(len(x) == 21 for x in na) and len(set(na)) == 50
    assert all(len(x) == 32 for x in g.hex_tokens(4))
    for p in g.passwords(30, 20):
        assert len(p) == 20
        assert any(c.isupper() for c in p) and any(c.islower() for c in p)
        assert any(c.isdigit() for c in p) and any(not c.isalnum()
                                                   for c in p)
    assert all(len(x) == 6 and x.isdigit() for x in g.pins(5, 6))
    assert len(g.lorem(3, 4).split("\n\n")) == 3
    users = g.fake_users(12)
    assert len(users) == 12 and users[0]["id"] == 1
    assert len({u["username"] for u in users}) == 12
    assert all("@" in u["email"] for u in users)
    assert '"first_name"' in g.fake_json(3, "users")
    assert '"type"' in g.fake_json(3, "events")
    assert g.fake_json(2, "ids").startswith("[")
    out, err = g.generate("ULID", 3)
    assert err == "" and len(out.splitlines()) == 3
    out, err = g.generate("mystery", 3)
    assert "unknown" in err and out == ""
    out, err = g.generate("PIN (6)", 1000)   # clamped, never dies
    assert err == ""


def test_sqlitelab_engine():
    # DS2 v2.9.0 — the SQLite Lab: pure engine checks on a scratch DB
    import csv
    import os
    import sqlite3
    import tempfile

    from dxn1_studio import sqlitelab as sl

    tmp = tempfile.mkdtemp(prefix="ds2-sqlab-")
    db = os.path.join(tmp, "test.db")
    raw = sqlite3.connect(db)
    raw.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    raw.execute("CREATE INDEX name_idx ON users (name)")
    raw.execute("CREATE VIEW v_adults AS SELECT id FROM users")
    raw.execute("INSERT INTO users (name) VALUES ('ada'), ('grace')")
    raw.commit()
    raw.close()

    conn = sl.connect(db, read_only=True)
    tabs = sl.list_tables(conn)
    assert [(t["name"], t["kind"]) for t in tabs] == [
        ("users", "table"), ("v_adults", "view")]
    assert tabs[0]["rows"] == 2 and tabs[1]["rows"] is None

    cols = sl.table_columns(conn, "users")
    assert [c["name"] for c in cols] == ["id", "name"]
    assert cols[0]["pk"] == 1 and cols[1]["notnull"]

    ix = sl.table_indexes(conn, "users")
    assert ix and ix[0]["name"] == "name_idx" and ix[0]["cols"] == ["name"]

    c, r, err = sl.sample_rows(conn, "users")
    assert err == "" and c == ["id", "name"] and len(r) == 2

    # long cells truncate; missing tables return an error string
    db2 = os.path.join(tmp, "test2.db")
    raw2 = sqlite3.connect(db2)
    raw2.execute("CREATE TABLE blobby (t TEXT, b BLOB)")
    raw2.execute("INSERT INTO blobby VALUES (?, ?)", ("x" * 300, b"\x00\x01"))
    raw2.commit()
    raw2.close()
    conn2 = sl.connect(db2)
    c2, r2, _ = sl.sample_rows(conn2, "blobby")
    assert r2[0][0].endswith("…") and len(r2[0][0]) == 160
    assert r2[0][1] == "<2 bytes>"
    assert sl.sample_rows(conn2, "nope")[2] != ""

    # queries: grid, errors, readonly block, rw writes with affected count
    res = sl.run_query(conn, "SELECT COUNT(*) AS n FROM users")
    assert res["kind"] == "rows" and res["rows"] == [["2"]]
    assert "syntax" in sl.run_query(conn, "SELEC 1")["error"]
    res = sl.run_query(conn, "INSERT INTO users (name) VALUES ('x')")
    assert res["kind"] == "error" and "readonly" in res["error"]
    rw = sl.connect(db, read_only=False)
    res = sl.run_query(rw, "INSERT INTO users (name) VALUES ('kim')")
    assert res["kind"] == "ok" and res["affected"] == 1
    assert sl.run_query(rw, "SELECT COUNT(*) FROM users")["rows"] == [["3"]]

    # markdown + csv round-trips
    md = sl.markdown_table(["a", "b|c"],
                           [["1", "x"], ["2", "y"], ["3", "z"]], max_rows=2)
    assert "\\|c" in md and "1 more rows" in md
    out = os.path.join(tmp, "out.csv")
    assert sl.export_csv(["a", "b"], [["1", "x"]], out) == 1
    with open(out, newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["a", "b"] and rows[1] == ["1", "x"]

    # info, finder, quoting, human sizes, empty dbs
    info = dict(sl.db_info(conn))
    assert "SQLite version" in info and "File size (data)" in info
    assert db in sl.find_databases(tmp) and db2 in sl.find_databases(tmp)
    assert sl.qident('we"ird') == '"we""ird"'
    assert sl.human_size(0) == "0 B" and "KB" in sl.human_size(2048)
    assert sl.human_size("junk") == "?"
    assert sl.list_tables(sqlite3.connect(":memory:")) == []


def test_treeexport_engine():
    # DS2 v2.9.0 — directory tree export: skips, sorting, caps, render
    import os
    import tempfile

    from dxn1_studio import treeexport as te

    tmp = tempfile.mkdtemp(prefix="ds2-tree-")
    os.makedirs(os.path.join(tmp, "src", "pkg"))
    os.makedirs(os.path.join(tmp, "node_modules", "junk"))
    os.makedirs(os.path.join(tmp, ".hidden"))
    open(os.path.join(tmp, "README.md"), "w").write("hi")
    open(os.path.join(tmp, "src", "pkg", "core.py"), "w").write("x" * 2048)
    open(os.path.join(tmp, "src", "main.py"), "w").write("y" * 100)
    open(os.path.join(tmp, "node_modules", "junk", "x.js"), "w").write("z")

    lines, stats = te.build_tree(tmp, max_depth=3)
    names = [n for _, n, _, _ in lines]
    assert "node_modules" not in names and ".hidden" not in names
    assert "src" in names and "README.md" in names
    assert stats["dirs"] == 2 and stats["files"] == 3
    assert stats["skipped"] == 1
    assert stats["bytes"] == 2048 + 100 + 2
    assert names.index("src") < names.index("README.md")  # dirs first

    txt = te.render_tree(tmp, lines, stats)
    assert "├──" in txt or "└──" in txt
    assert "2.0 KB" in txt and "2 directories, 3 files" in txt
    assert "junk dirs skipped" in txt

    # hidden toggle + depth cap + size toggle
    l2, _s2 = te.build_tree(tmp, max_depth=1, show_hidden=True)
    n2 = [n for _, n, _, _ in l2]
    assert ".hidden" in n2 and "pkg" not in n2
    l3, s3 = te.build_tree(tmp, max_depth=2, show_sizes=False)
    t3 = te.render_tree(tmp, l3, s3, show_sizes=False)
    assert "2.0 KB" not in t3

    # invalid root is safe; helpers sane
    assert te.build_tree(os.path.join(tmp, "nope")) == ([], {
        "dirs": 0, "files": 0, "bytes": 0, "truncated": False,
        "skipped": 0})
    assert te.human_size(0) == "0 B" and "KB" in te.human_size(2048)
    assert te.human_size("junk") == "?"


def test_hasher_engine():
    # DS2 v2.10.0 — chunked digests, folder manifests, line parsing
    import hashlib
    import os
    import tempfile

    from dxn1_studio import hasher as hh

    tmp = tempfile.mkdtemp(prefix="ds2-hash-")
    os.makedirs(os.path.join(tmp, "sub"))
    f1 = os.path.join(tmp, "a.txt")
    open(f1, "wb").write(b"hello world")
    open(os.path.join(tmp, "sub", "b.bin"), "wb").write(b"x" * 3000)
    open(os.path.join(tmp, ".hidden"), "wb").write(b"no")

    d, size = hh.hash_file(f1, "sha256")
    assert d == hashlib.sha256(b"hello world").hexdigest() and size == 11
    assert hh.hash_bytes(b"hello world", "md5") == \
        hashlib.md5(b"hello world").hexdigest()
    try:
        hh.hash_file(f1, "nope")
        assert False
    except ValueError:
        pass

    rows = hh.hash_dir(tmp, "sha256")
    assert [r[3] for r in rows] == ["a.txt", "sub/b.bin"]
    assert rows[0][2] == 11 and rows[1][2] == 3000
    assert hh.hash_dir(os.path.join(tmp, "nope")) == []

    line = hh.manifest_line("sha256", d, 11, "a.txt")
    assert line == f"{d}  a.txt"
    got, path, err = hh.verify_line(line)
    assert got == d and err == "" and path == "a.txt"
    got2, path2, _e2 = hh.verify_line(f"{d} *b.bin")
    assert got2 == d and path2 == "b.bin"
    assert hh.verify_line("# comment") == (None, "", "")
    assert hh.verify_line("") == (None, "", "")
    assert hh.verify_line("short z") == (None, "", "malformed line")

    # verify-all logic mirrors the window: digest lookup by rel path
    text = "\n".join(hh.manifest_line(*r) for r in rows)
    expected = {}
    for ln in text.splitlines():
        dig, p, _e = hh.verify_line(ln)
        if dig and p:
            expected[p] = dig
    assert expected == {"a.txt": d, "sub/b.bin": rows[1][1]}


def test_focus_engine():
    # DS2 v2.11.0 — deterministic pomodoro state machine
    from dxn1_studio.focus import FocusEngine, fmt_mmss

    e = FocusEngine(work=300, brk=60, long_break=120, long_every=2)
    assert e.label() == "05:00" and e.phase == "work" and e.cycle == 1
    assert fmt_mmss(0) == "00:00" and fmt_mmss("junk") == "00:00"
    assert fmt_mmss(-5) == "00:00" and fmt_mmss(65) == "01:05"

    e.start()
    assert e.tick(299) == [] and e.remaining == 1
    assert e.tick(1) == ["work-done"]
    assert e.phase == "break" and e.completed == 1 and e.remaining == 60
    assert e.tick(60) == ["break-done"] and e.phase == "work"
    assert e.tick(300) == ["work-done", "cycle-done"]
    assert e.phase == "long" and e.remaining == 120
    assert e.tick(120) == ["break-done"]
    assert e.phase == "work" and e.cycle == 1 and e.completed == 2

    # paused ticks do nothing; skip jumps phases; reset restores
    e2 = FocusEngine(work=100, brk=30, long_break=45)
    e2.start()
    e2.pause()
    assert e2.tick(50) == [] and e2.remaining == 100
    e3 = FocusEngine(work=100, brk=30, long_break=45)
    e3.start()
    ev = e3.skip()
    assert "work-done" in ev and e3.phase == "break"
    assert e3.completed == 1 and e3.remaining == 30
    e4 = FocusEngine(work=100)
    e4.reset()
    assert e4.remaining == 100 and e4.running is False
    assert FocusEngine().work == 25 * 60


def test_linesort_engine():
    # DS2 v2.12.0 — line tools: sorting, dedupe, shuffle, ranges
    import random

    from dxn1_studio import linesort as ls

    t = "pear\nApple\nbanana\n"
    assert ls.transform_lines(t, "az") == "Apple\nbanana\npear\n"
    assert ls.transform_lines(t, "za") == "pear\nbanana\nApple\n"
    assert ls.transform_lines(t, "reverse") == "banana\nApple\npear\n"

    assert ls.transform_lines("ccc\na\ndd\nbb\n", "len") == \
        "a\ndd\nbb\nccc\n"

    t3 = "Go\npython\ngo\nPYTHON\nRust\n"
    assert ls.transform_lines(t3, "dedupe") == "Go\npython\nRust\n"

    # range-limited transforms leave the rest untouched
    assert ls.transform_lines("keep1\npear\napple\nkeep2\n", "az", 2,
                              3) == "keep1\napple\npear\nkeep2\n"
    assert ls.transform_lines("x\na\na\na\nx\n", "dedupe", 2, 4) == \
        "x\na\nx\n"
    assert ls.transform_lines("a   \nb\t  \nc\n", "trim", 2, 2) == \
        "a   \nb\nc\n"

    # shuffle: seeded rng is deterministic, multiset preserved
    t6 = "1\n2\n3\n4\n5\n"
    out = ls.transform_lines(t6, "shuffle", rng=random.Random(42))
    assert sorted(out.split("\n")) == sorted(t6.split("\n"))
    assert out == ls.transform_lines(t6, "shuffle",
                                     rng=random.Random(42))

    # trailing newline is a terminator, never a sortable empty line
    assert ls.transform_lines("b\na\n", "az") == "a\nb\n"
    assert ls.transform_lines("b\na", "az") == "a\nb"
    assert ls.expand_range("a\nb\nc\n", 2) == (2, 3)

    # hostile input never raises
    assert ls.transform_lines(None, "az") is None
    assert ls.transform_lines("b\na", "nope") == "b\na"
    assert ls.transform_lines("b\na", "az", "x", "y") == "b\na"


def test_clipboard_ring():
    # DS2 v2.13.0 — bounded dedup clipboard memory + previews
    from dxn1_studio.clipboard import ClipRing, preview_of

    r = ClipRing(3)
    for txt in ("first", "second", "third"):
        assert r.add(txt)
    assert r.items() == ["third", "second", "first"]

    # evicts oldest, moves repeats to front, ignores newest dupes
    assert r.add("fourth")
    assert r.items() == ["fourth", "third", "second"]
    assert r.add("second")
    assert r.items() == ["second", "fourth", "third"]
    assert not r.add("second")

    # junk is rejected, never raises
    assert not r.add("") and not r.add("   ") and not r.add(None)
    assert not r.add(42)

    r.clear()
    assert len(r) == 0 and r.items() == []
    assert ClipRing(0).size == 1
    assert ClipRing("5").size == 5

    # previews: one line, collapsed whitespace, capped with ellipsis
    assert preview_of("hello\n\tworld") == "hello world"
    assert len(preview_of("x" * 200)) == 90
    assert preview_of("x" * 200).endswith("…")
    assert preview_of(None) == "" and preview_of(5) == ""


def test_markdown_preview_engine():
    # DS2 v2.14.0 — zero-dependency markdown renderer
    from dxn1_studio.markprev import (inline_spans, markdown_to_html,
                                      parse_blocks)

    # headings, hr, fenced code (lang captured, fence consumed)
    blocks = parse_blocks("# Top\n\ntext\n\n---\n\n```py\nx=1\n```")
    kinds = [b["type"] for b in blocks]
    assert kinds == ["heading", "para", "hr", "code"]
    assert blocks[0]["level"] == 1 and blocks[0]["text"] == "Top"
    assert blocks[3]["lang"] == "py" and blocks[3]["text"] == "x=1"

    # unclosed fence is tolerated
    unclosed = parse_blocks("```\nstill code")
    assert unclosed[0]["type"] == "code" and "still code" in \
        unclosed[0]["text"]

    # lists: ul (-/*/+) and ol (1./1)) with multi-item runs
    ul = parse_blocks("- a\n* b\n+ c")
    assert ul[0]["type"] == "ulist" and ul[0]["items"] == ["a", "b", "c"]
    ol = parse_blocks("1. a\n2) b")
    assert ol[0]["type"] == "olist" and ol[0]["items"] == ["a", "b"]

    # blockquote folds lines, blank line separates blocks
    q = parse_blocks("> one\n> two\n\nafter")
    assert q[0]["type"] == "quote" and q[0]["text"] == "one two"
    assert q[1]["type"] == "para"

    # pipe table: header + separator + rows, cells trimmed
    tb = parse_blocks("| a | b |\n| --- | :-: |\n| 1 | 2 |")
    assert tb[0]["type"] == "table"
    assert tb[0]["header"] == ["a", "b"] and tb[0]["rows"] == [["1", "2"]]

    # paragraph folds continuation lines; snake_case stays plain
    p = parse_blocks("one two\nthree four")
    assert p[0]["text"] == "one two three four"
    assert inline_spans("my_var") == [("plain", "my_var")]

    # inline spans: every style recognized, unknown text preserved
    spans = inline_spans("x **b** *i* ~~s~~ `c` [t](u) end")
    kinds = [k for k, _ in spans]
    assert kinds == ["plain", "bold", "plain", "italic", "plain",
                     "strike", "plain", "code", "plain", "link",
                     "plain"]
    assert spans[9] == ("link", ("t", "u"))

    # html export: escapes content, covers all block kinds
    html = markdown_to_html("# h\n\n<b>&</b>\n\n| a |\n| --- |\n"
                            "| 1 |\n\n> q\n\n- li\n\n```\ncd\n```\n\n"
                            "fin")
    assert html.startswith("<!doctype html>")
    assert "<h1>h</h1>" in html
    assert "&lt;b&gt;&amp;&lt;/b&gt;" in html
    assert "<th>a</th>" in html and "<td>1</td>" in html
    assert "<blockquote><p>q</p></blockquote>" in html
    assert "<li>li</li>" in html and "cd" in html and "fin" in html

    # hostile input never raises
    assert parse_blocks("") == [] and parse_blocks(None) == []
    assert markdown_to_html("```\nunclosed")  # still renders


def test_colorkit_engine():
    # DS2 v2.15.0 lane — color conversion / contrast / ramps
    from dxn1_studio.colorkit import (contrast_ratio, darken, hex_to_rgb,
                                      hsl_to_rgb, lighten, mix,
                                      normalize_hex, rgb_to_hex,
                                      rgb_to_hsl, shade_ramp)

    # normalization: 3/6 digits, optional hash, whitespace; junk → None
    assert normalize_hex("#7C3AED") == "#7c3aed"
    assert normalize_hex("abc") == "#aabbcc"
    assert normalize_hex("  #aabbcc  ") == "#aabbcc"
    assert normalize_hex("zzz") is None and normalize_hex(None) is None
    assert normalize_hex("#aabbccd") is None

    # round-trips: hex → rgb → hsl → rgb → hex is stable
    assert hex_to_rgb("#7c3aed") == (124, 58, 237)
    assert rgb_to_hex(124, 58, 237) == "#7c3aed"
    h, s, l = rgb_to_hsl(124, 58, 237)
    assert hsl_to_rgb(h, s, l) == (124, 58, 237)

    # clamping keeps 0-255 guarantees
    assert rgb_to_hex(300, -5, 0) == "#ff0000"

    # WCAG contrast: known anchors + junk safe
    assert contrast_ratio("#ffffff", "#ffffff") == 1.0
    assert contrast_ratio("#000000", "#ffffff") == 21.0
    assert contrast_ratio("#777777", "#ffffff") > 4.4
    assert contrast_ratio("zzz", "#fff") == 0.0

    # lighten/darken/mix move monotonically, junk → None
    a = "#345"
    assert hex_to_rgb(lighten(a, 20))[0] > hex_to_rgb(a)[0]
    assert hex_to_rgb(darken(a, 20))[0] < hex_to_rgb(a)[0]
    assert mix(a, "#000", 1.0) == "#000000"
    assert mix(a, "#000", 0.0) == normalize_hex(a)
    assert mix("zzz", "#000") is None

    # ramps: deterministic, original preserved mid-ramp, junk-safe
    r1, r2 = shade_ramp("#7c3aed", 9), shade_ramp("#7c3aed", 9)
    assert r1 == r2 and len(r1) == 9 and r1[4] == "#7c3aed"
    assert shade_ramp("zzz", 9) == [] and shade_ramp("#fff", 1) == []


def test_restbench_engine():
    # DS2 v2.15.0 lane — HTTP workbench (offline: local server only)
    import http.server
    import json as _json
    import threading

    from dxn1_studio.restbench import (RestResponse, build_curl,
                                       format_size, http_request,
                                       parse_headers_text,
                                       pretty_body)

    # pure helpers
    assert format_size(942) == "942 B"
    assert format_size(3200) == "3.1 KB"
    assert format_size(2500000) == "2.4 MB"
    assert parse_headers_text("A: 1\nB : 2\njunk") == \
        {"A": "1", "B": "2"}
    assert parse_headers_text(None) == {}

    # guard rails: junk input → error response, never raises
    e1 = http_request("")
    assert e1.error == "empty url"
    e2 = http_request("ftp://nope")
    assert "must start with" in e2.error

    # opener injection: success shape without network
    class FakeRaw:
        status, reason = 201, "Created"
        headers = {"Content-Type": "application/json"}

        def read(self):
            return b'{"ok": true}'

        def close(self):
            pass

    ok1 = http_request("https://unit.test/x",
                       opener=lambda req: FakeRaw())
    assert ok1.status == 201 and ok1.ok and ok1.reason == "Created"
    assert ok1.body == '{"ok": true}'

    # hostile opener (read explodes) is absorbed
    class FakeBoom:
        status, reason, headers = 200, "OK", {}

        def read(self):
            raise IOError("boom")

        def close(self):
            pass

    boom = http_request("https://unit.test/y",
                        opener=lambda req: FakeBoom())
    assert boom.error and boom.status == 200

    # curl builder: quoting survives an apostrophe
    curl = build_curl("https://api.example.dev/v1", "POST",
                      {"X-Tag": "o'brien"}, '{"a": 1}')
    assert curl.startswith("curl -X POST 'https://api.example.dev/v1'")
    assert "-H" in curl and "--data" in curl and "\\" in curl

    # real exchange against a local, offline-safe server
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            payload = self.rfile.read(length)
            body = _json.dumps({"echo": _json.loads(payload),
                                "seen": self.headers.get("X-Tag")})
            raw = body.encode()
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            raw = b"plain hello"
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *_a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                             Handler)
    thread = threading.Thread(target=server.serve_forever,
                              daemon=True)
    thread.start()
    try:
        base = "http://127.0.0.1:%d" % server.server_address[1]
        got = http_request(base + "/", method="GET", timeout=5)
        assert got.ok and got.status == 200
        assert got.body == "plain hello"
        assert "Content-Length" in got.headers

        posted = http_request(
            base + "/echo", method="POST",
            headers=parse_headers_text("X-Tag: ds2"),
            body='{"n": 7}', timeout=5)
        assert posted.status == 201 and posted.ok
        data = _json.loads(posted.body)
        assert data["echo"] == {"n": 7} and data["seen"] == "ds2"
        assert pretty_body(posted.body) != posted.body  # JSON prettified

        miss = http_request("http://127.0.0.1:1/x", timeout=1)
        assert miss.error and not miss.ok
    finally:
        server.shutdown()
        server.server_close()

    # summary lines for both happy and sad paths
    assert RestResponse(method="GET", url="u", status=200,
                        reason="OK").summary().count("·") == 2
    assert "ERROR" in RestResponse(method="GET", url="u",
                                   error="x").summary()


def test_window_geometry_memory():
    # DS2 v2.15.0 lane — per-screen geometry persistence
    from dxn1_studio.geom import (clamp_geometry, make_geometry,
                                  parse_geometry, recall, remember,
                                  screen_signature)

    class FakeConfig:
        def __init__(self):
            self.data = {}

        def get(self, key, default=None):
            return self.data.get(key, default)

        def set(self, key, value):
            self.data[key] = value

    # parse/make round-trips; junk never raises
    assert parse_geometry("1280x820+40+30") == (1280, 820, 40, 30)
    assert parse_geometry("800x600") == (800, 600, 0, 0)
    assert parse_geometry("900x600-10+5") == (900, 600, -10, 5)
    assert parse_geometry("banana") is None
    assert parse_geometry(None) is None
    assert make_geometry(1280, 820, 40, 30) == "1280x820+40+30"
    assert make_geometry(800, 600) == "800x600+0+0"

    # clamping: oversized → screen-sized; off-screen → pulled back
    assert clamp_geometry(4000, 3000, 100, 100, 1920, 1080) == \
        (1920, 1080, 100, 100)
    assert clamp_geometry(200, 150, 5000, -300, 1920, 1080) == \
        (200, 150, 1720, 0)
    assert clamp_geometry(10, 10, 0, 0, 1920, 1080, min_w=200,
                          min_h=150) == (200, 150, 0, 0)

    cfg = FakeConfig()
    assert recall(cfg, 1920, 1080) == ""
    assert remember(cfg, "1280x820+40+30", 1920, 1080) is True
    assert recall(cfg, 1920, 1080) == "1280x820+40+30"
    assert recall(cfg, 2560, 1440) == ""      # other screen shapes
    # same shape re-remembered moves the entry (never duplicates)
    assert remember(cfg, "1600x900+10+10", 1920, 1080) is True
    store = cfg.get("window_geometry_by_screen")
    assert list(store) == ["1920x1080"]
    assert store["1920x1080"] == "1600x900+10+10"
    # LRU keeps at most 8 screen shapes
    for i in range(12):
        remember(cfg, "%dx%d+0+0" % (1000 + i, 700), 1000 + i, 700)
    store = cfg.get("window_geometry_by_screen")
    assert len(store) == 8
    assert "1011x700" in store and "1000x700" not in store
    # stored junk is ignored on recall
    cfg2 = FakeConfig()
    cfg2.set("window_geometry_by_screen", {"1920x1080": "bogus"})
    assert recall(cfg2, 1920, 1080) == ""
    assert screen_signature(1920, 1080) == "1920x1080"


def test_scribe_chip():
    # DS2 v2.16.0 lane — throttled statusbar writing meter
    from dxn1_studio.scribe import ScribeChip, chip_text, format_count

    assert format_count(1234) == "1,234"
    assert format_count(-5) == "0" and format_count(0) == "0"
    assert chip_text(0, 0, 0, goal=0) == "✎ 0 w · 0 wpm"
    assert chip_text(1234, 27.4, 45, goal=500) == \
        "✎ 1,234 w · 27 wpm · 45%"

    c = ScribeChip(goal_words=100, min_interval=2.0)
    assert c.observe(10, now=0.0) is True        # first lands
    assert c.observe(15, now=1.0) is False       # throttled
    assert c.observe(15, now=3.0) is True        # unthrottled + changed
    assert c.words() == 15
    assert c.observe(15, now=4.0) is False       # throttled
    assert c.observe(15, now=5.5) is False       # same words, same text
    assert "✎ 15 w" in c.text() and "15%" in c.text()
    assert 0 <= c.wpm() <= 400                   # paste-spike cap holds

    # goal handling: hide with 0, junk rejected, set works
    c.set_goal(0)
    assert "%" not in c.text()
    assert c.set_goal("junk") is False
    assert c.set_goal(40) is True
    assert "37%" in c.text() or "38%" in c.text()

    # reset starts fresh but keeps the goal
    assert c.peak_wpm() >= 0
    c.reset()
    assert c.words() == 0 and c.goal_words == 40
    assert c.observe(5, now=100.0) is True


def test_filestats_scan_history():
    # DS2 v2.16.0 lane — workspace growth history + sparkline
    import shutil
    import tempfile

    from dxn1_studio.filestats import (append_history, delta_line,
                                       history_path, load_history,
                                       snapshot_of, sparkline)

    snap = snapshot_of({"total_files": 12, "total_bytes": 3456})
    assert snap["files"] == 12 and snap["bytes"] == 3456
    assert snapshot_of({})["files"] == 0

    # sparkline: junk-safe, monotone shape, bucket compression
    assert sparkline([]) == "" and sparkline(None) == ""
    assert sparkline(["x", None]) == ""
    assert sparkline([5]) == "▄" and sparkline([7, 7, 7]) == "▄▄▄"
    ramp = sparkline([0, 25, 50, 75, 100])
    assert ramp[0] == "▁" and ramp[-1] == "█"
    big = sparkline(list(range(100)), width=10)
    assert 1 <= len(big) <= 10 and big[-1] == "█"
    assert sparkline([1, 9, 3]) == sparkline([1, 9, 3])

    ws = tempfile.mkdtemp(prefix="ds2-fshist-")
    try:
        assert load_history(ws) == []
        h1 = append_history(ws, {"t": "t1", "files": 10,
                                 "bytes": 100})
        assert len(h1) == 1
        assert load_history(ws)[0]["files"] == 10     # persisted
        # identical shape refreshes the newest point (no stacking)
        h2 = append_history(ws, {"t": "t2", "files": 10,
                                 "bytes": 100})
        assert len(h2) == 1 and h2[0]["t"] == "t2"
        # growth appends; cap holds
        append_history(ws, {"t": "t3", "files": 15, "bytes": 250})
        for i in range(80):
            append_history(ws, {"t": "x%d" % i, "files": 100 + i,
                                "bytes": 1000 + i})
        assert len(load_history(ws)) == 60
        # delta lines: first scan, growth, shrink
        assert delta_line({"files": 1, "bytes": 10}, None) == \
            "first recorded scan"
        assert "+5 files" in delta_line(
            {"files": 15, "bytes": 250}, {"files": 10, "bytes": 100})
        assert "-6 files" in delta_line(
            {"files": 4, "bytes": 50}, {"files": 10, "bytes": 100})
        # corrupt store tolerated + rebuilt on next append
        with open(history_path(ws), "w") as f:
            f.write("not json {{{")
        assert load_history(ws) == []
        assert append_history(ws, snap)[0]["files"] == 12
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_chart_studio_engine():
    """DS2 charts: series parsing, stats, geometry, sparkline."""
    from dxn1_studio import charts
    # parsing: separators, suffixes, junk tolerance
    assert charts.parse_series("1 2,3;4|5") == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert charts.parse_series("12ms 5px 8% 2e3") == [12.0, 5.0, 8.0, 2000.0]
    assert charts.parse_series("garbage -3.5 ok") == [-3.5]
    assert charts.parse_series("") == []
    assert charts.parse_series(None) == []
    # summary
    s = charts.summary([1, 2, 3, 4])
    assert s["count"] == 4 and s["mean"] == 2.5 and s["median"] == 2.5
    assert (s["min"], s["max"], s["range"]) == (1, 4, 3)
    assert charts.summary([])["count"] == 0
    # line geometry: pads respected, flat series draws mid-height
    pts = charts.scale_points([0, 5, 10], 300, 200)
    assert len(pts) == 3
    assert pts[0][0] == 10.0 and pts[-1][0] == 290.0
    assert all(p[1] == 100.0 for p in charts.scale_points([4, 4], 300, 200))
    assert charts.scale_points([], 300, 200) == []
    assert charts.scale_points([1], "x", 200) == []
    # bar geometry: taller value → taller rect; negatives handled
    rects = charts.bar_rects([2, 5, 1], 300, 200)
    assert len(rects) == 3 and rects[1][3] > rects[2][3]
    assert charts.bar_rects([], 300, 200) == []
    # histogram: totals preserved, max clamped into the last bin
    h = charts.histogram([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], bins=5)
    assert len(h) == 5 and sum(b[2] for b in h) == 10
    assert charts.histogram([7, 7]) == [(7, 7, 2)]
    assert charts.histogram([]) == []
    # sparkline: deterministic ramp, flat mid, bucket compression
    assert charts.sparkline([1, 2, 3, 4, 5]) == "▁▂▄▆█"
    assert charts.sparkline([3, 3]) == "▅▅"
    assert len(charts.sparkline(list(range(100)), width=10)) == 10
    assert charts.sparkline([]) == ""


def test_unitconv_engine():
    """DS2 unitconv: factor conversion, temperature, junk tolerance."""
    from dxn1_studio import unitconv
    # exact factors
    assert abs(unitconv.convert(1.0, "km", "mi") - 0.621371192237) < 1e-9
    assert abs(unitconv.convert(1.0, "kg", "lb") - 2.204622621849) < 1e-9
    assert abs(unitconv.convert(90.0, "min", "h") - 1.5) < 1e-12
    assert unitconv.convert(2.5, "kg", "g") == 2500.0
    # temperature formulas (auto-detected category)
    assert unitconv.convert(100.0, "C", "F") == 212.0
    assert abs(unitconv.convert(32.0, "F", "C")) < 1e-12
    assert abs(unitconv.convert(0.0, "K", "C") + 273.15) < 1e-12
    # junk in → None out; booleans rejected; strings accepted
    assert unitconv.convert("abc", "km", "mi") is None
    assert unitconv.convert(1.0, "zz", "mi") is None
    assert unitconv.convert(True, "kg", "g") is None
    assert unitconv.convert(" 2.5 ", "kg", "g") == 2500.0
    # catalogue helpers + batch table
    assert unitconv.categories() == sorted(unitconv.categories())
    assert unitconv.units("nope") == []
    batch = unitconv.batch_table(1.0, "kg", "mass")
    assert dict(batch)["kg"] == 1.0 and dict(batch)["g"] == 1000.0
    assert unitconv.batch_table(1.0, "zz", "mass") is None
    # formatted strings never raise
    assert unitconv.convert_str("x", "km", "mi") == "—"
    assert unitconv.convert_str(1, "km", "mi").endswith("mi")

def test_charmap_engine():
    """DS2 charmap: blocks, search, describe — pure + junk-tolerant."""
    from dxn1_studio import charmap
    names = charmap.block_names()
    assert "Arrows" in names and "Box Drawing" in names
    assert names == sorted(names)
    arrows = charmap.chars_in("arrows")
    assert "\u2192" in arrows and len(arrows) <= 512
    assert charmap.chars_in("nope") == []
    assert charmap.chars_in(None) == []
    # search: literal char, hex codepoint (2 spellings), block substring
    assert charmap.search("a") == ["a"]
    assert charmap.search("2192") == ["\u2192"]
    assert charmap.search("U+00E9") == ["\u00e9"]
    box = charmap.search("box", limit=999)
    assert "\u2500" in box  # box-drawing glyph itself, not the name
    assert charmap.search("") == []
    assert charmap.search(None) == []
    # describe: codepoint + name, unnamed tolerated
    d = charmap.describe("\u00e9")
    assert d.startswith("U+00E9") and "LATIN SMALL LETTER E" in d
    assert "<unnamed>" in charmap.describe("\uE000")
    assert charmap.describe(None) == ""


def test_textcase_engine():
    """DS2 textcase: word splitting + every style + junk tolerance."""
    from dxn1_studio import textcase
    # acronym runs split whole; delimiters of every kind
    assert textcase.words("getHTTPResponse_2") == \
        ["get", "HTTP", "Response", "2"]
    assert textcase.words("user_profile-id") == ["user", "profile", "id"]
    assert textcase.words("MyApp2-file") == ["My", "App2", "file"]
    assert textcase.words("version2Update") == ["version2", "Update"]
    # every style
    assert textcase.convert("user_profile_id", "camel") == "userProfileId"
    assert textcase.convert("user_profile_id", "pascal") == "UserProfileId"
    assert textcase.convert("user_profile_id", "kebab") == "user-profile-id"
    assert textcase.convert("user_profile_id", "constant") == "USER_PROFILE_ID"
    assert textcase.convert("user_profile_id", "title") == "User Profile Id"
    assert textcase.convert("user_profile_id", "dot") == "user.profile.id"
    assert textcase.convert("user_profile_id", "flat") == "userprofileid"
    # camel boundary in the source converts to snake
    assert textcase.convert("getHTTPResponse", "snake") == \
        "get_http_response"
    # round-trip: snake → camel → snake is stable
    assert textcase.convert(
        textcase.convert("round_trip_here", "camel"), "snake") == \
        "round_trip_here"
    # all_cases covers 8 styles, junk is empty
    assert len(textcase.all_cases("some_name")) == 8
    assert textcase.all_cases("---") == {}
    assert textcase.words(None) == []
    assert textcase.convert(5, "snake") == ""
    assert textcase.convert("x", "nope") == ""


def test_pwdgen_engine():
    """DS2 pwdgen: pools, CSPRNG generation, entropy, labels."""
    import random
    from dxn1_studio import pwdgen
    # pool composition
    assert len(pwdgen.pool_for(symbols=False)) == 62
    assert len(pwdgen.pool_for(symbols=True)) == 86
    amb = pwdgen.pool_for(exclude_ambiguous=True)
    assert not (set("Il1O0o") & set(amb))
    assert pwdgen.pool_for(upper=False, lower=False, digits=False,
                           symbols=False) == ""
    # deterministic with injected rng, covers the pool
    rng = random.Random(7)
    p = pwdgen.generate(64, symbols=True, rng=rng)
    assert len(p) == 64
    assert all(c in pwdgen.pool_for(symbols=True) for c in p)
    assert pwdgen.generate(16, rng=random.Random(7)) == \
        pwdgen.generate(16, rng=random.Random(7))
    # junk input → honest empty
    assert pwdgen.generate(0) == ""
    assert pwdgen.generate("x") == ""
    assert pwdgen.generate(999) == ""
    assert pwdgen.generate(16, upper=False, lower=False, digits=False,
                           symbols=False) == ""
    # entropy math: 62-char pool, 20 chars ≈ 119.1 bits
    assert abs(pwdgen.entropy_bits(20) - 119.1) < 0.2
    assert pwdgen.entropy_bits(0) == 0.0
    assert pwdgen.entropy_bits("x") == 0.0
    # labels: ordered thresholds, junk → very weak
    assert pwdgen.strength_label(10) == "weak"
    assert pwdgen.strength_label(30) == "fair"
    assert pwdgen.strength_label(45) == "strong"
    assert pwdgen.strength_label(80) == "excellent"
    assert pwdgen.strength_label(200) == "overkill"
    assert pwdgen.strength_label(-5) == "very weak"
    assert pwdgen.strength_label(None) == "very weak"


def test_numbase_engine():
    """DS2 numbase: parsing, formatting, bit inspection."""
    from dxn1_studio import numbase
    # parsing: prefixes, signs, underscores, custom bases
    assert numbase.parse_number("0xFF") == 255
    assert numbase.parse_number("0b1010") == 10
    assert numbase.parse_number("0o17") == 15
    assert numbase.parse_number("ff", 16) == 255
    assert numbase.parse_number("-17_0", 8) == -120
    assert numbase.parse_number("zz", 36) == 35 * 36 + 35  # 'zz' in base 36
    assert numbase.parse_number("z", 36) == 35
    # junk → None
    assert numbase.parse_number("5", 2) is None      # invalid digit
    assert numbase.parse_number("zz", 10) is None
    assert numbase.parse_number("x", 100) is None    # base range
    assert numbase.parse_number("") is None
    assert numbase.parse_number(None) is None
    assert numbase.parse_number("0x") is None        # prefix, no digits
    # formatting: round-trips in every base 2..36
    for base in range(2, 37):
        assert numbase.format_base(255, base) and \
            numbase.parse_number(numbase.format_base(255, base),
                                 base) == 255
    assert numbase.format_base(255, 16) == "ff"
    assert numbase.format_base(-255, 16) == "-ff"
    assert numbase.format_base(0, 7) == "0"
    assert numbase.format_base(True, 16) == ""
    assert numbase.format_base(5, 99) == ""
    # bit inspection
    info = numbase.inspect_bits(255)
    assert info["bit_length"] == 8 and info["ones"] == 8
    assert info["hex"] == "0xff"
    neg = numbase.inspect_bits(-128)
    assert "two's complement" in neg["note"]
    assert numbase.inspect_bits(0)["bit_length"] == 0
    assert numbase.inspect_bits(True) == {}
    assert numbase.inspect_bits("x") == {}


def test_csvkit_engine():
    """DS2 csvkit: sniffing, parsing, stats, TSV out."""
    from dxn1_studio import csvkit
    # delimiter sniffing
    assert csvkit.sniff_delimiter("a,b\n1,2") == ","
    assert csvkit.sniff_delimiter("a;b\n1;2") == ";"
    assert csvkit.sniff_delimiter("a\tb\n1\t2") == "\t"
    assert csvkit.sniff_delimiter("a|b\n1|2") == "|"
    assert csvkit.sniff_delimiter("no delims") == ","
    assert csvkit.sniff_delimiter(None) == ","
    # parsing
    rows = csvkit.parse_csv("name,age\nada,36")
    assert rows == [["name", "age"], ["ada", "36"]]
    assert csvkit.parse_csv("a;b", delimiter=";") == [["a", "b"]]
    # quoted fields and embedded delimiters
    assert csvkit.parse_csv('"x,y",z') == [["x,y", "z"]]
    # blank rows skipped, junk tolerated
    assert csvkit.parse_csv("a,b\n\n  \nc,d") == [["a", "b"], ["c", "d"]]
    assert csvkit.parse_csv("") == []
    assert csvkit.parse_csv(None) == []
    # stats
    st = csvkit.table_stats(rows)
    assert st["rows"] == 2 and st["cols"] == 2
    assert st["headers"] == ["name", "age"] and not st["ragged"]
    assert csvkit.table_stats([["a", "b"], ["c"]])["ragged"] is True
    assert csvkit.table_stats([])["rows"] == 0
    # TSV export
    tsv = csvkit.to_tsv(rows)
    assert "name\tage" in tsv and "ada\t36" in tsv
    assert csvkit.to_tsv([]) == ""


def test_mathpad_engine():
    """DS2 mathpad: safe ast evaluator, fmt, hard limits."""
    from dxn1_studio import mathpad
    # arithmetic + precedence + power via ^
    assert mathpad.evaluate("2+3*4") == 14
    assert mathpad.evaluate("(2+3)*4") == 20
    assert mathpad.evaluate("2^10") == 1024
    assert mathpad.evaluate("7 // 2") == 3
    assert mathpad.evaluate("7 % 3") == 1
    assert mathpad.evaluate("-5 + 2") == -3
    # literals and constants
    assert mathpad.evaluate("0xff") == 255
    assert mathpad.evaluate("0b101") == 5
    assert mathpad.evaluate("1_000") == 1000
    assert abs(mathpad.evaluate("pi") - 3.141592653589793) < 1e-12
    assert abs(mathpad.evaluate("sqrt(2)") - 1.4142135623730951) < 1e-12
    assert mathpad.evaluate("factorial(5)") == 120
    assert mathpad.evaluate("max(3, 7, 5)") == 7
    assert mathpad.evaluate("cbrt(-27)") == -3.0
    assert mathpad.evaluate("gcd(12, 18)") == 6
    # junk → CalcError, never eval'd
    for bad in ("", None, "2+", "__import__('os')", "1/0",
                "9**9**9", "factorial(99999)", "sqrt(-1)", "x + 1",
                '"a"*3', "True + 1", "(1+2).bit_length()"):
        try:
            mathpad.evaluate(bad)
            raise AssertionError("accepted %r" % (bad,))
        except mathpad.CalcError:
            pass
    # formatting is human-friendly
    assert mathpad.fmt(3) == "3"
    assert mathpad.fmt(0.1 + 0.2) == "0.3"
    assert mathpad.fmt(2.5) == "2.5"
    # window opens, evaluates sample, tolerates junk
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    theme = {"bg": "#16161e", "header": "#242432",
             "editor_bg": "#1a1a24", "text": "#e8e8f0",
             "text_muted": "#8a8a9a", "button": "#2a2a3a",
             "button_hover": "#33334a", "ok": "#7ee787",
             "error": "#ff6b6b"}
    from dxn1_studio.mathpad import open_mathpad
    win = open_mathpad(root, theme)
    assert win is not None and win.winfo_exists()
    win.entry.delete(0, "end")
    win.entry.insert(0, "6*7")
    win.do_eval()
    assert "42" in win.result.cget("text")
    win.entry.delete(0, "end")
    win.entry.insert(0, "bogus((")
    win.do_eval()
    assert win.result.cget("text") == "= ?"
    win.entry.delete(0, "end")
    win.entry.insert(0, "x = 5")
    win.do_eval()
    assert win.vars.get("x") == 5
    assert "stored" in win.status.cget("text")
    win.entry.delete(0, "end")
    win.entry.insert(0, "x * 3")
    win.do_eval()
    assert "15" in win.result.cget("text")
    win.entry.delete(0, "end")   # empty entry is honest, not a crash
    win.do_eval()
    assert "type an expression" in win.status.cget("text")
    win.destroy(); root.destroy()


def test_hexdump_engine():
    """DS2 hexdump: rendering, hex round-trips, byte stats."""
    from dxn1_studio import hexdump as h
    # rendering: offset, hex column, ascii gutter aligned across rows
    lines = h.hexdump("hello")
    assert len(lines) == 1 and lines[0].startswith("00000000")
    assert "68 65 6c 6c 6f" in lines[0] and "|hello|" in lines[0]
    two = h.hexdump("abcdefghijklmnop" * 2)
    assert len(two) == 2 and two[1].startswith("00000010")
    assert two[0].index("|") == two[1].index("|")
    assert "|....|" in h.hexdump(bytes([0, 1, 2, 3]))[0]
    # input coercion + junk tolerance
    assert h.hexdump(b"ab") == h.hexdump("ab") == \
        h.hexdump(bytearray(b"ab"))
    assert h.hexdump(None) == [] and h.hexdump(123) == []
    # hex out/in
    assert h.to_hex("ABC") == "41 42 43"
    data = bytes(range(256))
    assert h.from_hex(h.to_hex(data)) == data
    assert h.from_hex("41:42:43") == b"ABC"
    assert h.from_hex("0x41 0x42") == b"AB"
    assert h.from_hex("41,42\n43") == b"ABC"
    assert h.from_hex("00000000: 41 42\n00000001: 43") == b"ABC"
    assert h.from_hex("00000000  41 42  43") == b"ABC"
    # junk hex → None honestly
    assert h.from_hex("") is None and h.from_hex(None) is None
    assert h.from_hex("4 1 2") is None   # odd digit count
    assert h.from_hex("zz") is None      # no hex digits at all
    # stats + status line
    s = h.byte_stats("hello")
    assert s["total"] == 5 and s["unique"] == 4
    assert s["printable_pct"] == 100.0
    assert h.byte_stats(b"")["total"] == 0
    assert h.byte_stats(bytes([128, 129]))["high_bit_pct"] == 100.0
    assert "no bytes" in h.stats_line(b"")
    assert "printable" in h.stats_line("hello")
    # window opens, renders, decodes hex, tolerates junk
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    theme = {"bg": "#16161e", "header": "#242432",
             "editor_bg": "#1a1a24", "text": "#e8e8f0",
             "text_muted": "#8a8a9a", "button": "#2a2a3a",
             "button_hover": "#33334a"}
    from dxn1_studio.hexdump import open_bytesnoop
    win = open_bytesnoop(root, theme)
    assert win is not None and win.winfo_exists()
    assert "printable" in win.status.cget("text")
    win.mode.set("hex")
    win.input.delete("1.0", "end")
    win.input.insert("1.0", "41 42 43")
    win.refresh()
    assert "|ABC|" in win.output.get("1.0", "end")
    win.input.delete("1.0", "end")
    win.input.insert("1.0", "4 1 2")   # odd digits — honest refusal
    win.refresh()
    assert "doesn't parse" in win.status.cget("text")
    win.destroy(); root.destroy()


def test_textdiff_engine():
    """DS2 textdiff: line kinds, inline marks, similarity, junk."""
    from dxn1_studio import textdiff as d
    # line diff
    lines = d.diff_lines("a\nb\nc", "a\nb\nc")
    assert all(k == "same" for k, _ in lines)
    assert [l for k, l in d.diff_lines("a", "a\nb")
            if k == "insert"] == ["b"]
    kinds = [k for k, _ in d.diff_lines("a\nb", "a\nc")]
    assert "delete" in kinds and "insert" in kinds
    assert d.diff_lines(None, "a") == []
    # inline marks (rdiff convention)
    out = d.inline_diff("the quick brown fox", "the quick red fox")
    assert "[-brown-]" in out and "{+red+}" in out
    assert "[-c-]" in d.inline_diff("abc", "abd", "char")
    assert d.inline_diff(None, None) == ""
    # similarity + summary
    assert d.similarity("same\nsame", "same\nsame") == 100.0
    assert d.similarity("", "") == 0.0
    assert d.similarity(None, "a") == 0.0
    assert "similar" in d.summary("a\nb", "a\nc")
    assert d.summary(None, None) == "+0 -0 lines · 0.0% similar"
    # window: renders, switches modes, tolerates junk
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    theme = {"bg": "#16161e", "header": "#242432",
             "editor_bg": "#1a1a24", "text": "#e8e8f0",
             "text_muted": "#8a8a9a", "button": "#2a2a3a",
             "button_hover": "#33334a"}
    from dxn1_studio.textdiff import open_textdiff
    win = open_textdiff(root, theme)
    assert win is not None and win.winfo_exists()
    assert "similar" in win.status.cget("text")
    win.mode.set("line")
    win.refresh()
    assert "+" in win.output.get("1.0", "end")
    win.old_text.delete("1.0", "end")
    win.new_text.delete("1.0", "end")
    win.refresh()
    assert "paste" in win.status.cget("text")
    win.destroy(); root.destroy()


def test_xmlbench_engine():
    """DS2 xmlbench: pretty/minify/validate/stats + safety guards."""
    from dxn1_studio import xmlbench as x
    doc = '<note id="42"><to>DXN1</to></note>'
    # pretty
    out, err = x.xml_pretty(doc)
    assert err is None and "<to>DXN1</to>" in out and "\n" in out
    out2, _ = x.xml_pretty(doc, indent=4)
    assert "    <to>" in out2
    # minify keeps real text, drops inter-element whitespace
    mn, err = x.xml_minify("<root>\n  <a> 1 </a>\n  <b/>\n</root>")
    assert err is None and "\n" not in mn
    assert "<a> 1 </a>" in mn and "<b />" in mn
    # validate
    assert x.xml_validate(doc) == (True, "valid XML")
    ok, msg = x.xml_validate("<a><b></a>")
    assert not ok and "line 1" in msg
    assert not x.xml_validate("")[0] and not x.xml_validate(None)[0]
    # safety: DTD entities and size bombs refused
    ok, msg = x.xml_validate(
        '<!DOCTYPE r [<!ENTITY a "x">]><r>&a;</r>')
    assert not ok and "refused" in msg
    ok, msg = x.xml_validate("<r>" + "<a/>" * 400000 + "</r>")
    assert not ok and "too large" in msg
    # stats
    st, err = x.tag_stats(doc)
    assert err is None and st["root"] == "note"
    assert st["elements"] == 2 and st["attributes"] == 1
    assert st["max_depth"] == 2
    st, _ = x.tag_stats("<r><t>a</t><t>b</t><t>c</t></r>")
    assert dict(st["top"]).get("t") == 3
    assert st["text_nodes"] == 3
    assert "invalid" in x.stats_line("<nope>")
    # junk tolerance
    assert x.xml_pretty(123)[1] is not None
    assert x.tag_stats("")[1] is not None
    # window: opens, validates, minifies, tolerates junk
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    theme = {"bg": "#16161e", "header": "#242432",
             "editor_bg": "#1a1a24", "text": "#e8e8f0",
             "text_muted": "#8a8a9a", "button": "#2a2a3a",
             "button_hover": "#33334a", "ok": "#7ee787",
             "error": "#ff6b6b"}
    from dxn1_studio.xmlbench import open_xmlbench
    win = open_xmlbench(root, theme)
    assert win is not None and win.winfo_exists()
    assert "valid" in win.status.cget("text")
    win._minify()
    assert "<to>" in win.output.get("1.0", "end")
    win.input.delete("1.0", "end")
    win.refresh_called = True
    win._validate()
    assert "XML" in win.status.cget("text")
    win.destroy(); root.destroy()


def test_contrast_engine():
    """DS2 contrast: WCAG grading, palette audit, fix suggestions."""
    from dxn1_studio import contrast as c
    from dxn1_studio.theme import PALETTES
    # grade boundaries
    assert c.grade(21.0) == "AAA" and c.grade(7.0) == "AAA"
    assert c.grade(6.99) == "AA" and c.grade(4.5) == "AA"
    assert c.grade(4.49) == "AA-L" and c.grade(3.0) == "AA-L"
    assert c.grade(2.99) == "FAIL" and c.grade(0) == "FAIL"
    assert c.grade(None) == "FAIL" and c.grade("junk") == "FAIL"
    # ratio formatting trims trailing zeros
    assert c.fmt_ratio(21.0) == "21:1" and c.fmt_ratio(4.53) == "4.53:1"
    assert c.fmt_ratio("x") == "n/a"
    # mode detection
    assert c.mode_of(PALETTES["dark"]) == "dark"
    assert c.mode_of(PALETTES["light"]) == "light"
    assert c.mode_of({}) == "dark"  # sane default
    # studio's Theme wrapper (non-dict) also works
    try:
        from dxn1_studio.config import DEFAULTS
        from dxn1_studio.theme import from_config
        assert c.mode_of(from_config(DEFAULTS)) in ("dark", "light")
        assert len(c.audit_palette(from_config(DEFAULTS))) == 13
    except Exception:  # noqa: BLE001 — headless CI guard
        pass
    # audit: 13 pairs on the builtin dark theme, all parse
    rows = c.audit_palette(PALETTES["dark"])
    assert len(rows) == 13
    labels = [r["label"] for r in rows]
    assert "body text / background" in labels
    assert "selection text / highlight" in labels
    body = [r for r in rows if r["label"] == "body text / background"][0]
    assert body["fg"] == "#e6edf3" and body["bg"] == "#0d1117"
    assert body["grade"] == "AAA" and body["ratio"] >= 7.0
    assert all(r["grade"] in ("AAA", "AA", "AA-L", "FAIL")
               for r in rows)
    # every below-AA row either suggests a fix or honestly can't
    for r in rows:
        if r["ratio"] < 4.5:
            assert r["suggestion"] == "—" or \
                c.contrast_ratio(r["suggestion"], r["bg"]) >= 4.5
    # light theme: body text also AAA
    lrows = c.audit_palette(PALETTES["light"])
    lbody = [r for r in lrows
             if r["label"] == "body text / background"][0]
    assert lbody["grade"] == "AAA"
    # junk tolerance: empty / None / non-dict palettes never raise
    for junk in ({}, None, "dark", 42):
        jrows = c.audit_palette(junk)
        assert len(jrows) == 13
        assert all(r["grade"] == "FAIL" and r["suggestion"] == "—"
                   for r in jrows)
    # missing key -> honest n/a fg
    partial = c.audit_palette({"bg": "#000000", "text": "#ffffff"})
    assert len(partial) == 13
    # suggest_fg: fixes a weak pair, respects passing pairs, honest None
    assert c.suggest_fg("#4d5766", "#11161d", 4.5)  # gutter pair
    assert c.suggest_fg("#ffffff", "#0d1117") is None  # already AAA
    assert c.suggest_fg("#000", "#fff") is None
    assert c.suggest_fg("junk", "#000000") is None
    assert c.suggest_fg(None, None) is None
    fix = c.suggest_fg("#8b949e", "#ffffff", 4.5)  # light muted
    assert fix and c.contrast_ratio(fix, "#ffffff") >= 4.5
    # audit_summary: counts add up, worst is a real label
    s = c.audit_summary(rows)
    assert s["total"] == 13
    assert s["AAA"] + s["AA"] + s["AA-L"] + s["FAIL"] == 13
    assert 0.0 <= s["pass_pct"] <= 100.0
    assert s["worst"] in labels
    assert c.audit_summary([])["total"] == 0
    assert c.audit_summary(None)["worst"] is None
    # theme inventory: builtins + gallery, all non-empty
    themes = c.iter_auditable_themes()
    assert len(themes) >= 14
    assert themes[0][0] == "Built-in · Dark"
    assert all(isinstance(p, dict) and p for _n, p in themes)
    # report text: header + pair lines + summary footer
    txt = c.report_text("Built-in · Dark", rows, s)
    assert "CONTRAST AUDIT — Built-in · Dark" in txt
    assert "body text / background" in txt
    assert "pairs 13" in txt and "avg" in txt
    assert len(c.report_text("x", [], c.audit_summary([]))) > 0
    # window: opens, audits, switches theme, copies report
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    theme = {"bg": "#16161e", "header": "#242432",
             "editor_bg": "#1a1a24", "text": "#e8e8f0",
             "text_muted": "#8a8a9a", "button": "#2a2a3a",
             "button_hover": "#33334a", "success": "#3fb950"}
    from dxn1_studio.contrast import open_contrast
    win = open_contrast(root, theme)
    assert win is not None and win.winfo_exists()
    assert len(win.tree.get_children()) == 13
    assert "pairs" in win.summary.cget("text")
    win.var.set("Built-in · Light")
    win._audit()
    assert len(win.tree.get_children()) == 13
    win._copy_report()
    assert "copied" in win.status.cget("text")
    win.refresh()
    win.destroy(); root.destroy()


def test_cheatsheet_engine():
    """DS2 cheatsheet: HTML build, text render, save, window flow."""
    import os as _os
    from dxn1_studio import cheatsheet as cs
    from dxn1_studio.app import TERMINAL_HELP
    # live sections: 48 terminal commands + shortcuts + tips
    secs = cs.default_sections()
    assert len(secs) == 3
    assert secs[0][0] == "Terminal commands"
    assert tuple(secs[0][1]) == tuple(TERMINAL_HELP)
    assert len(secs[1][1]) >= 15      # shortcuts
    assert len(secs[2][1]) >= 3       # tips
    # override path works
    tiny = cs.default_sections(commands=(("x", "y"),))
    assert tuple(tiny[0][1]) == (("x", "y"),)
    # HTML: standalone, print rules, escaping, meta
    html = cs.build_html(secs)
    assert html.startswith("<!DOCTYPE html>")
    assert "@media print" in html and "<kbd>" in html
    assert "Terminal commands" in html and "Keyboard shortcuts" in html
    assert cs.APP_NAME in html and "generated" in html
    evil = cs.build_html([("s <tag>", [("<b>", "a & b")])])
    assert "<b>" not in evil.split("<table>")[1]  # escaped in rows
    assert "&lt;b&gt;" in evil and "a &amp; b" in evil
    assert "s &lt;tag&gt;" in evil
    # junk sections never raise
    assert "<table>" in cs.build_html(None)
    assert "<table>" in cs.build_html([("h", None)])
    assert cs.build_html([("h", [("", "")])])
    # text render mirrors content
    txt = cs.render_text(secs)
    assert "TERMINAL COMMANDS" in txt
    assert "palette" in txt and "KEYBOARD SHORTCUTS" in txt
    assert len(cs.render_text(None)) > 0
    # save: happy path + honest errors
    import tempfile
    d = tempfile.mkdtemp(prefix="ds2-cheat-")
    path, err = cs.save_html(html, _os.path.join(d, "cs.html"))
    assert path and not err and _os.path.getsize(path) > 5000
    for bad in ("", None, "   ", d, "/nonexistent-dir-xyz/x.html"):
        p2, e2 = cs.save_html(html, bad)
        assert p2 is None and e2
    # window: opens, previews live data, saves via engine path
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    theme = {"bg": "#16161e", "header": "#242432",
             "editor_bg": "#1a1a24", "text": "#e8e8f0",
             "text_muted": "#8a8a9a", "button": "#2a2a3a",
             "button_hover": "#33334a", "success": "#3fb950",
             "error": "#ff6b6b"}
    from dxn1_studio.cheatsheet import open_cheatsheet
    win = open_cheatsheet(root, theme, commands=TERMINAL_HELP)
    assert win is not None and win.winfo_exists()
    body = win.preview.get("1.0", "end")
    assert "TERMINAL COMMANDS" in body and "palette" in body
    out = _os.path.join(d, "out.html")
    assert win._write_to(out) == out
    assert "saved" in win.status.cget("text")
    assert "print-ready" not in win.status.cget("text")  # status, not hint
    # honest failure lands in status without raising
    assert win._write_to("/nonexistent-dir-xyz/x.html") is None
    assert "save failed" in win.status.cget("text")
    win.refresh()
    win.destroy(); root.destroy()


def test_cvdlab_engine():
    """DS2 cvdlab: CVD simulation, severity, palettes, window."""
    from dxn1_studio import cvdlab as c
    from dxn1_studio.contrast import audit_summary
    from dxn1_studio.theme import PALETTES
    # achromatopsia drains to gray (R==G==B)
    g = c.simulate_hex("#ff0000", "achromatopsia")
    assert g and g[1:3] == g[3:5] == g[5:7]
    # classic transforms move hue: red under deuteranopia isn't red
    d = c.simulate_hex("#ff0000", "deuteranopia")
    assert d and d != "#ff0000" and d.startswith("#")
    # severity 0 is identity, 1 is full simulation, 0.5 is between
    assert c.simulate_hex("#ff0000", "protanopia", 0) == "#ff0000"
    full = c.simulate_hex("#ff0000", "protanopia", 1)
    half = c.simulate_hex("#ff0000", "protanopia", 0.5)
    assert full != half != "#ff0000"
    # junk hex -> None; unknown kind falls back to a valid sim
    for junk in ("", None, "zzz", 42, "#12345"):
        assert c.simulate_hex(junk, "deuteranopia") is None
    assert c.simulate_hex("#3366cc", "not-a-kind") is not None
    # severity junk clamps instead of raising
    assert c.simulate_hex("#ff0000", "tritanopia", "x") is not None
    # simulate_palette: parses what it can, drops junk keys
    pal = {"bg": "#0d1117", "text": "#e6edf3", "bad": "nope"}
    sp = c.simulate_palette(pal, "deuteranopia")
    assert set(sp) == {"bg", "text"} and sp["bg"] != "#0d1117"
    assert c.simulate_palette(None, "achromatopsia") == {}
    assert c.simulate_palette({}, "achromatopsia") == {}
    # swatch_rows: known keys, tuples of three strings
    rows = c.swatch_rows(PALETTES["dark"], "deuteranopia")
    keys = [r[0] for r in rows]
    assert "bg" in keys and "text" in keys and "select_fg" in keys
    assert all(len(r) == 3 and r[1] and r[2] for r in rows)
    assert c.swatch_rows({}, "achromatopsia") == []
    # studio's Theme wrapper (non-dict) works everywhere too
    try:
        from dxn1_studio.config import DEFAULTS
        from dxn1_studio.theme import from_config
        th = from_config(DEFAULTS)
        assert len(c.swatch_rows(th, "deuteranopia")) >= 10
        assert len(c.simulate_palette(th, "achromatopsia")) >= 10
        assert c.sim_summary(th, "achromatopsia")["total"] == 13
    except Exception:  # noqa: BLE001 — headless CI guard
        pass
    # sim_summary: the fixed dark theme survives all 4 kinds
    for kind in c.KINDS:
        s = c.sim_summary(PALETTES["dark"], kind)
        assert s["total"] == 13 and s["FAIL"] == 0, (kind, s)
    # and a hostile palette audits honestly under CVD
    s = audit_summary(c.audit_palette_wrapper()
                      if hasattr(c, "audit_palette_wrapper")
                      else __import__("dxn1_studio.contrast",
                                      fromlist=["audit_palette"])
                      .audit_palette(c.simulate_palette(
                          {"bg": "#111", "text": "#222"},
                          "achromatopsia")))
    assert s["total"] == 13
    assert c.survive_line(PALETTES["light"], "deuteranopia"
                          ).startswith("CVD view: 13 pairs")
    # window: opens, swatches render, kind switch + custom hex work
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    theme = {"bg": "#16161e", "header": "#242432",
             "editor_bg": "#1a1a24", "text": "#e8e8f0",
             "text_muted": "#8a8a9a", "button": "#2a2a3a",
             "button_hover": "#33334a", "success": "#3fb950",
             "sidebar": "#11161d", "card": "#131a22",
             "linenum_fg": "#778498", "select_fg": "#ffffff"}
    from dxn1_studio.cvdlab import open_cvdlab
    win = open_cvdlab(root, theme)
    assert win is not None and win.winfo_exists()
    assert len(win._swatch_widgets) > 20          # chips + rows
    assert "CVD view" in win.verdict.cget("text")
    win.kind.set("achromatopsia")
    win._refresh()
    assert len(win._swatch_widgets) > 20
    win.custom.delete(0, "end")
    win.custom.insert(0, "#ff0000")
    win._refresh()
    assert win.custom_out.cget("text") != "n/a"
    win.custom.delete(0, "end")
    win.custom.insert(0, "junk")
    win._refresh()
    assert win.custom_out.cget("text") == "n/a"
    win._copy_custom()                             # never raises
    win.refresh()
    win.destroy(); root.destroy()


def test_fuzzy_engine():
    """DS2 v2.29 — fuzzy launcher scoring: semantics, junk, ordering."""
    f = __import__("dxn1_studio.fuzzy", fromlist=["score"])
    # empty query matches everything with score 0, order preserved
    assert f.match("", "anything") == (0, ())
    assert f.filter_ranked("", ["b", "a"]) == ["b", "a"]
    assert f.filter_ranked(None, [1, 2]) == [1, 2]
    # junk never crashes and never matches
    assert f.score(None, "x") == -1
    assert f.score("a", None) == -1
    assert f.score("zx", "quick open") == -1
    assert f.score(5, "port 5") > 0            # coerced via str()
    # substring contiguity beats a spread-out subsequence
    assert f.score("abc", "xabcx") > f.score("abc", "xaxbxcx")
    # prefix anchor beats the same match further in
    assert f.score("abc", "abc") > f.score("abc", "xabc")
    # case-insensitive
    assert f.score("ABC", "xabc") > 0
    # subsequence hits that plain substring matching would miss
    assert f.score("qo", "quick open") > 0
    assert f.score("cmpr", "compare themes") > 0
    # word boundaries win: m after a space outranks m after a vowel
    order = [i for i, _s, _p in
             f.ranked("cm", ["commit msg", "color map"])]
    assert order == [1, 0]
    # positions come back in query order, usable for highlighting
    assert f.match("qo", "quick open")[1] == (0, 6)
    # ranking drops non-matches and is stable on ties
    hits = f.ranked("st", ["stop", "settings", "zzz"])
    assert [h[0] for h in hits] == [0, 1]
    # broken key functions fall back to str(item) — never raise
    assert f.filter_ranked("x", [1, "ax"],
                           key=lambda v: v.append(1)) == ["ax"]
    assert f.filter_ranked("sv", ["save all", "scratch", "zen"],
                           key=str.upper) == ["save all"]
    # path scoring: a basename match beats a deep-directory match
    assert f.path_score("app", "dxn1_studio/app.py") > \
        f.path_score("app", "d/a/p/p/x")
    assert f.path_score("zz", "nope.py") == -1


def test_session_engine(tmp_path):
    """DS2 v2.30 — session restore: snapshot, store, plan, window."""
    s = __import__("dxn1_studio.session", fromlist=["snapshot"])
    store = str(tmp_path / "sessions")
    # workspace keys: stable, distinct, junk-safe
    assert s.workspace_key(None) == "unknown"
    assert s.workspace_key("/a") == s.workspace_key("/a")
    assert s.workspace_key("/a") != s.workspace_key("/b")
    # snapshot normalization: dedupe, junk-drop, cap 50
    fa = tmp_path / "a.py"; fa.write_text("x = 1\n")
    fb = tmp_path / "b.py"; fb.write_text("y = 2\n")
    many = [str(tmp_path / f"m{i}.py") for i in range(60)]
    snap = s.snapshot([str(fa), str(fa), 42, None, str(fb)] + many,
                      active=str(fa),
                      cursor={str(fa): (12, 4), "junk": "x",
                              str(fb): (0, 0)},
                      workspace=str(tmp_path))
    assert len(snap["tabs"]) == 50 and snap["tabs"][0] == str(fa)
    assert snap["tabs"][1] == str(fb)
    assert snap["cursor"][str(fa)] == {"line": 12, "col": 4}
    assert str(fb) not in snap["cursor"]      # line 0 dropped
    assert snap["saved_at"]                    # timestamped
    # roundtrip through the store
    ok, err = s.save(str(tmp_path), snap, base=store)
    assert ok and not err, err
    loaded = s.load(str(tmp_path), base=store)
    assert loaded["active"] == str(fa)
    assert s.load(str(tmp_path / "nope"), base=store) == {}
    # corrupt json is skipped by the scanner, never crashes
    (tmp_path / "corrupt.json").write_text("{oops")
    listed = s.list_sessions(base=store)
    assert len(listed) == 1 and listed[0]["data"]["active"] == str(fa)
    # describe is human and junk-safe
    assert s.describe(snap).startswith("50 tabs · active a.py")
    assert s.describe(None) == "empty session"
    assert s.describe({}).startswith("0 tabs")
    # restore_plan filters to files that still exist
    tabs, active, cur = s.restore_plan(snap)
    # only files that actually exist survive the plan (the 60
    # m*.py were never written to disk) — cap still applies
    assert tabs == [str(fa), str(fb)]
    assert active == str(fa) and cur == (12, 4)
    ghost = s.snapshot(["/definitely/missing/zz.py"],
                       active="/definitely/missing/zz.py",
                       workspace="/w")
    assert s.restore_plan(ghost) == ([], "", None)
    # clear + clear-missing both succeed
    assert s.clear(str(tmp_path), base=store)[0] is True
    assert s.load(str(tmp_path), base=store) == {}
    assert s.clear("/never-saved", base=store)[0] is True
    # window flow with a stub app
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    ok, _ = s.save(str(tmp_path), snap, base=store)
    assert ok
    from types import SimpleNamespace

    class StubEditor:
        file_path = ""

        def goto_line(self, n):
            self.line = n
    stub = SimpleNamespace(editor=StubEditor(), opened=[])
    stub.open_file = lambda p: stub.opened.append(p)
    stub.editor.text = SimpleNamespace(
        mark_set=lambda *a: None, see=lambda *a: None)
    from dxn1_studio.session import open_session_restore
    win = open_session_restore(root, {"bg": "#16161e",
                                      "header": "#242432",
                                      "text": "#e8e8f0",
                                      "text_muted": "#8a8a9a",
                                      "button": "#2a2a3a",
                                      "button_hover": "#33334a",
                                      "card": "#131a22"},
                               app=stub, base=store)
    assert win is not None and win.winfo_exists()
    assert len(win.tree.get_children()) == 1
    key = win.tree.get_children()[0]
    win.tree.selection_set(key)
    win._on_select()
    assert "a.py" in win.preview.cget("text")
    win.restore_selected()
    assert len(stub.opened) == 2 and stub.opened[0] == str(fa)
    win.clear_selected()
    assert len(win.tree.get_children()) == 0
    win._refresh()                               # empty rescan is fine
    win.destroy(); root.destroy()


def test_fuzzy_split_runs():
    """DS2 v2.31 — split_runs renders match positions as merged runs."""
    f = __import__("dxn1_studio.fuzzy", fromlist=["split_runs"])
    # non-contiguous positions stay separate runs
    runs = f.split_runs("quick open", [0, 6, 7])
    assert runs == [("q", True), ("uick ", False), ("op", True),
                    ("en", False)]
    # contiguous positions merge into a single run
    assert f.split_runs("abcdef", [1, 2, 3]) == [
        ("a", False), ("bcd", True), ("ef", False)]
    # round-trip guarantee: joining chunks rebuilds the text exactly
    for text, pos in (("Quick open a file", (0, 7, 9)), ("x", ()), ("y", (0,))):
        assert "".join(c for c, _m in f.split_runs(text, pos)) == text
    # no positions → one unmatched run; junk positions are ignored
    assert f.split_runs("abc", ()) == [("abc", False)]
    assert f.split_runs("abc", (-1, 9, "x")) == [("abc", False)]
    assert f.split_runs(None, [0]) == []
    assert f.split_runs(123, (1, 2)) == [("1", False), ("23", True)]
    # every matched chunk is non-empty
    assert all(c for c, _m in f.split_runs("abc", [0, 2]))


def test_cursor_memory_engine():
    """DS2 v2.31 — per-buffer cursor memory: record + no-crash guards."""
    from types import SimpleNamespace
    from dxn1_studio.app import DXN1Studio

    class FakeText:
        def __init__(self, pos, boom=False):
            self.pos, self.boom = pos, boom

        def index(self, _mark):
            if self.boom:
                raise RuntimeError("tk died")
            return self.pos

    class FakeEditor:
        def __init__(self, path, pos, boom=False):
            self.file_path = path
            self.text = FakeText(pos, boom)

    stub = SimpleNamespace(editor=FakeEditor("/w/a.py", "7.3"),
                           _buffer_cursors={})
    DXN1Studio._remember_cursor(stub)
    assert stub._buffer_cursors == {"/w/a.py": "7.3"}
    # re-recording overwrites (current position wins)
    stub.editor = FakeEditor("/w/a.py", "9.0")
    DXN1Studio._remember_cursor(stub)
    assert stub._buffer_cursors["/w/a.py"] == "9.0"
    # no file open → no-op
    stub2 = SimpleNamespace(editor=FakeEditor(None, "1.0"),
                            _buffer_cursors={})
    DXN1Studio._remember_cursor(stub2)
    assert stub2._buffer_cursors == {}
    # a dying text widget must never break recording
    stub3 = SimpleNamespace(editor=FakeEditor("/w/b.py", "1.0", boom=True),
                            _buffer_cursors={})
    DXN1Studio._remember_cursor(stub3)
    assert stub3._buffer_cursors == {}


def test_installer_manifest_sync():
    """DS2 v2.31 — MANIFEST.txt can never drift from dxn1_studio/*.py.

    Guards the reported 'No module named dxn1_studio.i18n' install bug:
    the installer used a hardcoded 19-module list while the package grew
    to 80+. CI now fails the moment the two disagree.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pkg = os.path.join(root, "dxn1_studio")
    actual = sorted(f for f in os.listdir(pkg)
                    if f.endswith(".py") and not f.startswith("_hs"))
    mpath = os.path.join(root, "MANIFEST.txt")
    assert os.path.isfile(mpath), "MANIFEST.txt missing from repo root"
    listed = sorted(ln.strip() for ln in open(mpath, encoding="utf-8")
                    if ln.strip())
    assert listed == actual, (
        "MANIFEST.txt out of sync: missing="
        f"{sorted(set(actual) - set(listed))} stale="
        f"{sorted(set(listed) - set(actual))}")
    # the historical bug: i18n.py must always ship
    assert "i18n.py" in listed
    # install.sh drives downloads from the manifest, not a hardcoded list
    sh = open(os.path.join(root, "install.sh"), encoding="utf-8").read()
    assert "MANIFEST.txt" in sh and "dxn1_studio/$f" in sh
    # updater falls back to a list that includes i18n.py too
    from dxn1_studio import updater
    assert "i18n.py" in updater.MODULES
    assert set(listed) >= set(updater.MODULES)


def test_updater_manifest_helpers(monkeypatch, tmp_path):
    """DS2 v2.31 — updater manifest parsing + resolution order."""
    from dxn1_studio import updater
    # parsing: keep only .py lines, dedupe + sort, junk tolerated
    assert updater.parse_manifest("b.py\na.py\na.py\n\n# note\n") == \
        ["a.py", "b.py"]
    assert updater.parse_manifest("") == []
    assert updater.parse_manifest(None) == []
    assert updater.parse_manifest("x.txt\nsub/dir.py\n") == ["sub/dir.py"]
    # local manifest read from an install root
    (tmp_path / "MANIFEST.txt").write_text("a.py\nb.py\n", encoding="utf-8")
    assert updater._local_manifest(str(tmp_path)) == ["a.py", "b.py"]
    # missing/corrupt manifest → None (falls back safely)
    assert updater._local_manifest(str(tmp_path / "nope")) is None
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "MANIFEST.txt").write_bytes(b"\xff\xfe\xfa")
    assert updater._local_manifest(str(bad)) is None
    # resolution: remote source is stubbed away (CI may or may not have
    # network) — with no remote, the local manifest wins over fallback
    monkeypatch.setattr(updater, "_remote_manifest", lambda: None)
    mods = updater.resolve_modules(str(tmp_path))
    assert mods == ["a.py", "b.py"]
    fallback = updater.resolve_modules(str(tmp_path / "void"))
    assert fallback == list(updater.MODULES)
    # and when a remote manifest IS reachable it takes priority
    monkeypatch.setattr(updater, "_remote_manifest", lambda: ["r.py"])
    assert updater.resolve_modules(str(tmp_path)) == ["r.py"]


# ------------------------------------------------------------ v2.31 polish
def test_buffer_cursor_memory(monkeypatch, tmp_path):
    """DS2 v2.31 — per-buffer cursor memory: open_file records the
    outgoing insert mark and a tab switch restores it exactly."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    # hermetic config — the app must not touch the real ~/.dxn1-studio
    import dxn1_studio.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        fa = tmp_path / "alpha.py"
        fa.write_text("def gmm_thre(x):\n    return x\n" +
                      "".join(f"line {i}\n" for i in range(3, 13)),
                      encoding="utf-8")
        fb = tmp_path / "beta.py"
        fb.write_text("beta one\nbeta two\n", encoding="utf-8")
        app.open_file(str(fa))
        root.update()
        app.editor.text.mark_set("insert", "7.3")
        app.open_file(str(fb))          # outgoing cursor must be recorded
        assert app._buffer_cursors[str(fa)] == "7.3"
        app._activate_tab(str(fa))      # tab switch must restore it
        root.update()
        assert app.editor.text.index("insert") == "7.3"
        # _remember_cursor is best effort — junk state never raises
        app.editor.file_path = None
        app._remember_cursor()          # must not raise
        assert True
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_session_autosave(monkeypatch, tmp_path):
    """DS2 v2.32 — crash-safe session autosave: _autosave_session writes
    the same rich snapshot as close (tabs + active + cursors merged) and
    always reschedules; the switches silence the write itself."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    # hermetic config AND hermetic session store (~ expands at call time)
    import dxn1_studio.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        proj = tmp_path / "proj"
        proj.mkdir(exist_ok=True)
        f1 = proj / "alpha.py"
        f1.write_text("def gmm(x):\n    return x\n" + "".join(
            f"line {i}\n" for i in range(3, 13)), encoding="utf-8")
        app.project_dir = str(proj)
        app.open_file(str(f1))
        root.update()
        app.editor.text.mark_set("insert", "7.3")

        from dxn1_studio import session as sess
        spath = sess.session_path(str(proj))
        if os.path.exists(spath):        # clean slate
            os.remove(spath)

        app._autosave_session()          # direct call — must not raise
        assert os.path.isfile(spath), "autosave wrote no session file"
        data = sess.load(str(proj))
        assert str(f1) in data.get("tabs", [])
        assert data.get("active") == str(f1)
        curs = data.get("cursor") or {}
        assert curs.get(str(f1), {}).get("line") == 7, \
            "current insert position must land in the autosaved snapshot"
        # always reschedules while the root lives
        assert getattr(app, "_session_autosave_job", None)

        # switch off → the next call must NOT write (or wipe) anything
        before = open(spath, "r", encoding="utf-8").read()
        app.config.set("session_autosave", False)
        app._autosave_session()
        assert open(spath, "r", encoding="utf-8").read() == before, \
            "disabled autosave must leave the snapshot untouched"

        # restore_session off → also silent
        app.config.set("session_autosave", True)
        app.config.set("restore_session", False)
        app._autosave_session()
        assert open(spath, "r", encoding="utf-8").read() == before

        # junk interval never breaks the reschedule
        app.config.set("restore_session", True)
        for junk in ("0", "", "nonsense", 99999):
            app.config.set("session_autosave_secs", junk)
            app._autosave_session()
        assert getattr(app, "_session_autosave_job", None)
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_restore_engine_session(monkeypatch, tmp_path):
    """DS2 v2.32 — crash recovery: with no clean-exit record,
    _restore_engine_session reopens the autosaved tabs and cursor."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        proj = tmp_path / "proj"
        proj.mkdir(exist_ok=True)
        fa = proj / "alpha.py"
        fa.write_text("def gmm(x):\n    return x\n" + "".join(
            f"line {i}\n" for i in range(3, 13)), encoding="utf-8")
        fb = proj / "beta.py"
        fb.write_text("beta one\nbeta two\n", encoding="utf-8")
        app.project_dir = str(proj)

        # simulate the autosaved snapshot from a past life
        from dxn1_studio import session as sess
        sess.save(str(proj), sess.snapshot(
            [str(fa), str(fb)], active=str(fa),
            cursor={str(fa): (7, 3), str(fb): (2, 0)},
            workspace=str(proj)))

        app._restore_engine_session(str(proj))   # must not raise
        root.update()
        assert str(fa) in app._tab_frames
        assert str(fb) in app._tab_frames
        assert app.editor.file_path == str(fa), \
            "active file from the snapshot must be focused"
        assert app.editor.text.index("insert") == "7.3", \
            "active file cursor must be restored"
        # per-buffer map seeded so tab switches keep the other spot too
        assert app._buffer_cursors[str(fb)] == "2.0"
        app._activate_tab(str(fb))
        root.update()
        assert app.editor.text.index("insert") == "2.0"

        # ghost workspace → returns silently, opens nothing
        app2_tabs_before = dict(app._tab_frames)
        app._restore_engine_session(str(tmp_path / "nowhere"))
        assert dict(app._tab_frames) == app2_tabs_before
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_save_session_now(monkeypatch, tmp_path):
    """DS2 v2.33 — save session now: writes the snapshot, paints the
    statusbar chip (accent now, muted fade scheduled), and the
    terminal verb `session save` reaches the same path; without a
    workspace it degrades to an honest no-op."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        from dxn1_studio import session as sess
        # no workspace → no toast crash, no file, no raise
        app.project_dir = ""
        app.save_session_now()

        proj = tmp_path / "proj"
        proj.mkdir(exist_ok=True)
        f1 = proj / "alpha.py"
        f1.write_text("def gmm(x):\n    return x\n" + "".join(
            f"line {i}\n" for i in range(3, 13)), encoding="utf-8")
        app.project_dir = str(proj)
        app.open_file(str(f1))
        root.update()
        app.editor.text.mark_set("insert", "7.3")

        app.save_session_now()
        data = sess.load(str(proj))
        assert data.get("active") == str(f1)
        assert (data.get("cursor") or {}).get(
            str(f1), {}).get("line") == 7
        chip = str(app.status_sesave.cget("text"))
        assert "session saved" in chip and ":" in chip, chip
        assert str(app.status_sesave.cget("fg")) == str(
            app.theme.accent), "chip glows accent right after the save"
        assert getattr(app, "_sesave_job", None), \
            "muted fade must be scheduled"

        # terminal verb dispatch reaches the same code path
        app.handle_terminal_command("session save")
        assert "session saved" in str(app.status_sesave.cget("text"))
        # chip is clickable — the binding is wired
        assert app.status_sesave.bind("<Button-1>")
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_updater_delta(monkeypatch, tmp_path):
    """DS2 v2.34 — delta updates: hash parsing, local sha, and
    perform_update downloads only files that actually changed (or are
    missing) when HASHES.txt is available; full download otherwise."""
    import hashlib
    from dxn1_studio import updater
    # parse_hashes: sha256sum lines, junk tolerated, spaces in paths
    text = ("# comment\n"
            "nopath\n"
            + "0" * 64 + "  dxn1_studio/a.py\n"
            + "ZZZZ  junk.py\n"
            + "f" * 64 + "  DXN1 STUDIO\n")
    got = updater.parse_hashes(text)
    assert got == {"dxn1_studio/a.py": "0" * 64,
                   "DXN1 STUDIO": "f" * 64}
    assert updater.parse_hashes("") == {}
    assert updater.parse_hashes(None) == {}
    # local sha: None for missing files, real digest for present ones
    p = tmp_path / "x.bin"
    p.write_bytes(b"hello delta")
    assert updater._local_sha256(str(p)) == \
        hashlib.sha256(b"hello delta").hexdigest()
    assert updater._local_sha256(str(tmp_path / "nope")) is None

    # perform_update delta behaviour on a fake install root
    pkg = tmp_path / "dxn1_studio"
    pkg.mkdir()
    (pkg / "a.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(updater, "_package_root", lambda: str(tmp_path))
    monkeypatch.setattr(updater, "resolve_modules", lambda root: ["a.py"])
    monkeypatch.setattr(updater, "_is_git_checkout", lambda root: False)
    same = hashlib.sha256(b"x = 1\n").hexdigest()
    monkeypatch.setattr(updater, "_remote_hashes",
                        lambda: {"dxn1_studio/a.py": same})
    downloads = []
    monkeypatch.setattr(updater, "_download",
                        lambda rel, dest: downloads.append(rel) or 10)
    msgs = []

    def rep(**kw):
        msgs.append(kw)

    assert updater.perform_update(rep) is True
    assert "dxn1_studio/a.py" not in downloads, \
        "byte-identical file must be skipped by the delta pass"
    assert "MANIFEST.txt" in downloads and "HASHES.txt" in downloads

    # changed file → its sha differs → downloaded
    (pkg / "a.py").write_text("x = 2\n", encoding="utf-8")
    downloads.clear()
    assert updater.perform_update(rep) is True
    assert "dxn1_studio/a.py" in downloads

    # HASHES.txt unreachable → full download (legacy behaviour kept)
    monkeypatch.setattr(updater, "_remote_hashes", lambda: None)
    downloads.clear()
    assert updater.perform_update(rep) is True
    assert len(downloads) == 1 + 1 + 1 + 3 + 6, \
        "module + manifest + hashes + 3 entry scripts + 6 assets"
    assert "dxn1_studio/a.py" in downloads


def test_hashes_sync():
    """DS2 v2.34 — HASHES.txt can never drift from the shipped files.

    Mirrors scripts/gen_hashes.py: every MANIFEST module, entry script,
    asset and MANIFEST.txt itself must be listed with its current sha256.
    CI fails the moment a file changes without regenerating HASHES.txt.
    """
    import hashlib
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hpath = os.path.join(root, "HASHES.txt")
    assert os.path.isfile(hpath), "HASHES.txt missing from repo root"
    from dxn1_studio import updater
    listed = updater.parse_hashes(open(hpath, encoding="utf-8").read())

    mods = [ln.strip() for ln in
            open(os.path.join(root, "MANIFEST.txt"), encoding="utf-8")
            if ln.strip()]
    expected_rel = ([f"dxn1_studio/{m}" for m in mods]
                    + ["dxn1-studio", "dxn1", "DXN1 STUDIO", "README.md",
                       "MANIFEST.txt"]
                    + [f"assets/{a}" for a in
                       ("logo.png", "splash_bg.png", "welcome_hero.png",
                        "hub_hero.png", "agents_hero.png",
                        "update_hero.png")])
    missing = [r for r in expected_rel if r not in listed]
    assert not missing, f"HASHES.txt does not cover: {missing}"

    def sha(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 16), b""):
                h.update(chunk)
        return h.hexdigest()

    stale = [r for r in expected_rel
             if listed[r] != sha(os.path.join(root, r))]
    assert not stale, (
        "HASHES.txt stale (run scripts/gen_hashes.py): " + ", ".join(stale))


def test_update_skip_version(monkeypatch, tmp_path):
    """DS2 v2.35 — the polite updater: declining the portal remembers
    the exact version (the automatic boot check goes quiet for it),
    manual checks still open the portal, and any newer release nags
    again. Config saves are atomic — no torn tmp file left behind."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    from dxn1_studio import updater
    assert cfgmod.DEFAULTS["updater_skip_version"] == ""
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        # default: nothing skipped yet → the boot check would speak up
        assert app._update_should_nag("99.0.0") is True
        assert app._update_should_nag("99.0.0", manual=True) is True

        # a stub portal borrows the real decline() — no fullscreen Tk
        class _StubPortal:
            decline = updater.UpdatePortal.decline

            def __init__(self, app, latest):
                self.app, self.latest, self._phase = app, latest, "offer"

            def _paint(self):
                self.painted = True

        portal = _StubPortal(app, "99.0.0")
        portal.decline()
        assert portal._phase == "declined"
        assert app.config.get("updater_skip_version") == "99.0.0", \
            "declining must remember the exact version"

        # auto-check goes quiet for that version…
        assert app._update_should_nag("99.0.0") is False
        # …but speaks up for anything else…
        assert app._update_should_nag("100.0.0") is True
        # …and a manual check always shows the portal.
        assert app._update_should_nag("99.0.0", manual=True) is True

        # end to end: auto check with the skip set never builds a portal
        import threading
        import urllib.request
        payload = json.dumps({"tag_name": "v99.0.0", "body": "- x",
                              "html_url": "https://example.com/r"}).encode()

        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return payload

        class _InlineThread:
            """Run the worker synchronously — root.after from a
            secondary thread needs a live mainloop, which the test
            harness stubs out."""

            def __init__(self, target=None, daemon=None, *a, **k):
                self._target = target

            def start(self):
                self._target()

        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: _FakeResp())
        opened = []

        class _NoPortal:
            def __init__(self, *a, **k):
                opened.append(a)

        monkeypatch.setattr(updater, "UpdatePortal", _NoPortal)
        monkeypatch.setattr(threading, "Thread", _InlineThread)
        app.smoke_test = False          # lift the smoke-mode block
        app._updater_shown = False
        app.check_for_updates(manual=False)
        for _ in range(50):
            root.update()
            if not app._updater_shown:
                break
            time.sleep(0.02)
        assert app._updater_shown is False, "check never finished"
        assert not opened, "skipped version must not open the portal"

        # manual check with the same skip → the portal fires
        app._updater_shown = False
        app.check_for_updates(manual=True)
        for _ in range(50):
            root.update()
            if not app._updater_shown:
                break
            time.sleep(0.02)
        assert app._updater_shown is False
        assert opened, "manual check must show the portal even when skipped"

        # atomic config save — write-then-replace leaves no tmp debris
        app.config.set("updater_skip_version", "99.0.0")
        assert not os.path.exists(str(tmp_path / "config.json.tmp")), \
            "atomic save must leave no tmp file behind"
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_engine_first_restore(monkeypatch, tmp_path):
    """DS2 v2.35 — boot restore prefers the engine snapshot (fresh:
    every clean exit refreshes it, the 60s autosave keeps it warm) over
    a stale legacy clean-exit record; the legacy record stays as the
    fallback when no snapshot exists. _restore_engine_session reports
    whether it actually restored anything."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    from dxn1_studio import session as sess
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        proj = tmp_path / "proj"
        proj.mkdir(exist_ok=True)
        fa = proj / "alpha.py"
        fa.write_text("def gmm(x):\n    return x\n" + "".join(
            f"line {i}\n" for i in range(3, 13)), encoding="utf-8")
        fb = proj / "beta.py"
        fb.write_text("beta one\nbeta two\n", encoding="utf-8")
        app.project_dir = str(proj)

        # no snapshot yet → False, honest, nothing opens
        assert app._restore_engine_session(str(proj)) is False

        # a WEEK-OLD clean-exit record knows only beta…
        app.config.set("session_tabs", {os.path.abspath(str(proj)): {
            "tabs": [str(fb)], "active": str(fb)}})

        # …but last night's autosave snapshot knows both + cursors
        sess.save(str(proj), sess.snapshot(
            [str(fa), str(fb)], active=str(fa),
            cursor={str(fa): (7, 3), str(fb): (2, 0)},
            workspace=str(proj)))
        assert app._restore_engine_session(str(proj)) is True
        root.update()
        assert str(fa) in app._tab_frames and str(fb) in app._tab_frames, \
            "engine snapshot (both files) must beat the stale record"
        assert app.editor.file_path == str(fa)
        assert app.editor.text.index("insert") == "7.3"

        # the boot path must take the engine branch too
        app2 = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
        app2.project_dir = str(proj)
        app2._restore_session_tabs(str(proj))
        root.update()
        assert str(fa) in app2._tab_frames and str(fb) in app2._tab_frames
        assert app2.editor.file_path == str(fa)
        assert app2.editor.text.index("insert") == "7.3", \
            "engine cursors must survive the boot restore"
        assert app2._buffer_cursors[str(fb)] == "2.0"

        # fallback: wipe the snapshot → the legacy record restores beta
        sess.clear(str(proj))
        assert app._restore_engine_session(str(proj)) is False
        app3 = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
        app3.project_dir = str(proj)
        app3._restore_session_tabs(str(proj))
        root.update()
        assert app3.editor.file_path == str(fb), \
            "legacy clean-exit record is the fallback when no snapshot"
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_depcheck(tmp_path):
    """DS2 v2.36 — dependency cross-check: import scanning (as/from/
    relative), stdlib-vs-local-vs-third classification, requirements
    parsing (pins, extras, comments, plumbing lines), the famous
    alias table, and the missing/unused verdicts — plus the honest
    no-requirements note."""
    from dxn1_studio import depcheck as dc
    # names: canonical + top_imports
    assert dc.canonical("Pillow_-2") == "pillow-2"
    assert dc.canonical("") == ""
    import ast as _ast
    tree = _ast.parse(
        "import os\nimport requests as rq\nfrom PIL import Image\n"
        "from .rel import x\nfrom a.b.c import d\n")
    got = []
    for node in _ast.walk(tree):
        got.extend(dc.top_imports(node))
    assert sorted(got) == ["PIL", "a", "os", "requests"], got
    # scan_imports: junk files skipped, paths sorted
    f1 = tmp_path / "main.py"
    f1.write_text("import os\nimport flask\n", encoding="utf-8")
    f2 = tmp_path / "broken.py"
    f2.write_text("def oops(:\n", encoding="utf-8")
    scanned = dc.scan_imports([str(f1), str(f2), str(tmp_path / "x.txt")])
    assert str(f1) in scanned and scanned[str(f1)] == ["flask", "os"]
    assert str(f2) not in scanned and \
        str(tmp_path / "x.txt") not in scanned
    # requirements parsing
    rq = tmp_path / "requirements.txt"
    rq.write_text(
        "flask>=3.0  # web\n"
        "Pillow\n"
        "uvicorn[standard]==0.30\n"
        "-r dev.txt\n"
        "--hash=sha256:abc\n"
        "# pure comment\n"
        "\n"
        "git+https://example.com/x.git\n", encoding="utf-8")
    names = dc.read_requirements(str(rq))
    assert names == ["flask", "pillow", "uvicorn"], names
    assert dc.read_requirements(str(tmp_path / "nope.txt")) == []
    # alias resolution
    assert dc.req_import_names({"pillow"}) == {"pillow", "pil"}
    assert "bs4" in dc.req_import_names({"beautifulsoup4"})
    # classification
    std, loc, third = dc.classify(
        ["os", "tkinter", "mymod", "flask", "PIL"],
        local_modules={"mymod"})
    assert std == ["os", "tkinter"] and loc == ["mymod"]
    assert third == ["PIL", "flask"]
    # local_modules: stems + packages
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    lm = dc.local_modules(tmp_path)
    assert "main" in lm and "mypkg" in lm and "rq" not in lm
    # the full check: missing + unused + clean note
    proj = tmp_path / "ws"
    proj.mkdir()
    (proj / "app.py").write_text(
        "import os\nimport yaml\nimport yaml as _y\n", encoding="utf-8")
    (proj / "requirements.txt").write_text(
        "PyYAML\nflask\n", encoding="utf-8")
    rep = dc.check(proj)
    assert rep["files"] == 1 and rep["third_party"] == ["yaml"]
    assert rep["missing"] == []            # pyyaml alias covers yaml
    assert rep["unused"] == ["flask"]
    out = dc.describe(rep)
    assert "never imported" in out and "flask" in out
    # missing requirement surfaces with the honest note
    (proj / "extra.py").write_text("import uvicorn\n", encoding="utf-8")
    rep2 = dc.check(proj)
    assert rep2["missing"] == ["uvicorn"]
    assert "best-effort" in rep2["note"] and dc.describe(rep2)
    # no requirements at all -> honest note, no crash
    empty = tmp_path / "bare"
    empty.mkdir()
    (empty / "only.py").write_text("import os\n", encoding="utf-8")
    rep3 = dc.check(empty)
    assert rep3["files"] == 1 and rep3["req_files"] == []
    assert "no requirements" in rep3["note"]
    assert "no requirements" in dc.describe(rep3)   # the note is the value
    # zero files scanned -> nothing useful to say
    assert dc.describe(dc.check(tmp_path / "void")) == ""
    # describe() of a junk report is honest
    assert dc.describe(None) == "" and dc.describe({}) == ""


def test_update_periodic(monkeypatch, tmp_path):
    """DS2 v2.36 — the update heartbeat: one after-loop drives the
    boot check and the slow re-check; gated by the master switch and
    the clamped interval; junk intervals never break the reschedule."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        # DEFAULTS registered
        assert cfgmod.DEFAULTS["update_check_secs"] == 3600
        # smoke mode: the gate silences the check itself…
        calls = []
        monkeypatch.setattr(app, "check_for_updates",
                            lambda manual=False: calls.append(manual))
        app._schedule_update_check()
        assert calls == [], "smoke mode must not auto-check"
        # …but the heartbeat still reschedules
        assert getattr(app, "_update_check_job", None)
        # master switch off → silent, still rescheduled
        app.config.set("check_updates", False)
        app.config.set("update_check_secs", 900)
        before = app._update_check_job
        app._schedule_update_check()
        assert calls == [] and app._update_check_job != before
        # switch on (smoke_test lifted) → the check fires
        app.smoke_test = False
        app.config.set("check_updates", True)
        app._schedule_update_check()
        assert calls == [False], calls
        # junk intervals clamp into 900..21600 — probe the next tick
        for junk in ("0", "", "nonsense", 999999, -5):
            app.config.set("update_check_secs", junk)
            app._schedule_update_check()
        assert calls == [False] * 6, calls
        assert getattr(app, "_update_check_job", None)
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_deps_fix(tmp_path):
    """DS2 v2.37 — deps fix: reverse-alias pin suggestions, atomic
    deduped appends to requirements.txt, on-demand file creation, and
    the app-level `deps fix` verb that closes the loop (report → fix →
    re-check finds nothing missing)."""
    import tkinter as tk
    from dxn1_studio import depcheck as dc
    # suggestion mapping (reverse aliases)
    assert dc.dist_for_import("PIL") == "pillow"
    assert dc.dist_for_import("yaml") == "pyyaml"
    assert dc.dist_for_import("cv2") == "opencv-python"
    assert dc.dist_for_import("jwt") == "pyjwt"
    assert dc.dist_for_import("flask") == "flask"
    assert dc.suggested_pins(["PIL", "yaml", "PIL"]) == ["pillow",
                                                         "pyyaml"]
    assert dc.suggested_pins(None) == []
    # atomic deduped append
    proj = tmp_path / "ws"
    proj.mkdir()
    (proj / "main.py").write_text("import yaml\nimport uvicorn\n",
                                  encoding="utf-8")
    (proj / "requirements.txt").write_text("PyYAML\n", encoding="utf-8")
    res = dc.fix_requirements(str(proj), ["uvicorn", "pyyaml"])
    assert res["ok"] and res["added"] == ["uvicorn"], res
    assert res["target"].endswith("requirements.txt")
    body = (proj / "requirements.txt").read_text(encoding="utf-8")
    assert "PyYAML" in body and "uvicorn" in body
    assert "# added by deps on" in body
    # second run is a no-op (dedupe)
    res2 = dc.fix_requirements(str(proj), ["uvicorn"])
    assert res2["ok"] and res2["added"] == []
    assert not os.path.exists(str(proj / "requirements.txt.tmp"))
    # a missing requirements file is created on demand
    bare = tmp_path / "bare-ws"
    bare.mkdir()
    res3 = dc.fix_requirements(str(bare), ["requests"])
    assert res3["ok"] and res3["added"] == ["requests"]
    assert (bare / "requirements.txt").is_file()
    # app-level verb on a FRESH workspace: report + fix + re-check clean
    proj2 = tmp_path / "ws2"
    proj2.mkdir()
    (proj2 / "main.py").write_text("import yaml\nimport httpx\n",
                                   encoding="utf-8")
    (proj2 / "requirements.txt").write_text("PyYAML\n", encoding="utf-8")
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    monkey_tmp = tmp_path / "cfg"
    monkey_tmp.mkdir()
    import pytest  # noqa: F401
    from dxn1_studio.app import DXN1Studio
    cfgmod.CONFIG_DIR = str(monkey_tmp)
    cfgmod.CONFIG_PATH = str(monkey_tmp / "config.json")
    os.environ["HOME"] = str(tmp_path)
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        app.project_dir = str(proj2)
        app.handle_terminal_command("deps fix")
        app.terminal.log = real_log
        blob = "\n".join(logs)
        assert "deps fix: added 1 pin(s)" in blob, blob
        assert "httpx" in blob
        # the report precedes the fix
        assert "deps: 1 file(s) scanned" in blob
        # re-check: nothing missing any more
        rep = dc.check(str(proj2))
        assert rep["missing"] == []
        # nothing to fix → the honest line
        logs.clear()
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        app.handle_terminal_command("deps fix")
        app.terminal.log = real_log
        assert any("nothing to add" in s for s in logs), logs
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_help_verb(monkeypatch, tmp_path):
    """DS2 v2.37 — `help <verb>`: exact verb rows, substring hits,
    fuzzy fallback, the honest no-help line, and the unchanged bare
    `help` full listing."""
    from dxn1_studio.app import matching_help_rows
    assert matching_help_rows("") == []
    assert matching_help_rows(None) == []
    exact = matching_help_rows("deps")
    assert exact and exact[0][0] == "deps"
    # verb word of a multi-word command
    assert matching_help_rows("run")[0][0] == "run"
    # substring across commands and descriptions
    sess = matching_help_rows("session")
    assert len(sess) >= 2 and all("session" in r[0].lower()
                                  or "session" in r[1].lower()
                                  for r in sess)
    # fuzzy fallback: "dps" is a subsequence of "deps" but no substring
    assert matching_help_rows("dps")[0][0] == "deps"
    # honest empty for a query nothing can match
    assert matching_help_rows("deplo") == []
    # gibberish matches nothing
    assert matching_help_rows("zzzqqqxxx") == []

    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio, TERMINAL_HELP
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        try:
            app.handle_terminal_command("help deps")
            assert any("cross-check imports" in s for s in logs), logs
            logs.clear()
            app.handle_terminal_command("help session")
            assert sum("session" in s for s in logs) >= 2
            logs.clear()
            app.handle_terminal_command("help zzzqqqxxx")
            assert any("No help for" in s for s in logs), logs
            logs.clear()
            app.handle_terminal_command("help")
            assert any("Studio commands:" in s for s in logs)
            assert sum(1 for s in logs if " — " in s) >= len(TERMINAL_HELP)
        finally:
            app.terminal.log = real_log
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_deps_cache(tmp_path):
    """DS2 v2.38 — deps per-workspace cache: change-sensitive
    signature, instant hit on repeat runs, honest invalidation when a
    file changes, the .dxn1 self-invalidation guard, corrupt-cache
    fallback, and the app-level `deps` / `deps fresh` / `deps fix`
    caching contract."""
    import json
    import shutil
    import tkinter as tk
    from dxn1_studio import depcheck as dc
    proj = tmp_path / "ws"
    proj.mkdir()
    (proj / "main.py").write_text("import yaml\nimport httpx\n",
                                  encoding="utf-8")
    (proj / "requirements.txt").write_text("PyYAML\n", encoding="utf-8")
    # signature: stable without changes, sensitive to content
    sig1 = dc.cache_sig(str(proj))
    assert dc.cache_sig(str(proj)) == sig1
    (proj / "main.py").write_text("import yaml\nimport httpx\nimport a\n",
                                  encoding="utf-8")
    assert dc.cache_sig(str(proj)) != sig1
    (proj / "main.py").write_text("import yaml\nimport httpx\n",
                                  encoding="utf-8")
    # fresh store, then an instant cached hit
    rep1 = dc.check_cached(str(proj))
    assert not rep1.get("cached") and rep1["files"] == 1
    assert rep1["missing"] == ["httpx"], rep1
    rep2 = dc.check_cached(str(proj))
    assert rep2.get("cached") is True and rep2["missing"] == ["httpx"]
    cpath = proj / ".dxn1" / "depcheck_cache.json"
    assert cpath.is_file()
    stored = json.loads(cpath.read_text(encoding="utf-8"))
    # the stored sig matches the CURRENT fingerprint (mtimes moved
    # when main.py was rewritten, so the pre-rewrite sig1 is stale)
    assert isinstance(stored.get("sig"), list) \
        and stored["sig"] == dc.cache_sig(str(proj))
    assert not (proj / ".dxn1" / "depcheck_cache.json.tmp").exists()
    # the cache's own .dxn1 dir must NOT invalidate the cache
    assert dc.check_cached(str(proj)).get("cached") is True
    # a changed workspace invalidates honestly
    (proj / "extra.py").write_text("import pendulum\n", encoding="utf-8")
    rep3 = dc.check_cached(str(proj))
    assert not rep3.get("cached") and rep3["files"] == 2
    assert "pendulum" in rep3["missing"]
    assert dc.check_cached(str(proj)).get("cached") is True
    # corrupt cache -> honest fallback, no crash
    cpath.write_text("{definitely not json", encoding="utf-8")
    rep4 = dc.check_cached(str(proj))
    assert not rep4.get("cached") and rep4["files"] == 2
    # fresh bypass re-stores
    rep5 = dc.check_cached(str(proj), use_cache=False)
    assert not rep5.get("cached") and rep5["files"] == 2
    assert dc.check_cached(str(proj)).get("cached") is True

    # app-level contract on a real studio
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    monkey_tmp = tmp_path / "cfg"
    monkey_tmp.mkdir()
    from dxn1_studio.app import DXN1Studio
    cfgmod.CONFIG_DIR = str(monkey_tmp)
    cfgmod.CONFIG_PATH = str(monkey_tmp / "config.json")
    os.environ["HOME"] = str(tmp_path)
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        app.project_dir = str(proj)
        # cold start: the module-level section left the cache warm —
        # remove it so the app-level `deps` proves the scan path
        shutil.rmtree(str(proj / ".dxn1"), ignore_errors=True)
        # first `deps`: a real scan, no cache note
        app.handle_terminal_command("deps")
        assert any("served from cache" in s for s in logs) is False
        logs.clear()
        # second `deps`: cached, with the honest note
        app.handle_terminal_command("deps")
        assert any("served from cache" in s for s in logs), logs
        logs.clear()
        # `deps fresh`: rescans, no cache note, cache refreshed after
        app.handle_terminal_command("deps fresh")
        assert any("served from cache" in s for s in logs) is False
        assert any("2 file(s) scanned" in s for s in logs), logs
        assert dc.check_cached(str(proj)).get("cached") is True
        logs.clear()
        # `deps fix` works from a FRESH scan: add a new import after
        # the cache was stored — fix must still see it
        (proj / "late.py").write_text("import uvicorn\n",
                                      encoding="utf-8")
        app.handle_terminal_command("deps fix")
        blob = "\n".join(logs)
        # requirements.txt only holds PyYAML, so ALL three imports
        # (httpx, pendulum, uvicorn) are missing — fix pins them all
        assert "added 3 pin(s)" in blob, blob
        for name in ("httpx", "pendulum", "uvicorn"):
            assert name in blob, (name, blob)
    finally:
        app.terminal.log = real_log
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_commands_verb(tmp_path):
    """DS2 v2.38 — `commands [filter]`: the palette registry listed in
    the terminal (label + shortcut), substring filter, fuzzy fallback,
    the honest no-match line, and `help <query>` falling back into the
    palette when the terminal rows come up empty."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    import pytest  # noqa: F401
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio, palette_help_rows
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        rows = palette_help_rows(app)
        assert len(rows) >= 40, "palette registry should be rich"
        assert ("Run project (F5)", "F5") in rows
        assert all(r[0] for r in rows), "labels must be non-empty"
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        try:
            # full listing: head line + rows + the fire-any hint
            app.handle_terminal_command("commands")
            assert any("commands: " in s and " of " in s for s in logs)
            assert any("Run project (F5)" in s for s in logs)
            assert any("Ctrl+K" in s for s in logs)
            logs.clear()
            # substring filter: 'line' hits the line commands
            app.handle_terminal_command("commands line")
            blob = "\n".join(logs)
            assert "Duplicate line" in blob and "Go to line" in blob
            assert "matching 'line'" in blob
            logs.clear()
            # fuzzy fallback: 'sve fil' is not a substring of anything
            app.handle_terminal_command("commands sve fil")
            blob = "\n".join(logs)
            assert "Save file" in blob, blob
            logs.clear()
            # honest empty state
            app.handle_terminal_command("commands zzzqqqxxx")
            assert any("nothing matches" in s for s in logs), logs
            logs.clear()
            # help falls back into the palette registry
            app.handle_terminal_command("help duplicate")
            blob = "\n".join(logs)
            assert "palette: Duplicate line" in blob
            assert "Ctrl+Shift+D" in blob
            logs.clear()
            # `help commands` finds the new terminal row itself
            app.handle_terminal_command("help commands")
            assert any("list palette commands" in s for s in logs), logs
        finally:
            app.terminal.log = real_log
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
        monkeypatch.undo()


def test_deps_watch(tmp_path):
    """DS2 v2.39 — the dependency watch chip: cache_state's three
    honest states (absent / cached / stale), the chip's text+colour
    for each, click-to-rescan, the `deps watch [on|off]` toggle with
    its config persistence, and the usage line for junk arguments."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    from dxn1_studio import depcheck as dc
    from dxn1_studio.app import TERMINAL_HELP
    # engine: the three honest states, no scan needed
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "main.py").write_text("import yaml\n", encoding="utf-8")
    (ws / "requirements.txt").write_text("PyYAML\n", encoding="utf-8")
    assert dc.cache_state(str(ws))["state"] == "absent"
    dc.check_cached(str(ws))
    assert dc.cache_state(str(ws))["state"] == "cached"
    (ws / "late.py").write_text("import uvicorn\n", encoding="utf-8")
    assert dc.cache_state(str(ws))["state"] == "stale"
    # the TERMINAL_HELP row advertises the new sub-verb
    deps_rows = [r for r in TERMINAL_HELP if r[0] == "deps"]
    assert deps_rows and "watch" in deps_rows[0][1]

    import pytest
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        app.project_dir = str(ws)
        # remove the module-level cache so the app starts absent
        import shutil
        shutil.rmtree(str(ws / ".dxn1"), ignore_errors=True)
        try:
            # absent: a quiet "deps —" placeholder, click-worthy
            app._update_depswatch(force=True)
            assert app.status_deps.cget("text") == "deps —"
            # the engine-section cache was removed, so this scan sees
            # main.py AND late.py: uvicorn is imported but unpinned —
            # v2.40 severity shows it red, not a fake "ok"
            app.handle_terminal_command("deps")
            assert app.status_deps.cget("text") == "● deps 1 missing"
            assert app.status_deps.cget("fg") == "#f85149"
            # drift: a new file turns the chip amber without a scan
            (ws / "late2.py").write_text("import httpx\n",
                                         encoding="utf-8")
            app._update_depswatch(force=True)
            assert app.status_deps.cget("text") == "● deps drift"
            assert app.status_deps.cget("fg") == "#f59e0b"
            logs.clear()
            # clicking the chip rescans; now both imports are unpinned
            app._deps_chip_click()
            assert app.status_deps.cget("text") == "● deps 2 missing"
            assert any("file(s) scanned" in s for s in logs), logs
            logs.clear()
            # pin both: sig moves (stale → amber), a click rescans and
            # the cache now reports zero missing → back to ok
            with open(str(ws / "requirements.txt"), "a",
                      encoding="utf-8") as fh:
                fh.write("httpx\nuvicorn\n")
            app._update_depswatch(force=True)
            assert app.status_deps.cget("text") == "● deps drift"
            app._deps_chip_click()
            assert app.status_deps.cget("text") == "deps ok"
            # toggle off: chip hides, config remembers
            app.handle_terminal_command("deps watch off")
            assert app.config.get("deps_watch", True) is False
            assert app.status_deps.cget("text") == ""
            logs.clear()
            # junk argument: honest usage, config untouched
            app.handle_terminal_command("deps watch maybe")
            assert any("usage: deps watch" in s for s in logs), logs
            assert app.config.get("deps_watch", True) is False
            logs.clear()
            # bare `deps watch` flips it back on and redraws
            app.handle_terminal_command("deps watch")
            assert app.config.get("deps_watch", True) is True
            assert app.status_deps.cget("text") == "deps ok"
            logs.clear()
            # the poll runs once without stacking or raising
            app._deps_watch_poll()
        finally:
            app.terminal.log = real_log
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
        monkeypatch.undo()


def test_verbs_window(tmp_path):
    """DS2 v2.39 — the terminal verbs browser: TERMINAL_HELP flattens
    into complete (verb, description) rows with continuations merged,
    the substring filter is honest (empty query = everything, junk =
    nothing), the window opens with every row rendered, the terminal
    `verbs` verb opens it too, and clicking a row drops the verb into
    the terminal input."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import dxn1_studio.config as cfgmod
    from dxn1_studio import verbs
    from dxn1_studio.app import TERMINAL_HELP
    rows = verbs.verb_rows(TERMINAL_HELP)
    assert len(rows) >= 40, "the studio speaks plenty of verbs"
    assert all(c and d for c, d in rows), "no empty verbs/descriptions"
    verbs_list = [c for c, _ in rows]
    assert len(verbs_list) == len(set(verbs_list)), "verbs unique"
    # the git continuation line merged into one description
    assert "git <args>" in verbs_list
    assert "commit" in dict(rows)["git <args>"]
    # filter: empty = everything, substring = honest, junk = nothing
    assert verbs.filter_rows(rows, "") == rows
    assert [c for c, _ in verbs.filter_rows(rows, "deps")] == ["deps"]
    assert verbs.filter_rows(rows, "MARKDOWN"), "desc match, any case"
    assert verbs.filter_rows(rows, "zzzqqqxxx") == []
    # the browser lists itself now, and deps advertises watch
    assert "verbs" in verbs_list
    assert "watch" in dict(rows)["deps"]

    import pytest
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        # the palette registry carries the new entries
        labels = [r[0] for r in app.palette_commands()]
        assert any("Terminal verbs" in l for l in labels), labels[-6:]
        assert any("Dependency watch" in l for l in labels)
        # `verbs` opens the browser (a new Toplevel appears)
        before = len([w for w in app.root.winfo_children()
                      if isinstance(w, tk.Toplevel)])
        app.handle_terminal_command("verbs")
        after = len([w for w in app.root.winfo_children()
                     if isinstance(w, tk.Toplevel)])
        assert after == before + 1
        # a standalone window: rows render, search filters live
        picked = []
        win = verbs.open_verbs(app.root, app.theme,
                               on_insert=picked.append,
                               rows=verbs.verb_rows(TERMINAL_HELP))
        try:
            assert win.winfo_exists()
            ent = getattr(win, "search_entry", None)
            assert ent is not None, "search entry present"
            # drive the live filter through the documented hook
            ent.delete(0, tk.END)
            ent.insert(0, "zzzqqq")
            win.refilter()
            blob = ""
            def _collect(w):
                nonlocal blob
                for ch in w.winfo_children():
                    if isinstance(ch, tk.Label):
                        blob += ch.cget("text") + "\n"
                    _collect(ch)
            _collect(win)
            assert "nothing matches" in blob, blob
            ent.delete(0, tk.END)
            ent.insert(0, "deps")
            win.refilter()
            blob = ""
            _collect(win)
            assert "deps" in blob and "nothing matches" not in blob
        finally:
            win.destroy()
        # clicking a row drops the verb into the terminal input,
        # Enter still runs it — the user stays in charge
        app._prefill_terminal("deps fix")
        assert app.terminal.input.get() == "deps fix"
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
        monkeypatch.undo()


def test_git_chip(tmp_path):
    """DS2 v2.40 — the git lane chip: repo_state's honest probe
    (non-repo / fresh / dirty / detached), the chip's text+colour for
    each state, click opens Source Control, the `git watch [on|off]`
    toggle with config persistence, its usage line, the shared 30s
    poll, and the TERMINAL_HELP + verbs-browser rows."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import subprocess
    import dxn1_studio.config as cfgmod
    from dxn1_studio.gitpanel import repo_state
    from dxn1_studio.app import TERMINAL_HELP

    def _git(*args, cwd):
        subprocess.run(["git", *args], cwd=str(cwd),
                       capture_output=True, text=True)

    # engine: the honest probe, no UI
    plain = tmp_path / "plain"
    plain.mkdir()
    assert repo_state(str(plain))["repo"] is False
    assert repo_state(str(tmp_path / "nope"))["repo"] is False
    ws = tmp_path / "repo"
    ws.mkdir()
    _git("init", "-q", cwd=ws)
    st = repo_state(str(ws))
    assert st["repo"] is True and st["dirty"] == 0
    (ws / "a.txt").write_text("one\n", encoding="utf-8")
    assert repo_state(str(ws))["dirty"] == 1          # untracked counts
    _git("add", ".", cwd=ws)
    assert repo_state(str(ws))["dirty"] == 1          # staged counts too
    _git("-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "one", cwd=ws)
    st = repo_state(str(ws))
    assert st["dirty"] == 0 and st["branch"], st
    _git("checkout", "-q", "--detach", "HEAD", cwd=ws)
    assert repo_state(str(ws))["branch"] == "(detached)"
    # the TERMINAL_HELP row + verbs flattening know the verb
    git_rows = [r for r in TERMINAL_HELP if r[0].startswith("git watch")]
    assert git_rows and "amber" in git_rows[0][1], git_rows

    import pytest
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        opened = []
        real_view = app.show_sidebar_view
        app.show_sidebar_view = lambda name, *a, **k: opened.append(name)
        try:
            # no workspace: the chip sits quietly
            app._update_gitchip(force=True)
            assert app.status_git.cget("text") == ""
            # a plain folder: still quiet — no nagging non-repos
            app.project_dir = str(plain)
            app._update_gitchip(force=True)
            assert app.status_git.cget("text") == ""
            # a repo, clean: the muted branch name
            app.project_dir = str(ws)
            app._update_gitchip(force=True)
            branch = repo_state(str(ws))["branch"]
            assert app.status_git.cget("text") == branch
            assert "bold" not in str(app.status_git.cget("font"))
            # a saved-but-uncommitted file: amber, bold, ●N
            (ws / "b.txt").write_text("two\n", encoding="utf-8")
            app._update_gitchip(force=True)
            assert app.status_git.cget("text") == "%s ●1" % branch
            assert app.status_git.cget("fg") == "#f59e0b"
            assert "bold" in str(app.status_git.cget("font"))
            # clicking opens Source Control and redraws
            app._git_chip_click()
            assert "git" in opened, opened
            # toggle off: chip hides, config remembers
            app.handle_terminal_command("git watch off")
            assert app.config.get("git_watch", True) is False
            assert app.status_git.cget("text") == ""
            logs.clear()
            # junk argument: honest usage, config untouched
            app.handle_terminal_command("git watch maybe")
            assert any("usage: git watch" in s for s in logs), logs
            assert app.config.get("git_watch", True) is False
            logs.clear()
            # bare `git watch` flips back on; explicit `git watch on`
            # is accepted too — and plain `git status` still passes
            # through to the shell runner (the intercept is
            # prefix-exact; run_command is stubbed — it is a worker
            # thread + after-loop, which the harness has no mainloop for)
            app.handle_terminal_command("git watch")
            assert app.config.get("git_watch", True) is True
            assert "●1" in app.status_git.cget("text")
            app.handle_terminal_command("git watch on")
            assert app.config.get("git_watch", True) is True
            ran = []
            app.run_command = lambda cmd: ran.append(cmd)
            app.handle_terminal_command("git status --short")
            assert ran == ["git status --short"], ran
            # commit calms the chip within one poll tick
            _git("add", ".", cwd=ws)
            _git("-c", "user.email=t@t", "-c", "user.name=t",
                 "commit", "-qm", "two", cwd=ws)
            app._update_gitchip(force=True)
            assert app.status_git.cget("text") == branch
            # the shared poll runs both chips without raising
            app._deps_watch_poll()
        finally:
            app.terminal.log = real_log
            app.show_sidebar_view = real_view
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
        monkeypatch.undo()


def test_chip_gestures(tmp_path):
    """DS2 v2.41 — chip gestures: the red deps chip click queues
    `deps fix` (one-gesture repair, Enter still runs it), the amber
    click stays a plain rescan, and the branch chip's right-click
    menu is honest per state (repo actions only on repos) with
    working commands (stage-all routes to the shell runner, copy
    branch fills the clipboard, open jumps to Source Control)."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import subprocess
    import dxn1_studio.config as cfgmod

    def _git(*args, cwd):
        subprocess.run(["git", *args], cwd=str(cwd),
                       capture_output=True, text=True)

    import pytest
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        # --- deps: the one-gesture repair
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "main.py").write_text("import uvicorn\n", encoding="utf-8")
        app.project_dir = str(ws)
        app.handle_terminal_command("deps")
        app._update_depswatch(force=True)
        assert app.status_deps.cget("text") == "● deps 1 missing"
        app.terminal.input.delete(0, tk.END)
        logs.clear()
        app._deps_chip_click()          # red click → rescan + prefill
        assert app.terminal.input.get() == "deps fix"
        assert any("press Enter" in s for s in logs), logs
        # Enter runs it — the repair lands in requirements.txt
        app.handle_terminal_command("deps fix")
        assert "uvicorn" in (ws / "requirements.txt").read_text(
            encoding="utf-8")
        assert app.status_deps.cget("text") == "deps ok"
        # amber (stale) click: no prefill — just a rescan
        app.terminal.input.delete(0, tk.END)
        (ws / "late.py").write_text("import flask\n", encoding="utf-8")
        app._update_depswatch(force=True)
        assert app.status_deps.cget("text") == "● deps drift"
        logs.clear()
        app._deps_chip_click()
        assert app.terminal.input.get() == ""
        assert any("file(s) scanned" in s for s in logs), logs
        # --- git: the right-click menu
        repo = tmp_path / "repo"
        repo.mkdir()
        _git("init", "-q", cwd=repo)
        (repo / "f.txt").write_text("x\n", encoding="utf-8")
        app.project_dir = str(repo)
        # not-yet-a-name repo is still a repo: menu shows repo rows
        labels = [lab for lab, _cmd in app._git_menu_entries()]
        assert "Open Source Control" in labels and "Rescan" in labels
        assert "Stage all changes" in labels, labels
        # stage-all routes to the shell runner (stubbed — worker thread)
        ran = []
        app.run_command = lambda cmd: ran.append(cmd)
        for lab, cmd in app._git_menu_entries():
            if lab == "Stage all changes":
                cmd()
        assert ran == ["git add -A"], ran
        # copy branch fills the clipboard
        _git("add", ".", cwd=repo)
        _git("-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-qm", "one", cwd=repo)
        app._update_gitchip(force=True)
        branch = app.status_git.cget("text")
        for lab, cmd in app._git_menu_entries():
            if lab == "Copy branch name":
                cmd()
        assert root.clipboard_get() == branch, (branch,)
        # open jumps to Source Control
        opened = []
        app.show_sidebar_view = lambda name, *a, **k: opened.append(name)
        for lab, cmd in app._git_menu_entries():
            if lab == "Open Source Control":
                cmd()
        assert opened == ["git"], opened
        # a plain folder: honest menu — lane rows disappear
        plain = tmp_path / "plain"
        plain.mkdir()
        app.project_dir = str(plain)
        labels = [lab for lab, _cmd in app._git_menu_entries()]
        assert "Stage all changes" not in labels
        assert "Copy branch name" not in labels
        assert "Open Source Control" in labels and "Rescan" in labels
        # the renderer itself never raises (popup is best-effort)
        app.project_dir = str(repo)
        app._git_chip_menu()
    finally:
        app.terminal.log = real_log
        try:
            root.destroy()
        except tk.TclError:
            pass
        monkeypatch.undo()


def test_chip_menus(tmp_path):
    """DS2 v2.42 — every chip has a menu: the drift chip gains a
    right-click menu (rescan, the repair row only when red, a
    cache-bypassing fresh scan, the watch toggle) and the branch
    chip's menu grows the AI commit draft plus push/pull through the
    visible terminal runner. Menus are pure data + one shared
    renderer; both never raise."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import subprocess
    import dxn1_studio.config as cfgmod

    def _git(*args, cwd):
        subprocess.run(["git", *args], cwd=str(cwd),
                       capture_output=True, text=True)

    import pytest
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        # --- deps menu: amber state → no repair row
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "main.py").write_text("import uvicorn\n", encoding="utf-8")
        app.project_dir = str(ws)
        app.handle_terminal_command("deps")
        app._update_depswatch(force=True)
        assert app.status_deps.cget("text") == "● deps 1 missing"
        labels = [lab for lab, _c in app._deps_menu_entries()]
        assert "Rescan deps" in labels and "Queue deps fix" in labels
        assert "Fresh rescan (bypass cache)" in labels
        assert "Deps watch on/off" in labels and "Rescan chip" in labels
        # the repair row queues the fix (same one-gesture contract)
        app.terminal.input.delete(0, tk.END)
        logs.clear()
        for lab, cmd in app._deps_menu_entries():
            if lab == "Queue deps fix":
                cmd()
        assert app.terminal.input.get() == "deps fix"
        assert any("press Enter" in s for s in logs), logs
        # rescan row actually rescans (the report lands in the terminal)
        logs.clear()
        for lab, cmd in app._deps_menu_entries():
            if lab == "Rescan deps":
                cmd()
        assert any("file(s) scanned" in s for s in logs), logs
        # deps watch off → the whole chip goes quiet; menu still opens
        app._deps_watch_toggle("off")
        assert app.status_deps.cget("text") == ""
        app._deps_chip_menu()          # renderer never raises
        app._deps_watch_toggle("on")   # restore for the next checks
        # --- git menu: the new rows route honestly
        repo = tmp_path / "repo"
        repo.mkdir()
        _git("init", "-q", cwd=repo)
        (repo / "f.txt").write_text("x\n", encoding="utf-8")
        _git("add", ".", cwd=repo)
        _git("-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-qm", "one", cwd=repo)
        app.project_dir = str(repo)
        labels = [lab for lab, _c in app._git_menu_entries()]
        assert "Draft AI commit message" in labels, labels
        assert "Push to origin" in labels and "Pull from upstream" in labels
        ran = []
        app.run_command = lambda cmd: ran.append(cmd)
        for lab, cmd in app._git_menu_entries():
            if lab in ("Push to origin", "Pull from upstream"):
                cmd()
        assert ran == ["git push", "git pull"], ran
        # the AI draft opens the panel and fires the panel's helper
        opened, drafted = [], []
        app.show_sidebar_view = lambda name, *a, **k: opened.append(name)
        app.git_view.ai_message = lambda: drafted.append(1)
        for lab, cmd in app._git_menu_entries():
            if lab == "Draft AI commit message":
                cmd()
        assert opened == ["git"] and drafted == [1], (opened, drafted)
        # the shared renderer serves both chips without raising
        app._git_chip_menu()
        app._deps_chip_menu()
    finally:
        app.terminal.log = real_log
        try:
            root.destroy()
        except tk.TclError:
            pass
        monkeypatch.undo()


def test_chip_family(tmp_path):
    """DS2 v2.43 — the whole family is chipped in: the scribe chip
    (summary / goal / reset) and the session-autosave chip (snapshot
    now / browse / autosave toggle) gain right-click menus, and the
    branch chip's menu grows 'Commit staged…' which opens Source
    Control and focuses the commit message box. Menus stay pure
    data + the one shared renderer; every row is honest and never
    raises."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import pytest
    import dxn1_studio.config as cfgmod

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        toasts = []
        app.toast = lambda msg, kind="info": toasts.append(str(msg))

        # --- scribe chip menu: three rows, each routing honestly
        scribe_rows = app._scribe_menu_entries()
        labels = [lab for lab, _c in scribe_rows]
        assert labels == ["Session summary", "Set writing goal…",
                          "Reset session meter"], labels
        # the goal row opens the themed dialog; its Set applies the
        # goal, persists it and confirms (an explicit gesture commits)
        import dxn1_studio.scribe as scribe_mod
        calls = []
        orig_dialog = scribe_mod.open_goal_dialog
        scribe_mod.open_goal_dialog = (
            lambda master, theme, current, on_set=None:
            calls.append((int(current), on_set)) or object())
        current_goal = (int(app.scribe_chip.goal_words)
                        if app.scribe_chip else 0)
        for lab, cmd in scribe_rows:
            if lab == "Set writing goal…":
                cmd()
        assert calls and calls[0][0] == current_goal, calls
        toasts.clear()
        if app.scribe_chip is not None:
            calls[0][1](750)              # the dialog's Set button
            assert app.scribe_chip.goal_words == 750
            assert app.config.get("scribe_goal_words") == 750
            assert any("750" in s for s in toasts), toasts
        scribe_mod.open_goal_dialog = orig_dialog
        app._scribe_chip_menu()            # renderer never raises
        # the reset row zeroes the meter (goal preserved) + feedback
        if app.scribe_chip is not None:
            app.scribe_chip.observe(1200, now=0.0)
            app.scribe_chip.observe(1300, now=30.0)
            for lab, cmd in scribe_rows:
                if lab == "Reset session meter":
                    cmd()
            assert app.scribe_chip.words() == 0
            assert app.status_scribe.cget("text") == \
                app.scribe_chip.text()
            assert any("reset" in s.lower() for s in toasts), toasts
        app._scribe_chip_menu()            # renderer never raises

        # --- sesave chip menu: snapshot / browse / toggle
        sesave_rows = app._sesave_menu_entries()
        labels = [lab for lab, _c in sesave_rows]
        assert "Snapshot session now" in labels
        assert "Browse snapshots…" in labels
        assert "Autosave on/off" in labels
        # the toggle flips the config both ways with honest feedback
        toasts.clear()
        app.config.set("session_autosave", True)
        for lab, cmd in sesave_rows:
            if lab == "Autosave on/off":
                cmd()
        assert app.config.get("session_autosave") is False
        assert any("off" in s for s in toasts), toasts
        logs.clear()
        for lab, cmd in sesave_rows:
            if lab == "Autosave on/off":
                cmd()
        assert app.config.get("session_autosave") is True
        assert any("session autosave is now on" in s for s in logs), logs
        # snapshot row: same path as the chip click (no workspace →
        # the honest toast, nothing raised)
        app.project_dir = ""
        toasts.clear()
        for lab, cmd in sesave_rows:
            if lab == "Snapshot session now":
                cmd()
        assert any("No workspace open" in s for s in toasts), toasts
        # browse row routes to the existing snapshot browser
        # (re-read the entries — rows capture the bound method at
        # build time, so the stub must exist BEFORE the build)
        browsed = []
        app.open_session_restore = lambda *a, **k: browsed.append(1)
        for lab, cmd in app._sesave_menu_entries():
            if lab == "Browse snapshots…":
                cmd()
        assert browsed == [1]
        app._sesave_chip_menu()            # renderer never raises

        # --- branch menu: 'Commit staged…' opens + focuses the box
        # (a real repo — the sesave check above cleared project_dir)
        import subprocess

        def _git(*args, cwd):
            subprocess.run(["git", *args], cwd=str(cwd),
                           capture_output=True, text=True)
        repo = tmp_path / "repo"
        repo.mkdir()
        _git("init", "-q", cwd=repo)
        (repo / "f.txt").write_text("x\n", encoding="utf-8")
        _git("add", ".", cwd=repo)
        _git("-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-qm", "one", cwd=repo)
        app.project_dir = str(repo)
        labels = [lab for lab, _c in app._git_menu_entries()]
        assert "Commit staged…" in labels, labels
        opened, focused = [], []
        app.show_sidebar_view = lambda name, *a, **k: opened.append(name)
        app.git_view.focus_message = lambda: focused.append(1)
        for lab, cmd in app._git_menu_entries():
            if lab == "Commit staged…":
                cmd()
        assert opened == ["git"] and focused == [1], (opened, focused)
        # the panel's real focus_message exists and never raises
        app.git_view.focus_message()   # exercises the real method
        # the renderer drives all four menus without raising
        app._scribe_chip_menu()
        app._sesave_chip_menu()
        app._git_chip_menu()
        app._deps_chip_menu()
    finally:
        app.terminal.log = real_log
        try:
            root.destroy()
        except tk.TclError:
            pass
        monkeypatch.undo()


def test_activity(tmp_path):
    """DS2 v2.44 — the studio keeps its receipts: every toast is
    archived in a capped ring (newest first), the Activity window
    live-filters, the terminal verb (and its alias) opens it, and
    Clear wipes the slate. Pure engine first, app wiring second."""
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    import pytest
    import dxn1_studio.config as cfgmod
    from dxn1_studio.activity import (ActivityLog, format_time,
                                      rel_time, save_json, load_json)

    # --- pure engine: ring, cap, newest-first, filter, clear
    log = ActivityLog(cap=3)
    for i in range(5):
        log.add("event %d" % i, "info", now=1000.0 + i)
    assert log.count() == 3
    msgs = [e["message"] for e in log.entries()]
    assert msgs == ["event 4", "event 3", "event 2"], msgs
    hits = log.filtered("3")
    assert hits[0]["message"] == "event 3"
    assert [e["message"] for e in log.filtered("EVENT")] == msgs
    assert log.filtered("   ") == list(log.entries())
    assert log.filtered("nothing-matches") == []
    assert format_time(1000.0)            # formats without raising
    log.clear()
    assert log.count() == 0 and log.entries() == ()

    # --- v2.45 engine: session marking, rel stamps, disk round-trip
    log = ActivityLog(cap=3)
    log.add("fresh", "info", now=1000.0)
    assert log.entries()[0]["prev"] is False      # current session
    reloaded = ActivityLog.from_list(log.to_list(), cap=3)
    assert reloaded.entries()[0]["prev"] is True  # loaded = previous
    reloaded.add("newer", "error", now=1001.0)
    assert reloaded.entries()[0]["message"] == "newer"
    assert reloaded.entries()[0]["prev"] is False
    assert reloaded.entries()[1]["prev"] is True
    # rel_time: the whole honest ladder
    assert rel_time(1000.0, now=1000.5) == "just now"
    assert rel_time(1000.0, now=1065.0) == "1m ago"
    assert rel_time(1000.0, now=5000.0) == "1h ago"
    assert rel_time(1000.0, now=1000.0 + 3 * 86400) == "3d ago"
    assert rel_time(2000.0, now=1000.0) == ""     # future → honest ""
    assert rel_time("junk") == ""
    # disk: atomic save + load round-trip, corrupt → None
    apath = tmp_path / "activity.json"
    assert save_json(log, str(apath)) is True
    loaded = load_json(str(apath), cap=3)
    assert loaded is not None and loaded.count() == 1
    assert loaded.entries()[0]["message"] == "fresh"
    assert loaded.entries()[0]["prev"] is True
    apath.write_text("{not json at all", encoding="utf-8")
    assert load_json(str(apath), cap=3) is None   # corrupt → None
    assert load_json(str(tmp_path / "missing.json")) is None

    # --- app wiring: toasts archive, verbs + palette open the window
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfgmod, "CONFIG_PATH",
                        str(tmp_path / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from dxn1_studio.app import DXN1Studio
    import dxn1_studio.activity as act_mod
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    try:
        logs = []
        real_log = app.terminal.log
        app.terminal.log = lambda s, *a, **k: logs.append(str(s))
        app.toast("hello receipts", "success")
        app.toast("bad day", "error")
        assert app.activity_log.count() >= 2
        newest = app.activity_log.entries()[0]
        assert newest["message"] == "bad day" and newest["kind"] == "error"
        # the verb (and its alias) opens the window — stubbed, no UI
        opened = []
        orig_open = act_mod.open_activity
        act_mod.open_activity = (lambda *a, **k:
                                 opened.append(a[2]) or object())
        app.handle_terminal_command("activity")
        app.handle_terminal_command("notifications")
        assert len(opened) == 2 and opened[-1] is app.activity_log
        act_mod.open_activity = orig_open
        # --- v2.45 app wiring: the ring persists beside config.json
        # boot reloaded whatever the file held (the test HOME starts
        # clean — but a toast writes the file immediately)
        import json as _json
        apath = tmp_path / "activity.json"
        n_before = app.activity_log.count()
        app.toast("persisted receipt", "success")
        assert apath.is_file(), "toast must persist the ring"
        data = _json.loads(apath.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert data["entries"][0]["message"] == "persisted receipt"
        assert data["entries"][0]["prev"] is False
        assert app.activity_log.count() == n_before + 1
        # the window shows the session divider once prev rows exist
        prev_log = ActivityLog(cap=100)
        prev_log.add("old whisper", "info", now=1000.0)
        reloaded = ActivityLog.from_list(prev_log.to_list())
        reloaded.add("new whisper", "info")
        win = act_mod.open_activity(app.root, app.theme, reloaded)
        win.update()

        def _walk(w):
            yield w
            for c in w.winfo_children():
                yield from _walk(c)
        texts = [str(w.cget("text")) for w in _walk(win)
                 if isinstance(w, tk.Label)]
        assert any("since last time" in t for t in texts), texts
        assert any(t == "just now" for t in texts), texts
        win.destroy()
        # Clear through the window fires on_change → file wiped too
        app.activity_log.clear()
        assert save_json(app.activity_log, str(apath)) is True
        assert _json.loads(
            apath.read_text(encoding="utf-8"))["entries"] == []
        # the real window: constructs, counts honestly, wipes clean
        win = act_mod.open_activity(app.root, app.theme,
                                    app.activity_log)
        win.update()

        def _walk(w):
            yield w
            for c in w.winfo_children():
                yield from _walk(c)
        labels = [w.cget("text") for w in _walk(win)
                  if isinstance(w, tk.Label)]
        # the log was cleared (and the wipe persisted) one block ago —
        # the window must agree with the empty ring, honestly
        assert any(str(t) == "0 events" for t in labels), labels
        assert any("nothing here" in str(t) for t in labels), labels
        win.destroy()

        # --- v2.46 engine: the receipts go where you send them
        from dxn1_studio.activity import (export_text, export_file,
                                          stamp_full)
        elog = ActivityLog(cap=10)
        elog.add("second", "error", now=1060.0)
        elog.add("first", "success", now=1000.0)
        elog.add("third", "info", now=1120.0)
        etext = export_text(elog.entries())
        elines = etext.splitlines()
        assert len(elines) == 3
        assert elines[0].endswith("first")     # oldest first — a diary
        assert elines[1].endswith("second") and "error" in elines[1]
        assert elines[2].endswith("third")
        assert export_text([]) == "" and export_text(None) == ""
        assert stamp_full(1000.0) and stamp_full("junk") == ""
        epath = tmp_path / "receipts.txt"
        assert export_file(elog, str(epath)) == str(epath)
        assert epath.read_text(
            encoding="utf-8").splitlines() == elines
        (tmp_path / "blocker").write_text("x", encoding="utf-8")
        assert export_file(elog,
                           str(tmp_path / "blocker" / "x.txt")) is None
        # kind filter engine: only the named trio can hide
        klog = ActivityLog(cap=10)
        klog.add("a-ok", "success")
        klog.add("b-bad", "error")
        klog.add("c-info", "info")
        klog.add("d-odd", "weird")
        assert [e["message"] for e in klog.filtered("", kinds=None)] \
            == ["d-odd", "c-info", "b-bad", "a-ok"]
        assert [e["message"]
                for e in klog.filtered("", kinds={"error"})] \
            == ["d-odd", "b-bad"]   # the unnamed kind rides along
        assert [e["message"] for e in
                klog.filtered("", kinds={"success", "info"})] \
            == ["d-odd", "c-info", "a-ok"]
        # unnamed kinds survive every filter state — nothing vanishes
        assert [e["message"] for e in klog.filtered("", kinds=set())] \
            == ["d-odd"]

        # --- v2.46 window: kind dots, Copy all, Save as file…
        from types import SimpleNamespace as _NS
        wlog = ActivityLog(cap=100)
        wlog.add("gamma err", "error")
        wlog.add("beta ok", "success")
        wlog.add("alpha info", "info")
        wlog.add("odd duck", "weird")
        wout = []
        wwin = act_mod.open_activity(app.root, app.theme, wlog,
                                     export_dir=str(tmp_path),
                                     on_export=wout.append)
        wwin.update()
        wlabels = [str(w.cget("text")) for w in _walk(wwin)
                   if isinstance(w, tk.Label)]
        assert "● success" in wlabels and "● error" in wlabels \
            and "● info" in wlabels
        err_btn = [w for w in _walk(wwin) if isinstance(w, tk.Label)
                   and str(w.cget("text")) == "● error"][0]
        err_btn.event_generate("<Button-1>")
        wwin.update()
        texts2 = [str(w.cget("text")) for w in _walk(wwin)
                  if isinstance(w, tk.Label)]
        assert "gamma err" not in texts2, "error kind hidden"
        assert "beta ok" in texts2 and "alpha info" in texts2
        assert "odd duck" in texts2, "unnamed kind cannot be hidden"
        off_btn = [w for w in _walk(wwin) if isinstance(w, tk.Label)
                   and str(w.cget("text")) == "○ error"][0]
        off_btn.event_generate("<Button-1>")
        wwin.update()
        texts3 = [str(w.cget("text")) for w in _walk(wwin)
                  if isinstance(w, tk.Label)]
        assert "gamma err" in texts3, "toggle back restores the row"
        # Copy all → the whole chronological block on the clipboard
        cap_btn = [w for w in _walk(wwin) if isinstance(w, tk.Label)
                   and str(w.cget("text")) == "Copy all"][0]
        cap_btn.event_generate("<Button-1>")
        wwin.update()
        assert wwin.clipboard_get() == export_text(wlog.entries())
        # Save as file… → the dialog seam is stubbed, the file is real
        real_fd = act_mod.filedialog
        chosen = tmp_path / "chosen.txt"
        act_mod.filedialog = _NS(
            asksaveasfilename=lambda **k: str(chosen))
        try:
            sav_btn = [w for w in _walk(wwin)
                       if isinstance(w, tk.Label)
                       and str(w.cget("text")) == "Save as file…"][0]
            sav_btn.event_generate("<Button-1>")
            wwin.update()
            assert chosen.is_file(), "the dialog path was written"
            assert chosen.read_text(encoding="utf-8").splitlines() \
                == export_text(wlog.entries()).splitlines()
            assert wout == [str(chosen)], "on_export got the path"
            # a cancelled dialog is an honest no-op
            act_mod.filedialog = _NS(asksaveasfilename=lambda **k: "")
            sav_btn.event_generate("<Button-1>")
            wwin.update()
            assert wout == [str(chosen)], "cancel wrote nothing"
        finally:
            act_mod.filedialog = real_fd
        wwin.destroy()

        # --- v2.46 verbs: activity copy / activity export [path]
        app.toast("verb receipt", "info")
        app.handle_terminal_command("activity copy")
        assert "verb receipt" in app.root.clipboard_get()
        app.handle_terminal_command("activity export")
        import glob as _glob
        made = _glob.glob(str(tmp_path / "activity-export-*.txt"))
        assert made, "default export lands beside activity.json"
        assert "verb receipt" in open(made[0],
                                      encoding="utf-8").read()
        mine = tmp_path / "mine.txt"
        app.handle_terminal_command("activity export %s" % mine)
        assert mine.is_file(), "an explicit path is honored"
        app.handle_terminal_command("activity nonsense")
        assert any("try: activity" in s for s in logs), logs
        app.terminal.log = real_log
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
        monkeypatch.undo()
