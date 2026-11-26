"""Custom reading schedules: Markdown files in the Daily-Reading_schedules folder next to
the .exe (or next to app.py). The page parses them (the same way as the built-in
schedule); this module lists and reads the files, and ticks checkboxes in them.

Ticking a box changes exactly one character in the file ("[ ]" <-> "[x]") and nothing
else, after checking that the line still says what the page last read, so edits made in
a text editor are never overwritten.
"""
import os
import re

SCHEDULES_DIR_NAME = "Daily-Reading_schedules"
MAX_BYTES = 2_000_000
CHECKBOX = re.compile(r"\[( |x|X)\]")
NAME_LINE = re.compile(r"^\s*name\s*:\s*(.+?)\s*$", re.I)
TITLE_LINE = re.compile(r"^#\s+(.+?)\s*#*\s*$")


def _decode(data):
    """(text, encoding, bom) for a schedule file's bytes: UTF-8 (with or without a BOM),
    UTF-16 (what some editors save as "Unicode"), or else Windows-1252."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        enc = "utf-16-le" if data.startswith(b"\xff\xfe") else "utf-16-be"
        return data[2:].decode(enc, errors="replace"), enc, True
    bom = data.startswith(b"\xef\xbb\xbf")
    body = data[3:] if bom else data
    try:
        return body.decode("utf-8"), "utf-8", bom
    except UnicodeDecodeError:
        return body.decode("cp1252", errors="replace"), "cp1252", bom


def _display_name(text, stem):
    """Name from the settings block ("name: ..."), else the first "# Title", else the file name."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:40]:
            if line.strip() == "---":
                break
            m = NAME_LINE.match(line)
            if m:
                return m.group(1).strip().strip("\"'")
    for line in lines[:60]:
        m = TITLE_LINE.match(line)
        if m:
            return m.group(1)
    return stem.replace("_", " ").replace("-", " ").strip()


def _kind_hints(text):
    """What the page needs to place a schedule in the dropdown's groups without reading it
    all: its "mode:" setting, whether it has a start date, and whether it has checkboxes
    (comments don't count). The page turns these into the mode it would use."""
    lines = text.splitlines()
    settings = {}
    if lines and lines[0].strip() == "---":
        for line in lines[1:40]:
            if line.strip() == "---":
                break
            m = re.match(r"^\s*([A-Za-z][A-Za-z ]*?)\s*:\s*(.*?)\s*$", line)
            if m:
                settings[m.group(1).lower()] = m.group(2).strip("\"'")
    body = re.sub(r"<!--.*?(-->|$)", "", text, flags=re.S)
    return {"mode": settings.get("mode", ""), "hasStart": bool(settings.get("start")),
            "hasChecks": bool(re.search(r"^\s*\|.*\[( |x|X)\]", body, re.M))}


def _cell_spans(line):
    """(start, end) of each table cell in a Markdown table line, matching how the page splits
    it: an optional leading and trailing "|", then cells between pipes."""
    pipes = [i for i, ch in enumerate(line) if ch == "|"]
    if not pipes:
        return []
    stripped = line.strip()
    starts_with_pipe = stripped.startswith("|")
    ends_with_pipe = stripped.endswith("|") and len(stripped) > 1
    bounds = list(pipes)
    if not starts_with_pipe:
        bounds.insert(0, -1)
    if not ends_with_pipe:
        bounds.append(len(line.rstrip("\r\n")))
    return [(bounds[k] + 1, bounds[k + 1]) for k in range(len(bounds) - 1)]


