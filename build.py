import re
import json
import html
from pathlib import Path

# Translations in the toggle (order = toggle order).
#   file:   built into the page (public domain). *word* marks italics (supplied words).
#   online: copyrighted, fetched chapter by chapter with the reader's own API key
#           (see bible_api.py); "esv" = Crossway's ESV API, "apibible" = API.Bible.
TRANSLATIONS = [
    {"id": "av",   "label": "AV",   "name": "Authorized Version",              "file": "av.md", "italics": True},
    {"id": "esv",  "label": "ESV",  "name": "English Standard Version",        "online": "esv"},
    {"id": "nasb", "label": "NASB", "name": "New American Standard Bible 1995", "online": "apibible"},
    {"id": "niv",  "label": "NIV",  "name": "New International Version 2011",  "online": "apibible"},
]

# USFM book codes (what API.Bible calls the books), in the same order as av.md.
USFM = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG "
        "ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT "
        "ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV").split()

SMALL_WORDS = {"of", "the", "and"}


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def display_name(raw):
    words = raw.split()
    return " ".join(
        w.lower() if i > 0 and w.lower() in SMALL_WORDS else w[:1].upper() + w[1:]
        for i, w in enumerate(words)
    )


# 1. Parse a Bible markdown file:
#    # Title / ## Testament / ### Book / #### Chapter N / [N] verse text
def parse_bible(path):
    books = []
    testament, testament_title = "OT", "Old Testament"
    book = chapter = None
    with open(path, "r", encoding="utf-8-sig") as f:  # -sig: tolerate a BOM
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#### "):
                if book is None:
                    raise ValueError(f"{path}:{lineno}: chapter outside of a book")
                num = int(re.search(r'\d+', line).group(0))
                chapter = {"num": num, "verses": []}
                book["chapters"].append(chapter)
            elif line.startswith("### "):
                name = display_name(line[4:].strip())
                book = {"id": slugify(name), "name": name, "testament": testament,
                        "testament_title": testament_title, "chapters": []}
                books.append(book)
                chapter = None
            elif line.startswith("## "):
                testament_title = line[3:].strip()
                testament = "NT" if "new" in testament_title.lower() else "OT"
            elif line.startswith("# "):
                continue
            else:
                m = re.match(r'\[(\d+)\]\s*(.*)$', line) or re.match(r'(\d+)\s+(.*)$', line)
                if m and chapter is not None:
                    chapter["verses"].append([int(m.group(1)), m.group(2)])
                elif chapter is not None and chapter["verses"]:
                    chapter["verses"][-1][1] += " " + line  # wrapped continuation line
                else:
                    raise ValueError(f"{path}:{lineno}: unrecognised line: {line[:60]}")
    return books


# "+word" marks a verb in the historical present (a past event told in the present
# tense), as the NASB marks with an asterisk in print.
HISTORICAL_PRESENT = ('<span class="hist-present" title="Historical present: a past event '
                      'told in the present tense">+</span>')


def inline_text(text, italics):
    text = html.escape(text, quote=False)
    if italics:
        text = text.replace("** ", "* *")  # "*said,** Is*" -> "*said,* *Is*"
        text = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\+(?=\w)', HISTORICAL_PRESENT, text)
    return text.replace("*", "")


# Name shown in the top bar, where a chapter number follows ("Psalm 23").
BAR_NAMES = {"Psalms": "Psalm"}


def bar_name(name):
    return BAR_NAMES.get(name, name)


