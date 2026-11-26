"""Bibles from XML files in the Daily-Reading_bibles folder next to the app.

The files are Zefania XML, the format most free Bible downloads come in:

    <XMLBIBLE biblename="...">
      <BIBLEBOOK bnumber="1" bname="Genesis">
        <CHAPTER cnumber="1">
          <VERS vnumber="1">In the beginning God created the heaven and the earth.</VERS>

Books are matched by bnumber (1 = Genesis ... 66 = Revelation), so the book names can be
in any language or left out. Tag names may be upper or lower case. Inside a verse,
<STYLE> italics or small caps are kept, footnotes (<NOTE>) become markers the page can
show, and other markup keeps just its text. A <CAPTION> in a chapter (a psalm's title) is shown with its verse.

Listing the folder only looks at the start of each file, so it stays quick with many
large files; a bible is read in full the first time a chapter of it is asked for.
"""
import html
import os
import re
import threading
import xml.etree.ElementTree as ET
from collections import OrderedDict

BIBLES_DIR_NAME = "Daily-Reading_bibles"

# USFM book codes in the standard order (bnumber 1-66); the page asks for books by code.
USFM = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG "
        "ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT "
        "ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV").split()
BOOK_NUMBER = {code: i + 1 for i, code in enumerate(USFM)}

HEAD_BYTES = 64 * 1024            # how much of a file is read to decide whether it's a bible
MAX_FILE_BYTES = 200 * 1024 * 1024
KEEP_LOADED = 2                   # bibles kept in memory at once
ITALIC = re.compile(r"italic|emphasis", re.I)
SMALL_CAPS = re.compile(r"small-caps|divinename", re.I)
NUMBER = re.compile(r"\d+")


def tag(el):
    return el.tag.rsplit("}", 1)[-1].upper() if isinstance(el.tag, str) else ""


def esc(text):
    return html.escape(text or "", quote=False)


def tidy(text):
    return re.sub(r"\s+", " ", text).strip()


def number(value):
    m = NUMBER.search(value or "")
    return int(m.group(0)) if m else None


def footnote_marker(text):
    """A footnote, as the page shows it: a small marker that opens the note (shown or
    hidden by the Footnotes setting)."""
    return f'<sup class="fn" data-note="{html.escape(text, quote=True)}"></sup>'


def render(el):
    """A verse's (or caption's) content as HTML: only <em>, small caps and footnote markup."""
    out = [esc(el.text)]
    for child in el:
        name = tag(child)
        if name == "NOTE":
            text = tidy("".join(child.itertext()))
            if text and not re.search(r"cross", child.get("type", ""), re.I):
                out.append(footnote_marker(text))
        elif name in ("REMARK", "XREF"):
            pass                                        # cross-references
        elif name == "BR":
            out.append(" ")
        elif name == "STYLE":
            look = f'{child.get("fs", "")} {child.get("css", "")}'
            inner = render(child)
            if SMALL_CAPS.search(look):
                out.append(f'<span class="sc">{inner}</span>')
            elif ITALIC.search(look):
                out.append(f"<em>{inner}</em>")
            else:
                out.append(inner)
        else:
            out.append(render(child))                   # DIV, gr (Strong's numbers), etc.
        out.append(esc(child.tail))
    return "".join(out)


ORIG = re.compile(r"^\s*(\d+):(\d+)\s*$")


def orig_label(refs):
    """The translation's own number(s) for one KJV verse: "22:1", "22:1-2", "9:39-10:1"."""
    (c1, v1), (c2, v2) = min(refs), max(refs)
    if (c1, v1) == (c2, v2):
        return f"{c1}:{v1}"
    return f"{c1}:{v1}-{v2}" if c1 == c2 else f"{c1}:{v1}-{c2}:{v2}"


def looks_like_bible(path):
    """Whether a file starts like a Zefania XML bible (without reading all of it)."""
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return False
        with open(path, "rb") as f:
            head = f.read(HEAD_BYTES)
    except OSError:
        return False
    if head.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = head.decode("utf-16", errors="ignore")
    else:
        text = head.decode("utf-8", errors="ignore")
    return bool(re.search(r"<XMLBIBLE\b", text, re.I) and re.search(r"<BIBLEBOOK\b", text, re.I))


