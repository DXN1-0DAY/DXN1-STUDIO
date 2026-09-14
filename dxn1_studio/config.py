"""DXN1 STUDIO — configuration persistence.

All user preferences (display name, theme, accent colour, onboarding state,
agent brains, editor behaviour) live in a single JSON file under
~/.dxn1-studio/config.json so the IDE can detect a first launch and
personalise every session after it.
"""

import json
import os
from datetime import datetime

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".dxn1-studio")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    "version": "2.4.0",
    "onboarded": False,      # has the welcome wizard been completed?
    "tour_done": False,      # has the interactive tour been finished/skipped?
    "name": "",              # display name used in greetings
    "theme": "dark",         # "dark" | "light"
    "accent": "violet",      # violet | cyan | green | orange | rose | blue
    "launch_count": 0,
    "first_launch": None,    # ISO timestamp of first run
    "last_launch": None,     # ISO timestamp of most recent run
    # --- editor behaviour ------------------------------------------------
    "editor_font_size": 11,  # mono font size, clamped 8..20
    "word_wrap": False,      # soft-wrap long lines in the editor
    "auto_save": False,      # save the active buffer after idle moments
    # --- hub, splash ------------------------------------------------------
    "splash_enabled": True,  # boot splash (logo card) before launch
    "hub_on_startup": True,  # start every session at the Project Hub
    "recent_projects": [],   # [{path, kind, opened}] — hub recents
    "last_project": "",      # most recently opened workspace path
    # --- wizard -----------------------------------------------------------
    "wizard_first_kind": "",     # project type picked in the wizard (or "")
    # --- DXN1 Agents ------------------------------------------------------
    "agents_enabled": False,      # DXN1 Agents opted in via the wizard
    "agents_ask_edits": True,     # confirm before the agent writes files
    "agents_ask_commands": True,  # confirm before the agent runs commands
    "agents_backend": "local",    # local | free | byok | github | kilo
    "agents_provider": "openrouter",  # BYOK preset id (see llm.PRESETS)
    "agents_base_url": "",        # BYOK custom endpoint override
    "agents_api_key": "",         # BYOK key — stored locally only
    "agents_model": "",           # model id for the active backend
    "agents_github_key": "",      # optional PAT (else gh auth token)
    "agents_kilo_url": "",        # Kilo gateway endpoint override
    "agents_kilo_key": "",        # Kilo token
    "agents_system_prompt": "",   # extra persona instructions
    "agents_prompt_preset": "default",  # default | concise | senior | custom
    "agents_persona": "default",  # one-click persona (see agent.PERSONAS)
    "agents_max_steps": 12,       # tool-loop steps per message
    "agents_setup_pending": "",   # "" | "kilo" | "byok" — show Connect card
    "agents_tokens_used": 0,      # lifetime total reported by providers
}


class Config:
    """Tiny JSON-backed key/value store with safe defaults."""

    def __init__(self):
        self._data = dict(DEFAULTS)
        self.load()

    # ------------------------------------------------------------------ io
    def load(self):
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                    stored = json.load(fh)
                if isinstance(stored, dict):
                    self._data.update(stored)
        except (OSError, json.JSONDecodeError):
            # Corrupt config -> fall back to defaults, never crash the IDE.
            self._data = dict(DEFAULTS)

    def save(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2)
        except OSError:
            pass  # read-only home etc. — IDE keeps running with defaults

    # ------------------------------------------------------------- access
    def get(self, key, default=None):
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value, save=True):
        self._data[key] = value
        if save:
            self.save()

    # --------------------------------------------------------- session mgmt
    def register_launch(self):
        """Update launch bookkeeping. Returns True when this is the first run."""
        now = datetime.now().isoformat(timespec="seconds")
        first = self.get("first_launch") is None
        if first:
            self.set("first_launch", now, save=False)
        self.set("last_launch", now, save=False)
        self.set("launch_count", self.get("launch_count", 0) + 1, save=False)
        self.save()
        return first

    def reset(self):
        """Wipe all preferences (used by --reset-config)."""
        self._data = dict(DEFAULTS)
        self.save()

    @property
    def needs_onboarding(self):
        return not bool(self.get("onboarded"))
