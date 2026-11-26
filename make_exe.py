"""Build the app: a portable install in the Daily-Reading folder next to this script, and
Daily-Reading.zip of it to share.

    python make_exe.py

The Daily-Reading folder holds everything the app needs, and can be copied anywhere
(a USB stick, another computer) and run from there:

    Daily-Reading.exe
    _internal/                    the app's own files: Python, the page, the icon
    Daily-Reading_themes/         copied from the project
    Daily-Reading_schedules/      copied from the project
    README.md, LICENSE            copied from the project
    Daily-Reading_settings.json   made by the app when you change a setting
    Daily-Reading_keys.txt        optional, added by you
    Daily-Reading_bibles/         optional, XML bibles added by you

Daily-Reading.zip has the same files without your settings, keys and XML bibles, ready to
give to someone else ("Extract All" makes the Daily-Reading folder). The project's
Daily-Reading_bibles folder is never copied: many of those bibles are copyrighted.

The Daily-Reading_themes and Daily-Reading_schedules folders in the project are the ones
to work on; each build copies them into the app folder so it matches the project.
Anything in the app folder's copies that the project doesn't have, or that is newer there
(a theme saved from the app, boxes ticked while using it), is first backed up to
backups/<date-time>/ and listed, so nothing is lost. Your own files in the app folder
(settings, keys, anything else) are kept as they are.

PyInstaller's working files go to a temporary folder and are deleted afterwards, as are
Python's __pycache__ folders, so the project folder stays clean.
"""
import filecmp
import functools
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
APP_NAME = "Daily-Reading"
APP_DIR = ROOT / APP_NAME                 # the portable install
ZIP = ROOT / f"{APP_NAME}.zip"
OLD_DIST = ROOT / "dist"                  # where earlier builds went
FOLDERS = ["Daily-Reading_themes", "Daily-Reading_schedules"]
EXTRA_FILES = ["README.md", "LICENSE"]    # copied from the project into the app folder
PERSONAL = {"Daily-Reading_settings.json", "Daily-Reading_keys.txt",   # never in the zip
            "Daily-Reading_bibles"}                                    # (bibles: copyright)
EXE = f"{APP_NAME}.exe"
BUILD_OUTPUT = {EXE, "_internal"}         # what PyInstaller makes in APP_DIR
STAMP = time.strftime("%Y-%m-%d_%H%M%S")
print = functools.partial(print, flush=True)   # keep messages in order with build.py's output


def exe_running():
    if sys.platform != "win32":
        return False
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {EXE}", "/NH"], capture_output=True, text=True)
    return EXE.lower() in out.stdout.lower()


def back_up_changes(where):
    """Copy files in <where>/<folder> that hold changes the project doesn't have (missing
    from the project, or different and newer) to backups/<stamp>/."""
    saved = []
    for folder in FOLDERS:
        src, dst = ROOT / folder, where / folder
        if not dst.is_dir():
            continue
        for f in dst.iterdir():
            if not f.is_file():
                continue
            p = src / f.name
            if not p.exists() or (not filecmp.cmp(f, p, shallow=False) and f.stat().st_mtime > p.stat().st_mtime):
                backup = ROOT / "backups" / STAMP / folder / f.name
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, backup)
                saved.append(backup)
    return saved


def back_up_dist_changes():
    return back_up_changes(APP_DIR)


def user_files(folder):
    """Files and folders of the user's in an app folder: not build output, not the copied
    folders or files."""
    if not folder.is_dir():
        return []
    skip = BUILD_OUTPUT | set(FOLDERS) | set(EXTRA_FILES)
    return [item for item in folder.iterdir() if item.name not in skip]


def move_old_dist():
    """Earlier builds went into dist/ (dist/Daily-Reading/, or before that a single
    dist/Daily-Reading.exe with the folders beside it). Back up changes in their themes
    and schedules, move your own files (settings, keys) into the new app folder, and
    remove dist/. Returns the backed-up paths."""
    if not OLD_DIST.is_dir():
        return []
    saved = []
    for old_app in (OLD_DIST / APP_NAME, OLD_DIST):
        if not old_app.is_dir():
            continue
        saved += back_up_changes(old_app)
        for item in user_files(old_app):
            if old_app == OLD_DIST and (item.name == APP_NAME or (item.name == EXE and item.is_file())):
                continue
            APP_DIR.mkdir(exist_ok=True)
            if not (APP_DIR / item.name).exists():
                shutil.move(str(item), APP_DIR / item.name)
                print(f"  moved {item.relative_to(ROOT)} into {APP_NAME}/")
    shutil.rmtree(OLD_DIST)
    print("  removed dist/ (builds now go into the Daily-Reading folder)")
    return saved