def render_bible(books, italics):
    # One .book-block per book. The page only shows the current book and its
    # neighbours, so each block carries any headings that come before it.
    out = []
    testament = None
    for i, b in enumerate(books):
        out.append(f'<div class="book-block" data-book="{b["id"]}">')
        if i == 0:
            out.append('<h1 class="bible-title">Holy Bible</h1>')
        if b["testament"] != testament:
            testament = b["testament"]
            out.append(f'<h2 class="testament-title">{html.escape(b["testament_title"])}</h2>')
        # Book titles and chapter numbers use the same two-cell row as the top bar
        # (name in the left cell, number in the right), so each lines up with the bar.
        # A title is always followed by a chapter number, so it uses the bar name
        # ("Psalm 1"); the navigation on the left keeps the full name ("Psalms").
        out.append(f'<section class="book-section" id="{b["id"]}" data-book="{b["id"]}">'
                   f'<h3 class="book-title heading-row"><span class="book-name">{html.escape(bar_name(b["name"]))}</span>'
                   f'<span></span></h3>')
        for c in b["chapters"]:
            cid = f'{b["id"]}-{c["num"]}'
            out.append(f'<div class="chapter" id="{cid}" data-book="{b["id"]}" data-num="{c["num"]}">'
                       f'<div class="chapter-head"><div class="heading-row"><span></span>'
                       f'<span class="chapter-num">{c["num"]}</span></div></div>')
            for v, t in c["verses"]:
                out.append(f'<p class="verse" data-v="{v}"><span class="verse-num">{v}</span> '
                           f'<span class="verse-text">{inline_text(t, italics)}</span></p>')
            out.append('</div>')
        out.append('</section></div>')
    return "\n".join(out)


parsed = {tr["id"]: parse_bible(tr["file"]) for tr in TRANSLATIONS if "file" in tr}

# The first translation (AV) defines the navigation structure and the chapter layout
# (book titles, chapter numbers) that online translations fill in.
base_books = parsed[TRANSLATIONS[0]["id"]]
if len(base_books) != len(USFM):
    raise SystemExit(f"{TRANSLATIONS[0]['file']}: expected {len(USFM)} books, found {len(base_books)}")

books_data = [
    {"id": b["id"], "name": b["name"], "barName": bar_name(b["name"]), "testament": b["testament"],
     "usfm": code,
     "chapters": [{"num": str(c["num"]), "id": f'{b["id"]}-{c["num"]}'} for c in b["chapters"]]}
    for b, code in zip(base_books, USFM)
]

translation_templates = "\n".join(
    f'<template id="tr-{tr["id"]}">\n{render_bible(parsed[tr["id"]], tr["italics"])}\n</template>'
    for tr in TRANSLATIONS if "file" in tr
)
translations_meta = [{"id": t["id"], "label": t["label"], "name": t["name"], "online": t.get("online")}
                     for t in TRANSLATIONS]

# 2. The built-in reading schedule: schedule.md, embedded as text. The page parses it with
#    the same code it uses for custom schedules (Daily-Reading_schedules/*.md), so both
#    behave the same way.
with open("schedule.md", "r", encoding="utf-8-sig") as f:
    schedule_md = f.read()
# 3. Themes: every Daily-Reading_themes/*.css file is a theme. Its header comment names it:
#    /*
#     * Theme: Warm Parchment
#     */
#    The "Default" theme is built into template.html, so the folder may be empty or absent.
#    This list is only the starting point: the desktop app re-reads the folder at startup.
THEMES_DIR = "Daily-Reading_themes"
themes = []
for path in sorted(Path(THEMES_DIR).glob("*.css")):
    if path.stem == "default":
        continue  # reserved for the built-in theme
    head = path.read_text(encoding="utf-8")[:500]
    name = re.search(r'Theme:\s*(.+)', head)
    themes.append({
        "id": path.stem,
        "name": name.group(1).strip() if name else path.stem.replace("-", " ").title(),
    })
themes.sort(key=lambda t: t["name"].lower())

# 4. Inject into template.html
with open("template.html", "r", encoding="utf-8") as f:
    template = f.read()

final_html = (
    template
    .replace("/*{{BOOKS_JSON}}*/ []", json.dumps(books_data))
    .replace("/*{{SCHEDULE_MD}}*/ \"\"", json.dumps(schedule_md).replace("</", "<\\/"))
    .replace("/*{{TRANSLATIONS_JSON}}*/ []", json.dumps(translations_meta))
    .replace("/*{{THEMES_JSON}}*/ []", json.dumps(themes))
    .replace("{{TRANSLATION_TEMPLATES}}", translation_templates)
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"Built index.html with {len(books_data)} books, {len(TRANSLATIONS)} translations, "
      f"{len(themes)} themes and the built-in schedule!")
