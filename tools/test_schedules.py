"""Tests for schedules.py: reading schedule files and saving checkmarks.

    python tools/test_schedules.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import schedules as S  # noqa: E402

folder = tempfile.mkdtemp()
s = S.Schedules(folder)


def write(name, text, encoding="utf-8", bom=False):
    data = text.encode(encoding)
    if bom:
        data = {"utf-8": b"\xef\xbb\xbf", "utf-16-le": b"\xff\xfe"}[encoding] + data
    Path(folder, name).write_bytes(data)


def read(name, encoding="utf-8", skip=0):
    return Path(folder, name).read_bytes()[skip:].decode(encoding)


# A checklist with CRLF line endings and a byte-order mark
plan = ("---\r\nname: Test Plan\r\nmode: checklist\r\n---\r\n<!-- [ ] in a comment -->\r\n"
        "| Done | Reading |\r\n|---|---|\r\n| [ ] | Genesis 1 |\r\n| [ ] | [ ] Exodus 1 [x] Psalm 1 |\r\n")
write("Plan.md", plan, bom=True)
items = s.list()
assert items == [{"id": "Plan", "name": "Test Plan", "mode": "checklist", "hasStart": False, "hasChecks": True}], items

# One box
r = s.set_check("Plan", 8, 0, 0, "| [ ] | Genesis 1 |", True)
assert r["ok"] and r["line"] == "| [x] | Genesis 1 |", r
# Several boxes, two on the same line, in one write
r = s.set_checks("Plan", [[9, 0, 0, "| [ ] | [ ] Exodus 1 [x] Psalm 1 |", True],
                          [9, 1, 0, "| [ ] | [ ] Exodus 1 [x] Psalm 1 |", True],
                          [9, 1, 1, "| [ ] | [ ] Exodus 1 [x] Psalm 1 |", False]])
assert r["ok"] and r["lines"] == {"9": "| [x] | [x] Exodus 1 [ ] Psalm 1 |"}, r
data = Path(folder, "Plan.md").read_bytes()
assert data.startswith(b"\xef\xbb\xbf"), "byte-order mark lost"
text = data[3:].decode("utf-8")
assert text.count("\r\n") == plan.count("\r\n") and "\n" not in text.replace("\r\n", ""), "line endings changed"
assert text == plan.replace("| [ ] | Genesis 1 |", "| [x] | Genesis 1 |").replace(
    "| [ ] | [ ] Exodus 1 [x] Psalm 1 |", "| [x] | [x] Exodus 1 [ ] Psalm 1 |"), "more than the checkboxes changed"

# A line changed outside the app: nothing at all is written
before = Path(folder, "Plan.md").read_bytes()
r = s.set_checks("Plan", [[8, 0, 0, "| [x] | Genesis 1 |", False], [9, 0, 0, "| something else |", False]])
assert r.get("conflict") and Path(folder, "Plan.md").read_bytes() == before, r

# UTF-16 files keep their encoding
write("Wide.md", "| Done | Reading |\r\n|---|---|\r\n| [ ] | John 1 |\r\n", "utf-16-le", bom=True)
r = s.set_check("Wide", 3, 0, 0, "| [ ] | John 1 |", True)
assert r["ok"] and read("Wide.md", "utf-16-le", 2).endswith("| [x] | John 1 |\r\n"), r

# A file without settings: no mode, checkboxes only in a comment don't count
write("Plain.md", "<!-- [ ] -->\n## Week 1\n| Reading |\n|---|\n| Genesis 1 |\n")
plain = next(i for i in s.list() if i["id"] == "Plain")
assert plain["mode"] == "" and not plain["hasChecks"] and not plain["hasStart"], plain

assert not any(f.endswith(".saving") for f in os.listdir(folder)), "temporary file left behind"
print("OK: schedules.py")
