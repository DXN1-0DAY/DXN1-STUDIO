"""DXN1 STUDIO — Plugin API v1.

A small, explicit, approval-gated plugin system. Plugins live in

* ``<workspace>/.dxn1/plugins/``      (per-workspace), or
* ``~/.dxn1-studio/plugins/``         (global)

Each plugin is a folder containing a ``plugin.json`` manifest and a
``plugin.py`` entry module. On first load the studio shows the user the
plugin's name, version and permissions and asks for approval — exactly
once, remembered by the manifest's sha256 (any change to the plugin's
code re-triggers the prompt).

The host (``app.DXN1Studio``) hands the registry a *context factory*
so plugins never import app internals; they receive a plain dict:

``{"path":…, "text":…, "selection":…, "workspace":…}``

Plugin surface (the ``api`` object handed to ``register(api)``):

=====================================  ===============================
``api.register_command(label, fn)``    palette-runnable command; ``fn``
                                       receives the context dict
``api.on_save(fn)``                    fired after a file save
``api.on_open(fn)``                    fired when a file opens
``api.on_commit(fn)``                  fired with the commit message
``api.add_status_item(key, fn)``       statusbar text; ``fn`` gets ctx
``api.get_setting(key, default)``      namespaced config read
``api.set_setting(key, value)``        namespaced config write
``api.log(msg)``                       routed to the studio log
=====================================  ===============================

Everything in this module fails soft: a broken plugin is reported and
skipped, never allowed to break the studio.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time

from . import APP_NAME

# --------------------------------------------------------------- discovery
WORKSPACE_PLUGIN_DIR = os.path.join(".dxn1", "plugins")
GLOBAL_PLUGIN_DIR = os.path.join(os.path.expanduser("~"), ".dxn1-studio",
                                 "plugins")

MANIFEST = "plugin.json"
ENTRY = "plugin.py"


def plugin_dirs(workspace=None):
    """Plugin folders to scan, workspace first (wins on name clash)."""
    dirs = []
    if workspace:
        dirs.append(("workspace", os.path.join(workspace,
                                               WORKSPACE_PLUGIN_DIR)))
    dirs.append(("global", GLOBAL_PLUGIN_DIR))
    return dirs


def discover(workspace=None):
    """Scan plugin dirs -> list of manifest dicts (validated, deduped by
    name; workspace copies shadow global ones). Broken folders are
    reported as ``{"_error": …}`` entries so the manager can show them."""
    seen = set()
    out = []
    for scope, base in plugin_dirs(workspace):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if not os.path.isdir(folder):
                continue
            mpath = os.path.join(folder, MANIFEST)
            if not os.path.isfile(mpath):
                out.append({"_error": f"{name}: no {MANIFEST}",
                            "_folder": folder, "_scope": scope})
                continue
            try:
                with open(mpath, "r", encoding="utf-8") as fh:
                    manifest = json.load(fh)
                problems = validate_manifest(manifest)
                if problems:
                    out.append({"_error": f"{name}: {problems[0]}",
                                "_folder": folder, "_scope": scope})
                    continue
            except (OSError, ValueError) as exc:
                out.append({"_error": f"{name}: invalid manifest ({exc})",
                            "_folder": folder, "_scope": scope})
                continue
            key = manifest["name"].lower()
            if key in seen:
                continue          # workspace copy already registered
            seen.add(key)
            manifest["_folder"] = folder
            manifest["_scope"] = scope
            manifest["_fingerprint"] = _fingerprint(manifest, folder)
            out.append(manifest)
    return out


def validate_manifest(manifest):
    """Return a list of human-readable problems (empty = valid)."""
    problems = []
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]
    name = manifest.get("name")
    if not name or not isinstance(name, str):
        problems.append("'name' is required")
    elif len(name) > 48:
        problems.append("'name' must be <= 48 chars")
    if not isinstance(manifest.get("version", "0.0.0"), str):
        problems.append("'version' must be a string")
    hooks = manifest.get("hooks", [])
    if not isinstance(hooks, list):
        problems.append("'hooks' must be a list")
    cmds = manifest.get("commands", [])
    if not isinstance(cmds, list):
        problems.append("'commands' must be a list")
    else:
        for c in cmds:
            if not isinstance(c, dict) or not c.get("label"):
                problems.append("every command needs a 'label'")
                break
    return problems


def _fingerprint(manifest, folder):
    """sha256 over manifest + entry source — approval keys off this."""
    h = hashlib.sha256()
    h.update(json.dumps({k: v for k, v in manifest.items()
                         if not k.startswith("_")}, sort_keys=True)
             .encode("utf-8", "replace"))
    entry = os.path.join(folder, ENTRY)
    if os.path.isfile(entry):
        try:
            with open(entry, "rb") as fh:
                h.update(fh.read())
        except OSError:
            pass
    return h.hexdigest()[:32]


# ------------------------------------------------------------------ loader
def _load_module(manifest, log):
    folder = manifest["_folder"]
    entry = os.path.join(folder, ENTRY)
    if not os.path.isfile(entry):
        return None                       # manifest-only plugin is legal
    mod_name = f"dxn1_plugin_{manifest['name'].lower().replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(mod_name, entry)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {entry}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(mod_name, None)
        raise
    if not hasattr(module, "register"):
        raise AttributeError(f"{ENTRY} must define register(api)")
    return module


class PluginAPI:
    """The object handed to a plugin's ``register(api)``."""

    def __init__(self, manifest, registry):
        self.manifest = manifest
        self._registry = registry
        self.name = manifest["name"]

    # -- host-provided surface ------------------------------------------
    def register_command(self, label, fn):
        self._registry.commands.append(
            {"plugin": self.name, "label": str(label), "fn": fn})

    def on_save(self, fn):
        self._registry.hooks.setdefault("save", []).append(
            (self.name, fn))

    def on_open(self, fn):
        self._registry.hooks.setdefault("open", []).append(
            (self.name, fn))

    def on_commit(self, fn):
        self._registry.hooks.setdefault("commit", []).append(
            (self.name, fn))

    def add_status_item(self, key, fn):
        self._registry.status_items[(self.name, str(key))] = fn

    # -- settings are namespaced per plugin ------------------------------
    def get_setting(self, key, default=None):
        return self._registry.config.get(
            f"plugin.{self.name}.{key}", default)

    def set_setting(self, key, value):
        self._registry.config.set(f"plugin.{self.name}.{key}", value)

    def log(self, msg):
        self._registry.log(f"[plugin:{self.name}] {msg}")


