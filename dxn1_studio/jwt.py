"""DXN1 STUDIO — JWT decoder (DS2).

Paste a token, see its guts: header, payload, every time claim
humanized ("expires in 2h 14m" / "expired 3d ago"), issuer/subject/
audience pulled to the front.  Decode-only — DS2 never verifies
signatures and will tell you so.  All engines are pure and
unit-tested; the window is a thin skin.

Open from the palette ("JWT decoder…") or terminal `jwt <token>`.
"""

import base64
import json
import re
import tkinter as tk
from datetime import datetime, timezone
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO


_B64URL_OK = re.compile(r"^[A-Za-z0-9_-]*={0,2}$")


def b64url_decode(seg):
    """base64url segment -> bytes (padding fixed, strict charset)."""
    seg = (seg or "").strip().strip('"')
    if not _B64URL_OK.match(seg):
        return b""
    seg += "=" * (-len(seg) % 4)
    try:
        return base64.urlsafe_b64decode(seg)
    except Exception:
        return b""


def decode_jwt(token):
    """-> (dict(header, payload, signature_len), error). Never raises."""
    parts = (token or "").strip().split(".")
    if len(parts) != 3:
        return {}, (f"a JWT has 3 dot-separated parts, got {len(parts)}"
                    if parts else "empty token")
    header_b = b64url_decode(parts[0])
    payload_b = b64url_decode(parts[1])
    if not header_b or not payload_b:
        return {}, "parts 1 or 2 are not valid base64url JSON"
    try:
        header = json.loads(header_b)
        payload = json.loads(payload_b)
    except (ValueError, UnicodeDecodeError) as e:
        return {}, f"header/payload are not JSON: {e}"
    if not isinstance(header, dict) or not isinstance(payload, dict):
        return {}, "header/payload must be JSON objects"
    return {"header": header, "payload": payload,
            "signature_len": len(parts[2]), "alg": header.get("alg", "?"),
            "typ": header.get("typ", "")}, ""


def _human_delta(seconds):
    seconds = int(abs(seconds))
    steps = ((86400, "d"), (3600, "h"), (60, "m"))
    out = []
    for secs, unit in steps:
        if seconds >= secs:
            out.append(f"{seconds // secs}{unit}")
            seconds %= secs
    return " ".join(out) or "0s"


def token_status(payload, now=None):
    """-> (state, human string). state in expired/valid/not yet/none."""
    exp = payload.get("exp")
    if exp is None:
        return "none", "no expiry claim"
    now = now or datetime.now(timezone.utc).timestamp()
    try:
        exp = float(exp)
    except (TypeError, ValueError):
        return "none", "exp is not a number"
    if exp < now:
        return "expired", f"expired {_human_delta(now - exp)} ago"
    return "valid", f"expires in {_human_delta(exp - now)}"


def claims_table(payload, now=None):
    """-> [(claim, value, human)] — time claims first, humanized."""
    rows = []
    now = now or datetime.now(timezone.utc).timestamp()
    time_claims = {"exp": ("expires", "expired"), "iat": ("issued at", ""),
                   "nbf": ("not before", ""), "auth_time": ("authed at", "")}
    seen = set()
    for claim, (label, _u) in time_claims.items():
        if claim in payload:
            seen.add(claim)
            v = payload[claim]
            try:
                dt = datetime.fromtimestamp(float(v), tz=timezone.utc)
                human = dt.strftime("%Y-%m-%d %H:%M UTC")
                if claim == "exp":
                    state, extra = token_status(payload, now)
                    human += f" ({extra})"
            except (TypeError, ValueError, OSError, OverflowError):
                human = "unreadable timestamp"
            rows.append((claim, str(v), human))
    for claim in ("iss", "sub", "aud", "jti"):
        if claim in payload:
            seen.add(claim)
            rows.append((claim, str(payload[claim]), ""))
    for claim, v in payload.items():
        if claim not in seen:
            if isinstance(v, (dict, list)):
                try:
                    v = json.dumps(v, ensure_ascii=False)
                except (TypeError, ValueError):
                    v = str(v)
            rows.append((claim, str(v), ""))
    return rows


# --------------------------------------------------------------- window

