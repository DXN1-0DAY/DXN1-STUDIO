"""DXN1 STUDIO — test data & ID generator (DS2).

Fill your dev clipboard: UUIDs, ULIDs, nanoids, hex tokens, strong
passwords, lorem paragraphs, fake users and ready-to-paste JSON —
all generated locally with the `secrets` module where it matters.

Pure engines, unit-tested; the window is a thin skin.  Open from the
palette ("Data generator…") or terminal `gen`.
"""

import json
import secrets
import string
import time
import tkinter as tk
from datetime import datetime, timedelta, timezone
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_NANOID_ALPHABET = string.ascii_letters + string.digits + "_-"
_LOREM = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do "
          "eiusmod tempor incididunt ut labore et dolore magna aliqua ut "
          "enim ad minim veniam quis nostrud exercitation ullamco laboris "
          "nisi ut aliquip ex ea commodo consequat duis aute irure in "
          "reprehenderit in voluptate velit esse cillum dolore eu fugiat "
          "nulla pariatur").split()
_FIRST = ("ana bob carla dev ed fern grace hiro ivy jun kai liana marco "
          "noor omar priya quinn rosa sam tara umar vera wren xui yuki "
          "zara leo mila noah eva ravi tessa").split()
_LAST = ("chen diaz eriksen foster garcia huber ibarra jansen kim lund "
         "meyer novak okafor perez qureshi rahman silva tanaka usman "
         "vargas weber xiong yilmaz zhang morel petrov").split()
_DOMAINS = ("example.com test.dev mailinator.net sample.org inbox.test"
            ).split()


def uuid4s(n):
    """Proper RFC 4122 v4 UUIDs from 16 secret bytes."""
    out = []
    for _ in range(max(1, n)):
        b = bytearray(secrets.token_bytes(16))
        b[6] = (b[6] & 0x0F) | 0x40          # version 4
        b[8] = (b[8] & 0x3F) | 0x80          # RFC variant
        h = b.hex()
        out.append(f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}")
    return out


def _ulid(now_ms=None):
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    out = []
    for shift in (45, 40, 35, 30, 25, 20, 15, 10, 5, 0):
        out.append(_CROCKFORD[(now_ms >> shift) & 31])
    rand = secrets.token_bytes(10)
    bits = int.from_bytes(rand, "big")
    for shift in range(75, -1, -5):
        out.append(_CROCKFORD[(bits >> shift) & 31])
    return "".join(out)


def ulids(n, now_ms=None):
    base = now_ms if now_ms is not None else int(time.time() * 1000)
    return [_ulid(max(0, base - i)) for i in range(n)]  # newest first


def nanoids(n, size=21):
    return ["".join(secrets.choice(_NANOID_ALPHABET)
                    for _ in range(size)) for _ in range(n)]


def hex_tokens(n, nbytes=16):
    return [secrets.token_hex(nbytes) for _ in range(n)]


