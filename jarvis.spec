# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for JARVIS — single-folder build bundling hotword models."""

import sys
from pathlib import Path

block_cipher = None

# Hotword model files to bundle
hotword_models = []
_model_dir = Path.home() / ".jarvis" / "hotword_models"
if _model_dir.exists():
    for onnx in _model_dir.glob("*.onnx"):
        hotword_models.append((str(onnx), "hotword_models"))

a = Analysis(
    ["src/main.py"],
    pathex=["."],
    binaries=[],
    datas=hotword_models + [
        ("src/ui/resources", "resources"),
    ],
    hiddenimports=[
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "sqlalchemy.dialects.sqlite",
        "anthropic",
        "openai",
        "google.generativeai",
        "pydantic",
        "fastapi",
        "uvicorn",
        "uvicorn.protocols.http.h11_impl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jarvis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="src/ui/resources/jarvis.ico" if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="jarvis",
)
