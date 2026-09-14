# DXN1 STUDIO — Plugin Guide (v1)

Plugins are small folders that add commands and hooks to the studio.
They run **locally**, they are **approval-gated** (one prompt per code
fingerprint — any edit re-asks), and a broken plugin can never break
the studio: failures are caught, logged and shown in the Plugin
Manager.

Open the manager from the Command Palette (`Ctrl+Shift+P` →
**Plugin manager**) to approve, disable or reload plugins.

## Quick start (30 seconds)

1. Open the plugin folder: palette → *Plugin manager* → **Open plugin
   folder** (or create `~/.dxn1-studio/plugins/` yourself).
2. Copy one of the **sample plugins** there — the studio ships
   `insert-header`, `commit-lint` and `session-clock` into that folder
   automatically on first run (source in
   `dxn1_studio/plugins.py → write_sample_plugins`).
3. Palette → **Plugin manager** → *Approve & enable*.
4. Your plugin's commands now appear in the palette as
   `<label> · plugin:<name>`.

## Folder layout

```
~/.dxn1-studio/plugins/
└── my-plugin/
    ├── plugin.json     ← manifest (required)
    └── plugin.py       ← entry module (required for hooks/commands)
```

Workspace-scoped plugins live in `<workspace>/.dxn1/plugins/` and win
over global plugins with the same name — useful for project-specific
tooling you can commit to git.

## The manifest (`plugin.json`)

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What it does, in one line.",
  "author": "you",
  "commands": [
    { "label": "Do a thing" }
  ],
  "hooks": ["save", "open", "commit"]
}
```

| Field         | Required | Notes                                     |
|---------------|----------|-------------------------------------------|
| `name`        | yes      | ≤ 48 chars, unique per scope              |
| `version`     | no       | shown in the manager                      |
| `description` | no       | shown in the manager                      |
| `author`      | no       | shown in the approval dialog              |
| `commands`    | no       | labels become palette entries             |
| `hooks`       | no       | declaration shown in the approval dialog  |

## The entry module (`plugin.py`)

The studio imports the module and calls `register(api)` exactly once:

```python
def register(api):
    # 1) palette command — fn receives a context dict
    api.register_command("Say hello", lambda ctx: f"hello from {ctx['path']}")

    # 2) hooks
    api.on_save(my_on_save)          # ctx: {event, path, text, workspace}
    api.on_open(my_on_open)
    api.on_commit(my_on_commit)      # ctx: {event, message, workspace}

    # 3) status bar text (return "" to hide)
    api.add_status_item("clock", lambda ctx: time.strftime("%H:%M"))

    # 4) namespaced settings (stored in the studio config)
    api.set_setting("greeting", "hi")
    api.get_setting("greeting", "default")

    # 5) logging — lands in the terminal panel
    api.log("my-plugin ready")
```

### Command results

A command may return:

* a **string** → inserted at the editor cursor (snippets!),
* any other value → logged to the terminal,
* nothing → silent.

### The context dict

| key         | value                                   |
|-------------|-----------------------------------------|
| `path`      | current file path ("" if none)          |
| `text`      | current file text ("" if none)          |
| `selection` | current editor selection ("" if none)   |
| `workspace` | workspace root                          |
| `message`   | commit message (commit hook only)       |

## Safety model

* First load shows a dialog listing exactly what the plugin wants to
  do. Approval is remembered by a **sha256 fingerprint** of the
  manifest + code — editing the plugin re-triggers the prompt.
* `Disable` unloads it for this session; removing the folder (or
  deleting the entry from `approved_plugins` in your config)
  un-approves it.
* Every hook call and command is wrapped: exceptions are logged, never
  raised into the studio.
* Plugins get **no** network layer and **no** hidden filesystem
  rights — they run with your normal Python permissions, which is
  exactly why the approval prompt exists. Only install plugins you
  trust, like you would any local tool.

## Publishing ideas

Drop a `plugin.json` + `plugin.py` into a public GitHub repo and share
the link — users clone it into their plugin folder. Tag releases with
the studio version you tested against (`studio: >=2.0`).
