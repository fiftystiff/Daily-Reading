"""Compare verse numbering in the online translations with the AV, in chapters where
English translations are known to differ (verses some translations leave out, or number
differently). Needs API keys:

    set ESV_KEY=...  &  set APIBIBLE_KEY=...  &  python tools/check_versification.py
"""
import os
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import bible_api as b  # noqa: E402

CHAPTERS = [("Matthew", "MAT", 17), ("Matthew", "MAT", 18), ("Matthew", "MAT", 23), ("Mark", "MRK", 7),
            ("Mark", "MRK", 9), ("Mark", "MRK", 11), ("Mark", "MRK", 15), ("Luke", "LUK", 17), ("Luke", "LUK", 23),
            ("John", "JHN", 5), ("Acts", "ACT", 8), ("Acts", "ACT", 15), ("Acts", "ACT", 19), ("Acts", "ACT", 24),
            ("Acts", "ACT", 28), ("Romans", "ROM", 14), ("Romans", "ROM", 16), ("2 Corinthians", "2CO", 13),
            ("3 John", "3JN", 1), ("Revelation", "REV", 12), ("Revelation", "REV", 13), ("Malachi", "MAL", 4),
            ("Joel", "JOL", 2), ("Psalms", "PSA", 3), ("Daniel", "DAN", 4), ("1 Kings", "1KI", 4)]

# AV verse numbers from av.md
av, book, chap = {}, None, None
for line in (PROJECT / "av.md").read_text(encoding="utf-8-sig").splitlines():
    if line.startswith("### "):
        book = " ".join(w.capitalize() if not w[0].isdigit() else w for w in line[4:].split())
    elif line.startswith("#### "):
        chap = int(re.search(r"\d+", line).group())
    elif (m := re.match(r"\[(\d+)\]", line.strip())):
        av.setdefault((book, chap), []).append(int(m.group(1)))


def describe(nums, ref):
    missing = sorted(set(ref) - set(nums))
    extra = sorted(set(nums) - set(ref))
    if not missing and not extra:
        return "same"
    return ", ".join(x for x in [f"no verse {', '.join(map(str, missing))}" if missing else "",
                                 f"extra verse {', '.join(map(str, extra))}" if extra else ""] if x)


esv, ab = os.environ.get("ESV_KEY"), os.environ.get("APIBIBLE_KEY")
for name, usfm, ch in CHAPTERS:
    ref = av.get((name, ch), [])
    out = [f"{name} {ch} (AV 1-{max(ref) if ref else '?'}):"]
    if esv:
        try:
            out.append("ESV " + describe([v for v, _ in b.esv_chapter(esv, name, ch)["verses"]], ref))
        except b.FetchError as err:
            out.append(f"ESV error: {err}")
    for tr in ("nasb", "niv"):
        if ab:
            try:
                out.append(f"{tr.upper()} " + describe([v for v, _ in b.api_bible_chapter(ab, tr, usfm, ch)["verses"]], ref))
            except b.FetchError as err:
                out.append(f"{tr.upper()} error: {err}")
    print("  ".join(out))
