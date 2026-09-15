"""DXN1 STUDIO 3 — engine package.

The Python engine is the brain of the studio: it owns the workspace
(files, scenes, projects) and speaks a line-based JSON protocol on
stdio. The Electron UI is only the face — every mutation goes through
here, so the same brain can later serve any face we invent.

Run:  python3 -m engine [workspace]
"""

__version__ = "3.0.05"
