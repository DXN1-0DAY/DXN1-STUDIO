"""DXN1 STUDIO — visual git graph (DS2 v1.4).

A canvas that renders the repository's commit history as a real branch
graph: lanes are assigned from parent relationships (not ASCII art), so
branch/merge topology is drawn the way GitHub draws it — coloured dots,
vertical trunk lines, diagonal branch/merge curves, and ref decorations
(HEAD, branches, tags) next to their commits.

Clicking a commit opens a detail strip with the full metadata and three
actions: copy the SHA, checkout the commit, or open a visual diff of
that commit against its first parent (via ``diffview.DiffViewer``).

Pure stdlib + Tk. One short-lived ``git`` call per refresh, so the graph
costs nothing when it is not on screen.
"""

import subprocess
import tkinter as tk
from tkinter import ttk

from . import hints
from .theme import FONT_UI, FONT_MONO

# GitHub-graph lane colours — vivid enough for dark, deep enough for light
LANE_COLORS = ["#8b5cf6", "#22d3ee", "#4ade80", "#fb923c",
               "#fb7185", "#60a5fa", "#fbbf24", "#34d399"]

ROW_H = 30
LANE_W = 26
DOT_R = 5


def _run_git(repo, *args, timeout=15):
    """Run git in repo; return (ok, stdout, stderr)."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True,
            timeout=timeout)
    except FileNotFoundError:
        return False, "", "git is not installed"
    except subprocess.TimeoutExpired:
        return False, "", "git timed out"
    except OSError as exc:
        return False, "", str(exc)
    return proc.returncode == 0, proc.stdout, proc.stderr.strip()


def fetch_commits(repo, limit=200, all_branches=True):
    """Fetch commit metadata newest-first.

    Returns ``(commits, err)`` where each commit is a dict with
    ``sha, parents (list), sha7, author, when, refs (list), subject``.
    """
    fmt = "%H%x1f%P%x1f%h%x1f%an%x1f%ar%x1f%d%x1f%s%x1e"
    args = ["log", f"--max-count={limit}", "--date-order"]
    if all_branches:
        args.append("--all")
    args += [f"--pretty=format:{fmt}"]
    ok, out, err = _run_git(repo, *args)
    if not ok:
        return [], err
    commits = []
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if not rec.strip():
            continue
        parts = rec.split("\x1f")
        if len(parts) < 6:
            continue
        sha, parents_s, sha7, author, when, refs_s, subject = parts[:7]
        refs = []
        for ref in refs_s.replace("(", "").replace(")", "").split(","):
            ref = ref.strip()
            if ref:
                refs.append(ref)
        commits.append({
            "sha": sha,
            "parents": parents_s.split() if parents_s else [],
            "sha7": sha7,
            "author": author,
            "when": when,
            "refs": refs,
            "subject": subject,
        })
    return commits, ""


def assign_lanes(commits):
    """Assign each commit a graph lane from parent topology.

    Returns ``(rows, lane_count)`` where rows is a list of
    ``(lane, commit, edges)``. ``edges`` maps ``parent_sha -> lane``
    that this commit connects to (drawn as diagonal lines on the row
    above the parent).
    """
    lanes = []            # lane -> sha expected to appear next (parent)
    lane_of = {}          # sha -> lane index
    rows = []
    for commit in commits:
        sha = commit["sha"]
        parents = commit["parents"]
        lane = None
        for i, expected in enumerate(lanes):
            if expected == sha:
                lane = i
                break
        if lane is None:
            lane = len(lanes)
            lanes.append(None)
        edges = {}
        # first parent continues in this lane, others branch out
        for pi, parent in enumerate(parents):
            if pi == 0:
                edges[parent] = lane
                lanes[lane] = parent
            else:
                target = None
                for i, expected in enumerate(lanes):
                    if i != lane and expected == parent:
                        target = i
                        break
                if target is None:
                    lanes.append(parent)
                    target = len(lanes) - 1
                edges[parent] = target
        lane_of[sha] = lane
        rows.append((lane, commit, edges))
    return rows, max(1, len(lanes))


class GitGraphWindow(tk.Toplevel):
    """The commit graph window ('Graph' button in Source Control)."""

    def __init__(self, parent, theme, repo, on_log=None):
        super().__init__(parent)
        self.t = theme
        self.repo = repo
        self.on_log = on_log or (lambda msg: None)
        self.commits = []
        self.rows = []
        self.selected_sha = None
        self.zoom = 1.0                     # v2.48 — row-density zoom
        self._tip = None                    # v2.49 — hover tooltip
        self._tip_sha = None
        self.title("Git Graph — DXN1 STUDIO")
        self.configure(bg=self.t["bg"])
        self.geometry("860x640")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 860x640 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 860, 640))
        self.minsize(560, 380)
        self.transient(parent.winfo_toplevel()
                       if parent is not None else parent)

        self._build_header()
        self._build_canvas()
        self._build_hintbar()
        self._build_detail()
        self.bind("<Escape>", lambda e: self.destroy())
        # v2.48 — the graph answers to keys, and the bar says so
        self.bind("<F5>", lambda e: self.refresh())
        self.bind("<Control-r>", lambda e: self.refresh())
        self.bind("<Key-plus>", lambda e: self.zoom_step(0.25))
        self.bind("<Key-equal>", lambda e: self.zoom_step(0.25))
        self.bind("<Key-minus>", lambda e: self.zoom_step(-0.25))
        self.bind("<Key-0>", lambda e: self.zoom_reset())
        self.after(80, self.refresh)
        self._center()

    # ------------------------------------------------------------ chrome
    def _build_hintbar(self):
        """v2.48 — the honest door sign (only really-bound keys)."""
        self.hintbar = hints.hint_bar(
            self, self.t,
            pairs=(("F5", "refresh", "F5"),
                   ("+", "zoom in", "+ / −"),
                   ("-", "zoom out", "−"),
                   ("0", "zoom reset", "0")),
            notes=("click a commit for details",
                   "hover a commit for the full message"))

    # ------------------------------------------------------------ chrome
    def _center(self):
        try:
            self.update_idletasks()
            w, h = 860, 640
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _build_header(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=46)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="⑂  COMMIT GRAPH", bg=t["header"],
                 fg=t["text"], font=(FONT_UI, 11, "bold")).pack(
            side=tk.LEFT, padx=14)
        self.info_lbl = tk.Label(bar, text="", bg=t["header"],
                                 fg=t["text_muted"], font=(FONT_MONO, 8))
        self.info_lbl.pack(side=tk.LEFT, padx=8)
        refresh = tk.Label(bar, text="⟳ Refresh", bg=t["card"],
                           fg=t["text_secondary"], font=(FONT_UI, 9),
                           cursor="hand2", padx=10, pady=4)
        refresh.pack(side=tk.RIGHT, padx=12)
        refresh.bind("<Button-1>", lambda e: self.refresh())
        self.all_var = tk.BooleanVar(value=True)
        tk.Checkbutton(bar, text="all branches", variable=self.all_var,
                       command=self.refresh, bg=t["header"], fg=t["text_muted"],
                       activebackground=t["header"], activeforeground=t["text"],
                       selectcolor=t["editor"], font=(FONT_UI, 8),
                       highlightthickness=0, bd=0).pack(side=tk.RIGHT, padx=6)

    def _build_canvas(self):
        t = self.t
        wrap = tk.Frame(self, bg=t["bg"])
        wrap.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(wrap, bg=t["bg"], highlightthickness=0,
                                bd=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL,
                           command=self.canvas.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(
                             -1 if e.delta > 0 else 1, "units"))
        self.canvas.bind("<Button-4>",
                         lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>",
                         lambda e: self.canvas.yview_scroll(1, "units"))

    def _build_detail(self):
        t = self.t
        self.detail = tk.Frame(self, bg=t["card"], highlightthickness=1,
                               highlightbackground=t["card_border"],
                               height=118)
        self.detail.pack(fill=tk.X, side=tk.BOTTOM)
        self.detail.pack_propagate(False)
        self.detail_title = tk.Label(self.detail, text="Select a commit",
                                     bg=t["card"], fg=t["text"],
                                     font=(FONT_UI, 10, "bold"), anchor="w")
        self.detail_title.pack(fill=tk.X, padx=14, pady=(10, 2))
        self.detail_meta = tk.Label(self.detail, text="", bg=t["card"],
                                    fg=t["text_secondary"],
                                    font=(FONT_MONO, 8), anchor="w")
        self.detail_meta.pack(fill=tk.X, padx=14)
        row = tk.Frame(self.detail, bg=t["card"])
        row.pack(fill=tk.X, padx=12, pady=(6, 10))
        self._detail_btns = {}
        for key, label in (("copy", "⧉ Copy SHA"),
                           ("checkout", "⑂ Checkout"),
                           ("diff", "⇄ Diff vs parent")):
            btn = tk.Label(row, text=label, bg=t["editor"],
                           fg=t["text_secondary"], font=(FONT_UI, 8, "bold"),
                           cursor="hand2", padx=10, pady=4)
            btn.pack(side=tk.LEFT, padx=(0, 6))
            btn.bind("<Button-1>", lambda e, k=key: self._detail_action(k))
            self._detail_btns[key] = btn

    # ------------------------------------------------------------ zoom
    def zoom_step(self, delta):
        """v2.48 — nudge the row-density zoom (clamped 0.5–3.0)."""
        try:
            self.zoom = round(min(3.0, max(0.5, self.zoom + delta)), 2)
        except Exception:  # noqa: BLE001 — zoom is garnish
            self.zoom = 1.0
        self._draw()
        return self.zoom

    def zoom_reset(self):
        """v2.48 — back to the comfortable default density."""
        self.zoom = 1.0
        self._draw()
        return self.zoom

    def _rh(self):
        return max(14, int(ROW_H * self.zoom))

    def _lw(self):
        return max(12, int(LANE_W * self.zoom))

    # ------------------------------------------------------------ render
    def refresh(self):
        commits, err = fetch_commits(self.repo, 200,
                                     all_branches=self.all_var.get())
        if err:
            self.info_lbl.config(text=err)
            return
        self.commits = commits
        self.rows, lane_count = assign_lanes(commits)
        self.info_lbl.config(
            text=f"{len(commits)} commits · {lane_count} lanes")
        self._draw()

    def _draw(self):
        c = self.canvas
        t = self.t
        c.delete("all")
        if not self.rows:
            c.create_text(20, 30, anchor="w", fill=t["text_muted"],
                          font=(FONT_UI, 10),
                          text="No commits yet — or this folder is not a "
                               "repository.")
            return
        rh, lw = self._rh(), self._lw()
        c.configure(scrollregion=(0, 0, 1000, len(self.rows) * rh + 40))
        graph_w = lw * 9
        # current head for decoration boldness
        current = ""
        ok, head, _ = _run_git(self.repo, "rev-parse", "--abbrev-ref", "HEAD")
        if ok:
            current = head.strip()
        prev_y = None
        lane_last_y = {}
        # v2.49 BUGFIX — lane_of was referenced here since v1.4 but only
        # ever defined inside assign_lanes, so every draw of a repo with
        # ≥2 commits died mid-loop with NameError (silently: the 80ms
        # refresh timer rarely fired before the old checks looked).
        lane_of = {cm["sha"]: ln for ln, cm, _e in self.rows}
        for idx, (lane, commit, edges) in enumerate(self.rows):
            y = idx * rh + int(rh * 0.6)
            x = 20 + lane * lw
            color = LANE_COLORS[lane % len(LANE_COLORS)]
            # vertical continuation lines for every active lane
            for li in range(min(lane_count_max(self.rows), 9)):
                lx = 20 + li * lw
                if li in lane_last_y:
                    c.create_line(lx, lane_last_y[li], lx, y,
                                  fill=LANE_COLORS[li % len(LANE_COLORS)],
                                  width=1, dash=())
            # diagonal edges to parents
            for parent_sha, pl in edges.items():
                if parent_sha in lane_of:
                    prow = lane_of[parent_sha]
                    py = prow * rh + int(rh * 0.6)
                    px = 20 + prow * lw
                    if py > y:  # parent below (newer rows are drawn first)
                        c.create_line(x, y, px, py,
                                      fill=color, width=1,
                                      smooth=True, splinesteps=4)
            # dot
            selected = commit["sha"] == self.selected_sha
            r = max(3, int(DOT_R * self.zoom)) + (2 if selected else 0)
            outline = t["text"] if selected else t["bg"]
            c.create_oval(x - r, y - r, x + r, y + r, fill=color,
                          outline=outline, width=1 if selected else 0)
            lane_last_y[lane] = y
            # text columns
            tx = graph_w + 6
            is_head_ref = any(rf.startswith("HEAD") or rf == current
                              for rf in commit["refs"])
            sha_col = c.create_text(tx, y, anchor="w", fill=t["text_muted"],
                                    font=(FONT_MONO, 9),
                                    text=commit["sha7"])
            subj = commit["subject"]
            if len(subj) > 72:
                subj = subj[:71] + "…"
            subj_col = c.create_text(tx + 60, y, anchor="w",
                                     fill=t["text"] if is_head_ref
                                     else t["text_secondary"],
                                     font=(FONT_MONO, 9, "bold")
                                     if is_head_ref else (FONT_MONO, 9),
                                     text=subj)
            # decorations (HEAD -> main, tag: …) in accent
            if commit["refs"]:
                deco = ", ".join(commit["refs"][:3])
                c.create_text(tx + 60 + min(len(subj) * 7, 520), y,
                              anchor="w", fill=t.accent,
                              font=(FONT_UI, 8, "bold"), text=" " + deco)
            author_col = c.create_text(tx + 640, y, anchor="e",
                                       fill=t["text_muted"],
                                       font=(FONT_UI, 8),
                                       text=f"{commit['author']} · "
                                            f"{commit['when']}")
            # row hover + click zones
            c.addtag_withtag("row", sha_col)
            for item in (sha_col, subj_col, author_col):
                c.addtag_withtag(f"rowdata:{commit['sha']}", item)
        # invisible row bands for clicks
        for idx, (lane, commit, _e) in enumerate(self.rows):
            y0 = idx * rh
            band = c.create_rectangle(0, y0, 1000, y0 + rh, fill="",
                                      outline="", width=0)
            c.addtag_withtag(f"rowdata:{commit['sha']}", band)
            c.tag_lower(band)

    # ------------------------------------------------------------ events
    def _hit(self, x, y):
        """Map canvas coords → row index (zoom-aware)."""
        rh = self._rh()
        idx = int((self.canvas.canvasy(y) - int(rh * 0.6) + rh / 2) // rh)
        if 0 <= idx < len(self.rows):
            return idx
        return None

    def _on_hover(self, event):
        idx = self._hit(event.x, event.y)
        self.canvas.config(cursor="hand2" if idx is not None else "arrow")
        if idx is None:
            self._hide_tip()
            return
        _lane, commit, _e = self.rows[idx]
        if commit["sha"] == self._tip_sha:
            return                      # already whispering about this row
        self._hide_tip()
        self._show_tip(commit, event)

    def _on_leave(self, _event=None):
        try:
            self.canvas.config(cursor="arrow")
        except Exception:  # noqa: BLE001 — dying canvas is fine
            pass
        self._hide_tip()

    def _show_tip(self, commit, event):
        """v2.49 — the lane hover tooltip: the full subject (never
        truncated), every ref, and the author line. The canvas row is
        a summary; the tooltip is the whole truth. Never raises."""
        try:
            t = self.t
            tip = tk.Toplevel(self)
            try:
                tip.wm_overrideredirect(True)
            except Exception:  # noqa: BLE001 — decoration is garnish
                pass
            tip.configure(bg=t["card_border"])
            body = tk.Frame(tip, bg=t["card"])
            body.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
            tk.Label(body, text=commit["subject"], bg=t["card"],
                     fg=t["text"], font=(FONT_UI, 9, "bold"), anchor="w",
                     wraplength=380, justify="left").pack(
                fill=tk.X, padx=10, pady=(7, 2))
            tk.Label(body, text="%s · %s · %s" % (commit["sha7"],
                                                   commit["author"],
                                                   commit["when"]),
                     bg=t["card"], fg=t["text_muted"],
                     font=(FONT_MONO, 8), anchor="w").pack(
                fill=tk.X, padx=10, pady=(0, 7 if not commit["refs"] else 0))
            if commit["refs"]:
                tk.Label(body, text=", ".join(commit["refs"]),
                         bg=t["card"], fg=t.accent,
                         font=(FONT_UI, 8, "bold"), anchor="w",
                         wraplength=380, justify="left").pack(
                    fill=tk.X, padx=10, pady=(0, 7))
            # clamp to ≥0 — a negative "+-x+y" geometry is Tcl-invalid
            # and would silently kill the tooltip off-screen
            x = max(0, self.winfo_rootx() + event.x + 14)
            y = max(0, self.winfo_rooty() + event.y + 18)
            tip.wm_geometry("+%d+%d" % (x, y))
            self._tip = tip
            self._tip_sha = commit["sha"]
        except Exception:  # noqa: BLE001 — a tooltip must never raise
            self._tip = None
            self._tip_sha = None

    def _hide_tip(self, _event=None):
        tip = self._tip
        self._tip = None
        self._tip_sha = None
        try:
            if tip is not None:
                tip.destroy()
        except Exception:  # noqa: BLE001 — never raise on cleanup
            pass

    def _on_click(self, event):
        idx = self._hit(event.x, event.y)
        if idx is None:
            return
        self._hide_tip()
        _lane, commit, _e = self.rows[idx]
        self.selected_sha = commit["sha"]
        self._draw()
        self._show_detail(commit)

    def _show_detail(self, commit):
        t = self.t
        refs = ("  " + ", ".join(commit["refs"])) if commit["refs"] else ""
        self.detail_title.config(
            text=f"{commit['subject'][:80]}{refs}")
        parents = ", ".join(p[:7] for p in commit["parents"]) or "—"
        self.detail_meta.config(
            text=f"{commit['sha']}   ·   {commit['author']}   ·   "
                 f"{commit['when']}   ·   parents: {parents}")
        self._detail_commit = commit

    def _detail_action(self, key):
        commit = getattr(self, "_detail_commit", None)
        if not commit:
            return
        if key == "copy":
            self.clipboard_clear()
            self.clipboard_append(commit["sha"])
            self.on_log(f"copied SHA {commit['sha7']}")
        elif key == "checkout":
            ok, _, err = _run_git(self.repo, "checkout", commit["sha"])
            self.on_log(f"checkout {commit['sha7']}: "
                        + ("ok" if ok else err[:80]))
            self.refresh()
        elif key == "diff":
            self._open_commit_diff(commit)

    def _open_commit_diff(self, commit):
        """Visual diff of this commit against its first parent."""
        from . import diffview
        if not commit["parents"]:
            return
        ok, new_text, _ = _run_git(self.repo, "show", "-s", "--format=",
                                   commit["sha"])
        ok2, old_text, _ = _run_git(
            self.repo, "show", "-s", "--format=",
            commit["parents"][0] + "^{commit}")
        if not (ok and ok2):
            return
        diffview.DiffViewer(
            self, self.t, old_text, new_text,
            old_label=commit["parents"][0][:7] + " (parent)",
            new_label=commit["sha7"] + " (this)",
            title=f"Commit {commit['sha7']}")


def lane_count_max(rows):
    """Highest lane index used +1 — keeps vertical lines bounded."""
    return max((lane for lane, _c, _e in rows), default=0) + 1
