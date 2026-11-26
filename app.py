import json
import os
import re
import shutil
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote

import webview

from bible_api import KEYS_FILE_NAME, OnlineBibles
from local_bibles import BIBLES_DIR_NAME, LocalBibles
from schedules import SCHEDULES_DIR_NAME, Schedules

THEMES_DIR_NAME = "Daily-Reading_themes"


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller .exe"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def get_themes_dir():
    """The Daily-Reading_themes folder the app reads themes from and saves them to.

    It sits next to the .exe (or next to app.py when run from source; that's also the
    folder build.py reads). Themes are plain .css files there, so they can be added,
    edited or removed. If the folder doesn't exist, only the built-in "Default" theme is
    offered; saving a theme from the settings panel creates it.
    """
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), THEMES_DIR_NAME)
    return get_resource_path(THEMES_DIR_NAME)


SETTINGS_FILE_NAME = "Daily-Reading_settings.json"


class SettingsFile:
    """The app's settings (the look, theme, translation and schedule) in
    Daily-Reading_settings.json in the app folder, so the folder is a portable install
    that carries them along. If the folder can't be written (an install in Program Files,
    say), %APPDATA%\\Daily-Reading\\settings.json is used instead."""

    def __init__(self, app_dir):
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        self.paths = [os.path.join(app_dir, SETTINGS_FILE_NAME),
                      os.path.join(appdata, "Daily-Reading", "settings.json")]

    def load(self):
        """The most recently saved settings, or None if there are none yet."""
        found = []
        for path in self.paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    found.append((os.path.getmtime(path), data))
            except (OSError, ValueError):
                continue
        return max(found, key=lambda x: x[0])[1] if found else None

    def save(self, data):
        if not isinstance(data, dict):
            return {"ok": False, "error": "Settings weren't in the expected format."}
        text = json.dumps(data, indent=2, ensure_ascii=False)
        if len(text) > 500_000:
            return {"ok": False, "error": "Settings are too large to save."}
        for path in self.paths:          # the app folder first, then AppData
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tmp = path + ".saving"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(text + "\n")
                os.replace(tmp, path)
                return {"ok": True, "path": path}
            except OSError:
                continue
        return {"ok": False, "error": "Couldn't save the settings anywhere."}


THEME_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,48}$")
VAR_NAME = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
BAD_VALUE = re.compile(r"[;{}<>\\\r\n]|/\*|\*/")


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48]


def read_theme_name(path):
    """Theme name from a theme file's header comment (same format build.py reads)."""
    with open(path, "r", encoding="utf-8") as f:
        head = f.read(500)
    name = re.search(r"Theme:\s*(.+)", head)
    stem = os.path.splitext(os.path.basename(path))[0]
    return name.group(1).strip() if name else stem.replace("-", " ").title()