def set_aside_user_files(stash):
    """PyInstaller empties the app folder when it builds: keep the user's own files there."""
    kept = []
    for item in user_files(APP_DIR):
        shutil.move(str(item), stash / item.name)
        kept.append(stash / item.name)
    return kept


def put_back(kept):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    for item in kept:
        shutil.move(str(item), APP_DIR / item.name)


def mirror(folder):
    """Make <app folder>/<folder> an exact copy of the project's <folder>."""
    src, dst = ROOT / folder, APP_DIR / folder
    if not src.is_dir():
        print(f"  (no {folder} in the project)")
        return
    dst.mkdir(parents=True, exist_ok=True)
    names = {f.name for f in src.iterdir() if f.is_file()}
    for f in dst.iterdir():
        if f.is_file() and f.name not in names:
            f.unlink()
    for name in sorted(names):
        shutil.copy2(src / name, dst / name)
    print(f"  {dst.relative_to(ROOT)}: {len(names)} files")


def make_zip():
    """Daily-Reading.zip: the app folder's contents at the top of the zip (Windows' "Extract
    All" puts them in a Daily-Reading folder by itself), without your settings, keys and
    XML bibles (and without leftovers of an interrupted save)."""
    tmp = ZIP.with_suffix(".zip.tmp")
    count = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(APP_DIR.rglob("*")):
            rel = path.relative_to(APP_DIR)
            if rel.parts[0] in PERSONAL or path.name.endswith(".saving"):
                continue
            arcname = rel
            if path.is_dir():
                z.write(path, arcname.as_posix() + "/")
            else:
                z.write(path, arcname.as_posix())
                count += 1
    os.replace(tmp, ZIP)
    print(f"  {ZIP.name}: {count} files, {ZIP.stat().st_size / 1e6:.1f} MB (without your settings, keys and bibles)")


def clean_up():
    """Remove what Python and earlier builds leave in the project folder."""
    removed = []
    for path in [ROOT / "build", ROOT / f"{APP_NAME}.spec",
                 *[p for p in ROOT.rglob("__pycache__") if APP_DIR not in p.parents]]:
        if not path.exists():
            continue
        if path.is_dir():
            if path.name == "build" and (path / "dist-backups").is_dir():
                # backups made by earlier versions of this script: keep them in backups/
                shutil.copytree(path / "dist-backups", ROOT / "backups", dirs_exist_ok=True)
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(path.relative_to(ROOT).as_posix())
    if removed:
        print(f"  removed {', '.join(removed)}")


def main():
    if exe_running():
        sys.exit(f"{EXE} is running; close it and run this again.")

    saved = move_old_dist() + back_up_dist_changes()
    if saved:
        print("These files had changes the project doesn't have; they were backed up before being")
        print("replaced. Copy any you want to keep into the project's folders:")
        for p in saved:
            print(f"  {p.relative_to(ROOT)}")

    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    print("Building index.html ...")
    subprocess.run([sys.executable, "build.py"], cwd=ROOT, check=True, env=env)

    print(f"Building {APP_NAME} ...")
    with tempfile.TemporaryDirectory(prefix="daily-reading-build-") as work:
        work = Path(work)
        (work / "stash").mkdir()
        kept = set_aside_user_files(work / "stash")
        sep = ";" if sys.platform == "win32" else ":"
        try:
            result = subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed",
                 "--name", APP_NAME, "--icon", str(ROOT / "Daily-Reading.ico"),
                 "--distpath", str(ROOT), "--workpath", str(work / "build"), "--specpath", str(work),
                 "--add-data", f"{ROOT / 'index.html'}{sep}.", "--add-data", f"{ROOT / 'Daily-Reading.ico'}{sep}.",
                 str(ROOT / "app.py")],
                cwd=ROOT, capture_output=True, text=True, env=env)
        finally:
            put_back(kept)
    if result.returncode:
        print(result.stdout + result.stderr)   # PyInstaller's log, only when it fails
        sys.exit("PyInstaller failed.")

    print(f"Copying into {APP_NAME}/ ...")
    for folder in FOLDERS:
        mirror(folder)
    for name in EXTRA_FILES:
        if (ROOT / name).is_file():
            shutil.copy2(ROOT / name, APP_DIR / name)
    if kept:
        print(f"  kept your files: {', '.join(p.name for p in kept)}")

    print("Zipping ...")
    make_zip()
    print("Cleaning up ...")
    clean_up()
    print(f"Done: {APP_NAME}/{EXE}  (and {ZIP.name} to share)")


if __name__ == "__main__":
    main()
