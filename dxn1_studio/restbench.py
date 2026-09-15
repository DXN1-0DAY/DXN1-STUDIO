"""DS2 REST Bench — fire HTTP requests without leaving the studio.

A zero-dependency HTTP workbench built on ``urllib.request``: pick a
method, edit URL / headers / body, send, and inspect the response
(status, time, size, headers, body). Requests are kept in a history
ring; any request can be copied as a ``curl`` command.

Engine (http_request / build_curl / parse_headers_text) is pure and
unit-tested — tests run against a local ``http.server`` so the suite
never touches the network. The window never raises on bad input.

Open with: Workshop menu, palette, terminal ``rest`` / ``http``.
"""

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import tkinter as tk

__all__ = ["RestResponse", "http_request", "build_curl",
           "parse_headers_text", "format_size", "RestBench",
           "open_restbench"]

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
DEFAULT_TIMEOUT = 15.0


@dataclass
class RestResponse:
    """Everything the UI needs about one exchange."""

    status: int = 0
    reason: str = ""
    headers: dict = field(default_factory=dict)
    body: str = ""
    elapsed_ms: float = 0.0
    url: str = ""
    method: str = "GET"
    error: str = ""

    @property
    def ok(self):
        return not self.error and 200 <= self.status < 400

    @property
    def size_bytes(self):
        return len(self.body.encode("utf-8", errors="replace"))

    def summary(self):
        """One-line status for logs / history rows."""
        if self.error:
            return "%s %s — ERROR: %s" % (self.method, self.url,
                                          self.error)
        return "%s %s — %d %s · %d ms · %s" % (
            self.method, self.url, self.status, self.reason,
            round(self.elapsed_ms), format_size(self.size_bytes))


def format_size(n):
    """Human byte size: 942 B, 3.1 KB, 2.4 MB."""
    n = max(0, int(n))
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%.1f KB" % (n / 1024.0)
    return "%.1f MB" % (n / (1024.0 * 1024.0))


def parse_headers_text(text):
    """Parse ``Key: Value`` lines into a dict (junk tolerated).

    Blank lines and lines without a colon are skipped; keys keep
    their original case; later duplicates win.
    """
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if key:
            out[key] = value.strip()
    return out


def http_request(url, method="GET", headers=None, body="",
                 timeout=DEFAULT_TIMEOUT, opener=None):
    """One HTTP exchange; returns a RestResponse (never raises).

    ``opener`` may be injected for tests (a callable taking the
    urllib Request and returning a response-like object). Network
    errors, bad URLs and timeouts all come back as error responses.
    """
    url = (url or "").strip()
    method = (method or "GET").upper()
    started = time.perf_counter()
    resp = RestResponse(url=url, method=method)
    if not url:
        resp.error = "empty url"
        return resp
    if not url.lower().startswith(("http://", "https://")):
        resp.error = "url must start with http:// or https://"
        return resp
    try:
        data = None
        send_headers = dict(headers or {})
        if body and method not in ("GET", "HEAD"):
            data = body.encode("utf-8")
            send_headers.setdefault("Content-Type",
                                    "application/json")
        req = urllib.request.Request(url, data=data, method=method,
                                     headers=send_headers)
        do_open = opener if opener is not None else \
            urllib.request.urlopen
        raw = do_open(req, timeout=timeout) if opener is None \
            else opener(req)
        try:
            resp.status = int(getattr(raw, "status", 0) or
                              getattr(raw, "code", 0) or 0)
            resp.reason = getattr(raw, "reason", "") or ""
            try:
                resp.headers = dict(raw.headers.items())
            except Exception:  # noqa: BLE001
                resp.headers = {}
            payload = raw.read()
        finally:
            try:
                raw.close()
            except Exception:  # noqa: BLE001
                pass
        resp.body = payload.decode("utf-8", errors="replace")
        if resp.reason and not str(resp.reason)[0].isdigit():
            pass
        else:
            resp.reason = ""
    except urllib.error.HTTPError as exc:
        resp.status = int(exc.code)
        resp.reason = str(exc.reason)
        try:
            resp.body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            resp.body = ""
        resp.headers = dict(exc.headers.items()) if exc.headers else {}
    except urllib.error.URLError as exc:
        resp.error = str(getattr(exc, "reason", exc))
    except Exception as exc:  # noqa: BLE001 — bench never crashes
        resp.error = "%s: %s" % (type(exc).__name__, exc)
    resp.elapsed_ms = (time.perf_counter() - started) * 1000.0
    return resp


