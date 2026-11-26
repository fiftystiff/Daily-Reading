"""Put an XML bible's verses under the KJV's chapter and verse numbers, keeping each
verse's own number, so the app shows the right text for every reference.

    python tools/renumber_xml_bible.py "Daily-Reading_bibles\\Some Bible.xml" [OUTPUT.xml]
    python tools/renumber_xml_bible.py --check Daily-Reading_bibles      (report only)
    python tools/renumber_xml_bible.py "...xml" --books DAN,JOL          (only these books)

Check what --check reports before renumbering: a translation that combines verses
("1-3", leaving "(SEE 1:1)" placeholders) or counts psalm titles as verse 1 can look
renumbered when it isn't; use --books to change only the books that really differ.

Some bibles number differently from the KJV (the app's AV): Septuagint and Vulgate
psalms (LXX Psalm 22 is KJV Psalm 23), the Septuagint's Jeremiah and Exodus 35-40,
Hebrew numbering in Joel and Malachi, and so on. This finds where each verse belongs by
matching its wording against the AV (names and uncommon words, in sequence, so runs of
verses stay together) and rewrites only the books that need it:

    <VERS vnumber="1" orig="22:1">...</VERS>     KJV Psalm 23:1; the bible's own 22:1

The app shows the "orig" numbers in the text, so the numbering of the translation is
still visible, while navigation, schedules and switching translations use the KJV's.
Without OUTPUT the file is replaced (a copy of the original is kept in backups/).
"""
import argparse
import math
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import local_bibles as lb  # noqa: E402

STOP = set("""the and of to in that a i he his for is be it was with they them shall unto not him all
their thou thy which my me as but by from are you your will have on at this who were so there had we
when out then also up do or its an what said no o lord god thee ye hath upon these those into him her
she our us said say saith says one every man men may would should could did made make let come came
go went before over after things thing day days now even because therefore thus how may yea behold
like than more any shalt wilt hast art doth hast mine thine own very great""".split())


def stem(w):
    for end in ("eth", "est", "ing", "ed", "es", "s"):
        if len(w) > len(end) + 3 and w.endswith(end):
            return w[: -len(end)]
    return w


def words(text):
    text = re.sub(r"<[^>]+>", " ", text.lower())
    return {stem(w) for w in re.findall(r"[a-z]+", text) if len(w) > 2 and w not in STOP}


def tag(el):
    return el.tag.rsplit("}", 1)[-1].upper() if isinstance(el.tag, str) else ""


