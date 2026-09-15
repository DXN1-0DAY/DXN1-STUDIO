"""Verify the webridge queue-pump with a REAL mainloop harness.

Worker thread does HTTP only; the Tk main loop drains the pump.
Prints the tab state that the web UI would render.
"""
import json
import pathlib
import sys
import tempfile
import threading
import time
import urllib.request

sys.path.insert(0, "/home/z/dxn1-studio-original")

from dxn1_studio import config as cfgmod  # noqa: E402
from dxn1_studio.app import DXN1Studio  # noqa: E402
from dxn1_studio.webridge import start_bridge  # noqa: E402

app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
ws = tempfile.mkdtemp(prefix="dxn1-pump-")
app.project_dir = ws
pathlib.Path(ws + "/demo.py").write_text("def hello():\n    return 1\n")
server, url, tok = start_bridge(app)
result = {}


def worker():
    def req(p, data=None):
        r = urllib.request.Request(
            url + p,
            **({"data": json.dumps(data).encode()} if data else {}))
        r.add_header("X-DXN1-Token", tok)
        r.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(r, timeout=5) as fh:
            return json.loads(fh.read())
    try:
        time.sleep(0.4)
        result["open"] = req("/api/open", {"path": "demo.py"})
        time.sleep(1.2)
        result["state"] = req("/api/state")
    except Exception as e:  # noqa: BLE001
        result["err"] = repr(e)


# main thread schedules its own quit — no cross-thread after anywhere
app.root.after(3000, app.root.destroy)
threading.Thread(target=worker, daemon=True).start()
app.root.mainloop()
print("open ->", result.get("open"))
print("state tabs ->", result.get("state", {}).get("tabs"))
print("buffers ->", list(app._buffers.keys()), flush=True)
