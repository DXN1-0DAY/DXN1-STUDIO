"""DXN1 STUDIO — LLM backends for DXN1 Agents.

Everything here talks plain HTTPS with ``urllib`` from the Python
standard library. No SDKs, no Node, no helper processes — the entire
agent brain costs a few MB of RAM on top of the Tk window you are
already running.

Backends
--------
local    The agent's built-in offline skills (rule engine, no network).
free     Pollinations — free cloud models with **no account, no API key,
         no login at all**. Usage is tracked anonymously (per IP) on their
         side; from the studio's side it's a single tiny POST per turn.
byok     Bring Your Own Key — any OpenAI-compatible endpoint:
         OpenRouter, Groq, Google AI Studio, Mistral, OpenAI, Ollama…
github   GitHub Models — free tier, authenticated with your existing
         GitHub login (``gh auth token``); usage is tracked by GitHub.
kilo     Kilo gateway — free-model routing through Kilo's API. Sign in
         with Google on their site, paste the token back into the
         studio's in-app Connect flow. This is a tiny direct HTTP client,
         NOT the VS Code extension: no editor fork, no Node process,
         near-zero extra RAM.
"""

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request

UA = "DXN1-Studio/1.1.2 (agents)"
TIMEOUT = 120

# ------------------------------------------------------------------ presets
# id -> label, base_url, suggested models, note, key hint, free tier?
PRESETS = {
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            "deepseek/deepseek-chat-v3.1:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "qwen/qwen-2.5-coder-32b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "openai/gpt-4o-mini",
        ],
        "note": "Sign in with Google, create a key — models marked :free cost nothing.",
        "key_hint": "sk-or-v1-…",
        "free": True,
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "models": [
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "llama-3.1-8b-instant",
        ],
        "note": "Free tier on absurdly fast hardware.",
        "key_hint": "gsk_…",
        "free": True,
    },
    "gemini": {
        "label": "Google AI Studio",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "models": ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"],
        "note": "Generous free tier with a Google AI Studio API key.",
        "key_hint": "AIza…",
        "free": True,
    },
    "mistral": {
        "label": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "models": ["mistral-small-latest", "codestral-latest"],
        "note": "Free experiment tier on La Plateforme.",
        "key_hint": "token…",
        "free": True,
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4o"],
        "note": "The reference API.",
        "key_hint": "sk-…",
        "free": False,
    },
    "ollama": {
        "label": "Ollama (local)",
        "base_url": "http://127.0.0.1:11434/v1",
        "models": ["qwen2.5-coder:7b", "deepseek-coder-v2:16b", "llama3.2"],
        "note": "Runs 100% on your machine — no key, no cloud, free forever.",
        "key_hint": "not needed",
        "free": True,
    },
    "custom": {
        "label": "Custom endpoint",
        "base_url": "",
        "models": [],
        "note": "Any OpenAI-compatible /chat/completions server (LM Studio, vLLM…).",
        "key_hint": "optional",
        "free": False,
    },
}

BACKEND_KINDS = ("local", "free", "byok", "github", "kilo")

BACKEND_INFO = {
    "local":  ("Local skills", "Offline rule engine — zero network, zero setup."),
    "free":   ("Free cloud", "No account, no key, no login — anonymous & free."),
    "byok":   ("BYOK", "Your own API key on any OpenAI-compatible provider."),
    "github": ("GitHub Models", "Free tier tracked via your GitHub login."),
    "kilo":   ("Kilo gateway", "Free models — Google login, token pasted in-app."),
}

# The free backend walks this chain until a model answers.
# "openai" is the provider's stable alias (currently maps to openai-fast);
# the second entry covers renames so the brain survives provider reshuffles.
FREE_MODELS = ("openai", "openai-fast")


class BackendError(Exception):
    """Raised with a human-friendly message when a chat call fails."""


# ------------------------------------------------------------------ plumbing
def _host(url):
    """Short host label for error messages."""
    for sep in ("/api", "/v1"):
        if sep in url:
            url = url.split(sep)[0]
    return url.replace("https://", "").replace("http://", "")


def _post_json(url, payload, headers, timeout=TIMEOUT):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    for k, v in headers.items():
        if v:
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")[:400]
        except Exception:
            detail = ""
        try:
            j = json.loads(detail)
            detail = j.get("error", {}).get("message") or j.get("message") or detail
        except Exception:
            pass
        raise BackendError(f"HTTP {exc.code} from {_host(url)}: "
                           f"{detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise BackendError(f"can't reach {_host(url)} ({exc.reason}) — "
                           f"check your connection") from exc
    except TimeoutError:
        raise BackendError("the provider took too long to answer") from None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # some free endpoints answer with plain text — accept that too
        if "text/plain" in ctype or (raw.strip() and not raw.lstrip()
                                     .startswith(("{", "["))):
            return {"choices": [{"message": {"content": raw}}]}
        raise BackendError("provider sent a response I couldn't parse") from None