def build_curl(url, method="GET", headers=None, body=""):
    """A copy-pasteable ``curl`` command for the request."""
    url = (url or "").strip() or "https://example.invalid"
    method = (method or "GET").upper()
    parts = ["curl -X %s '%s'" % (method, url.replace("'", "'\\''"))]
    for key, value in (headers or {}).items():
        parts.append(" -H '%s: %s'" % (key, str(value)
                                       .replace("'", "'\\''")))
    if body and method not in ("GET", "HEAD"):
        parts.append(" --data '%s'" % body.replace("'", "'\\''"))
    return " \\\n".join(parts)


PRETTY_LIMIT = 200 * 1024


def pretty_body(text):
    """Pretty-print JSON bodies when possible (best effort)."""
    if not text or len(text) > PRETTY_LIMIT:
        return text
    stripped = text.lstrip()
    if not stripped[:1] in ("{", "["):
        return text
    try:
        return json.dumps(json.loads(text), indent=2,
                          ensure_ascii=False)
    except Exception:  # noqa: BLE001 — not JSON, show raw
        return text


class RestBench(tk.Toplevel):
    """HTTP request workbench (method/url/headers/body → response)."""

    def __init__(self, parent, theme, initial_url=""):
        super().__init__(parent)
        self.theme = theme or {}
        self.history = []            # RestResponse, newest first
        t = self.theme

        self.title("REST Bench — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("900x640")
        # DS2 v2.62 — width accounting round four: once the build
        # settles, open no narrower (or shorter) than what it
        # actually packed (the 900x640 default is the floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 900, 640))
        self.minsize(640, 480)
        try:
            self.transient(parent)
        except Exception:
            pass

        self._build_request_bar(initial_url)
        self._build_body_panes()
        self._build_response_pane()
        self._build_statusbar()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Control-Return>", lambda _e: self.send())

        self._flash("Ctrl+Enter sends · response pane pretty-prints "
                    "JSON")

    # ------------------------------------------------------------ UI
    def _bar_lbl(self, bar, text):
        return tk.Label(bar, text=text,
                        bg=bar.cget("bg"),
                        fg=self.theme.get("text_muted", "#8a8a9a"))

    def _build_request_bar(self, initial_url):
        t = self.theme
        bar = tk.Frame(self, bg=t.get("header", "#242432"))
        bar.pack(fill=tk.X)

        self.method = tk.StringVar(value="GET")
        combo = tk.OptionMenu(bar, self.method, *METHODS)
        combo.configure(bg=t.get("button_bg", "#2c2c3c"),
                        fg=t.get("text", "#e8e8f0"),
                        activebackground=t.get("select", "#31445c"),
                        activeforeground=t.get("text", "#e8e8f0"),
                        relief=tk.FLAT, highlightthickness=0,
                        cursor="hand2")
        combo.pack(side=tk.LEFT, padx=(10, 4), pady=6)

        self.url = tk.Entry(bar,
                            bg=t.get("editor_bg", "#1a1a24"),
                            fg=t.get("text", "#e8e8f0"),
                            insertbackground=t.get("text", "#fff"),
                            relief=tk.FLAT)
        self.url.pack(side=tk.LEFT, fill=tk.X, expand=True,
                      padx=4, pady=6, ipady=3)
        if initial_url:
            self.url.insert(0, initial_url)

        self.send_btn = tk.Button(
            bar, text="Send ▶ (Ctrl+↵)", command=self.send,
            bg=t.get("accent", "#7c3aed"),
            fg="#ffffff", activebackground=t.get("select", "#31445c"),
            activeforeground="#ffffff", relief=tk.FLAT, padx=12,
            cursor="hand2")
        self.send_btn.pack(side=tk.LEFT, padx=4, pady=6)

        bar2 = tk.Frame(self, bg=t.get("header", "#242432"))
        bar2.pack(fill=tk.X)
        self._bar_lbl(bar2, "headers (Key: Value)").pack(
            side=tk.LEFT, padx=(10, 6), pady=2)
        tk.Button(bar2, text="Copy as curl", command=self.copy_curl,
                  bg=t.get("button_bg", "#2c2c3c"),
                  fg=t.get("text", "#e8e8f0"), relief=tk.FLAT,
                  padx=8, cursor="hand2").pack(side=tk.RIGHT,
                                               padx=8, pady=2)

    def _build_body_panes(self):
        t = self.theme
        mid = tk.Frame(self, bg=t.get("bg", "#16161e"))
        mid.pack(fill=tk.BOTH)
        tk.Label(mid, text="body (sent for POST/PUT/PATCH/DELETE)",
                 anchor="w", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(
            fill=tk.X, padx=10)
        self.headers = tk.Text(mid, height=4, wrap="none",
                               bg=t.get("editor_bg", "#1a1a24"),
                               fg=t.get("text", "#e8e8f0"),
                               insertbackground=t.get("text", "#fff"),
                               relief=tk.FLAT)
        from .theme import make_scrollbar
        _hsb = make_scrollbar(mid, t, "vertical", command=self.headers.yview)
        self.headers.configure(yscrollcommand=_hsb.set)
        _hsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 4))
        self.headers.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.headers.insert("1.0",
                            "Content-Type: application/json\n"
                            "User-Agent: DXN1-STUDIO-RestBench")
        self.body = tk.Text(mid, height=5, wrap="word", undo=True,
                            bg=t.get("editor_bg", "#1a1a24"),
                            fg=t.get("text", "#e8e8f0"),
                            insertbackground=t.get("text", "#fff"),
                            relief=tk.FLAT)
        _bsb = make_scrollbar(mid, t, "vertical", command=self.body.yview)
        self.body.configure(yscrollcommand=_bsb.set)
        _bsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 6))
        self.body.pack(fill=tk.BOTH, padx=10, pady=(0, 6))

    def _build_response_pane(self):
        t = self.theme
        box = tk.LabelFrame(
            self, text=" response ", bg=t.get("bg", "#16161e"),
            fg=t.get("text", "#e8e8f0"))
        box.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))

        self.status_lbl = tk.Label(box, anchor="w",
                                   bg=t.get("bg", "#16161e"),
                                   fg=t.get("text", "#e8e8f0"),
                                   font=("TkDefaultFont", 10, "bold"))
        self.status_lbl.pack(fill=tk.X, padx=6, pady=(2, 0))

        self.view = tk.Text(box, wrap="word", state=tk.DISABLED,
                            bg=t.get("editor_bg", "#1a1a24"),
                            fg=t.get("text", "#e8e8f0"),
                            relief=tk.FLAT, padx=8, pady=6,
                            font=("Courier", 10))
        _vsb = make_scrollbar(box, t, "vertical", command=self.view.yview)
        self.view.configure(yscrollcommand=_vsb.set)
        _vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6))
        self.view.pack(fill=tk.BOTH, expand=True)
        self.view.tag_configure("hdr",
                                foreground=t.get("text_muted", "#8a8a9a"))

    def _build_statusbar(self):
        t = self.theme
        self.status = tk.Label(self, anchor="w",
                               bg=t.get("header", "#242432"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    # ------------------------------------------------------- actions
    def send(self):
        """Fire the request off the UI thread-ish (after-loop)."""
        self.send_btn.configure(state=tk.DISABLED,
                                text="sending…")
        self.after(10, self._send_now)

    def _send_now(self):
        try:
            resp = http_request(
                self.url.get(),
                method=self.method.get(),
                headers=parse_headers_text(
                    self.headers.get("1.0", "end-1c")),
                body=self.body.get("1.0", "end-1c").strip())
            self.history.insert(0, resp)
            del self.history[30:]
            self._show(resp)
            self._flash(resp.summary())
        except Exception as exc:  # noqa: BLE001 — bench stays alive
            self._flash("send failed — %s" % exc)
        finally:
            try:
                self.send_btn.configure(state=tk.NORMAL,
                                        text="Send ▶ (Ctrl+↵)")
            except Exception:  # noqa: BLE001
                pass

    def _show(self, resp):
        self.status_lbl.configure(text=resp.summary())
        self.view.configure(state=tk.NORMAL)
        self.view.delete("1.0", "end")
        if resp.error:
            self.view.insert("end", "ERROR: %s\n" % resp.error)
        else:
            for key in sorted(resp.headers):
                self.view.insert(
                    "end", "%s: %s\n" % (key, resp.headers[key]),
                    "hdr")
            self.view.insert("end", "\n")
            self.view.insert("end", pretty_body(resp.body) or
                             "(empty body)")
        self.view.configure(state=tk.DISABLED)

    def copy_curl(self):
        try:
            cmd = build_curl(
                self.url.get(), self.method.get(),
                parse_headers_text(self.headers.get("1.0", "end-1c")),
                self.body.get("1.0", "end-1c").strip())
            self.clipboard_clear()
            self.clipboard_append(cmd)
            self._flash("curl command copied")
        except Exception:  # noqa: BLE001
            self._flash("clipboard unavailable")

    def _flash(self, msg):
        try:
            self.status.configure(text=msg)
        except Exception:  # noqa: BLE001
            pass


def open_restbench(parent, theme, initial_url=""):
    """Public opener — palette / menu / terminal entry point."""
    return RestBench(parent, theme, initial_url=initial_url)
