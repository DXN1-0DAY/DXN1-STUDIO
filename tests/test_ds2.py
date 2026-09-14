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


# -------------------------------------------------------------- standalone
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "--no-header"]))
