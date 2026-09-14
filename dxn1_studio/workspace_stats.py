"""DXN1 STUDIO — workspace statistics (DS2 v1.8).

Fast, honest numbers for any folder: file count, total lines, language
mix (by extension buckets), disk size and — when it's a git repo — the
commit count and last-commit subject. Used by the Project Hub's recent
cards and available as a one-call helper for anything else.

Design rules: stdlib only, one os.walk pass, skip the usual junk
(.git, node_modules, caches…), cap the walk so a huge folder never
freezes the UI thread, and never raise.
"""

import os
import subprocess

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules",
             ".mypy_cache", ".pytest_cache", "dist", "build",
             ".next", "target", ".dxn1", ".idea", ".vscode"}

LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JSX", ".tsx": "TSX", ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".go": "Go", ".rs": "Rust", ".java": "Java",
    ".c": "C", ".h": "C", ".cpp": "C++", ".rb": "Ruby", ".php": "PHP",
    ".sh": "Shell", ".md": "Markdown", ".json": "JSON", ".yaml": "YAML",
    ".yml": "YAML", ".toml": "TOML", ".txt": "Text", ".sql": "SQL",
    ".kt": "Kotlin", ".swift": "Swift", ".dart": "Dart",
}

WALK_CAP = 8000          # files examined max
LINE_SAMPLE_CAP = 200000  # lines counted max


def stats_for(path):
    """Compute workspace stats. Returns {} on any problem."""
    if not path or not os.path.isdir(path):
        return {}
    files = 0
    lines = 0
    size = 0
    lang_lines = {}
    try:
        for root, dirs, names in os.walk(path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS
                       and not d.startswith(".")]
            for name in names:
                if files >= WALK_CAP:
                    break
                full = os.path.join(root, name)
                try:
                    if os.path.islink(full) or not os.path.isfile(full):
                        continue
                    st = os.stat(full)
                    size += st.st_size
                    files += 1
                    ext = os.path.splitext(name)[1].lower()
                    lang = LANG_BY_EXT.get(ext)
                    if lang and lines < LINE_SAMPLE_CAP and st.st_size < 1_500_000:
                        with open(full, "rb") as fh:
                            data = fh.read(1_500_000)
                        n = data.count(b"\n")
                        if data and not data.endswith(b"\n"):
                            n += 1          # final line without newline
                        lines += n
                        lang_lines[lang] = lang_lines.get(lang, 0) + n
                except OSError:
                    continue
            if files >= WALK_CAP:
                break
    except OSError:
        pass

    languages = dict(sorted(lang_lines.items(), key=lambda kv: -kv[1]))
    out = {
        "files": files,
        "lines": lines,
        "size_mb": round(size / (1024 * 1024), 1),
        "languages": languages,
        "primary_language": next(iter(languages), ""),
        "commits": None,
        "last_commit": "",
    }
    # git extras — best effort
    try:
        proc = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"], cwd=path,
            capture_output=True, text=True, timeout=8)
        if proc.returncode == 0 and proc.stdout.strip().isdigit():
            out["commits"] = int(proc.stdout.strip())
        proc = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%s"], cwd=path,
            capture_output=True, text=True, timeout=8)
        if proc.returncode == 0:
            out["last_commit"] = proc.stdout.strip()[:80]
        out["is_git"] = True
    except (OSError, subprocess.SubprocessError):
        out["is_git"] = False
    return out


def summary_line(stats):
    """One compact, human line for a card: '128 files · Python 61% · 12 commits'."""
    if not stats:
        return ""
    parts = [f"{stats.get('files', 0):,} files"]
    if stats.get("primary_language"):
        lang = stats["primary_language"]
        total = sum(stats.get("languages", {}).values()) or 1
        pct = int(stats["languages"].get(lang, 0) * 100 / total)
        parts.append(f"{lang} {pct}%")
    if stats.get("commits") is not None:
        parts.append(f"{stats['commits']:,} commits")
    parts.append(f"{stats.get('size_mb', 0)} MB")
    return "  ·  ".join(parts)


def language_mix(stats, top=4):
    """[(lang, pct), …] for mini bars."""
    langs = stats.get("languages", {})
    total = sum(langs.values()) or 1
    mix = [(name, round(n * 100 / total)) for name, n in
           sorted(langs.items(), key=lambda kv: -kv[1])[:top]]
    used = sum(p for _n, p in mix)
    if mix and used < 100:
        name, pct = mix[-1]
        mix[-1] = (name, pct + (100 - used))
    return mix
