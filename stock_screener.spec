# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PPP Stock Screener
Build with: pyinstaller stock_screener.spec
"""

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('backend/static', 'static'),
        ('backend/app', 'app'),
    ],
    hiddenimports=[
        'fastapi',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'fastapi.staticfiles',
        'fastapi.responses',
        'uvicorn',
        'uvicorn.config',
        'uvicorn.main',
        'pydantic',
        'pydantic_settings',
        'pandas',
        'numpy',
        'pyarrow',
        'aiofiles',
        'httpx',
        'requests',
        'yfinance',
        'sse_starlette',
        'starlette',
        'starlette.middleware',
        'starlette.staticfiles',
        'starlette.responses',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PPPStockScreener',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for debugging (set to False for production)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add .ico file path here if desired
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PPPStockScreener'
)
