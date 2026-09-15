#!/usr/bin/env python3
"""Boot a smoke studio + web bridge on a fixed port for visual QA.

Usage: python3 scripts/webui_preview.py [port]
Prints the tokened URL on stdout. Keeps the Tk main loop alive.
"""
import sys

sys.path.insert(0, ".")

from dxn1_studio import config as cfgmod  # noqa: E402
from dxn1_studio.app import DXN1Studio  # noqa: E402
from dxn1_studio import webridge as wb  # noqa: E402


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
    # optional second arg: workspace dir (QA against a throwaway
    # workspace instead of the repo root — keeps the tree clean)
    ws = sys.argv[2] if len(sys.argv) > 2 else "."
    app = DXN1Studio(cfgmod.Config(), smoke_test=True, no_splash=True)
    app.project_dir = ws
    server, url, token = wb.start_bridge(app, host="127.0.0.1",
                                         port=port)
    print(f"URL: {url}/?token={token}", flush=True)
    try:
        import time
        while True:
            try:
                app.root.update()
                time.sleep(0.08)
            except Exception as exc:  # noqa: BLE001
                print(f"LOOP-EXIT: {exc!r}", flush=True)
                break
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