class Api:
    """Functions the page can call as window.pywebview.api.<name>(...)."""

    LOCAL_PREFIX = "xml:"     # translation ids of the XML bibles: "xml:<file name>"

    def __init__(self, themes_dir, bibles_dir=None):
        self._themes_dir = themes_dir
        # Daily-Reading_keys.txt sits beside the themes folder: next to the .exe (or app.py).
        app_dir = os.path.dirname(os.path.abspath(themes_dir))
        self._online = OnlineBibles(os.path.join(app_dir, KEYS_FILE_NAME))
        # Daily-Reading_bibles (XML bibles), also beside the themes folder
        self._local = LocalBibles(bibles_dir or os.path.join(app_dir, BIBLES_DIR_NAME))
        # Daily-Reading_schedules, also beside the themes folder
        self._schedules = Schedules(os.path.join(app_dir, SCHEDULES_DIR_NAME))
        # Daily-Reading_settings.json, also beside it
        self._settings = SettingsFile(app_dir)

    def save_settings(self, data):
        return self._settings.save(data)

    def reset_settings(self):
        """Settings > Reset all settings: delete the settings file(s), so the app starts
        with the defaults (the page reloads afterwards)."""
        removed, failed = [], []
        for path in self._settings.paths:
            for p in (path, path + ".saving"):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                        removed.append(p)
                    except OSError as err:
                        failed.append(f"{p}: {err.strerror or err}")
        if failed:
            return {"ok": False, "error": "Couldn't delete " + "; ".join(failed)}
        return {"ok": True, "removed": removed}

    def clear_app_data(self):
        """Settings > Delete app data: remove %APPDATA%\\Daily-Reading (API keys saved in the
        app, the ID used for API.Bible's usage reporting, and settings kept there when the
        app folder couldn't be written). Nothing next to the .exe is touched."""
        base = os.environ.get("APPDATA")
        if not base:
            return {"ok": False, "error": "The AppData folder couldn't be found."}
        folder = os.path.join(base, "Daily-Reading")
        if not os.path.isdir(folder):
            return {"ok": True, "message": "There was no app data to delete."}
        try:
            shutil.rmtree(folder)
        except OSError as err:
            return {"ok": False, "error": f"Couldn't delete {folder}: {err.strerror or err}"}
        return {"ok": True, "message": f"Deleted {folder}."}

    # Custom reading schedules -- see schedules.py
    def list_schedules(self):
        return self._schedules.list()

    def load_schedule(self, schedule_id):
        return self._schedules.load(schedule_id)

    def schedule_mtime(self, schedule_id):
        return self._schedules.mtime(schedule_id)

    def set_schedule_check(self, schedule_id, line_no, cell, ordinal, expected, checked):
        return self._schedules.set_check(schedule_id, line_no, cell, ordinal, expected, checked)

    def set_schedule_checks(self, schedule_id, edits):
        return self._schedules.set_checks(schedule_id, edits)

    # Online translations (ESV, NASB, NIV) -- see bible_api.py
    def online_status(self):
        return self._online.status()

    def set_api_key(self, kind, key):
        return self._online.set_key(kind, key)

    def get_chapter(self, translation, usfm, book_name, chapter):
        if isinstance(translation, str) and translation.startswith(self.LOCAL_PREFIX):
            return self._local.get_chapter(translation[len(self.LOCAL_PREFIX):], usfm, book_name, chapter)
        return self._online.get_chapter(translation, usfm, book_name, chapter)

    # XML bibles in Daily-Reading_bibles -- see local_bibles.py
    def list_local_bibles(self):
        return [{"id": self.LOCAL_PREFIX + b["file"], "name": b["name"]} for b in self._local.list()]

    def report_fums(self, tokens):
        return self._online.report_fums(tokens)

    def open_url(self, url):
        """Open a link in the default browser (inside the app window it would replace the
        page). Only the sites the app links to."""
        if isinstance(url, str) and re.match(r"^https://(api\.esv\.org|www\.esv\.org|api\.bible|docs\.api\.bible)/", url):
            webbrowser.open(url)
            return True
        return False

    def _theme_path(self, theme_id):
        if not isinstance(theme_id, str) or not THEME_ID.match(theme_id):
            return None
        return os.path.join(self._themes_dir, f"{theme_id}.css")

    def list_themes(self):
        """Every theme file in the folder: [{"id", "name"}, ...]."""
        if not os.path.isdir(self._themes_dir):
            return []
        themes = []
        for file in sorted(os.listdir(self._themes_dir)):
            stem, ext = os.path.splitext(file)
            if ext.lower() == ".css" and THEME_ID.match(stem) and stem != "default":
                themes.append({"id": stem, "name": read_theme_name(os.path.join(self._themes_dir, file))})
        return themes

    def get_theme(self, theme_id):
        path = self._theme_path(theme_id)
        if not path or not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def save_theme(self, name, groups, overwrite=False):
        """Write the page's current look to Daily-Reading_themes/<slug>.css.

        groups: [[section title, [[variable name without "--", value], ...]], ...]
        Returns {"ok": True, "id", "name"}, or {"exists": True, "name"} when a theme with
        that name exists and overwrite is false, or {"ok": False, "error"}.
        """
        name = re.sub(r"[\r\n*/]", "", str(name or "")).strip()[:40]
        theme_id = slugify(name)
        if not theme_id:
            return {"ok": False, "error": "Enter a name using letters or numbers."}
        if theme_id == "default":
            return {"ok": False, "error": "“Default” is the built-in theme; choose another name."}

        sections = []
        try:
            for title, variables in groups:
                title = re.sub(r"[\r\n*/]", "", str(title))[:60]
                lines = []
                for var_name, value in variables:
                    var_name, value = str(var_name), str(value).strip()
                    if not VAR_NAME.match(var_name) or not value or len(value) > 200 or BAD_VALUE.search(value):
                        return {"ok": False, "error": f"Unexpected value for --{var_name[:40]}."}
                    lines.append(f"  --{var_name}: {value};")
                if lines:
                    sections.append(f"  /* {title} */\n" + "\n".join(lines))
        except (TypeError, ValueError):
            return {"ok": False, "error": "The theme data was not in the expected format."}
        if not sections:
            return {"ok": False, "error": "There was nothing to save."}

        path = self._theme_path(theme_id)
        if os.path.exists(path) and not overwrite:
            return {"exists": True, "id": theme_id, "name": read_theme_name(path)}

        css = f"/*\n * Theme: {name}\n */\n:root {{\n" + "\n\n".join(sections) + "\n}\n"
        try:
            os.makedirs(self._themes_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(css)
        except OSError as err:
            return {"ok": False, "error": f"Couldn't write {path}: {err.strerror or err}"}
        return {"ok": True, "id": theme_id, "name": name}


def main():
    themes_dir = get_themes_dir()
    icon_file = get_resource_path("Daily-Reading.ico")

    # Load the page as a file:// URL (not through pywebview's local web server, which
    # picks a new port each launch and so would forget saved settings), and tell it
    # where the themes folder is so it can load theme files straight from there.
    page_url = Path(get_resource_path("index.html")).resolve().as_uri()
    themes_url = Path(themes_dir).resolve().as_uri() + "/"
    api = Api(themes_dir)
    # The saved settings go along too, so the page has them from the start ("new" when
    # there's no settings file yet: the page then brings over what it had saved before).
    settings = api._settings.load()
    settings_param = quote(json.dumps(settings, separators=(",", ":")), safe="") if settings is not None else "new"
    # Passed after "#": WebView2 treats "?" in a file address as part of the file name.
    url = f"{page_url}#themes={quote(themes_url, safe='')}&settings={settings_param}"

    webview.create_window(
        title="Daily-Reading",
        url=url,
        width=1360,
        height=860,
        min_size=(960, 600),
        js_api=api,
    )

    # private_mode=False keeps your theme and settings saved; icon sets the window/taskbar icon
    webview.start(private_mode=False, icon=icon_file)


if __name__ == "__main__":
    main()
