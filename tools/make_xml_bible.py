"""Convert a Bible to the Zefania XML format the app reads from Daily-Reading_bibles.

    python tools/make_xml_bible.py SOURCE "OUTPUT.xml" --name "Title" [--rights "..."]
                                   [--source-note "where it came from"] [--description "..."]
                                   [--drop-hebrew-numbers]

--rights is shown below the text in the app (a copyright or licence line).

SOURCE is either
  - a folder of USFM files (.usfm / .sfm, one book per file), as downloaded from
    ebible.org ("USFM" zip), Door43, the Open English Bible, etc.; or
  - an unzipped SWORD module (the folder with mods.d/ and modules/), as downloaded from
    crosswire.org; zText or rawText modules in KJV versification, with GBF, OSIS or
    ThML markup.

Kept: verse text, psalm titles (as <CAPTION>), supplied words / italics, the divine name
in small capitals, and footnotes (as <NOTE>, where they are in the text). Left out:
cross-references, section headings, introductions and Strong's numbers. Books outside Genesis-Revelation (the Apocrypha)
are skipped.
"""
import argparse
import html
import re
import struct
import sys
import zlib
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

PROJECT = Path(__file__).resolve().parent.parent
USFM = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG "
        "ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT "
        "ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV").split()
BOOK_NUMBER = {code: i + 1 for i, code in enumerate(USFM)}
ITALIC, SMALL_CAPS = "italic", "divineName"


class Bible:
    """books[n] = {"name", "chapters": {c: {"verses": {v: [(style, text)]}, "captions": {v: [...]}}}}"""

    def __init__(self):
        self.books = {}

    def chapter(self, book, c):
        b = self.books.setdefault(book, {"name": "", "chapters": {}})
        return b["chapters"].setdefault(c, {"verses": {}, "captions": {}})

    def add(self, book, c, v, style, text, caption=False):
        if not text:
            return
        ch = self.chapter(book, c)
        (ch["captions"] if caption else ch["verses"]).setdefault(v, []).append((style, text))


# ---- USFM ------------------------------------------------------------------------------

SKIP_PARAS = {"h", "toc1", "toc2", "toc3", "toca1", "toca2", "toca3", "mt", "mt1", "mt2", "mt3", "mt4",
              "mte", "mte1", "mte2", "imt", "imt1", "imt2", "imt3", "imt4", "imte", "is", "is1", "is2", "ip", "ipi", "im", "imi",
              "ipq", "imq", "ipr", "iq", "iq1", "iq2", "ib", "ili", "ili1", "ili2", "iot", "io", "io1",
              "io2", "io3", "ior", "iex", "ie", "s", "s1", "s2", "s3", "s4", "ms", "ms1", "ms2", "ms3",
              "mr", "r", "sr", "sp", "sd", "sd1", "sd2", "qa", "cl", "cp", "cd", "rem", "ide", "periph",
              "sts", "restore", "lit", "usfm"}
TEXT_PARAS = {"p", "m", "pi", "pi1", "pi2", "pi3", "q", "q1", "q2", "q3", "q4", "qr", "qc", "qm", "qm1",
              "qm2", "qd", "li", "li1", "li2", "li3", "li4", "lh", "lf", "lim", "lim1", "lim2", "pmo",
              "pc", "pr", "nb", "b", "pm", "pmc", "pmr", "mi", "po", "ph", "ph1", "ph2", "tr", "th1",
              "th2", "tc1", "tc2", "pb"}
CHAR_STYLES = {"add": ITALIC, "it": ITALIC, "em": ITALIC, "tl": ITALIC, "nd": SMALL_CAPS, "sc": SMALL_CAPS}
# Cross-references, figures, and alternate / printed verse numbers (\va 3\va*): left out
NOTES = re.compile(r"\\(x|ex|fig|va|vp|ca)\s.*?\\\1\*", re.S)
# Footnotes: kept, as a placeholder in the text until the verse is written out
FOOTNOTES = re.compile(r"\\(f|fe|ef)\s(.*?)\\\1\*", re.S)
NOTE_START, NOTE_END = "\ue000", "\ue001"


