# -*- mode: python ; coding: utf-8 -*-
"""
LabToolbox PyInstaller 打包配置 (Windows + macOS 通用)

用法:
    pyinstaller labtoolbox.spec
"""
import sys
import os

# 项目根目录
ROOT = os.path.dirname(os.path.abspath(SPECFILE)) if 'SPECFILE' in globals() else os.getcwd()

# 图标: 暂时用默认 (可后续加 .ico/.icns)
icon_path = None
for cand in [os.path.join(ROOT, "assets", "labtoolbox.ico"),
             os.path.join(ROOT, "assets", "labtoolbox.icns")]:
    if os.path.exists(cand):
        icon_path = cand
        break

datas = []
# 包含示例数据 (可选)
# datas.append((os.path.join(ROOT, "data", "examples"), "data/examples"))

a = Analysis(
    [os.path.join(ROOT, "labtoolbox", "gui.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "labtoolbox.growth_curve",
        "labtoolbox.lipss_dloa",
        "labtoolbox.xdlvo",
        "labtoolbox.livedead",
        "labtoolbox.contact_angle",
        "labtoolbox.common.io_utils",
        "labtoolbox.common.fitting",
        "labtoolbox.common.stats",
        "labtoolbox.i18n",
        "scipy.optimize",
        "scipy.ndimage",
        "scipy.stats",
        "statsmodels.formula.api",
        "statsmodels.api",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter.test", "pydoc"],   # 注意: 不能排除 unittest (pyparsing 依赖)
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LabToolbox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # GUI 应用不显示控制台
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LabToolbox",
)

# macOS: 生成 .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="LabToolbox.app",
        icon=icon_path,
        bundle_identifier="uk.ac.dundee.labtoolbox",
        info_plist={
            "CFBundleName": "LabToolbox",
            "CFBundleDisplayName": "LabToolbox",
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
        },
    )