def read_av():
    """{book: [(chapter, verse, text), ...]} in order, from av.md."""
    av, book, ch = {}, 0, 0
    for line in (PROJECT / "av.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            book += 1
            av[book] = []
        elif line.startswith("#### "):
            ch = int(line.split()[-1])
        elif (m := re.match(r"\[(\d+)\]\s*(.*)", line)) and book:
            av[book].append((ch, int(m.group(1)), m.group(2).replace("*", "")))
    return av


class Scorer:
    """Similarity of a verse to each AV verse of a book: shared uncommon words, weighted by
    how rare they are in the book (0..1)."""

    def __init__(self, ref):
        self.sets = [words(t) for _, _, t in ref]
        df = Counter(w for s in self.sets for w in s)
        n = len(ref)
        self.idf = {w: math.log((n + 1) / c) for w, c in df.items()}
        self.norm = [math.sqrt(sum(self.idf[w] for w in s)) or 1 for s in self.sets]
        self.index = defaultdict(list)
        for j, s in enumerate(self.sets):
            for w in s:
                self.index[w].append(j)

    def candidates(self, text, top=40):
        ws = words(text)
        score = defaultdict(float)
        for w in ws:
            if w in self.idf:
                for j in self.index[w]:
                    score[j] += self.idf[w]
        norm = math.sqrt(sum(self.idf.get(w, 0) for w in ws)) or 1
        best = sorted(score.items(), key=lambda x: -x[1])[:top]
        return {j: s / (norm * self.norm[j]) for j, s in best}


RESCUE_MIN = 0.3        # how well a left-over verse must match an empty KJV verse to go there
SEQUENCE_BONUS = 0.2    # per neighbour that's next to it in the KJV too, when two compete
STEP, STAY, SKIP1, SKIP2, JUMP = 0, 1, 2, 3, 4
PENALTY = {STEP: 0.0, STAY: 0.12, SKIP1: 0.12, SKIP2: 0.3, JUMP: 0.9}


def align(sims, n):
    """Viterbi: for source verses i (with candidate scores sims[i]) choose AV verse j_i, where
    the next AV verse is free, staying (two verses in one) or skipping a little costs a bit,
    and jumping elsewhere costs more."""
    neg = -1e18
    prev = [sims[0].get(j, 0.0) - (0 if j == 0 else PENALTY[JUMP]) for j in range(n)]
    back = []
    for i in range(1, len(sims)):
        best_j = max(range(n), key=prev.__getitem__)
        jump_val = prev[best_j] - PENALTY[JUMP]
        s = sims[i]
        cur = [0.0] * n
        choice = bytearray(n)
        for j in range(n):
            v, c = jump_val, JUMP
            if j >= 1 and prev[j - 1] > v:
                v, c = prev[j - 1], STEP
            if prev[j] - PENALTY[STAY] > v:
                v, c = prev[j] - PENALTY[STAY], STAY
            if j >= 2 and prev[j - 2] - PENALTY[SKIP1] > v:
                v, c = prev[j - 2] - PENALTY[SKIP1], SKIP1
            if j >= 3 and prev[j - 3] - PENALTY[SKIP2] > v:
                v, c = prev[j - 3] - PENALTY[SKIP2], SKIP2
            cur[j] = v + s.get(j, 0.0)
            choice[j] = c
        back.append((choice, best_j))
        prev = cur
    j = max(range(n), key=prev.__getitem__)
    path = [j]
    for choice, best_j in reversed(back):
        c = choice[j]
        j = {STEP: j - 1, STAY: j, SKIP1: j - 2, SKIP2: j - 3, JUMP: best_j}[c]
        path.append(j)
    return path[::-1]


def book_verses(book_el):
    """[(chapter, verse, VERS element, text)] in the file's order, and captions."""
    out, captions = [], []
    for ch in book_el:
        if tag(ch) != "CHAPTER":
            continue
        c = lb.number(ch.get("cnumber"))
        for item in ch:
            if tag(item) == "VERS" and lb.number(item.get("vnumber")):
                out.append((c, lb.number(item.get("vnumber")), item, lb.render(item)))
            elif tag(item) == "CAPTION":
                captions.append((c, item))
    return out, captions


def renumber_book(book_el, ref, scorer):
    """Returns (mapping [(kjv_c, kjv_v) per source verse], verses, captions, stats) or None
    when the book already follows the KJV."""
    verses, captions = book_verses(book_el)
    if not verses:
        return None
    pos = {(c, v): j for j, (c, v, _) in enumerate(ref)}
    sims = [scorer.candidates(t) for _, _, _, t in verses]
    # Quick look: do whole chapters match other KJV chapters?
    votes = defaultdict(Counter)
    for (c, _, _, _), s in zip(verses, sims):
        if s:
            j = max(s, key=s.get)
            votes[c][ref[j][0]] += 1
    suspect = [c for c, cnt in votes.items() if sum(cnt.values()) >= 3 and cnt.most_common(1)[0][0] != c
               and cnt.most_common(1)[0][1] > cnt.get(c, 0) * 1.5]
    if not suspect:
        return None
    path = align(sims, len(ref))
    identity = sum(s.get(pos.get((c, v), -1), 0.0) for (c, v, _, _), s in zip(verses, sims))
    aligned = sum(s.get(j, 0.0) for j, s in zip(path, sims))
    moved = sum(1 for (c, _, _, _), j in zip(verses, path) if ref[j][0] != c)
    if moved < 3 or aligned < identity * 1.05 + 1:
        return None
    # Two separate stretches of the file landing on the same KJV verse means one of them
    # has no KJV counterpart (the Greek additions to Esther and Daniel, say): keep the
    # stretch that matches the verse better, and leave the other out rather than splice it
    # into the middle of a chapter. (Before renumbering those weren't shown either.)
    runs = defaultdict(list)          # j -> [[i, ...], ...] runs of consecutive source verses
    for i, j in enumerate(path):
        groups = runs[j]
        if groups and groups[-1][-1] == i - 1:
            groups[-1].append(i)
        else:
            groups.append([i])
    def in_sequence(g, j):
        """How many of the stretch's neighbours sit right next to it in the KJV too."""
        before = g[0] > 0 and path[g[0] - 1] in (j - 1, j)
        after = g[-1] + 1 < len(path) and path[g[-1] + 1] in (j, j + 1)
        return before + after

    # Empty verses (some files keep a number with no text) have nothing to show.
    empty = {i for i, (_, _, _, t) in enumerate(verses) if not re.sub(r"<[^>]+>|\s", "", t)}
    for j in runs:
        runs[j] = [g for g in ([i for i in g if i not in empty] for g in runs[j]) if g]
    dropped = set(empty)
    for j, groups in runs.items():
        if len(groups) > 1:
            # How well the wording matches counts most; fitting in with its neighbours helps.
            best = max(groups, key=lambda g: sum(sims[i].get(j, 0.0) for i in g) / len(g) + SEQUENCE_BONUS * in_sequence(g, j))
            dropped.update(i for g in groups if g is not best for i in g)
    # A verse that lost out may still belong somewhere the alignment left empty (in jumbled
    # passages like Exodus 35-40): put it at its best clearly matching empty KJV verse.
    final = {i: j for i, j in enumerate(path) if i not in dropped}
    taken = set(final.values())
    for i in sorted(dropped - empty, key=lambda i: -max(sims[i].values(), default=0)):
        free = {j: s for j, s in sims[i].items() if j not in taken and s >= RESCUE_MIN}
        if free:
            j = max(free, key=free.get)
            final[i] = j
            taken.add(j)
    mapping = [(ref[final[i]][0], ref[final[i]][1]) if i in final else None for i in range(len(path))]
    left = [i for i in range(len(path)) if i not in final and i not in empty]
    left_out = [f"{verses[i][0]}:{verses[i][1]}" for i in left]
    # Left out although it reads much like some KJV verse: worth a look.
    doubtful = [f"{verses[i][0]}:{verses[i][1]}" for i in left if max(sims[i].values(), default=0) >= 0.5]
    return mapping, verses, captions, {"moved": moved, "identity": identity, "aligned": aligned,
                                        "suspect": sorted(suspect), "left_out": left_out, "doubtful": doubtful}


def write_xml(root, books_out, path, note):
    """books_out: [(bnumber, bname, original element or None, {kjv_c: [(v, orig, el)]}, captions)]"""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    attrs = "".join(f' {k}={quote(v)}' for k, v in root.attrib.items() if "}" not in k)
    lines.append(f"<XMLBIBLE{attrs}>")
    info = next((el for el in root if tag(el) == "INFORMATION"), None)
    if info is None:
        info = ET.Element("INFORMATION")
    desc = next((el for el in info if tag(el) == "DESCRIPTION"), None)
    if desc is None:
        desc = ET.SubElement(info, "description")
    if note not in (desc.text or ""):
        desc.text = f"{(desc.text or '').strip()} {note}".strip()
    info.tail = None
    lines.append("  " + ET.tostring(info, encoding="unicode").strip())
    for b, bname, original, chapters, caps in books_out:
        if original is not None:
            original.tail = None
            lines.append("  " + ET.tostring(original, encoding="unicode").strip())
            continue
        lines.append(f'  <BIBLEBOOK bnumber="{b}"' + (f" bname={quote(bname)}" if bname else "") + ">")
        for c in sorted(chapters):
            lines.append(f'    <CHAPTER cnumber="{c}">')
            for vref, cap in sorted(caps.get(c, []), key=lambda x: x[0]):
                cap.set("vref", str(vref))
                cap.tail = None
                lines.append("      " + ET.tostring(cap, encoding="unicode").strip())
            for v, orig, el in sorted(chapters[c], key=lambda x: x[0]):
                el.set("vnumber", str(v))
                el.set("orig", orig)
                el.tail = None
                lines.append("      " + ET.tostring(el, encoding="unicode").strip())
            lines.append("    </CHAPTER>")
        lines.append("  </BIBLEBOOK>")
    lines.append("</XMLBIBLE>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def quote(v):
    from xml.sax.saxutils import quoteattr
    return quoteattr(v)


NOTE = "Verses placed under KJV chapter and verse numbers (each keeps its own number in orig)."


def process(path, out=None, check=False, quiet=False, only=None):
    t0 = time.time()
    av = read_av()
    tree = ET.parse(path)
    root = tree.getroot()
    books_out, report = [], []
    for el in root:
        if tag(el) != "BIBLEBOOK":
            continue
        b = lb.number(el.get("bnumber"))
        if not b or b not in av:
            continue
        if any(item.get("orig") for item in el.iter() if tag(item) == "VERS") or (only and lb.USFM[b - 1] not in only):
            books_out.append((b, el.get("bname"), el, None, None))      # already renumbered / not asked for
            continue
        ref = av[b]
        result = renumber_book(el, ref, Scorer(ref))
        if not result:
            books_out.append((b, el.get("bname"), el, None, None))
            continue
        mapping, verses, captions, stats = result
        report.append((lb.USFM[b - 1], stats))
        chapters = defaultdict(list)
        where = {}
        for (c, v, vers, _), target in zip(verses, mapping):
            if target is None:
                continue
            kc, kv = target
            chapters[kc].append((kv, f"{c}:{v}", vers))
            where.setdefault((c, v), (kc, kv))
        caps = defaultdict(list)
        for c, cap in captions:
            vref = lb.number(cap.get("vref")) or 1
            kc, kv = where.get((c, vref)) or where.get((c, 1)) or (c, vref)
            caps[kc].append((kv, cap))
        books_out.append((b, el.get("bname"), None, chapters, caps))
    name = Path(path).name
    if not report:
        if not quiet:
            print(f"{name}: follows the KJV numbering, nothing to change ({time.time() - t0:.0f}s)")
        return []
    summary = ", ".join(f"{code} ({s['moved']} verses moved" + (f", {len(s['left_out'])} left out" if s["left_out"] else "") + ")"
                        for code, s in report)
    print(f"{name}: {summary} ({time.time() - t0:.0f}s)")
    for code, s in report:
        if s["left_out"]:
            shown = s["left_out"] if len(s["left_out"]) <= 12 else s["left_out"][:6] + ["..."] + s["left_out"][-3:]
            print(f"  {code} left out (no KJV counterpart): {', '.join(shown)}")
        if s["doubtful"]:
            print(f"  {code} CHECK: left out but similar to a KJV verse: {', '.join(s['doubtful'])}")
    if check:
        return report
    target = Path(out) if out else Path(path)
    if not out:
        backup = PROJECT / "backups" / time.strftime("%Y-%m-%d_%H%M%S") / "Daily-Reading_bibles" / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        print(f"  original saved as {backup.relative_to(PROJECT)}")
    write_xml(root, books_out, target, NOTE)
    print(f"  wrote {target}")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="an XML bible, or (with --check) a folder of them")
    ap.add_argument("output", type=Path, nargs="?")
    ap.add_argument("--check", action="store_true", help="only report which books would change")
    ap.add_argument("--books", default="", help="only these books, as USFM codes: --books DAN,JOL")
    args = ap.parse_args()
    only = {b.strip().upper() for b in args.books.split(",") if b.strip()} or None
    if only and only - set(lb.USFM):
        sys.exit(f"Unknown book codes: {', '.join(sorted(only - set(lb.USFM)))} (use USFM codes like GEN, PSA, MAT)")
    if args.source.is_dir():
        if not args.check:
            sys.exit("Give one file to renumber, or use --check with a folder.")
        for f in sorted(args.source.glob("*.xml"), key=lambda p: p.name.casefold()):
            process(f, check=True, quiet=True, only=only)
    else:
        process(args.source, args.output, args.check, only=only)


if __name__ == "__main__":
    main()