class PluginRegistry:
    """Loads, approves, fires and unloads plugins."""

    def __init__(self, config=None, log=None):
        try:
            if config is None:
                from .config import Config
                config = Config()
        except Exception:               # noqa: BLE001 — headless safety
            config = None
        self.config = config
        self._log = log or (lambda msg: None)
        self.plugins = {}               # name -> {"manifest", "module", "api"}
        self.errors = []                # (name, reason)
        self.commands = []
        self.hooks = {}                 # hook -> [(plugin, fn)]
        self.status_items = {}          # (plugin, key) -> fn

    # -- approval bookkeeping -------------------------------------------
    def approved(self, manifest):
        if self.config is None:
            return False
        approved = self.config.get("approved_plugins") or {}
        return approved.get(manifest["name"]) == manifest["_fingerprint"]

    def approve(self, manifest):
        if self.config is not None:
            approved = dict(self.config.get("approved_plugins") or {})
            approved[manifest["name"]] = manifest["_fingerprint"]
            self.config.set("approved_plugins", approved)

    def revoke(self, name):
        if self.config is not None:
            approved = dict(self.config.get("approved_plugins") or {})
            approved.pop(name, None)
            self.config.set("approved_plugins", approved)
        self.unload(name)

    # -- lifecycle --------------------------------------------------------
    def load(self, manifest):
        """Import + register one plugin. Returns True on success."""
        name = manifest["name"]
        if name in self.plugins:
            return True
        try:
            module = _load_module(manifest, self._log)
            api = PluginAPI(manifest, self)
            if module is not None:
                module.register(api)
            self.plugins[name] = {"manifest": manifest,
                                  "module": module, "api": api}
            self._log(f"plugin loaded: {name} "
                      f"v{manifest.get('version', '0')} "
                      f"({manifest['_scope']})")
            return True
        except Exception as exc:        # noqa: BLE001 — never crash host
            self.errors.append((name, str(exc)))
            self._log(f"plugin failed: {name} — {exc}")
            return False

    def unload(self, name):
        info = self.plugins.pop(name, None)
        if not info:
            return False
        self.commands = [c for c in self.commands
                         if c["plugin"] != name]
        for hook, entries in list(self.hooks.items()):
            self.hooks[hook] = [e for e in entries if e[0] != name]
            if not self.hooks[hook]:
                del self.hooks[hook]
        for key in [k for k in self.status_items if k[0] == name]:
            del self.status_items[key]
        self._log(f"plugin unloaded: {name}")
        return True

    def reload(self, name):
        info = self.plugins.get(name)
        manifest = info["manifest"] if info else None
        self.unload(name)
        target = manifest
        if target is None:
            for m in discover(_ws_of(name)):
                if m.get("name") == name and not m.get("_error"):
                    target = m
                    break
        return bool(target) and self.load(target)

    # -- loading all discoverable plugins ---------------------------------
    def load_all(self, workspace=None, request_approval=None):
        """Load every valid plugin. ``request_approval(manifest)`` is the
        host's consent UI; None means only already-approved load."""
        loaded = []
        for manifest in discover(workspace):
            if manifest.get("_error"):
                self.errors.append((manifest.get("_error"), ""))
                continue
            name = manifest["name"]
            if name in self.plugins:
                continue
            if self.approved(manifest):
                if self.load(manifest):
                    loaded.append(name)
            elif request_approval is not None:
                if request_approval(manifest):
                    self.approve(manifest)
                    if self.load(manifest):
                        loaded.append(name)
                else:
                    self._log(f"plugin declined: {name}")
        return loaded

    # -- firing -----------------------------------------------------------
    def _context(self, **kw):
        return kw

    def fire_save(self, path, text, workspace=None):
        ctx = self._context(event="save", path=path, text=text,
                            workspace=workspace)
        for _, fn in self.hooks.get("save", []):
            self._safe(fn, ctx)

    def fire_open(self, path, text, workspace=None):
        ctx = self._context(event="open", path=path, text=text,
                            workspace=workspace)
        for _, fn in self.hooks.get("open", []):
            self._safe(fn, ctx)

    def fire_commit(self, message, workspace=None):
        ctx = self._context(event="commit", message=message,
                            workspace=workspace)
        for _, fn in self.hooks.get("commit", []):
            self._safe(fn, ctx)

    def status_text(self, workspace=None, path=None):
        """Current values for every registered status item."""
        out = {}
        for (plugin, key), fn in self.status_items.items():
            ctx = self._context(workspace=workspace, path=path)
            val = self._safe(fn, ctx, default="")
            if val:
                out[(plugin, key)] = str(val)
        return out

    def _safe(self, fn, ctx, default=None):
        try:
            return fn(ctx)
        except Exception as exc:        # noqa: BLE001
            self._log(f"plugin hook error: {exc}")
            return default


