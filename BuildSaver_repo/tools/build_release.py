"""Builds the release: SkillSaver.sdkmod, SkillSaverUI_1001_P.pak and BuildSaver_v<version>.zip.

usage: python tools/build_release.py --menu-html <the game's menu_bigmap.html> [--out dist]
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pakv8  # noqa: E402

INJECT = '<script src="coui://uiresources/_skillsaver/ui.js"></script>'
MOD_FILES = ("__init__.py", "ingame.py", "gear.py", "kbd.py")


def version() -> str:
    src = open(os.path.join(ROOT, "src", "SkillSaver", "__init__.py"), encoding="utf-8").read()
    return re.search(r'^VERSION = "([^"]+)"', src, re.M).group(1)


def build_sdkmod(out: str) -> None:
    # .sdkmod = zip with exactly one top folder named like the file
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("SkillSaver/", "")
        for f in MOD_FILES:
            z.write(os.path.join(ROOT, "src", "SkillSaver", f), f"SkillSaver/{f}")


def build_pak(out: str, menu_html: str) -> None:
    html = open(menu_html, "rb").read()                      # bytes: keep the game's line endings
    inject, close = INJECT.encode(), b"</widget-bigmap>"
    if inject not in html:
        if close not in html:
            sys.exit("menu_bigmap.html: closing </widget-bigmap> tag not found - wrong file?")
        html = html.replace(close, inject + close, 1)
    with tempfile.TemporaryDirectory() as tmp:
        ui = os.path.join(tmp, "OakGame", "Content", "uiresources")
        os.makedirs(os.path.join(ui, "_skillsaver"))
        os.makedirs(os.path.join(ui, "menu_bigmap"))
        shutil.copy(os.path.join(ROOT, "src", "ui", "ui.js"), os.path.join(ui, "_skillsaver", "ui.js"))
        with open(os.path.join(ui, "menu_bigmap", "menu_bigmap.html"), "wb") as f:
            f.write(html)
        pakv8.build(out, tmp)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--menu-html", required=True, help="the game's uiresources/menu_bigmap/menu_bigmap.html")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    v = version()
    mod = os.path.join(a.out, "SkillSaver.sdkmod")
    pak = os.path.join(a.out, "SkillSaverUI_1001_P.pak")
    build_sdkmod(mod)
    build_pak(pak, a.menu_html)
    zpath = os.path.join(a.out, f"BuildSaver_v{v}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(mod, "sdk_mods/SkillSaver.sdkmod")
        z.write(pak, "OakGame/Content/Paks/SkillSaverUI_1001_P.pak")
        for f in ("README.md", "KEYBOARD.md", "LICENSE", "CHANGELOG.md"):
            z.write(os.path.join(ROOT, f), f"BuildSaver_docs/{f}")
    print(zpath)


if __name__ == "__main__":
    main()
