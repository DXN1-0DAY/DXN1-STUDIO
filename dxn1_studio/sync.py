"""DXN1 STUDIO — settings sync (DS2 v2.1).

Your setup, everywhere: export the safe subset of studio preferences to
a private GitHub gist and pull them back on any machine. The bundle
never contains secrets — API keys, tokens and agent brain details stay
home; theme, accent, editor behaviour, language and prompt presets
travel.

Auth reuses the GitHub CLI's login (``gh auth token``) — no extra
accounts, nothing to paste. If ``gh`` isn't installed or logged in,
sync reports it honestly and does nothing.
"""

import json
import os
import subprocess
import urllib.request

from . import APP_NAME, APP_VERSION

SYNC_FILE = "dxn1-studio-settings.json"
GIST_DESCRIPTION = f"{APP_NAME} settings sync (do not edit by hand)"

# the safe subset — keys that travel. Everything else stays local.
SYNC_KEYS = ("theme", "accent", "editor_font_size", "word_wrap",
             "auto_save", "splash_enabled", "hub_on_startup",
             "agents_prompt_preset", "agents_persona", "agents_enabled",
             "custom_theme_name", "custom_theme", "language",
             "pinned_projects")


def _run(args, timeout=20, input_text=None):
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=timeout, input=input_text)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return False, "", str(exc)
    return proc.returncode == 0, proc.stdout, proc.stderr.strip()


def gh_token():
    """Token from the GitHub CLI, or empty."""
    ok, out, _ = _run(["gh", "auth", "token"])
    return out.strip() if ok and out.strip() else ""


def export_bundle(config):
    """The portable settings dict (never secrets)."""
    bundle = {"app": APP_NAME, "version": APP_VERSION, "settings": {}}
    for key in SYNC_KEYS:
        value = config.get(key)
        if value is not None:
            bundle["settings"][key] = value
    return bundle


def apply_bundle(config, bundle):
    """Apply a synced bundle. Returns the list of keys applied."""
    if not isinstance(bundle, dict):
        return []
    settings = bundle.get("settings") or {}
    applied = []
    for key, value in settings.items():
        if key in SYNC_KEYS:
            try:
                config.set(key, value, save=False)
                applied.append(key)
            except Exception:
                continue
    try:
        config.save()
    except Exception:
        pass
    return applied


# ------------------------------------------------------------- gist io
def find_sync_gist(token):
    """The gist id carrying our settings file, or None."""
    ok, out, err = _run(["gh", "gist", "list", "--limit", "50"])
    if not ok:
        return None
    for line in out.splitlines():
        # format: <id>  <description>  (files)
        if SYNC_FILE in line:
            return line.split()[0]
    return None


def push(config, token=None):
    """Export settings to the sync gist. Returns (ok, message)."""
    token = token or gh_token()
    if not token:
        return False, "no GitHub CLI login — run: gh auth login"
    bundle = export_bundle(config)
    body = json.dumps(bundle, ensure_ascii=False, indent=2)
    gist_id = find_sync_gist(token)
    if gist_id:
        ok, out, err = _run(["gh", "gist", "edit", gist_id,
                             SYNC_FILE, "--desc", GIST_DESCRIPTION],
                            input_text=body)
        return (ok, "settings synced to existing gist ✓" if ok
                else f"gist update failed: {err[:80]}")
    ok, out, err = _run(["gh", "gist", "create", "--desc",
                         GIST_DESCRIPTION, "-"],
                        input_text=body)
    # `gh gist create -` reads stdin, prints the URL
    if ok and out.strip():
        return True, "settings pushed to a new private gist ✓"
    return False, f"gist create failed: {err[:80]}"


def pull(config, token=None):
    """Pull settings from the sync gist. Returns (ok, message, applied)."""
    token = token or gh_token()
    if not token:
        return False, "no GitHub CLI login — run: gh auth login", []
    gist_id = find_sync_gist(token)
    if not gist_id:
        return False, "no sync gist yet — push first", []
    ok, out, err = _run(["gh", "gist", "view", gist_id,
                         "--files", "--raw"], timeout=30)
    if not ok:
        # fall back to the API route for raw content
        try:
            req = urllib.request.Request(
                f"https://api.github.com/gists/{gist_id}",
                headers={"Authorization": f"token {token}",
                         "User-Agent": APP_NAME})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.load(resp)
            content = (data.get("files", {})
                       .get(SYNC_FILE, {}).get("content", ""))
        except Exception as exc:
            return False, f"gist read failed: {exc}", []
    else:
        content = out
    try:
        # gh --raw prints metadata; find the JSON blob defensively
        start = content.find('{"app"')
        bundle = json.loads(content[start:content.rfind("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return False, "sync gist content unreadable", []
    applied = apply_bundle(config, bundle)
    if applied:
        return True, f"pulled {len(applied)} settings ✓", applied
    return False, "nothing to apply", []


def sync_status():
    """(logged_in, has_gist) for the settings dialog line."""
    token = gh_token()
    if not token:
        return False, False
    return True, find_sync_gist(token) is not None