class Schedules:
    def __init__(self, folder):
        self.folder = folder

    def _files(self):
        """{id: path} for every .md file in the folder (id = file name without .md)."""
        if not os.path.isdir(self.folder):
            return {}
        out = {}
        for name in sorted(os.listdir(self.folder), key=str.lower):
            stem, ext = os.path.splitext(name)
            path = os.path.join(self.folder, name)
            if ext.lower() == ".md" and os.path.isfile(path) and not stem.startswith("~"):
                out[stem] = path
        return out

    def _path(self, schedule_id):
        return self._files().get(schedule_id) if isinstance(schedule_id, str) else None

    def list(self):
        items = []
        for stem, path in self._files().items():
            try:
                with open(path, "rb") as f:
                    text, _, _ = _decode(f.read(MAX_BYTES))
            except OSError:
                continue
            items.append({"id": stem, "name": _display_name(text, stem), **_kind_hints(text)})
        return items

    def load(self, schedule_id):
        path = self._path(schedule_id)
        if not path:
            return {"ok": False, "error": f"The schedule “{schedule_id}” isn't in {SCHEDULES_DIR_NAME} any more."}
        try:
            if os.path.getsize(path) > MAX_BYTES:
                return {"ok": False, "error": "That schedule file is too large."}
            with open(path, "rb") as f:
                text, _, _ = _decode(f.read())
            return {"ok": True, "text": text, "mtime": os.path.getmtime(path),
                    "fileName": os.path.basename(path)}
        except OSError as err:
            return {"ok": False, "error": f"Couldn't read the schedule: {err.strerror or err}"}

    def mtime(self, schedule_id):
        path = self._path(schedule_id)
        try:
            return os.path.getmtime(path) if path else None
        except OSError:
            return None

    def set_check(self, schedule_id, line_no, cell, ordinal, expected, checked):
        """Tick or untick one checkbox (see set_checks)."""
        res = self.set_checks(schedule_id, [[line_no, cell, ordinal, expected, checked]])
        if res.get("ok"):
            res["line"] = res["lines"][str(int(line_no))]
        return res

    def set_checks(self, schedule_id, edits):
        """Tick or untick checkboxes. Each edit is [line_no, cell, ordinal, expected, checked]:
        the ordinal-th "[ ]"/"[x]" in table cell `cell` of line `line_no` (1-based), where
        `expected` is the line as the page last read it. Every line is checked before
        anything is written, and the file is written once: if any line has changed in the
        file, nothing is written and {"conflict": True} is returned.
        Returns {"ok": True, "lines": {line_no: new line}, "mtime"}."""
        path = self._path(schedule_id)
        if not path:
            return {"ok": False, "conflict": True, "error": "The schedule file isn't there any more."}
        changed = {"ok": False, "conflict": True,
                   "error": "The schedule file was changed outside the app, so it was reloaded. Try again."}
        try:
            with open(path, "rb") as f:
                data = f.read()
            text, encoding, bom = _decode(data)
            # Split on \r\n, \n or \r only, the same as the page does, so line numbers agree.
            lines = re.findall(r"[^\r\n]*(?:\r\n|\n|\r)|[^\r\n]+$", text)
            new_bodies = {}
            for line_no, cell, ordinal, expected, checked in edits:
                line_no, cell, ordinal = int(line_no), int(cell), int(ordinal)
                if not (1 <= line_no <= len(lines)):
                    return changed
                original = lines[line_no - 1].rstrip("\r\n")
                if original.rstrip() != str(expected).rstrip():
                    return changed
                body = new_bodies.get(line_no, original)
                spans = _cell_spans(body)
                if not (0 <= cell < len(spans)):
                    return changed
                boxes = list(CHECKBOX.finditer(body, *spans[cell]))
                if not (0 <= ordinal < len(boxes)):
                    return changed
                pos = boxes[ordinal].start(1)
                new_bodies[line_no] = body[:pos] + ("x" if checked else " ") + body[pos + 1:]
            for line_no, body in new_bodies.items():
                line = lines[line_no - 1]
                lines[line_no - 1] = body + line[len(line.rstrip("\r\n")):]
            if new_bodies:
                # Same encoding and byte-order mark as the file had
                out = (chr(0xFEFF) if bom else "") + "".join(lines)
                tmp = path + ".saving"
                with open(tmp, "wb") as f:
                    f.write(out.encode(encoding, errors="replace"))
                os.replace(tmp, path)
            return {"ok": True, "lines": {str(k): v for k, v in new_bodies.items()}, "mtime": os.path.getmtime(path)}
        except PermissionError:
            return {"ok": False, "error": "Couldn't save the checkmarks: the schedule file is read-only or open "
                                          "in another program."}
        except (OSError, ValueError, TypeError) as err:
            return {"ok": False, "error": f"Couldn't save the checkmarks: {getattr(err, 'strerror', None) or err}"}
