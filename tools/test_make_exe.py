"""Test make_exe.py's backup, copy and move-over steps on a throwaway copy (the real
project and app folder are never touched).

    python tools/test_make_exe.py
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import make_exe as m  # noqa: E402

root = Path(tempfile.mkdtemp())
try:
    for folder in m.FOLDERS:
        shutil.copytree(PROJECT / folder, root / folder)
    m.ROOT, m.APP_DIR, m.OLD_DIST = root, root / m.APP_NAME, root / "dist"

    # 1. Earlier builds in dist/: the newest layout (dist/Daily-Reading/) with your settings
    #    and keys, and a theme saved from the app; the oldest (dist/Daily-Reading.exe and
    #    folders) beside it
    old_app = m.OLD_DIST / m.APP_NAME
    for folder in m.FOLDERS:
        shutil.copytree(PROJECT / folder, old_app / folder)
    (old_app / "_internal").mkdir()
    (old_app / m.EXE).write_bytes(b"exe")
    (old_app / "Daily-Reading_settings.json").write_text('{"theme": "nord"}', encoding="utf-8")
    (old_app / "Daily-Reading_keys.txt").write_text("ESV = test", encoding="utf-8")
    (old_app / "Daily-Reading_themes" / "saved-from-app.css").write_text("/* Theme: Mine */", encoding="utf-8")
    (m.OLD_DIST / m.EXE).write_bytes(b"older exe")
    saved = sorted(p.name for p in m.move_old_dist())
    assert saved == ["saved-from-app.css"], saved
    assert not m.OLD_DIST.exists(), "dist/ should be gone"
    assert sorted(p.name for p in m.APP_DIR.iterdir()) == ["Daily-Reading_keys.txt", "Daily-Reading_settings.json"]
    print("OK: earlier builds in dist/ are moved over (settings and keys kept, changes backed up)")

    # 2. A build: your files survive PyInstaller emptying the app folder
    for folder in m.FOLDERS:
        shutil.copytree(PROJECT / folder, m.APP_DIR / folder)
    (m.APP_DIR / "_internal").mkdir()
    (root / "stash").mkdir()
    kept = m.set_aside_user_files(root / "stash")
    assert sorted(p.name for p in kept) == ["Daily-Reading_keys.txt", "Daily-Reading_settings.json"], kept
    shutil.rmtree(m.APP_DIR)                      # what PyInstaller does
    m.put_back(kept)
    assert (m.APP_DIR / "Daily-Reading_settings.json").read_text(encoding="utf-8") == '{"theme": "nord"}'
    print("OK: settings and keys in the app folder are kept through a build")

    # 3. Changes made in the app folder's copies are backed up, then it matches the project
    for folder in m.FOLDERS:
        shutil.copytree(PROJECT / folder, m.APP_DIR / folder)
    sched = next((m.APP_DIR / "Daily-Reading_schedules").glob("*.md"))
    time.sleep(0.05)
    sched.write_text(sched.read_text(encoding="utf-8").replace("[ ]", "[x]", 1), encoding="utf-8")
    old = next((m.APP_DIR / "Daily-Reading_themes").glob("o*.css"))
    old.write_text("old version", encoding="utf-8")
    os.utime(old, (1, 1))                         # older than the project's: not backed up
    saved = m.back_up_dist_changes()
    assert sorted(p.name for p in saved) == [sched.name], saved
    assert saved[0].relative_to(root).parts[0] == "backups", saved
    for folder in m.FOLDERS:
        m.mirror(folder)
    for folder in m.FOLDERS:
        a = {p.name: p.read_bytes() for p in (root / folder).iterdir()}
        b = {p.name: p.read_bytes() for p in (m.APP_DIR / folder).iterdir()}
        assert a == b, f"{folder} doesn't match the project"
    print("OK: changed files were backed up, and the app folder matches the project afterwards")

    # 4. The zip: the whole app folder as "Daily-Reading/", without settings and keys
    import zipfile
    m.ZIP = root / "Daily-Reading.zip"
    (m.APP_DIR / "_internal").mkdir(exist_ok=True)
    (m.APP_DIR / "_internal" / "lib.dll").write_bytes(b"x")
    (m.APP_DIR / m.EXE).write_bytes(b"exe")
    (m.APP_DIR / "Daily-Reading_bibles").mkdir(exist_ok=True)
    (m.APP_DIR / "Daily-Reading_bibles" / "Some Bible.xml").write_text("<XMLBIBLE/>", encoding="utf-8")
    m.make_zip()
    names = zipfile.ZipFile(m.ZIP).namelist()
    assert not any("Daily-Reading_bibles" in n for n in names), "XML bibles zipped"
    assert "Daily-Reading.exe" in names and "_internal/lib.dll" in names, names[:5]   # contents at the top
    assert any(n.startswith("Daily-Reading_schedules/") for n in names)
    assert not any(n.startswith("Daily-Reading/") for n in names), "the zip shouldn't hold a Daily-Reading folder"
    assert not any(n.endswith(("Daily-Reading_settings.json", "Daily-Reading_keys.txt")) for n in names), "personal files zipped"
    print("OK: the zip has the app folder's contents, without your settings, keys and bibles")

    # 5. Cleaning up: build/, the .spec and __pycache__ go; backups from old builds are kept
    (root / "build" / "Daily-Reading").mkdir(parents=True)
    (root / "build" / "dist-backups" / "old" / "Daily-Reading_themes").mkdir(parents=True)
    (root / "build" / "dist-backups" / "old" / "Daily-Reading_themes" / "x.css").write_text("x")
    (root / "Daily-Reading.spec").write_text("spec")
    (root / "__pycache__").mkdir()
    (root / "tools" / "__pycache__").mkdir(parents=True)
    m.clean_up()
    assert not (root / "build").exists() and not (root / "Daily-Reading.spec").exists()
    assert not (root / "__pycache__").exists() and not (root / "tools" / "__pycache__").exists()
    assert (root / "backups" / "old" / "Daily-Reading_themes" / "x.css").exists(), "old backups lost"
    print("OK: clean-up removes build files and keeps old backups")
finally:
    shutil.rmtree(root, ignore_errors=True)