# shared registry instance (app.py wires it up defensively)
_default_registry = None


def get_registry(config=None, log=None):
    global _default_registry
    if _default_registry is None:
        _default_registry = PluginRegistry(config=config, log=log)
    elif config is not None and _default_registry.config is None:
        _default_registry.config = config
    return _default_registry


def _ws_of(_name):
    """Best-effort workspace hint for reload (v1: global scope only)."""
    return None


# ------------------------------------------------------------- manager UI
_PM_C = {"bg": "#0d1117", "card": "#131a22", "border": "#232c3d",
         "text": "#e6edf3", "secondary": "#9aa7b8", "muted": "#6e7a8a",
         "ok": "#3fb950", "warn": "#d29922", "bad": "#f85149"}


def open_manager(master, theme, config=None, workspace=None, on_log=None,
                 on_commands_changed=None):
    """Open the Plugin Manager window."""
    return PluginManager(master, theme, config, workspace,
                         on_log=on_log,
                         on_commands_changed=on_commands_changed)


class PluginManager:
    """List / approve / disable / reload plugins; open the plugin folder;
    show the command surface each plugin contributes."""

    def __init__(self, master, theme, config=None, workspace=None,
                 on_log=None, on_commands_changed=None):
        import tkinter as tk
        from tkinter import messagebox

        self.tk = tk
        self.theme = theme
        self.accent = getattr(theme, "accent", "#7c3aed")
        self.registry = get_registry(config=config,
                                     log=on_log or (lambda m: None))
        self.workspace = workspace
        self.on_commands_changed = on_commands_changed
        self.msgbox = messagebox

        self.win = tk.Toplevel(master)
        self.win.title(f"{APP_NAME} — Plugin Manager")
        self.win.configure(bg=_PM_C["bg"])
        self.win.transient(master)
        self.win.resizable(False, False)
        self.win.bind("<Escape>", lambda e: self.win.destroy())

        head = tk.Frame(self.win, bg=_PM_C["bg"])
        head.pack(fill="x", padx=22, pady=(16, 0))
        tk.Label(head, text="Plugins", bg=_PM_C["bg"], fg=_PM_C["text"],
                 font=("sans-serif", 14, "bold")).pack(side="left")
        self.count = tk.Label(head, text="", bg=_PM_C["bg"],
                              fg=_PM_C["muted"], font=("sans-serif", 9))
        self.count.pack(side="left", padx=(10, 0))
        close = tk.Label(head, text="✕", bg=_PM_C["bg"], fg=_PM_C["muted"],
                         font=("sans-serif", 11, "bold"), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.win.destroy())

        tk.Label(self.win,
                 text="Plugins get one approval prompt, remembered by a "
                      "code fingerprint — any edit re-asks.",
                 bg=_PM_C["bg"], fg=_PM_C["secondary"],
                 font=("sans-serif", 9)).pack(anchor="w", padx=22)

        self.list_box = tk.Frame(self.win, bg=_PM_C["bg"])
        self.list_box.pack(fill="both", expand=True, padx=22, pady=(10, 4))

        btns = tk.Frame(self.win, bg=_PM_C["bg"])
        btns.pack(fill="x", padx=22, pady=(6, 16))
        scan = tk.Label(btns, text="Scan & load", bg=_PM_C["card"],
                        fg=_PM_C["text"], font=("sans-serif", 9, "bold"),
                        padx=12, pady=6, cursor="hand2")
        scan.pack(side="left")
        scan.bind("<Button-1>", lambda e: self.scan())
        folder = tk.Label(btns, text="Open plugin folder", bg=_PM_C["card"],
                          fg=_PM_C["text"], font=("sans-serif", 9, "bold"),
                          padx=12, pady=6, cursor="hand2")
        folder.pack(side="left", padx=(8, 0))
        folder.bind("<Button-1>", lambda e: self._open_folder())
        self.status = tk.Label(btns, text="", bg=_PM_C["bg"],
                               fg=_PM_C["muted"], font=("sans-serif", 8))
        self.status.pack(side="right")

        self.refresh()
        self._center()

    # ---------------------------------------------------------------- ui
    def refresh(self):
        tk = self.tk
        for w in self.list_box.winfo_children():
            w.destroy()
        ws = self.workspace
        manifests = discover(ws)
        live = self.registry.plugins
        if not manifests:
            tk.Label(self.list_box,
                     text="No plugins found.\n\nDrop a folder with "
                          "plugin.json + plugin.py into\n"
                          f"{GLOBAL_PLUGIN_DIR}\nor your workspace's "
                          f".dxn1/plugins/ — see PLUGINS.md.",
                     bg=_PM_C["bg"], fg=_PM_C["muted"],
                     font=("sans-serif", 9), justify="left"
                     ).pack(anchor="w", pady=8)
        n_cmds = len(self.registry.commands)
        self.count.config(text=f"{len(manifests)} found · "
                               f"{len(live)} active · {n_cmds} commands")
        for m in manifests:
            self._row(m)
        errs = self.registry.errors
        if errs:
            tk.Label(self.list_box, text="Broken plugins:",
                     bg=_PM_C["bg"], fg=_PM_C["bad"],
                     font=("sans-serif", 9, "bold")
                     ).pack(anchor="w", pady=(8, 0))
            for name, why in errs[-4:]:
                tk.Label(self.list_box, text=f"  ✗ {name} — {why}",
                         bg=_PM_C["bg"], fg=_PM_C["bad"],
                         font=("sans-serif", 8)).pack(anchor="w")

    def _row(self, manifest):
        tk = self.tk
        if manifest.get("_error"):
            row = tk.Frame(self.list_box, bg=_PM_C["card"],
                           highlightthickness=1,
                           highlightbackground=_PM_C["border"])
            row.pack(fill="x", pady=3, ipady=4)
            tk.Label(row, text=f"✗ {manifest['_error']}", bg=_PM_C["card"],
                     fg=_PM_C["bad"], font=("sans-serif", 9)
                     ).pack(anchor="w", padx=12)
            return
        name = manifest["name"]
        active = name in self.registry.plugins
        approved = self.registry.approved(manifest)

        row = tk.Frame(self.list_box, bg=_PM_C["card"],
                       highlightthickness=1,
                       highlightbackground=_PM_C["border"])
        row.pack(fill="x", pady=3, ipady=5)

        head = tk.Frame(row, bg=_PM_C["card"])
        head.pack(fill="x", padx=12)
        dot = _PM_C["ok"] if active else (_PM_C["warn"] if approved
                                          else _PM_C["muted"])
        tk.Label(head, text="●", bg=_PM_C["card"], fg=dot,
                 font=("sans-serif", 9)).pack(side="left")
        tk.Label(head, text=f" {name}  v{manifest.get('version', '0')}",
                 bg=_PM_C["card"], fg=_PM_C["text"],
                 font=("sans-serif", 10, "bold")).pack(side="left")
        tk.Label(head, text=manifest.get("_scope", ""),
                 bg=_PM_C["card"], fg=_PM_C["muted"],
                 font=("sans-serif", 8)).pack(side="left", padx=(8, 0))
        state = tk.Label(head, text="active" if active else
                         ("approved" if approved else "not approved"),
                         bg=_PM_C["card"],
                         fg=dot, font=("sans-serif", 8))
        state.pack(side="right")

        desc = manifest.get("description") or "No description."
        tk.Label(row, text=desc, bg=_PM_C["card"], fg=_PM_C["secondary"],
                 font=("sans-serif", 8), wraplength=520,
                 justify="left").pack(anchor="w", padx=12, pady=(2, 0))

        actions = tk.Frame(row, bg=_PM_C["card"])
        actions.pack(fill="x", padx=12, pady=(4, 2))
        if active:
            self._action(actions, "Reload", lambda n=name: (
                self.registry.reload(n), self.refresh()))
            self._action(actions, "Disable", lambda n=name: (
                self.registry.unload(n), self.refresh()))
        elif approved:
            self._action(actions, "Enable", lambda m=manifest: (
                self.registry.load(m), self.refresh()))
        else:
            self._action(actions, "Approve & enable",
                         lambda m=manifest: self._ask_and_load(m))
        cmds = [c["label"] for c in self.registry.commands
                if c["plugin"] == name]
        hooks = manifest.get("hooks") or []
        info = " · ".join(filter(None, [
            f"{len(cmds)} commands" if cmds else "",
            ", ".join(hooks) if hooks else "",
        ]))
        if info:
            tk.Label(row, text=info, bg=_PM_C["card"], fg=_PM_C["muted"],
                     font=("sans-serif", 8)).pack(anchor="w", padx=12)

    def _action(self, parent, label, cmd):
        tk = self.tk
        btn = tk.Label(parent, text=label, bg=_PM_C["bg"],
                       fg=self.accent, font=("sans-serif", 8, "bold"),
                       padx=8, pady=2, cursor="hand2")
        btn.pack(side="left", padx=(0, 6))
        btn.bind("<Button-1>", lambda e: cmd())

    def _center(self):
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        mx = self.master_root_x() + (self._master_width() - w) // 2
        my = self.master_root_y() + (self._master_height() - h) // 3
        self.win.geometry(f"+{max(0, mx)}+{max(0, my)}")

    def master_root_x(self):
        try:
            return self.win.master.winfo_rootx()
        except Exception:               # noqa: BLE001
            return 0

    def master_root_y(self):
        try:
            return self.win.master.winfo_rooty()
        except Exception:               # noqa: BLE001
            return 0

    def _master_width(self):
        try:
            return self.win.master.winfo_width()
        except Exception:               # noqa: BLE001
            return 800

    def _master_height(self):
        try:
            return self.win.master.winfo_height()
        except Exception:               # noqa: BLE001
            return 600

    # ------------------------------------------------------------ actions
    def _ask_and_load(self, manifest):
        name = manifest["name"]
        hooks = manifest.get("hooks") or []
        cmds = manifest.get("commands") or []
        perms = []
        if "save" in hooks:
            perms.append("run code when you save files")
        if "open" in hooks:
            perms.append("run code when files open")
        if "commit" in hooks:
            perms.append("run code on git commits")
        if cmds:
            perms.append(f"add {len(cmds)} command(s) to the palette")
        if "status" in hooks:
            perms.append("show text in the status bar")
        body = (f"Allow “{name}” v{manifest.get('version', '0')} "
                f"({manifest.get('author') or 'unknown author'}) to:\n\n"
                + "\n".join(f"  • {p}" for p in perms)
                + "\n\nIt runs locally with the studio's permissions. "
                  "Only approve plugins you trust.")
        if not perms:
            body = (f"Load “{name}” v{manifest.get('version', '0')}?\n\n"
                    "It declares no extra permissions.")
        ok = self.msgbox.askyesno("Approve plugin?", body,
                                  icon="warning")
        if ok:
            self.registry.approve(manifest)
            self.registry.load(manifest)
        else:
            self.registry.log(f"plugin declined: {name}")
        self.refresh()

    def scan(self):
        loaded = self.registry.load_all(workspace=self.workspace)
        self.status.config(
            text=f"scan done · {len(loaded)} loaded"
                 if loaded else "scan done · nothing new",
            fg=self.accent)
        self.refresh()
        if self.on_commands_changed:
            try:
                self.on_commands_changed()
            except Exception:           # noqa: BLE001
                pass

    def _open_folder(self):
        import subprocess
        target = GLOBAL_PLUGIN_DIR
        if self.workspace:
            target = os.path.join(self.workspace, WORKSPACE_PLUGIN_DIR)
        os.makedirs(target, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(target)    # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except OSError as exc:
            self.status.config(text=f"cannot open folder: {exc}",
                               fg=_PM_C["bad"])


# ------------------------------------------------------------ sample pack
def write_sample_plugins(root_dir):
    """Write the DS2 sample plugins into ``root_dir`` (idempotent).
    Returns the list of created plugin folder names."""
    samples = {
        "insert-header": {
            "manifest": {
                "name": "insert-header",
                "version": "1.0.0",
                "description": "Adds a palette command that inserts a "
                               "file header comment with the date.",
                "author": "DXN1 STUDIO",
                "commands": [{"label": "Insert file header"}],
            },
            "plugin.py": '''"""DS2 sample: insert a dated file header."""
import time


def register(api):
    api.register_command("Insert file header", _insert)


def _insert(ctx):
    """Commands receive a context dict; we return a snippet for the
    host to insert when it can (the palette wiring shows a toast)."""
    name = (ctx or {}).get("path") or "untitled.py"
    return "# {} — edited {}\\n".format(
        name.rsplit("/", 1)[-1], time.strftime("%Y-%m-%d %H:%M"))
''',
        },
        "commit-lint": {
            "manifest": {
                "name": "commit-lint",
                "version": "1.0.0",
                "description": "Logs a reminder when a commit message "
                               "is very short.",
                "author": "DXN1 STUDIO",
                "hooks": ["commit"],
            },
            "plugin.py": '''"""DS2 sample: gentle commit-message lint."""


def register(api):
    api.on_commit(_check)


def _check(ctx):
    msg = ((ctx or {}).get("message") or "").strip()
    if len(msg) < 10:
        api_log("commit message is short — future-you wants details")
    else:
        api_log("commit message looks good")


def api_log(_m):
    # v1 sample: printing keeps the plugin dependency-free
    print("[commit-lint]", _m)
''',
        },
        "session-clock": {
            "manifest": {
                "name": "session-clock",
                "version": "1.0.0",
                "description": "Adds a command that reports how long "
                               "this studio session has been running.",
                "author": "DXN1 STUDIO",
                "commands": [{"label": "Session clock"}],
            },
            "plugin.py": '''"""DS2 sample: session uptime."""
import time

_STARTED = time.time()


def register(api):
    api.register_command("Session clock", _uptime)


def _uptime(ctx):
    mins = int((time.time() - _STARTED) // 60)
    return f"session uptime: {mins} min"
''',
        },
    }
    created = []
    for name, files in samples.items():
        folder = os.path.join(root_dir, name)
        os.makedirs(folder, exist_ok=True)
        mpath = os.path.join(folder, MANIFEST)
        if not os.path.exists(mpath):
            with open(mpath, "w", encoding="utf-8") as fh:
                json.dump(files["manifest"], fh, indent=2)
            with open(os.path.join(folder, ENTRY), "w",
                      encoding="utf-8") as fh:
                fh.write(files["plugin.py"])
            created.append(name)
    return created