def note_placeholder(text):
    """Footnote text, cleaned of markup, wrapped so it survives parsing as part of the verse."""
    text = re.sub(r"\s+", " ", re.sub(r"[\ue000\ue001]", "", text)).strip()
    return f"{NOTE_START}{text}{NOTE_END}" if text else ""


def usfm_note(m):
    body = m.group(2)
    body = re.sub(r"^\s*\S+\s*", "", body, count=1)                       # the caller ("+", "-", "a")
    body = re.sub(r"\\(fr|xo)\s[^\\]*", " ", body)                        # "1:3 " (the note's reference)
    body = re.sub(r"\\fv\s[^\\]*\\fv\*", " ", body)                       # verse numbers inside the note
    body = re.sub(r"\\\+?[a-z]+[0-9]*\*?", " ", body)                     # remaining markers (\ft, \fq ...)
    return note_placeholder(body)
ATTRIBUTES = re.compile(r"\|[^\\|]*(?=\\\+?[a-z]+[0-9]*\*)")      # \w word|strong="H1234"\w*
TOKENS = re.compile(r"(\\\+?[a-z]+[0-9]*\*?)")
VERSE_START = re.compile(r"\s*(\d+)[a-z]?(?:[-\u2013,]\d+[a-z]?)?\s?(.*)", re.S)
NUMBER_START = re.compile(r"\s*(\d+)\S*\s?(.*)", re.S)


def read_usfm_folder(folder, bible):
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".usfm", ".sfm"))
    if not files:
        sys.exit(f"No .usfm or .sfm files in {folder}")
    for path in files:
        read_usfm(path.read_text(encoding="utf-8-sig"), bible)


def read_usfm(text, bible):
    text = FOOTNOTES.sub(usfm_note, NOTES.sub("", ATTRIBUTES.sub("", text)))
    book = chapter = verse = None
    mode = "skip"          # "text" (verse text), "caption" (\d), "skip" (headings etc.), "name" (\h)
    styles = []
    parts = TOKENS.split(text)
    i = 0
    while i < len(parts):
        piece = parts[i]
        i += 1
        if not piece.startswith("\\"):
            if book is None:
                continue
            if mode == "name":
                bible.books.setdefault(book, {"name": "", "chapters": {}})["name"] = piece.strip()
                mode = "skip"
            elif mode in ("text", "caption") and chapter:
                style = next((s for _, s in reversed(styles) if s), None)
                target = verse if mode == "text" else (verse or 0) + 1
                if mode == "text" and not verse:
                    continue
                bible.add(book, chapter, target, style, piece, caption=(mode == "caption"))
            continue
        marker = piece[1:].lstrip("+")
        closing = marker.endswith("*")
        name = marker.rstrip("*")
        if not closing and i < len(parts) and parts[i][:1] in (" ", "\n", "\r", "\t"):
            parts[i] = parts[i][2:] if parts[i][:2] == "\r\n" else parts[i][1:]   # the space after a marker is part of it
        following = parts[i] if i < len(parts) else ""
        if closing:
            for k in range(len(styles) - 1, -1, -1):
                if styles[k][0] == name:
                    del styles[k]
                    break
            continue
        if name == "id":
            code = following.split()[0] if following.split() else ""
            book = BOOK_NUMBER.get(code.upper())
            chapter = verse = None
            mode, styles = "skip", []
            parts[i] = ""
        elif book is None:
            continue
        elif name == "c":
            m = NUMBER_START.match(following)
            if m:
                chapter, verse = int(m.group(1)), None
                bible.chapter(book, chapter)
                parts[i] = ""
            mode, styles = "skip", []
        elif name == "v":
            m = VERSE_START.match(following)
            if m and chapter:
                verse = int(m.group(1))
                parts[i] = m.group(2)
                mode = "text"
                bible.add(book, chapter, verse, None, " ")
        elif name == "d":
            # A psalm's title; one after verse text (Habakkuk 3:19) stays with that verse.
            mode = "text" if verse else "caption"
        elif name == "h":
            mode = "name"
        elif name in SKIP_PARAS:
            mode = "skip"
        elif name in TEXT_PARAS:
            if mode == "caption" or (mode == "skip" and verse):
                mode = "text" if verse else mode
            if verse and mode == "text":
                bible.add(book, chapter, verse, None, " ")
        else:
            styles.append((name, CHAR_STYLES.get(name)))   # \w, \wj, \bd, \qs ...: no style, text kept