class JWTWindow(tk.Toplevel):
    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.t = theme
        self.title("JWT decoder — DXN1 STUDIO")
        self.configure(bg=theme["bg"])
        self.geometry("880x600")
        self.minsize(700, 460)
        try:
            self.transient(parent.winfo_toplevel()
                           if parent is not None else parent)
        except Exception:
            pass
        self._build()
        if initial:
            self.var.set(initial.strip())
        self._update()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 880, 600
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _mono(self, master, height=9):
        t = self.t
        wrap = tk.Frame(master, bg=t["border"])
        txt = tk.Text(wrap, height=height, wrap="word", relief="flat",
                      bg=t["editor"], fg=t["text"],
                      insertbackground=t["text"], font=(FONT_MONO, 10),
                      padx=8, pady=6, bd=0)
        txt.pack(fill="both", expand=True)
        return wrap, txt

    def _build(self):
        t = self.t
        top = tk.Frame(self, bg=t["bg"])
        top.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(top, text="token", bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 10)).pack(side="left")
        self.var = tk.StringVar()
        self.entry = tk.Entry(top, textvariable=self.var, relief="flat",
                              bg=t["editor"], fg=t["text"],
                              insertbackground=t["text"],
                              font=(FONT_MONO, 11), bd=0,
                              highlightthickness=1,
                              highlightbackground=t["border"],
                              highlightcolor=t.get("accent", t["hover"]))
        self.entry.pack(side="left", fill="x", expand=True, padx=(8, 8),
                        ipady=6)
        self.var.trace_add("write", lambda *a: self._update())

        self.status = tk.Label(self, text="", bg=t["bg"],
                               fg=t["text_muted"], font=(FONT_UI, 10),
                               anchor="w", justify="left", wraplength=840)
        self.status.pack(fill="x", padx=12)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Jwt.Treeview", background=t["card"],
                        fieldbackground=t["card"], foreground=t["text"],
                        rowheight=24, borderwidth=0, font=(FONT_MONO, 10))
        style.configure("Jwt.Treeview.Heading", background=t["header"],
                        foreground=t["text_secondary"], relief="flat",
                        font=(FONT_UI, 9))

        mid = tk.Frame(self, bg=t["bg"])
        mid.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        hw = tk.Frame(mid, bg=t["border"])
        hw.pack(side="left", fill="both", expand=True)
        tk.Label(hw, text="header", bg=t["header"],
                 fg=t["text_secondary"], font=(FONT_UI, 9), anchor="w",
                 padx=8).pack(fill="x")
        _w, self.header_txt = self._mono(hw, height=7)
        pw = tk.Frame(mid, bg=t["border"])
        pw.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(pw, text="payload", bg=t["header"],
                 fg=t["text_secondary"], font=(FONT_UI, 9), anchor="w",
                 padx=8).pack(fill="x")
        pw2, self.payload_txt = self._mono(pw, height=7)
        pw2.pack(fill="both", expand=True)

        tk.Label(self, text="claims", bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 9)).pack(anchor="w", padx=12, pady=(10, 2))
        tw = tk.Frame(self, bg=t["border"])
        tw.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.claims = ttk.Treeview(tw, columns=("c", "v", "h"),
                                   show="headings", height=7,
                                   style="Jwt.Treeview")
        for cid, label, w in (("c", "claim", 110), ("v", "value", 330),
                              ("h", "human", 340)):
            self.claims.heading(cid, text=label)
            self.claims.column(cid, width=w, anchor="w")
        self.claims.pack(fill="both", expand=True)

    def _update(self):
        token = self.var.get()
        data, err = decode_jwt(token)
        try:
            self.header_txt.delete("1.0", "end")
            self.payload_txt.delete("1.0", "end")
            self.claims.delete(*self.claims.get_children(""))
            if err:
                self.status.configure(text=err, fg=self.t["text_muted"])
                return
            state, human = token_status(data["payload"])
            color = self.t["success"] if state == "valid" else \
                self.t["text_secondary"] if state != "expired" else \
                self.t["text"]
            alg = data["alg"]
            self.status.configure(
                text=f"alg {alg} · signature {data['signature_len']} chars "
                     f"(not verified — decode only) · {human}",
                fg=color)
            self.header_txt.insert(
                "1.0", json.dumps(data["header"], indent=2,
                                  ensure_ascii=False))
            self.payload_txt.insert(
                "1.0", json.dumps(data["payload"], indent=2,
                                  ensure_ascii=False))
            for row in claims_table(data["payload"]):
                self.claims.insert("", "end", values=row)
        except tk.TclError:
            pass


def open_jwt(parent, theme, initial=""):
    return JWTWindow(parent, theme, initial)
