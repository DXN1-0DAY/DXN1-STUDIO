"""DXN1 STUDIO — dependency cross-check (DS2 v2.36).

The ``deps`` verb asks an honest question: does the code import
things the requirements never mention, and does the requirements
file demand things the code never imports? Pure static analysis —
an AST walk over ``*.py`` plus canonical-name parsing over
``requirements*.txt`` (and ``pyproject.toml`` ``[project]``
dependencies via ``tomllib`` when available) — the project's code
is never executed and nothing touches the network.

The mapping between a distribution name and its import name is not
always mechanical (``Pillow`` ships ``PIL``, ``beautifulsoup4``
ships ``bs4``), so a small table of famous pairs covers the classic
cases and everything else falls back to PEP 503 normalisation.
Best effort by design: an unknown pair can raise a false "missing"
— the report says so, and ``python -c "import X"`` remains the
final judge. Junk in, honest report out: unreadable files are
skipped, missing requirements files produce a clear notice instead
of an error.
"""

import ast
import os
import re
import sys
import time

try:  # py3.11+ — pyproject.toml [project] dependencies support
    import tomllib
except ImportError:  # pragma: no cover — older interpreters
    tomllib = None

try:  # py3.10+ — the honest stdlib list
    _STDLIB = frozenset(sys.stdlib_module_names)
except AttributeError:  # pragma: no cover — ancient fallback
    _STDLIB = frozenset({
        "os", "sys", "re", "json", "math", "time", "datetime", "tkinter",
        "subprocess", "threading", "collections", "itertools", "functools",
        "pathlib", "typing", "logging", "random", "shutil", "tempfile"})

SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "env", "node_modules",
             ".dxn1", ".tox", ".mypy_cache", ".pytest_cache", "build",
             "dist", ".eggs", "site-packages"}

# famous distribution name (PEP 503 canonical) -> top-level import name
ALIASES = {
    "pillow": "pil",
    "beautifulsoup4": "bs4",
    "python-dateutil": "dateutil",
    "pyyaml": "yaml",
    "opencv-python": "cv2",
    "opencv-contrib-python": "cv2",
    "opencv-python-headless": "cv2",
    "scikit-learn": "sklearn",
    "scikit-image": "skimage",
    "python-dotenv": "dotenv",
    "python-markdown": "markdown",
    "protobuf": "google",
    "pycryptodome": "crypto",
    "pycryptodomex": "cryptodome",
    "biopython": "bio",
    "attrs": "attr",
    "pymupdf": "fitz",
    "python-telegram-bot": "telegram",
    "msgpack-python": "msgpack",
    "pywin32": "win32",
    "pypdf2": "pypdf",
    "pymysql": "pymysql",
    "psycopg2-binary": "psycopg2",
    "pyjwt": "jwt",
    "python-jose": "jose",
    "python-multipart": "multipart",
}

# reverse map: import name -> the distribution we would pin. Ties
# (three opencv dists ship cv2) resolved by an explicit hint so the
# suggestion is the classic package, not an exotic variant.
ALIASES_INV = {}
for _dist in sorted(ALIASES):
    ALIASES_INV.setdefault(ALIASES[_dist], _dist)
ALIASES_INV.update({
    "cv2": "opencv-python",
    "google": "protobuf",
    "pypdf": "pypdf",
})

_REQ_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


# ----------------------------------------------------------------- names
def canonical(name):
    """PEP 503 normalisation: ``Pillow_-2`` -> ``pillow-2``."""
    return re.sub(r"[-_.]+", "-", str(name or "").strip()).lower()