def read_bible(path):
    """{"books": {bnumber: {cnumber: [[verse, html], ...]}}, "rights": str}"""
    root = ET.parse(path).getroot()
    if tag(root) != "XMLBIBLE":
        raise ValueError("it doesn't start with <XMLBIBLE>")
    books = {}
    for book in root:
        if tag(book) != "BIBLEBOOK":
            continue
        b = number(book.get("bnumber"))
        if not b:
            continue
        chapters = books.setdefault(b, {})
        for chapter in book:
            if tag(chapter) != "CHAPTER":
                continue
            c = number(chapter.get("cnumber"))
            if not c:
                continue
            verses, captions, origs = {}, {}, {}
            for item in chapter:
                name = tag(item)
                if name == "VERS":
                    v = number(item.get("vnumber"))
                    if v:
                        text = tidy(render(item))
                        verses[v] = f"{verses[v]} {text}".strip() if v in verses else text
                        # The translation's own number ("22:1"), when it was renumbered to
                        # the KJV's (tools/renumber_xml_bible.py)
                        orig = ORIG.match(item.get("orig") or "")
                        if orig:
                            origs.setdefault(v, []).append((int(orig.group(1)), int(orig.group(2))))
                elif name == "CAPTION":
                    v = number(item.get("vref")) or 0     # no vref: the chapter's first verse
                    captions[v] = tidy(f'{captions.get(v, "")} {render(item)}')
            if not verses:
                continue
            for v, caption in captions.items():
                target = v if v in verses else min(verses)
                verses[target] = f"{caption} {verses[target]}".strip()
            chapters[c] = [[v, verses[v], orig_label(origs[v])] if v in origs else [v, verses[v]]
                           for v in sorted(verses)]
    if not books:
        raise ValueError("no books with chapters and verses were found")
    info = next((el for el in root if tag(el) == "INFORMATION"), None)
    rights = ""
    if info is not None:
        el = next((e for e in info if tag(e) == "RIGHTS"), None)
        rights = tidy("".join(el.itertext()))[:300] if el is not None else ""
    return {"books": books, "rights": rights}


class LocalBibles:
    def __init__(self, folder):
        self.folder = folder
        self._loaded = OrderedDict()    # file name -> (mtime, bible)
        self._lock = threading.Lock()

    def _path(self, file_name):
        """The file in the folder with this name, or None (names only, no paths)."""
        if not isinstance(file_name, str) or os.path.basename(file_name) != file_name or not file_name.lower().endswith(".xml"):
            return None
        path = os.path.join(self.folder, file_name)
        return path if os.path.isfile(path) else None

    def list(self):
        """[{"file", "name"}, ...] for each XML bible in the folder, by name."""
        if not os.path.isdir(self.folder):
            return []
        found = []
        for file_name in os.listdir(self.folder):
            path = os.path.join(self.folder, file_name)
            if file_name.lower().endswith(".xml") and os.path.isfile(path) and looks_like_bible(path):
                found.append({"file": file_name, "name": os.path.splitext(file_name)[0].strip()})
        return sorted(found, key=lambda b: b["name"].casefold())

    def _bible(self, file_name):
        path = self._path(file_name)
        if not path:
            return None
        mtime = os.path.getmtime(path)
        with self._lock:                 # chapters are asked for several at a time
            cached = self._loaded.get(file_name)
            if cached and cached[0] == mtime:
                self._loaded.move_to_end(file_name)
                return cached[1]
            bible = read_bible(path)
            self._loaded[file_name] = (mtime, bible)
            while len(self._loaded) > KEEP_LOADED:
                self._loaded.popitem(last=False)
            return bible

    def get_chapter(self, file_name, usfm, book_name, chapter):
        """{"ok": True, "verses": [[n, html], ...], "copyright"} or {"ok": False, "error",
        "missing"?} ("missing": the bible doesn't have that book or chapter)."""
        name = os.path.splitext(str(file_name))[0]
        try:
            bible = self._bible(file_name)
        except (OSError, ET.ParseError, ValueError) as err:
            return {"ok": False, "error": f"{name} couldn't be read ({err})."}
        if bible is None:
            return {"ok": False, "missing": True,
                    "error": f"{name} isn't in the {BIBLES_DIR_NAME} folder any more."}
        book = bible["books"].get(BOOK_NUMBER.get(usfm))
        if not book:
            return {"ok": False, "missing": True, "error": f"{name} doesn't include {book_name}."}
        verses = book.get(number(str(chapter)))
        if not verses:
            return {"ok": False, "missing": True, "error": f"{name} doesn't include {book_name} {chapter}."}
        return {"ok": True, "verses": verses, "copyright": bible["rights"]}
