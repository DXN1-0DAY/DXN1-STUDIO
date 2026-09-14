"""DXN1 STUDIO — error handling.

One place that turns "something went wrong" into something useful:

* every uncaught exception is appended to ``~/.dxn1-studio/logs/studio.log``
  with a timestamp and traceback (capped, so it can't grow forever);
* the UI is told through a callback (a toast in the status corner) so the
  user sees a friendly one-liner instead of a dead window;
* helpers wrap common risky operations so callers get one-liner logging
  without try/except noise.
"""

import os
import traceback
from datetime import datetime

from . import APP_NAME, APP_VERSION

LOG_DIR = os.path.join(os.path.expanduser("~"), ".dxn1-studio", "logs")
LOG_PATH = os.path.join(LOG_DIR, "studio.log")
MAX_LOG_BYTES = 256 * 1024          # ~256 KB, then the oldest half is cut

_toast_cb = None                    # set by the app: fn(message, kind)


def set_notifier(callback):
    """Register fn(message, kind). kind ∈ {"info", "success", "error"}."""
    global _toast_cb
    _toast_cb = callback


def _notify(message, kind):
    try:
        if _toast_cb is not None:
            _toast_cb(message, kind)
    except Exception:   # noqa: BLE001 — the notifier must never raise
        pass


def log_exception(prefix="", quiet=False):
    """Append the active exception to the log file; optionally toast."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    head = f"[{stamp}] {prefix}: " if prefix else f"[{stamp}] "
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        if os.path.exists(LOG_PATH) and \
                os.path.getsize(LOG_PATH) > MAX_LOG_BYTES:
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as fh:
                old = fh.read()
            with open(LOG_PATH, "w", encoding="utf-8") as fh:
                fh.write(old[len(old) // 2:])
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(head + traceback.format_exc() + "\n")
    except OSError:
        pass  # logging must never take the studio down with it
    if not quiet:
        short = prefix or "Something went wrong"
        _notify(f"{short} — details written to the studio log", "error")


def friendly(exc, context=""):
    """One human line for an exception (no tracebacks in the UI)."""
    text = str(exc) or exc.__class__.__name__
    if len(text) > 160:
        text = text[:157] + "…"
    return f"{context}: {text}" if context else text


def install(root):
    """Route Tk-interpreted uncaught exceptions through log_exception."""
    def handler(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            root.destroy()
            return
        log_exception("uncaught")
    root.report_callback_exception = handler