# ---- SWORD modules (crosswire.org) -------------------------------------------------------

def kjv_verse_counts():
    """[[verses in chapter 1, ...] for each of the 66 books], from the app's av.md (the KJV
    versification SWORD modules use)."""
    counts, chapter = [], None
    for line in (PROJECT / "av.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            counts.append([])
        elif line.startswith("#### "):
            counts[-1].append(0)
        elif counts and counts[-1] and (m := re.match(r"\[(\d+)\]", line)):
            counts[-1][-1] = max(counts[-1][-1], int(m.group(1)))   # the last verse's number
    if len(counts) != 66:
        sys.exit("av.md doesn't have the expected 66 books")
    return counts


def read_conf(module_dir):
    confs = list((module_dir / "mods.d").glob("*.conf"))
    if not confs:
        sys.exit(f"No mods.d/*.conf in {module_dir}")
    conf = {}
    for line in confs[0].read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            conf.setdefault(k.strip(), v.strip())
    return conf


def sword_entries(data_dir, testament, driver):
    """Yields each verse slot's raw bytes for one testament ("ot" / "nt"), in index order."""
    if driver.lower() == "ztext":
        bzs, bzv, bzz = (data_dir / f"{testament}.{x}" for x in ("bzs", "bzv", "bzz"))
        if not bzv.exists() or bzv.stat().st_size == 0:
            return
        blocks = bzs.read_bytes()
        data = bzz.read_bytes()
        cache = {}
        index = bzv.read_bytes()
        for k in range(len(index) // 10):
            block, offset, size = struct.unpack_from("<IIH", index, k * 10)
            if size == 0:
                yield b""
                continue
            if block not in cache:
                start, csize, _ = struct.unpack_from("<III", blocks, block * 12)
                cache = {block: zlib.decompress(data[start:start + csize])}
            yield cache[block][offset:offset + size]
    elif driver.lower() == "rawtext":
        txt, vss = data_dir / testament, data_dir / f"{testament}.vss"
        if not vss.exists():
            return
        index, data = vss.read_bytes(), txt.read_bytes()
        for k in range(len(index) // 6):
            offset, size = struct.unpack_from("<IH", index, k * 6)
            yield data[offset:offset + size]
    else:
        sys.exit(f"Module driver {driver} isn't supported (zText and RawText are)")


GBF_TAG = re.compile(r"<([A-Z][A-Za-z0-9]*)[^>]*>")
GBF_DROP = re.compile(r"<TS>.*?<Ts>|<RX>.*?<Rx>", re.S)
GBF_NOTE = re.compile(r"<RF>(.*?)<Rf>", re.S)


RTF_CODE = re.compile(r"\\[a-z]+-?\d*\s?")          # \ul1, \pa ... left in some old GBF modules


def gbf_segments(text):
    text = GBF_NOTE.sub(lambda m: note_placeholder(html.unescape(GBF_TAG.sub(" ", RTF_CODE.sub("", m.group(1))))), text)
    text = RTF_CODE.sub("", GBF_DROP.sub("", text))
    out, style, pos = [], None, 0
    for m in GBF_TAG.finditer(text):
        out.append((style, text[pos:m.start()]))
        tag = m.group(1)
        if tag == "FI":
            style = ITALIC
        elif tag == "Fi":
            style = None
        elif tag in ("CM", "CL", "Cm"):
            out.append((style, " "))
        pos = m.end()
    out.append((style, text[pos:]))
    return [(s, html.unescape(t)) for s, t in out if t]


OSIS_DROP = re.compile(r"<(title|rdg|reference)\b[^>]*?(?<!/)>.*?</\1>", re.S)
OSIS_NOTE = re.compile(r"<note\b([^>]*?)(?<!/)>(.*?)</note>", re.S)
XML_TAG = re.compile(r"<(/?)([A-Za-z:]+)([^>]*?)(/?)>")


def osis_note(m):
    if re.search(r"crossReference", m.group(1), re.I):
        return ""                                   # cross-references: left out
    inner = re.sub(r"<(reference|catchWord)\b[^>]*>.*?</\1>", lambda x: x.group(0) if x.group(1) == "catchWord" else "", m.group(2), flags=re.S)
    return note_placeholder(html.unescape(XML_TAG.sub(" ", inner)))


def markup_segments(text):
    """OSIS or ThML: headings dropped, footnotes kept as notes, added words italic, the
    divine name in small caps, other tags removed."""
    text = OSIS_NOTE.sub(osis_note, text)
    text = OSIS_DROP.sub("", text)
    text = re.sub(r"<scripRef\b.*?</scripRef>", "", text, flags=re.S)
    out, stack, pos = [], [], 0
    for m in XML_TAG.finditer(text):
        style = next((s for s in reversed(stack) if s), None)
        out.append((style, text[pos:m.start()]))
        closing, name, attrs, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if selfclose:
            if name in ("lb", "br", "l", "milestone"):
                out.append((style, " "))
        elif closing:
            if stack:
                stack.pop()
        else:
            if (name == "transchange" and "added" in attrs) or (name in ("hi", "font") and "ital" in attrs) or name in ("i", "em"):
                stack.append(ITALIC)
            elif name == "divinename" or (name == "hi" and "small-caps" in attrs):
                stack.append(SMALL_CAPS)
            else:
                stack.append(None)
            if name in ("l", "p", "lg", "div"):
                out.append((None, " "))
        pos = m.end()
    out.append((next((s for s in reversed(stack) if s), None), text[pos:]))
    return [(s, html.unescape(t)) for s, t in out if t]


def read_sword_module(module_dir, bible):
    conf = read_conf(module_dir)
    v11n = conf.get("Versification", "KJV")
    if v11n != "KJV":
        sys.exit(f"Versification {v11n} isn't supported (only KJV)")
    data_dir = (module_dir / conf["DataPath"]).resolve()
    if data_dir.suffix or not data_dir.is_dir():
        data_dir = data_dir.parent if not data_dir.is_dir() else data_dir
    encoding = "utf-8" if conf.get("Encoding", "").upper() == "UTF-8" else "cp1252"
    source = conf.get("SourceType", "Plaintext").upper()
    parse = gbf_segments if source == "GBF" else markup_segments if source in ("OSIS", "THML") else (lambda t: [(None, t)])
    counts = kjv_verse_counts()
    for testament, books in (("ot", range(0, 39)), ("nt", range(39, 66))):
        entries = list(sword_entries(data_dir, testament, conf.get("ModDrv", "zText")))
        if not entries:
            continue
        expected = 2 + sum(1 + len(counts[b]) + sum(counts[b]) for b in books)
        if len(entries) != expected:
            sys.exit(f"{testament}: {len(entries)} index entries, expected {expected} for KJV versification")
        k = 2                                   # 0: module heading, 1: testament heading
        for b in books:
            k += 1                              # book heading
            for c, n in enumerate(counts[b], start=1):
                k += 1                          # chapter heading
                for v in range(1, n + 1):
                    raw = entries[k].decode(encoding, errors="replace")
                    k += 1
                    for style, text in parse(raw):
                        bible.add(b + 1, c, v, style, text)


# ---- Writing -----------------------------------------------------------------------------

HEBREW_NUMBER = re.compile(r"\(\d+[-:]\d+\)\s?")      # "(3-2)": the Hebrew verse number (JPS, Leeser)
DROP_HEBREW_NUMBERS = False


def segments_xml(segments):
    merged = []
    for style, text in segments:
        style = style if style in (ITALIC, SMALL_CAPS) else None
        text = text.replace("||", " ")                 # the LSV's poetry line breaks
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]", " ", text)   # not allowed in XML
        if DROP_HEBREW_NUMBERS:
            text = HEBREW_NUMBER.sub("", text)
        text = re.sub(r"\s+", " ", text)
        if merged and merged[-1][0] == style:
            merged[-1][1] += text
        else:
            merged.append([style, text])
    out = []
    for style, text in merged:
        if style:
            inner = text.strip()
            if inner:
                lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
                out.append(f'{escape(lead)}<STYLE fs="{style}">{escape(inner)}</STYLE>{escape(trail)}')
            else:
                out.append(escape(text))
        else:
            out.append(escape(text))
    xml = "".join(out)
    xml = re.sub(r" {2,}", " ", xml).strip()
    xml = re.sub(r" ([,.;:!?])", r"\1", xml)
    # Footnotes (already escaped above) become <NOTE>s where they were in the text.
    xml = re.sub(rf"\s*{NOTE_START}(.*?){NOTE_END}", lambda m: f'<NOTE type="x-studynote">{m.group(1).strip()}</NOTE>', xml)
    return xml.replace(NOTE_START, "").replace(NOTE_END, "")


def write_zefania(bible, out, name, rights, source, description):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f"<XMLBIBLE biblename={quoteattr(name)}>",
             "  <INFORMATION>",
             f"    <title>{escape(name)}</title>"]
    for tag, value in (("rights", rights), ("source", source), ("description", description)):
        if value:
            lines.append(f"    <{tag}>{escape(value)}</{tag}>")
    lines.append("  </INFORMATION>")
    stats = {"books": 0, "chapters": 0, "verses": 0}
    for b in sorted(bible.books):
        chapters = {c: ch for c, ch in bible.books[b]["chapters"].items()
                    if any(segments_xml(s) for s in ch["verses"].values())}
        if not chapters:
            continue
        stats["books"] += 1
        bname = bible.books[b]["name"]
        lines.append(f'  <BIBLEBOOK bnumber="{b}"' + (f" bname={quoteattr(bname)}" if bname else "") + ">")
        for c in sorted(chapters):
            stats["chapters"] += 1
            lines.append(f'    <CHAPTER cnumber="{c}">')
            for v, segs in sorted(chapters[c]["captions"].items()):
                cap = segments_xml(segs)
                if cap:
                    lines.append(f'      <CAPTION vref="{v}">{cap}</CAPTION>')
            for v, segs in sorted(chapters[c]["verses"].items()):
                text = segments_xml(segs)
                if text:
                    stats["verses"] += 1
                    lines.append(f'      <VERS vnumber="{v}">{text}</VERS>')
            lines.append("    </CHAPTER>")
        lines.append("  </BIBLEBOOK>")
    lines.append("</XMLBIBLE>")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--name", required=True)
    ap.add_argument("--rights", default="")
    ap.add_argument("--source-note", dest="source_note", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--drop-hebrew-numbers", action="store_true",
                    help='remove notes like "(3-2)" giving the Hebrew verse number (JPS 1917, Leeser)')
    args = ap.parse_args()
    global DROP_HEBREW_NUMBERS
    DROP_HEBREW_NUMBERS = args.drop_hebrew_numbers
    bible = Bible()
    if (args.source / "mods.d").is_dir():
        read_sword_module(args.source, bible)
    else:
        read_usfm_folder(args.source, bible)
    stats = write_zefania(bible, args.output, args.name, args.rights, args.source_note, args.description)
    print(f"{args.output.name}: {stats['books']} books, {stats['chapters']} chapters, {stats['verses']} verses")


if __name__ == "__main__":
    main()
