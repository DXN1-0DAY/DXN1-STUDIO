"""DXN1 STUDIO — AI commit messages (DS2 v1.6).

One chip in the Source Control panel: "✨ AI". It reads the staged diff
(falling back to the working tree when nothing is staged), asks the
configured brain for a Conventional Commits message — 50-char subject,
imperative mood, optional short body — and streams it into the commit
box. The user can edit anything before committing; the AI only drafts,
never commits.

Runs entirely on a worker thread; the UI is touched through ``after()``
marshalling so the panel stays responsive while the brain thinks.
"""

import threading
import tkinter as tk

from . import llm

SUBJECT_MAX = 72


def _run_git(repo, *args, timeout=20):
    import subprocess
    try:
        proc = subprocess.run(["git", *args], cwd=repo,
                              capture_output=True, text=True,
                              timeout=timeout)
    except Exception:
        return False, "", "git unavailable"
    return proc.returncode == 0, proc.stdout, proc.stderr.strip()


def collect_diff(repo):
    """The material the message should describe.

    Prefers the staged diff; falls back to unstaged + untracked files
    (with a note) so a one-click flow still works before staging.
    Returns (diff_text, note) where note explains what was summarised.
    """
    ok, staged, _ = _run_git(repo, "diff", "--cached", "-U3")
    if ok and staged.strip():
        return staged, "staged changes"
    ok, unstaged, _ = _run_git(repo, "diff", "-U3")
    ok2, names, _ = _run_git(repo, "ls-files", "--others",
                             "--exclude-standard")
    pieces = []
    if ok and unstaged.strip():
        pieces.append(unstaged)
    if ok2 and names.strip():
        listing = ", ".join(names.strip().splitlines()[:12])
        more = "" if len(names.strip().splitlines()) <= 12 else \
            f" (+{len(names.strip().splitlines()) - 12} more)"
        pieces.append(f"# untracked files: {listing}{more}\n")
    return "\n".join(pieces), "unstaged + untracked changes"


def build_prompt(diff_text, note):
    return (
        "Write a git commit message for the following "
        f"{note}.\n\n"
        "Rules:\n"
        "- Conventional Commits style: 'feat: …', 'fix: …', 'docs: …', "
        "'refactor: …', 'chore: …'\n"
        "- Subject line: imperative mood, max 72 chars, no trailing "
        "period\n"
        "- After the subject, ONE blank line, then a short body of 1-3 "
        "bullets only if the change is non-trivial\n"
        "- Reply with the message text only — no quotes, no code fences, "
        "no explanation\n\n"
        f"{diff_text[:12000]}")


def generate_message(config, diff_text, note, on_delta, on_done,
                     should_stop=None):
    """Worker-thread entry: stream the message draft.

    ``on_delta(str)`` / ``on_done(str|None)`` are called from the
    worker — wrap them with ``widget.after`` on the caller's side.
    """
    try:
        backend = llm.build_backend(config)
        if backend is None:
            on_done(None)
            return
        messages = [
            {"role": "system",
             "content": "You write precise, boring-in-a-good-way git "
                        "commit messages. Conventional Commits. Output "
                        "the message only."},
            {"role": "user", "content": build_prompt(diff_text, note)},
        ]
        answer = backend.chat_stream(messages, on_delta,
                                     should_stop=should_stop)
        on_done(answer)
    except Exception:
        try:
            answer = _sync_fallback(config, diff_text, note)
            on_done(answer)
        except Exception:
            on_done(None)


def _sync_fallback(config, diff_text, note):
    backend = llm.build_backend(config)
    messages = [
        {"role": "system", "content": "You write concise Conventional "
         "Commits messages. Output the message only."},
        {"role": "user", "content": build_prompt(diff_text, note)},
    ]
    return backend.chat(messages)


def _clean_message(text):
    """Strip fences/quotes the model may add, cap the subject."""
    text = (text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].strip() if len(parts) > 1 else text.strip("` \n")
    if text.startswith('"') and text.endswith('"') and len(text) > 1:
        text = text[1:-1]
    lines = text.splitlines()
    if lines:
        lines[0] = lines[0][:SUBJECT_MAX].rstrip()
    return "\n".join(lines).strip()


def stream_into(gitpanel):
    """The panel-chip handler: draft a message into the commit box."""
    repo = getattr(gitpanel, "workspace", None)
    config = getattr(gitpanel, "config", None)
    if not repo or config is None:
        gitpanel._say("AI commit needs a workspace + settings.")
        return
    entry = gitpanel.msg
    state = {"stop": False}

    def on_delta(chunk):
        pass  # keep the box clean; the live draft lands at the end

    def worker():
        diff_text, note = collect_diff(repo)
        if not diff_text.strip():
            entry.after(0, lambda: gitpanel._say(
                "Nothing to describe — stage or edit something first."))
            state["stop"] = True
            return
        placeholder = "⌛ drafting…"

        def set_ph():
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.config(fg=gitpanel.theme["text_muted"])
        entry.after(0, set_ph)

        def on_done(answer):
            def apply():
                if answer is None:
                    entry.delete(0, tk.END)
                    entry.insert(0, "")
                    entry.config(fg=gitpanel.theme["text"])
                    gitpanel._say("AI draft failed — write it yourself.")
                    return
                msg = _clean_message(answer)
                entry.delete(0, tk.END)
                entry.insert(0, msg)
                entry.config(fg=gitpanel.theme["text"])
                gitpanel._say(f"AI draft ({note}) — edit freely, then "
                              f"commit.")
                gitpanel.on_log("AI drafted a commit message")
            entry.after(0, apply)

        generate_message(config, diff_text, note, on_delta, on_done,
                         should_stop=lambda: state["stop"])

    threading.Thread(target=worker, daemon=True).start()
