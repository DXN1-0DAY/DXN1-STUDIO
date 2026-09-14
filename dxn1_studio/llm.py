"""DXN1 STUDIO — LLM backends for DXN1 Agents.

Everything here talks plain HTTPS with ``urllib`` from the Python
standard library. No SDKs, no Node, no helper processes — the entire
agent brain costs a few MB of RAM on top of the Tk window you are
already running.

Backends
--------
local    The agent's built-in offline skills (rule engine, no network).
free     The free stack — tries keyless cloud models first (Pollinations),
         then transparently fails over to GitHub Models when a GitHub
         login exists, and reports which brain answered. One setting,
         zero accounts required, three ways to stay online.
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
import urllib.parse
import urllib.request

UA = "DXN1-Studio/1.1.5 (agents)"
TIMEOUT = 120
# Pollinations' anonymous tier checks that requests come from a web
# origin — an https Referer keeps the keyless route open (plain API
# calls without one get 403'd). Points at the project page.
REFERRER = "https://dxn1-termux.github.io/DXN1-STUDIO/"

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
    "free":   ("Free cloud", "Keyless, with auto-failover to GitHub Models."),
    "byok":   ("BYOK", "Your own API key on any OpenAI-compatible provider."),
    "github": ("GitHub Models", "Free tier tracked via your GitHub login."),
    "kilo":   ("Kilo gateway", "Free models — Google login, token pasted in-app."),
}

# The free backend walks this chain until a model answers.
# "openai" is the provider's stable alias (currently maps to openai-fast);
# the second entry covers renames so the brain survives provider reshuffles.
FREE_MODELS = ("openai", "openai-fast")
FREE_GET_URL = "https://text.pollinations.ai/"


class AutoFreeBackend:
    """The 'free' brain as a resilient stack, not a single vendor.

    Order: Pollinations (keyless, anonymous) -> GitHub Models (free tier
    through your existing GitHub login, when a token is available). The
    first provider that answers wins for the rest of the session, and
    ``display`` always shows which brain is actually talking so the
    status bar is never a guess.
    """

    def __init__(self, config=None):
        self.config = config
        self._poll = PollinationsBackend(config)
        self._gh = None              # built lazily — needs a token
        self._active = self._poll
        self._gh_failed = False

    # keep usage accounting on whichever backend is active
    @property
    def last_usage(self):
        return getattr(self._active, "last_usage", None)

    @property
    def total_tokens(self):
        return getattr(self._active, "total_tokens", 0)

    @property
    def provider_name(self):
        if self._active is self._poll:
            return "pollinations"
        return "github models"

    @property
    def display(self):
        name = self.provider_name
        model = getattr(self._active, "model", "") or "default model"
        return f"Free cloud · {name} · {model}"

    def _github(self):
        if self._gh_failed or self._gh is not None:
            return self._gh
        try:
            self._gh = GitHubModelsBackend(self.config)
        except BackendError:
            self._gh_failed = True      # no login — don't retry every turn
            self._gh = None
        return self._gh

    def chat(self, messages, max_tokens=2048, temperature=0.3):
        try:
            text = self._poll.chat(messages, max_tokens=max_tokens,
                                   temperature=temperature)
            self._active = self._poll
            return text
        except BackendError as poll_exc:
            gh = self._github()
            if gh is not None:
                try:
                    text = gh.chat(messages, max_tokens=max_tokens,
                                   temperature=temperature)
                    self._active = gh
                    return text
                except BackendError:
                    pass
            # both clouds failed — surface the keyless error (it is the
            # one every user can act on without any account)
            raise poll_exc

    def chat_stream(self, messages, on_delta, should_stop=None,
                    max_tokens=2048, temperature=0.3):
        """Stream from the keyless cloud first, then GitHub Models.

        Any BackendError bubbles up so the caller can retry with the
        plain (non-streaming) chat — which carries the full fallback
        chain, including the GET route.
        """
        try:
            text = self._poll.chat_stream(
                messages, on_delta, should_stop, max_tokens=max_tokens,
                temperature=temperature)
            self._active = self._poll
            return text
        except BackendError as poll_exc:
            gh = self._github()
            if gh is not None:
                try:
                    text = gh.chat_stream(
                        messages, on_delta, should_stop,
                        max_tokens=max_tokens, temperature=temperature)
                    self._active = gh
                    return text
                except BackendError:
                    pass
            raise poll_exc


class BackendError(Exception):
    """Raised with a human-friendly message when a chat call fails."""


class StopGeneration(Exception):
    """Raised inside a stream when the user presses ■ stop."""


# Providers under load sometimes answer HTTP 200 with boilerplate error
# prose instead of a completion ("the API key used for this request has
# reached its budget" …). Guard so that junk never reaches the chat as
# if it were an answer. Short + specific phrases keeps false positives
# away from legit answers that merely discuss rate limits.
_PROVIDER_ERROR_MARKS = (
    "reached its budget",
    "api key used for this request",
    "insufficient_quota",
    "billing details",
    "exceeded your current quota",
)


def _looks_like_provider_error(text):
    """True when a completion is actually provider boilerplate."""
    if not text:
        return False
    # boilerplate always opens the message — judge the leading chunk so
    # a long markdown-wrapped notice still trips the check
    low = text[:240].lower()
    return any(mark in low for mark in _PROVIDER_ERROR_MARKS)


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


def _sse_post(url, payload, headers, on_delta, should_stop,
              timeout=TIMEOUT):
    """POST with "stream": true and read the answer as server-sent events.

    ``on_delta(full_text_so_far)`` fires as tokens land; raising
    :class:`StopGeneration` from ``should_stop``-driven checks aborts the
    read and the partial answer is lost on purpose. Returns the full text.
    """
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "text/event-stream")
    for k, v in headers.items():
        if v:
            req.add_header(k, v)
    chunks = []
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")[:400]
        except Exception:
            detail = ""
        try:
            j = json.loads(detail)
            detail = j.get("error", {}).get("message") or detail
        except Exception:
            pass
        raise BackendError(f"HTTP {exc.code} from {_host(url)}: "
                           f"{detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise BackendError(f"can't reach {_host(url)} ({exc.reason}) — "
                           f"check your connection") from exc
    except TimeoutError:
        raise BackendError("the provider took too long to answer") from None
    with resp:
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "text/event-stream" not in ctype:
            # provider ignored the stream flag — parse as a plain answer
            raw = resp.read().decode("utf-8", "replace")
            try:
                data = json.loads(raw)
                text = data["choices"][0]["message"]["content"] or ""
            except Exception:
                text = raw
            if should_stop():
                raise StopGeneration()
            if text.strip():
                chunks.append(text)
                on_delta(text)
            return "".join(chunks)
        for raw_line in resp:
            if should_stop():
                raise StopGeneration()
            line = raw_line.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            try:
                delta = obj["choices"][0].get("delta", {}).get("content") \
                    or ""
            except (KeyError, IndexError, TypeError):
                delta = ""
            if delta:
                chunks.append(delta)
                on_delta("".join(chunks))
    return "".join(chunks)


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

    def chat_stream(self, messages, on_delta, should_stop=None,
                    max_tokens=2048, temperature=0.3):
        """SSE streaming variant of :meth:`chat`.

        Returns the complete answer; raises StopGeneration when the user
        aborts. Falls back to the plain request when the endpoint refuses
        to stream.
        """
        if not self.base_url:
            raise BackendError("no endpoint configured")
        payload = {
            "model": self.model or "default",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        headers.update(self.extra_headers)
        text = _sse_post(f"{self.base_url}/chat/completions", payload,
                         headers, on_delta, should_stop or (lambda: False))
        if not text.strip():
            raise BackendError("the provider streamed an empty answer")
        self.last_usage = None          # streams rarely report usage
        self.total_tokens += max(1, len(text) // 4)   # ~4 chars per token
        return text


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
                         label="Free cloud",
                         extra_headers={"Referer": REFERRER,
                                        "User-Agent": UA})
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
                text = self._attempt(model, messages, max_tokens,
                                     temperature)
                if _looks_like_provider_error(text):
                    # HTTP 200, but the body is provider boilerplate —
                    # treat exactly like a failed request and fall over
                    raise BackendError("provider answered with an "
                                       "out-of-budget notice")
                return text
            except BackendError as exc:
                tried.append(f"{model}: {exc}")
                # a 403/401 means the anonymous POST tier itself is closed
                # for this IP — no point walking the remaining models
                if "HTTP 403" in str(exc) or "HTTP 401" in str(exc):
                    self._chain = []
                if self._chain:
                    model = self._chain.pop(0)
                    continue
                # last resort: the provider's plain-GET route — a different
                # code path that keeps the brain alive if the POST API moves
                try:
                    return self._get_fallback(messages)
                except BackendError as exc2:
                    tried.append(f"get-route: {exc2}")
                raise BackendError(
                    "the free cloud tier didn't answer ("
                    + (" · ".join(tried[:2]))
                    + "). It's rate-limited per IP — try again shortly, or "
                      "switch to a free Google-login brain (Kilo / GitHub "
                      "Models) or BYOK in Settings → DXN1 Agents.") from None

    def chat_stream(self, messages, on_delta, should_stop=None,
                    max_tokens=2048, temperature=0.3):
        """Streamed free-cloud call with the same boilerplate guard."""
        text = super().chat_stream(messages, on_delta, should_stop,
                                   max_tokens=max_tokens,
                                   temperature=temperature)
        if _looks_like_provider_error(text):
            raise BackendError("provider answered with an out-of-budget "
                               "notice")
        return text

    @staticmethod
    def _flatten(messages):
        """Squash a chat transcript into one plain prompt for the GET route."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            if role == "system":
                parts.append(f"[instructions] {content}")
            elif role == "assistant":
                parts.append(f"[assistant said] {content}")
            else:
                parts.append(content)
        prompt = "\n\n".join(parts)[-6000:]
        return urllib.parse.quote(prompt, safe="")

    def _get_fallback(self, messages):
        """Plain-text GET route — no JSON, no body, maximum compatibility."""
        url = FREE_GET_URL + self._flatten(messages)
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", UA)
        req.add_header("Referer", REFERRER)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                text = resp.read().decode("utf-8", "replace").strip()
        except urllib.error.HTTPError as exc:
            raise BackendError(f"HTTP {exc.code} on the GET route") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise BackendError(f"GET route unreachable — {exc}") from exc
        if not text:
            raise BackendError("GET route returned an empty answer")
        if _looks_like_provider_error(text):
            raise BackendError("GET route answered with an out-of-budget "
                               "notice")
        return text


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
            return AutoFreeBackend(config)
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

    def chat_stream(self, messages, on_delta, should_stop=None,
                    max_tokens=2048, temperature=0.3):
        raise BackendError(self.reason)


def describe_backend(config):
    """Short status-bar description of the active brain."""
    kind = (config.get("agents_backend") or "local").strip()
    if kind == "local":
        return "local skills"
    if kind == "free":
        # build the stack without any network calls — pure wiring
        return AutoFreeBackend(config).display
    backend = build_backend(config)
    if backend is None:
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


# ------------------------------------------------------- streaming shim
def stream_from_backend(backend, messages, on_delta, should_stop=None,
                        max_tokens=2048, temperature=0.3):
    """Stream if the backend can, else answer in one piece.

    Returns the full reply text. Raises StopGeneration when aborted,
    BackendError when the brain can't be reached at all. Never raises
    for "backend simply can't stream" — that path is invisible.
    """
    stop = should_stop or (lambda: False)
    fn = getattr(backend, "chat_stream", None)
    if fn is not None:
        try:
            return fn(messages, on_delta, stop, max_tokens=max_tokens,
                      temperature=temperature)
        except StopGeneration:
            raise
        except BackendError:
            pass                       # fall through to the plain call
    text = backend.chat(messages, max_tokens=max_tokens,
                        temperature=temperature)
    if stop():
        raise StopGeneration()
    if text.strip():
        on_delta(text)
    return text