def top_imports(node):
    """Top-level module names imported by one ast node (Import /
    ImportFrom). Relative imports yield nothing — they are local by
    definition."""
    out = []
    if isinstance(node, ast.Import):
        for a in node.names:
            out.append(str(a.name).split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        if getattr(node, "level", 0):
            return out                     # from .x import y — local
        if node.module:
            out.append(str(node.module).split(".")[0])
    return out


def scan_imports(paths):
    """``{file: [top-level module, ...]}`` for each readable ``.py``.

    Unreadable or unparseable files are skipped — a broken file must
    not blind the whole report."""
    out = {}
    for p in paths:
        try:
            if not str(p).endswith(".py"):
                continue
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                tree = ast.parse(fh.read())
        except Exception:  # noqa: BLE001 — junk file, keep going
            continue
        names = set()
        for node in ast.walk(tree):
            names.update(top_imports(node))
        out[str(p)] = sorted(names)
    return out


def classify(names, local_modules=()):
    """Split module names into ``(stdlib, local, third_party)``."""
    local = {str(m) for m in (local_modules or ())}
    stdlib, third = [], []
    for n in names:
        if n in _STDLIB:
            stdlib.append(n)
        elif n in local:
            continue                       # counted via `local` set
        else:
            third.append(n)
    return sorted(stdlib), sorted(set(local) & set(names)), sorted(third)


# ---------------------------------------------------------- requirements
def read_requirements(path):
    """Canonical requirement names from one requirements-style file.

    Handles pins (``flask>=3``), extras (``uvicorn[standard]``),
    inline comments, ``-r``/``-e``/``--hash`` plumbing lines and
    URL requirements (``name @ https://...``). Junk lines skipped."""
    names = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except Exception:  # noqa: BLE001 — unreadable is just empty
        return names
    for ln in lines:
        ln = ln.split("#", 1)[0].strip()
        if not ln or ln.startswith(("-", ".")):
            continue                       # -r, -e, --hash, . dirs
        if re.match(r"^[A-Za-z]+\+", ln):
            continue                       # git+/svn+/hg+ VCS URLs
        m = _REQ_NAME.match(ln)
        if m:
            names.append(canonical(m.group(1)))
    return names


def pyproject_dependencies(root):
    """``[project] dependencies`` from pyproject.toml (py3.11+ with
    tomllib). Returns ``[]`` when there is nothing to read."""
    if tomllib is None:
        return []
    p = os.path.join(str(root), "pyproject.toml")
    try:
        with open(p, "rb") as fh:
            data = tomllib.load(fh)
        deps = (data.get("project") or {}).get("dependencies") or []
        out = []
        for d in deps:
            m = _REQ_NAME.match(str(d).strip())
            if m:
                out.append(canonical(m.group(1)))
        return out
    except Exception:  # noqa: BLE001 — absent or junk pyproject
        return []


def find_requirements(root):
    """Every ``requirements*.txt`` at the workspace root (sorted)."""
    root = str(root)
    out = []
    try:
        for name in sorted(os.listdir(root)):
            if name.startswith("requirements") and name.endswith(".txt"):
                out.append(os.path.join(root, name))
    except Exception:  # noqa: BLE001 — unreadable root
        pass
    return out


def req_import_names(req_names):
    """Every import name a set of requirements could satisfy — the
    names themselves plus their famous aliases."""
    out = set(req_names)
    for n in req_names:
        a = ALIASES.get(n)
        if a:
            out.add(a)
    return out


# -------------------------------------------------------------------- fix
def dist_for_import(imp):
    """Best-effort distribution name for an import name — the reverse
    alias table first, else the name itself (PEP 503 canonical)."""
    n = canonical(imp)
    return ALIASES_INV.get(n, n)


def suggested_pins(missing_imports):
    """Distribution names worth pinning for missing imports — deduped,
    sorted, canonical. ``PIL`` becomes ``pillow``, ``yaml`` becomes
    ``pyyaml``, ``flask`` stays ``flask``."""
    out = []
    for imp in missing_imports or []:
        d = dist_for_import(imp)
        if d and d not in out:
            out.append(d)
    return sorted(out)


def fix_requirements(root, pins, path=None):
    """Append missing pins to a requirements file — atomically, never
    overwriting content, never duplicating a line already present.

    Returns ``{ok, added, target, error}``. When no requirements file
    exists and ``path`` is not given, ``requirements.txt`` is created
    at the workspace root. """
    root = str(root)
    if path:
        target = str(path)
    else:
        found = find_requirements(root)
        target = found[0] if found else os.path.join(root,
                                                     "requirements.txt")
    existing = set()
    if os.path.isfile(target):
        existing = {canonical(n) for n in read_requirements(target)}
    fresh = sorted({canonical(p) for p in (pins or [])
                    if p and canonical(p) not in existing})
    if not fresh:
        return {"ok": True, "added": [], "target": target, "error": ""}
    stamp = time.strftime("%Y-%m-%d")
    block = (f"# added by deps on {stamp}\n"
             + "\n".join(fresh) + "\n")
    try:
        old = ""
        if os.path.isfile(target):
            with open(target, "r", encoding="utf-8",
                      errors="replace") as fh:
                old = fh.read()
        if old and not old.endswith("\n"):
            old += "\n"
        tmp = target + ".tmp"
        d = os.path.dirname(target)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(old + block)
        os.replace(tmp, target)
        return {"ok": True, "added": fresh, "target": target,
                "error": ""}
    except Exception as exc:  # noqa: BLE001 — honest failure
        return {"ok": False, "added": [], "target": target,
                "error": str(exc)}


# ----------------------------------------------------------------- local
def local_modules(root):
    """Import names the workspace itself provides: ``*.py`` stems and
    directories with an ``__init__.py`` at the root level."""
    root = str(root)
    out = set()
    try:
        for name in os.listdir(root):
            if name.endswith(".py"):
                out.add(name[:-3])
            elif os.path.isdir(os.path.join(root, name)) and \
                    os.path.isfile(os.path.join(root, name,
                                                "__init__.py")):
                out.add(name)
    except Exception:  # noqa: BLE001 — unreadable root
        pass
    return out


def python_files(root):
    """Every ``.py`` under the workspace, junk directories skipped."""
    found = []
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                found.append(os.path.join(dirpath, f))
    return found


# ---------------------------------------------------------------- report
def check(root):
    """The full cross-check report for a workspace. Never raises.

    Keys: ``files``, ``third_party``, ``missing``, ``unused``,
    ``req_files``, ``requirements`` (count), ``note`` (honest caveats).
    """
    root = str(root)
    files = python_files(root)
    imports = scan_imports(files)
    all_names = sorted({n for ns in imports.values() for n in ns})
    _std, _loc, third = classify(all_names,
                                 local_modules=local_modules(root))

    req_files = find_requirements(root)
    req_names = set()
    for rf in req_files:
        req_names.update(read_requirements(rf))
    pyreqs = pyproject_dependencies(root)
    req_names.update(pyreqs)
    if pyreqs:
        req_files = req_files + ["pyproject.toml"]

    satisfied = req_import_names(req_names)   # canonical + aliases, lower
    # imports keep their original case ("PIL") — compare lowercased
    missing = [n for n in third if n.lower() not in satisfied]
    used = {str(n).lower() for n in all_names}
    unused = [r for r in sorted(req_names)
              if r not in used and ALIASES.get(r) not in used]

    note = ""
    if not req_files:
        note = ("no requirements*.txt (or pyproject dependencies) at "
                "the workspace root — drop one in and re-run `deps`")
    elif missing:
        note = ("best-effort static check — a rare distribution ships "
                "an unexpected import name; verify with "
                "`python -c \"import X\"` before pinning")
    return {"files": len(imports), "third_party": third,
            "missing": missing, "unused": unused,
            "req_files": req_files, "requirements": len(req_names),
            "note": note}


def describe(rep):
    """Human multi-line summary for the terminal. Empty report -> ''."""
    if not isinstance(rep, dict) or not rep.get("files"):
        return ""
    lines = [f"deps: {rep['files']} file(s) scanned · "
             f"{len(rep['third_party'])} third-party import(s) · "
             f"{rep['requirements']} requirement(s) "
             f"({len(rep['req_files'])} file(s))"]
    if rep.get("missing"):
        lines.append("  imported but NOT in requirements:")
        for n in rep["missing"][:12]:
            lines.append(f"    ! {n}")
        if len(rep["missing"]) > 12:
            lines.append(f"    … +{len(rep['missing']) - 12} more")
    if rep.get("unused"):
        lines.append("  in requirements but never imported:")
        for n in rep["unused"][:12]:
            lines.append(f"    - {n}")
        if len(rep["unused"]) > 12:
            lines.append(f"    … +{len(rep['unused']) - 12} more")
    if not rep.get("missing") and not rep.get("unused") and \
            rep.get("req_files"):
        lines.append("  imports and requirements agree — clean bill")
    if rep.get("note"):
        lines.append(f"  note: {rep['note']}")
    return "\n".join(lines)


# -------------------------------------------------------------- self-test
if __name__ == "__main__":
    import tempfile
    base = tempfile.mkdtemp(prefix="ds2-depcheck-selftest-")
    with open(os.path.join(base, "main.py"), "w") as fh:
        fh.write("import os\nimport requests as r\nfrom PIL import Image\n"
                 "import localmod\nfrom .rel import x\n")
    with open(os.path.join(base, "localmod.py"), "w") as fh:
        fh.write("x = 1\n")
    with open(os.path.join(base, "requirements.txt"), "w") as fh:
        fh.write("requests>=2.0  # the client\nflask\npillow\n"
                 "-r other.txt\n--hash=sha256:abc\n")
    rep = check(base)
    assert rep["files"] == 2, rep
    assert "requests" in rep["third_party"] and "PIL" in rep["third_party"]
    assert rep["missing"] == [], rep
    assert rep["unused"] == ["flask"], rep
    assert "requirements agree" not in describe(rep)
    rep2 = check(tempfile.mkdtemp(prefix="ds2-empty-"))
    assert rep2["files"] == 0 and "no requirements" in rep2["note"]
    assert describe(rep2) == ""
    assert canonical("Pillow_-2") == "pillow-2"
    assert read_requirements("/no/such/file") == []
    # fix lane: suggestions + atomic append + dedupe
    assert dist_for_import("PIL") == "pillow"
    assert dist_for_import("yaml") == "pyyaml"
    assert dist_for_import("cv2") == "opencv-python"
    assert dist_for_import("flask") == "flask"
    assert suggested_pins(["PIL", "yaml", "PIL"]) == ["pillow",
                                                       "pyyaml"]
    reqp = os.path.join(base, "requirements.txt")
    res = fix_requirements(base, ["uvicorn", "flask", "httpx"])
    assert res["ok"] and res["added"] == ["httpx", "uvicorn"], res
    body = open(reqp).read()
    assert "uvicorn" in body and "# added by deps on" in body
    res2 = fix_requirements(base, ["uvicorn"])
    assert res2["ok"] and res2["added"] == [], res2
    assert open(reqp).read().count("uvicorn") == 1
    # a missing requirements file is created on demand
    bare = os.path.join(base, "sub")
    os.makedirs(bare, exist_ok=True)
    res3 = fix_requirements(bare, ["requests"])
    assert res3["ok"] and res3["added"] == ["requests"]
    assert os.path.isfile(os.path.join(bare, "requirements.txt"))
    assert not os.path.exists(reqp + ".tmp"), "atomic append leaves no tmp"
    print("depcheck.py self-test OK")
