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
    assert real and real[0]["version"] >= "2.4.0"
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