def _get_json(url, api_key="", timeout=20):
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", UA)
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        raise BackendError(f"HTTP {exc.code} while listing models at "
                           f"{_host(url)}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise BackendError(f"can't reach {_host(url)} — {exc}") from exc
    except json.JSONDecodeError:
        raise BackendError("model list wasn't valid JSON") from None


def fetch_models(base_url, api_key=""):
    """Best-effort model-id list from an OpenAI-compatible /models route.

    Raises BackendError with a readable message on failure.
    """
    base = (base_url or "").rstrip("/")
    if not base:
        raise BackendError("no endpoint configured")
    if "text.pollinations.ai" in base:
        data = _get_json("https://text.pollinations.ai/models", "")
        out = []
        for item in (data if isinstance(data, list) else data.get("data", [])):
            if isinstance(item, dict) and item.get("name"):
                out.append(item["name"])
            elif isinstance(item, str):
                out.append(item)
        return out[:40] or list(FREE_MODELS)
    data = _get_json(f"{base}/models", api_key)
    items = data.get("data", data) if isinstance(data, dict) else data
    out = []
    for item in items if isinstance(items, list) else []:
        mid = item.get("id") if isinstance(item, dict) else item
        if mid:
            out.append(str(mid))
    return sorted(out)[:60]


class OpenAICompatBackend:
    """Minimal OpenAI-compatible chat client (works with every preset)."""

    def __init__(self, base_url, api_key, model, label="BYOK",
                 extra_headers=None):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = (model or "").strip()
        self.label = label
        self.extra_headers = extra_headers or {}
        self.last_usage = None       # {"total_tokens": n} when reported
        self.total_tokens = 0        # lifetime accumulation for this backend

    @property
    def display(self):
        return f"{self.label} · {self.model or 'default model'}"

    # ------------------------------------------------------------- request
    def _request(self, messages, max_tokens, temperature):
        if not self.base_url:
            raise BackendError("no endpoint configured")
        payload = {
            "model": self.model or "default",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        headers.update(self.extra_headers)
        return _post_json(f"{self.base_url}/chat/completions", payload, headers)

    @staticmethod
    def _content_of(data):
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise BackendError("provider response had no message content") \
                from None

    def chat(self, messages, max_tokens=2048, temperature=0.3):
        data = self._request(messages, max_tokens, temperature)
        usage = data.get("usage") if isinstance(data, dict) else None
        self.last_usage = usage if isinstance(usage, dict) else None
        if isinstance(self.last_usage, dict):
            self.total_tokens += int(self.last_usage.get("total_tokens") or 0)
        return self._content_of(data)


# ------------------------------------------------------------- Pollinations
class PollinationsBackend(OpenAICompatBackend):
    """Free cloud models with zero setup — no account, no key, no login.

    Anonymous usage is tracked per-IP by the provider; nothing is stored
    in DXN1 STUDIO and nothing to sign up for. Walks a small fallback
    chain so one busy/removed model doesn't break the brain.
    """

    BASE = "https://text.pollinations.ai/openai"

    def __init__(self, config=None):
        model = (config.get("agents_model") or "").strip() if config else ""
        super().__init__(self.BASE, "", model or FREE_MODELS[0],
                         label="Free cloud")
        self._chain = [m for m in FREE_MODELS if m != self.model]

    def _attempt(self, model, messages, max_tokens, temperature):
        self.model = model
        return super().chat(messages, max_tokens=max_tokens,
                            temperature=temperature)

    def chat(self, messages, max_tokens=2048, temperature=0.3):
        tried = []
        model = self.model
        while True:
            try:
                return self._attempt(model, messages, max_tokens, temperature)
            except BackendError as exc:
                tried.append(f"{model}: {exc}")
                if self._chain:
                    model = self._chain.pop(0)
                    continue
                raise BackendError(
                    "the free cloud tier didn't answer ("
                    + (" · ".join(tried[:2]))
                    + "). It's rate-limited per IP — try again shortly, or "
                      "switch to a free Google-login brain (Kilo / GitHub "
                      "Models) or BYOK in Settings → DXN1 Agents.") from None


# ---------------------------------------------------------------- GitHub free
def gh_cli_token():
    """Token from an authenticated GitHub CLI, if one is around."""
    exe = shutil.which("gh")
    if not exe:
        return ""
    try:
        out = subprocess.run([exe, "auth", "token"], capture_output=True,
                             text=True, timeout=8)
        return (out.stdout or "").strip()
    except Exception:
        return ""


def resolve_github_token(config=None):
    """Explicit PAT -> environment -> GitHub CLI. Empty string if none."""
    if config is not None:
        pat = (config.get("agents_github_key") or "").strip()
        if pat:
            return pat
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        val = (os.environ.get(var) or "").strip()
        if val:
            return val
    return gh_cli_token()


class GitHubModelsBackend(OpenAICompatBackend):
    """Free models via GitHub Models — usage tracked through GitHub auth.

    Tries the current models.github.ai endpoint first and transparently
    falls back to the legacy azure endpoint if the account/route needs it.
    """

    NEW_BASE = "https://models.github.ai/inference"
    OLD_BASE = "https://models.inference.ai.azure.com"
    DEFAULT_MODEL = "openai/gpt-4o-mini"

    def __init__(self, config=None):
        token = resolve_github_token(config)
        if not token:
            raise BackendError(
                "GitHub Models needs your GitHub login — run `gh auth login`, "
                "or paste a token in Settings → DXN1 Agents.")
        model = (config.get("agents_model") or "").strip() if config else ""
        super().__init__(self.NEW_BASE, token, model or self.DEFAULT_MODEL,
                         label="GitHub Models")
        self._legacy_tried = False

    def chat(self, messages, max_tokens=2048, temperature=0.3):
        try:
            return super().chat(messages, max_tokens=max_tokens,
                                temperature=temperature)
        except BackendError as exc:
            if "HTTP 404" in str(exc) and not self._legacy_tried and \
                    self.base_url == self.NEW_BASE:
                # old route wants bare model ids ("gpt-4o-mini")
                self._legacy_tried = True
                self.base_url = self.OLD_BASE
                self.model = self.model.split("/")[-1]
                return super().chat(messages, max_tokens=max_tokens,
                                    temperature=temperature)
            raise


# --------------------------------------------------------------------- Kilo
class KiloBackend(OpenAICompatBackend):
    """Kilo gateway — free-model routing over one tiny HTTP client.

    Deliberately NOT a bundled VS Code extension / Kilo instance: those
    eat hundreds of MB of RAM. This is a single ``urllib`` POST per turn,
    so the studio stays as light as it was without the agent.
    """

    DEFAULT_BASE = "https://api.kilocode.ai/v1"

    def __init__(self, config=None):
        base = (config.get("agents_kilo_url") or "").strip() if config else ""
        key = (config.get("agents_kilo_key") or "").strip() if config else ""
        model = (config.get("agents_model") or "").strip() if config else ""
        super().__init__(base or self.DEFAULT_BASE, key, model or "auto",
                         label="Kilo")


# ------------------------------------------------------------------ factory
def build_backend(config):
    """Return a live backend for the configured kind, or None for local."""
    kind = (config.get("agents_backend") or "local").strip()
    try:
        if kind == "free":
            return PollinationsBackend(config)
        if kind == "byok":
            preset_id = config.get("agents_provider") or "openrouter"
            preset = PRESETS.get(preset_id, PRESETS["openrouter"])
            base = (config.get("agents_base_url") or "").strip() \
                or preset["base_url"]
            key = (config.get("agents_api_key") or "").strip()
            model = (config.get("agents_model") or "").strip() \
                or (preset["models"][0] if preset["models"] else "")
            if not base:
                return None
            extra = {}
            if preset_id == "openrouter":
                extra = {"HTTP-Referer": "https://dxn1.studio",
                         "X-Title": "DXN1 STUDIO"}
            if preset_id == "ollama":
                extra = {"Authorization": ""}   # local server: skip auth
            return OpenAICompatBackend(base, key, model,
                                       label=preset["label"],
                                       extra_headers=extra)
        if kind == "github":
            return GitHubModelsBackend(config)
        if kind == "kilo":
            return KiloBackend(config)
    except BackendError as exc:
        # surface the reason through a stub that fails loudly in chat
        return BrokenBackend(str(exc))
    return None


class BrokenBackend:
    """Placeholder that turns configuration problems into chat messages."""

    label = "Not configured"

    def __init__(self, reason):
        self.reason = reason

    @property
    def display(self):
        return "setup needed"

    def chat(self, messages, max_tokens=2048, temperature=0.3):
        raise BackendError(self.reason)


def describe_backend(config):
    """Short status-bar description of the active brain."""
    kind = (config.get("agents_backend") or "local").strip()
    backend = build_backend(config) if kind != "local" else None
    if kind == "local" or backend is None:
        return "local skills"
    if isinstance(backend, BrokenBackend):
        return "setup needed"
    return backend.display


def test_backend(backend):
    """Tiny round-trip used by the settings page. Returns (ok, detail)."""
    try:
        text = backend.chat(
            [{"role": "user",
              "content": "Reply with exactly: OK"}],
            max_tokens=8, temperature=0.0)
        ok = bool(text and text.strip())
        return (ok, text.strip()[:60] if ok else "empty response")
    except BackendError as exc:
        return (False, str(exc))
    except Exception as exc:  # noqa: BLE001 — the test button never crashes
        return (False, f"unexpected error: {exc}")
