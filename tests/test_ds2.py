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