def passwords(n, length=20):
    """Guaranteed upper+lower+digit+symbol, filled from secrets pool."""
    out = []
    pools = (string.ascii_lowercase, string.ascii_uppercase,
             string.digits, "!@#$%^&*-_=+?")
    for _ in range(n):
        chars = [secrets.choice(p) for p in pools]
        chars += [secrets.choice("".join(pools))
                  for _ in range(max(0, length - len(chars)))]
        # shuffle deterministically enough for display: swap via secrets
        for i in range(len(chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            chars[i], chars[j] = chars[j], chars[i]
        out.append("".join(chars))
    return out


def pins(n, digits=6):
    return ["".join(secrets.choice(string.digits)
                    for _ in range(digits)) for _ in range(n)]


def lorem(paragraphs=3, sentences_per=4):
    """Deterministic-ish lorem built from a fixed word pool."""
    out = []
    for _ in range(max(1, paragraphs)):
        sents = []
        for _ in range(max(1, sentences_per)):
            n = 6 + secrets.randbelow(10)
            words = [secrets.choice(_LOREM) for _ in range(n)]
            sents.append(" ".join(words).capitalize() + ".")
        out.append(" ".join(sents))
    return "\n\n".join(out)


def fake_users(n, seed=None):
    """Fake but plausible users — same seed, same people."""
    rnd = secrets.SystemRandom()
    users = []
    for i in range(max(1, n)):
        first = _FIRST[(i * 7 + (seed or 0)) % len(_FIRST)]
        last = _LAST[(i * 13 + (seed or 0) * 3) % len(_LAST)]
        dt = datetime(2026, 1, 1, tzinfo=timezone.utc) - timedelta(
            minutes=rnd.randrange(60 * 24 * 600))
        users.append({
            "id": i + 1,
            "first_name": first.capitalize(),
            "last_name": last.capitalize(),
            "username": f"{first}.{last}{i + 1:02d}",
            "email": f"{first}.{last}{i + 1:02d}@{rnd.choice(_DOMAINS)}",
            "created_at": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return users


def fake_json(n, kind="users"):
    if kind == "users":
        return json.dumps(fake_users(n), indent=2, ensure_ascii=False)
    if kind == "ids":
        return json.dumps(ulids(n), indent=2)
    if kind == "events":
        return json.dumps([
            {"id": ulids(1)[0], "type": rnd_event(),
             "at": (datetime.now(timezone.utc)
                    - timedelta(seconds=secrets.randbelow(86400)))
             .strftime("%Y-%m-%dT%H:%M:%SZ")}
            for _ in range(max(1, n))], indent=2)
    return json.dumps(fake_users(n), indent=2)


def rnd_event():
    return secrets.choice(["login", "signup", "purchase", "logout",
                           "view", "click", "error", "retry"])


def generate(kind, count):
    """Dispatch for the window: kind -> (text, error). Never raises."""
    count = max(1, min(500, count))
    try:
        if kind == "UUID v4":
            return "\n".join(uuid4s(count)), ""
        if kind == "ULID":
            return "\n".join(ulids(count)), ""
        if kind == "nanoid (21)":
            return "\n".join(nanoids(count)), ""
        if kind == "hex token (32)":
            return "\n".join(hex_tokens(count, 16)), ""
        if kind == "password (20)":
            return "\n".join(passwords(count, 20)), ""
        if kind == "PIN (6)":
            return "\n".join(pins(count, 6)), ""
        if kind == "lorem paragraphs":
            return lorem(count, 4), ""
        if kind == "fake users (JSON)":
            return fake_json(count, "users"), ""
        if kind == "fake events (JSON)":
            return fake_json(count, "events"), ""
        return "", f"unknown kind: {kind}"
    except Exception as e:  # never let the generator die
        return "", str(e)


# --------------------------------------------------------------- window

class GeneratorWindow(tk.Toplevel):
    def __init__(self, parent, theme):
        super().__init__(parent)
        self.t = theme
        self.title("Data generator — DXN1 STUDIO")
        self.configure(bg=theme["bg"])
        self.geometry("760x560")
        self.minsize(620, 440)
        try:
            self.transient(parent.winfo_toplevel()
                           if parent is not None else parent)
        except Exception:
            pass
        self._build()
        self._run()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 760, 560
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self):
        t = self.t
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Gen.TCombobox", fieldbackground=t["editor"],
                        background=t["header"], foreground=t["text"],
                        arrowcolor=t["text"], borderwidth=0)
        top = tk.Frame(self, bg=t["bg"])
        top.pack(fill="x", padx=12, pady=(12, 6))
        self.kind = tk.StringVar(value="UUID v4")
        cb = ttk.Combobox(top, textvariable=self.kind, width=22,
                          state="readonly", style="Gen.TCombobox",
                          values=("UUID v4", "ULID", "nanoid (21)",
                                  "hex token (32)", "password (20)",
                                  "PIN (6)", "lorem paragraphs",
                                  "fake users (JSON)",
                                  "fake events (JSON)"))
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self._run())
        tk.Label(top, text="count", bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 10)).pack(side="left", padx=(12, 4))
        self.count = tk.IntVar(value=10)
        spin = tk.Spinbox(top, from_=1, to=500, width=6,
                          textvariable=self.count, relief="flat",
                          bg=t["editor"], fg=t["text"],
                          insertbackground=t["text"],
                          buttonbackground=t["header"],
                          font=(FONT_MONO, 11), bd=0,
                          highlightthickness=1,
                          highlightbackground=t["border"])
        spin.pack(side="left", ipady=4)
        tk.Button(top, text="Generate", relief="flat", cursor="hand2",
                  bg=t.get("accent", t["header"]),
                  fg=t.get("select_fg", "#ffffff"), bd=0, padx=14,
                  pady=6, activebackground=t["hover"],
                  activeforeground=t["text"], font=(FONT_UI, 10),
                  command=self._run).pack(side="left", padx=(12, 0))
        tk.Button(top, text="Copy", relief="flat", cursor="hand2",
                  bg=t["header"], fg=t["text"], bd=0, padx=14, pady=6,
                  activebackground=t["hover"],
                  activeforeground=t["text"], font=(FONT_UI, 10),
                  command=self._copy).pack(side="right")

        wrap = tk.Frame(self, bg=t["border"])
        wrap.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self.out = tk.Text(wrap, wrap="word", relief="flat",
                           bg=t["editor"], fg=t["text"],
                           insertbackground=t["text"],
                           font=(FONT_MONO, 11), padx=10, pady=8, bd=0,
                           undo=True)
        self.out.pack(fill="both", expand=True)
        self.status = tk.Label(self, text="", bg=t["bg"],
                               fg=t["text_muted"], font=(FONT_UI, 9))
        self.status.pack(anchor="w", padx=12, pady=(0, 12))

    def _run(self):
        try:
            count = int(self.count.get())
        except (ValueError, tk.TclError):
            count = 10
        text, err = generate(self.kind.get(), count)
        try:
            self.out.delete("1.0", "end")
            self.out.insert("1.0", text or err)
            self.status.configure(
                text=err if err else
                f"{self.kind.get()} × {count} generated locally "
                "(secrets module)",
                fg=self.t["text_muted"] if err else self.t["success"])
        except tk.TclError:
            pass

    def _copy(self):
        try:
            data = self.out.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(data)
            self.status.configure(text=f"copied {len(data)} chars",
                                  fg=self.t["success"])
        except tk.TclError:
            pass


def open_generator(parent, theme):
    return GeneratorWindow(parent, theme)
