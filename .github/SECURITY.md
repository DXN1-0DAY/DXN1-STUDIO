# Security Policy — DXN1 STUDIO

## Supported versions

DXN1 STUDIO is a fast-moving desktop IDE. Only the **latest tagged
release** receives security fixes. Older tags (v1.4.x …) are kept for
reference and are not patched retroactively — please update.

| Version | Supported |
|---------|-----------|
| latest `vX.Y.Z` tag | ✅ |
| older tags          | ❌ (update first) |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

1. Use GitHub's **Private vulnerability reporting** on this repository
   (Security tab → Report a vulnerability), or
2. Contact the maintainer via GitHub (`@DXN1-termux`).

Include: affected version (`Help → About` output or the tag), a minimal
reproduction, and your assessment of the impact. You will get an
acknowledgement within **7 days** and a fix-or- mitigation plan within
**30 days** for accepted reports.

## Scope notes

DXN1 STUDIO is a local desktop application. The following are considered
in scope:

- Arbitrary code execution via crafted **project files** that the studio
  loads (e.g. malicious `.dxn1/` metadata, workspace JSON, plugin files)
- The agent/sandbox layer escaping the workspace root without consent
- Secret leakage (API keys for LLM backends) to unexpected destinations
- Insecure update/installer paths (`install.sh`, `updater`)

Out of scope: vulnerabilities in third-party LLM providers the user
configures, social engineering, and issues requiring physical access.

## Design notes for maintainers

- The agent sandbox (`sandbox.WorkspaceSandbox`) restricts file writes to
  the workspace root — never widen this without a security review.
- Plugin/theme files are data, not code: load them as JSON/config, never
  `exec`/`eval` their contents.
- API keys live in the local config file only; they must never be synced
  or logged.
