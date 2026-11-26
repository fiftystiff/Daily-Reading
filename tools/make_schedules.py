"""Write the sample schedules into Daily-Reading_schedules (from av.md's real chapter and
verse counts, so every reading exists).

    python tools/make_schedules.py

Only the files this script makes are written; other schedules in the folder are left alone.
Edit the plans below (or the files themselves) and run it again to regenerate them."""
import datetime as dt
import re
import sys
from pathlib import Path

project = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
out = project / "Daily-Reading_schedules"
out.mkdir(exist_ok=True)   # existing files are overwritten only if this script writes them

# ---- books and chapter counts from av.md ---------------------------------------------
SMALL = {"of", "the", "and"}
COUNTS, ORDER = {}, []
VERSES = {}   # (book, chapter) -> number of verses
book = None
for line in (project / "av.md").read_text(encoding="utf-8-sig").splitlines():
    if line.startswith("### "):
        words = line[4:].strip().split()
        book = " ".join(w.lower() if i and w.lower() in SMALL else w[:1].upper() + w[1:] for i, w in enumerate(words))
        COUNTS[book] = 0
        ORDER.append(book)
    elif line.startswith("#### "):
        COUNTS[book] += 1
    else:
        m = re.match(r"\[(\d+)\]", line.strip())
        if m:
            VERSES[(book, COUNTS[book])] = int(m.group(1))
OT, NT = ORDER[:39], ORDER[39:]
assert len(ORDER) == 66 and sum(COUNTS.values()) == 1189, (len(ORDER), sum(COUNTS.values()))


def chapters(*books):
    return [(b, c) for b in books for c in range(1, COUNTS[b] + 1)]


def name(b, plural):
    return ("Psalms" if plural else "Psalm") if b == "Psalms" else b


def fmt(chs):
    """[(book, ch), ...] -> "Genesis 1-3", "Genesis 50; Exodus 1-2", "Jude", "Psalm 23"."""
    runs = []
    for b, c in chs:
        if runs and runs[-1][0] == b and runs[-1][2] == c - 1:
            runs[-1][2] = c
        else:
            runs.append([b, c, c])
    parts = []
    for b, a, z in runs:
        if COUNTS[b] == 1:
            parts.append(b)
        elif a == z:
            parts.append(f"{name(b, False)} {a}")
        else:
            parts.append(f"{name(b, True)} {a}-{z}")
    return "; ".join(parts)


def split(seq, days):
    """Divide a list of chapters into `days` nearly equal, in-order portions."""
    return [seq[round(d * len(seq) / days):round((d + 1) * len(seq) / days)] for d in range(days)]


HELP = """<!--
  A custom reading schedule for Daily-Reading. Put .md files like this one in the
  Daily-Reading_schedules folder next to Daily-Reading.exe, then pick it from the
  dropdown at the top of the Schedule panel.

  Settings (the block between the --- lines, all optional):
    name:  the name shown in the dropdown
    mode:  weekly    - "## Week N" is week N of the year (like the built-in schedule)
           monthly   - row N is day N of the month (the last row for any later days)
           yearly    - row N is day N of the year (February 29 repeats February 28)
           dated     - the first row is the start date, then one row per day
           checklist - "Next" goes to the first day that isn't ticked off
    start: the date of the first reading (dated): a date (2027-01-04), a day every year
           (12-01 or Dec 1), or a day worked out from Easter each year (Ash Wednesday,
           Palm Sunday, Good Friday, Easter, Pentecost, Advent Sunday, or Easter-7 etc.)
    days:  weekdays (Saturday shows Friday's reading, Sunday Monday's) or daily

  Readings go in Markdown tables. "##" headings divide them into weeks, months or
  any sections you like, or leave the headings out for one long list. References like
  "Genesis 1-3", "Psalm 23, 24", "1 Cor 13", "Jn 3:16-21" or a whole book ("Jude")
  become links. "[ ]" makes a checkbox, either in a column of its own (one per day) or
  before a reading; ticking it in the app saves an "x" in this file. You can also tick
  boxes here in a text editor, and the app picks up the change.
-->
"""


def write(filename, settings, title, body_lines):
    head = ["---"] + [f"{k}: {v}" for k, v in settings.items()] + ["---", HELP, f"# {title}", ""]
    (out / filename).write_text("\n".join(head + body_lines) + "\n", encoding="utf-8")


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("-" * (len(h) + 2) for h in headers) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return lines + [""]


def by_month(days):
    """365 daily portions -> "## January" ... sections with Done / Date / Reading."""
    body = []
    for month in range(1, 13):
        rows = []
        for d, portion in enumerate(days):
            date = dt.date(2027, 1, 1) + dt.timedelta(days=d)   # a 365-day year
            if date.month == month:
                rows.append(["[ ]", f"{date:%b} {date.day}", fmt(portion)])
        body += [f"## {dt.date(2027, month, 1):%B}"] + table(["Done", "Date", "Reading"], rows)
    return body


# 1. Bible in a Year: cover to cover, about 3-4 chapters a day, by date every year (yearly)
write("Bible in a Year.md", {"name": "Bible in a Year", "mode": "yearly"}, "Bible in a Year",
      by_month(split(chapters(*ORDER), 365)))

# 2. New Testament in 90 Days: one long list (checklist)
days = split(chapters(*NT), 90)
write("New Testament in 90 Days.md", {"name": "New Testament in 90 Days", "mode": "checklist"},
      "New Testament in 90 Days",
      table(["Done", "Day", "Reading"], [["[ ]", str(i + 1), fmt(p)] for i, p in enumerate(days)]))

# 3. New Testament on Weekdays: a chapter each weekday for a year (dated, weekdays)
nt = chapters(*NT)   # 260 chapters = 52 weeks of 5 weekdays
body = []
for w in range(52):
    body += [f"## Week {w + 1}"] + table(["Done", "New Testament"], [["[ ]", fmt([c])] for c in nt[w * 5:w * 5 + 5]])
write("New Testament on Weekdays.md", {"name": "New Testament on Weekdays", "mode": "weekly"},
      "New Testament on Weekdays", body)

# 4. Gospels in 40 Days (checklist, by week)
days = split(chapters("Matthew", "Mark", "Luke", "John"), 40)
body = []
for w in range(0, 40, 7):
    body += [f"## Week {w // 7 + 1}"] + table(["Done", "Day", "Reading"],
                                              [["[ ]", str(d + 1), fmt(days[d])] for d in range(w, min(w + 7, 40))])
write("Gospels in 40 Days.md", {"name": "Gospels in 40 Days", "mode": "checklist"}, "Gospels in 40 Days", body)

# 5. Psalms and Proverbs in a Month: the classic plan, five psalms and a proverb a day
#    (day N: Psalms N, N+30, N+60, N+90, N+120 and Proverbs N), a checkbox for each
rows = []
for d in range(1, 32):
    ps = f"[ ] Psalms {d}, {d + 30}, {d + 60}, {d + 90}, {d + 120}" if d <= 30 else ""
    rows.append([str(d), ps, f"[ ] Proverbs {d}"])
write("Psalms and Proverbs in a Month.md", {"name": "Psalms and Proverbs in a Month", "mode": "checklist"},
      "Psalms and Proverbs in a Month", table(["Day", "Psalms", "Proverbs"], rows))

# 6. Paul's Letters in 30 Days (checklist, sections by letter)
sections = [("Romans", ["Romans"], 6), ("Corinthians", ["1 Corinthians", "2 Corinthians"], 10),
            ("Galatians to Colossians", ["Galatians", "Ephesians", "Philippians", "Colossians"], 7),
            ("Thessalonians", ["1 Thessalonians", "2 Thessalonians"], 3),
            ("Timothy, Titus and Philemon", ["1 Timothy", "2 Timothy", "Titus", "Philemon"], 4)]
body, day = [], 0
for title, books, n in sections:
    rows = []
    for portion in split(chapters(*books), n):
        day += 1
        rows.append(["[ ]", str(day), fmt(portion)])
    body += [f"## {title}"] + table(["Done", "Day", "Reading"], rows)
assert day == 30
write("Paul's Letters in 30 Days.md", {"name": "Paul's Letters in 30 Days", "mode": "checklist"},
      "Paul's Letters in 30 Days", body)

# 7. Wisdom Books in 12 Weeks: Job to Song of Solomon on weekdays (dated, weekdays)
days = split(chapters("Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon"), 60)
body = []
for w in range(12):
    body += [f"## Week {w + 1}"] + table(["Done", "Day", "Reading"],
                                         [["[ ]", str(d + 1), fmt(days[d])] for d in range(w * 5, w * 5 + 5)])
write("Wisdom Books in 12 Weeks.md", {"name": "Wisdom Books in 12 Weeks", "mode": "checklist"},
      "Wisdom Books in 12 Weeks", body)

# 8. Advent: December 1-25, prophecies of the Messiah to the birth of Jesus (dated, daily)
advent = ["Genesis 3", "Genesis 12", "Numbers 24", "2 Samuel 7", "Psalm 2", "Psalm 89", "Isaiah 7",
          "Isaiah 9", "Isaiah 11", "Isaiah 40", "Isaiah 42", "Isaiah 53", "Isaiah 60", "Jeremiah 23",
          "Micah 5", "Malachi 3", "Luke 1", "Matthew 1", "John 1", "Galatians 4", "Philippians 2",
          "Colossians 1", "Hebrews 1", "Matthew 2", "Luke 2"]
assert len(advent) == 25
write("Advent.md", {"name": "Advent", "mode": "dated", "start": "12-01", "days": "daily"}, "Advent",
      table(["Done", "Date", "Reading"], [["[ ]", f"Dec {i + 1}", r] for i, r in enumerate(advent)]))

# 9. Anglican Psalter: the Book of Common Prayer (1662) 30-day course of the Psalms,
#    morning and evening, by day of the month (monthly). On the 31st the 30th day's psalms
#    are read again, as the Prayer Book directs.
psalter = [
    ("1-5", "6-8"), ("9-11", "12-14"), ("15-17", "18"), ("19-21", "22-23"), ("24-26", "27-29"),
    ("30-31", "32-34"), ("35-36", "37"), ("38-40", "41-43"), ("44-46", "47-49"), ("50-52", "53-55"),
    ("56-58", "59-61"), ("62-64", "65-67"), ("68", "69-70"), ("71-72", "73-74"), ("75-77", "78"),
    ("79-81", "82-85"), ("86-88", "89"), ("90-92", "93-94"), ("95-97", "98-101"), ("102-103", "104"),
    ("105", "106"), ("107", "108-109"), ("110-113", "114-115"), ("116-118", "119:1-32"),
    ("119:33-72", "119:73-104"), ("119:105-144", "119:145-176"), ("120-125", "126-131"),
    ("132-135", "136-138"), ("139-141", "142-143"), ("144-146", "147-150"),
]
assert len(psalter) == 30


def psalms(ref):
    return f"Psalm {ref}" if ":" in ref or "-" not in ref else f"Psalms {ref}"


# every psalm is read once in the month
covered = set()
for m, e in psalter:
    for ref in (m, e):
        a, _, z = ref.split(":")[0].partition("-")
        covered.update(range(int(a), int(z or a) + 1))
assert covered == set(range(1, 151)), sorted(set(range(1, 151)) - covered)
write("Anglican Psalter.md", {"name": "Anglican Psalter", "mode": "monthly"}, "Anglican Psalter",
      ["<!-- The Psalms read through each month at Morning and Evening Prayer. The app opens",
       "     the row for today's date; on the 31st, day 30 is read again. -->", ""]
      + table(["Day", "Morning Prayer", "Evening Prayer"],
              [[str(d + 1), psalms(m), psalms(e)] for d, (m, e) in enumerate(psalter)]))

# ---- helpers for the plans below -------------------------------------------------------
def easter(y):
    """Western (Gregorian) Easter Sunday."""
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    return dt.date(y, (h + ll - 7 * m + 114) // 31, (h + ll - 7 * m + 114) % 31 + 1)


assert easter(2027) == dt.date(2027, 3, 28) and easter(2025) == dt.date(2025, 4, 20) and easter(2024) == dt.date(2024, 3, 31)
NEXT_EASTER = easter(2027)   # the next Easter after this was written (November 2026)


def verse_split(book, first, last, days, last_verse=None, snap=8):
    """Divide a book from chapter `first` to `last` (ending at last_verse, or the chapter's
    end) into `days` portions of about equal verses. A cut within `snap` verses of the
    start of a chapter moves there, so portions begin with a chapter where they can."""
    verses = [(c, v) for c in range(first, last + 1) for v in range(1, VERSES[(book, c)] + 1)
              if not (c == last and last_verse and v > last_verse)]
    cuts = [0]
    for d in range(1, days):
        i = round(d * len(verses) / days)
        starts = [j for j in range(max(cuts[-1] + 1, i - snap), min(len(verses), i + snap + 1)) if verses[j][1] == 1]
        cuts.append(min(starts, key=lambda j: abs(j - i)) if starts else i)
    cuts.append(len(verses))
    out = []
    for d in range(days):
        part = verses[cuts[d]:cuts[d + 1]]
        (c1, v1), (c2, v2) = part[0], part[-1]
        whole_start, whole_end = v1 == 1, v2 == VERSES[(book, c2)]
        if c1 == c2:
            out.append(f"{book} {c1}" if whole_start and whole_end else f"{book} {c1}:{v1}" + (f"-{v2}" if v2 != v1 else ""))
        else:
            out.append(f"{book} {c1}-{c2}" if whole_start and whole_end else f"{book} {c1}:{v1}-{c2}:{v2}")
    return out


def date_label(d):
    return f"{d:%b} {d.day}"


# 10. Proverbs a Day: chapter N on day N of the month (monthly)
write("Proverbs a Day.md", {"name": "Proverbs a Day", "mode": "monthly"}, "Proverbs a Day",
      table(["Day", "Reading"], [[str(d), f"Proverbs {d}"] for d in range(1, 32)]))

# 11. Psalms of Ascent: the pilgrim songs, Psalms 120-134, one a day (checklist)
write("Psalms of Ascent.md", {"name": "Psalms of Ascent", "mode": "checklist"}, "Psalms of Ascent",
      table(["Done", "Day", "Reading"], [["[ ]", str(d + 1), f"Psalm {120 + d}"] for d in range(15)]))

# 12. Psalm 119 in 22 Days: one 8-verse section (one Hebrew letter) a day (checklist)
letters = ["Aleph", "Beth", "Gimel", "Daleth", "He", "Vau", "Zain", "Cheth", "Teth", "Jod", "Caph", "Lamed",
           "Mem", "Nun", "Samech", "Ain", "Pe", "Tzaddi", "Koph", "Resh", "Schin", "Tau"]
assert len(letters) * 8 == VERSES[("Psalms", 119)] == 176
write("Psalm 119 in 22 Days.md", {"name": "Psalm 119 in 22 Days", "mode": "checklist"}, "Psalm 119 in 22 Days",
      table(["Done", "Day", "Letter", "Reading"],
            [["[ ]", str(i + 1), name_, f"Psalm 119:{8 * i + 1}-{8 * i + 8}"] for i, name_ in enumerate(letters)]))

# 13. Old Testament on Weekdays: 929 chapters over 52 weeks of weekdays (dated, weekdays)
days = split(chapters(*OT), 260)
body = []
for w in range(52):
    body += [f"## Week {w + 1}"] + table(["Done", "Old Testament"], [["[ ]", fmt(p)] for p in days[w * 5:w * 5 + 5]])
write("Old Testament on Weekdays.md", {"name": "Old Testament on Weekdays", "mode": "weekly"},
      "Old Testament on Weekdays", body)

# 14. Bible in 90 Days: about 13 chapters a day (checklist, sections of 10 days)
days = split(chapters(*ORDER), 90)
body = []
for s in range(0, 90, 10):
    body += [f"## Days {s + 1}-{s + 10}"] + table(["Done", "Day", "Reading"],
                                                  [["[ ]", str(d + 1), fmt(days[d])] for d in range(s, s + 10)])
write("Bible in 90 Days.md", {"name": "Bible in 90 Days", "mode": "checklist"}, "Bible in 90 Days", body)

# 15. Professor Horner's Bible Reading System: ten lists, a chapter from each every day;
#     each list starts again when it ends, so they drift in and out of step. One full
#     cycle of the longest list (250 days) (checklist, sections of 25 days)
horner = [
    ("Gospels", chapters("Matthew", "Mark", "Luke", "John")),
    ("Pentateuch", chapters("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy")),
    ("Epistles I", chapters("Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians",
                            "Colossians", "Hebrews")),
    ("Epistles II", chapters("1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
                             "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation")),
    ("Wisdom", chapters("Job", "Ecclesiastes", "Song of Solomon")),
    ("Psalms", chapters("Psalms")),
    ("Proverbs", chapters("Proverbs")),
    ("History", chapters("Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles",
                         "2 Chronicles", "Ezra", "Nehemiah", "Esther")),
    ("Prophets", chapters(*ORDER[ORDER.index("Isaiah"):ORDER.index("Malachi") + 1])),
    ("Acts", chapters("Acts")),
]
cycle = max(len(lst) for _, lst in horner)
assert cycle == 250
rows = [["[ ]", str(d + 1), "; ".join(fmt([lst[d % len(lst)]]) for _, lst in horner)] for d in range(cycle)]
body = ["<!-- The ten lists, in the order of each day's readings: " + ", ".join(n for n, _ in horner) + ". -->", ""]
for s in range(0, cycle, 25):
    body += [f"## Days {s + 1}-{s + 25}"] + table(["Done", "Day", "Readings"], rows[s:s + 25])
write("Horner's Ten Lists.md", {"name": "Horner's Ten Lists", "mode": "checklist"}, "Horner's Ten Lists", body)

# 16. Holy Week: Palm Sunday to Easter Day through the Gospels (dated, daily)
holy_week = [
    ("Palm Sunday", "Matthew 21:1-11; John 12:12-19"),
    ("Monday", "Mark 11:12-19"),
    ("Tuesday", "Mark 11:20-33; Matthew 24:1-14"),
    ("Wednesday", "Mark 14:1-11"),
    ("Maundy Thursday", "John 13:1-17; Luke 22:7-23; Mark 14:32-50"),
    ("Good Friday", "John 18:28-19:42"),
    ("Holy Saturday", "Matthew 27:57-66"),
    ("Easter Day", "John 20:1-18; Luke 24:13-35"),
]
write("Holy Week.md", {"name": "Holy Week", "mode": "dated", "start": "Palm Sunday", "days": "daily"}, "Holy Week",
      ["<!-- Starts on Palm Sunday, worked out from the date of Easter each year. -->", ""]
      + table(["Done", "Day", "Reading"], [["[ ]", day, r] for day, r in holy_week]))

# 17. Lent with Luke: Ash Wednesday to Easter. Luke up to Jesus' arrival in Jerusalem
#     (1:1-19:27) on the weekdays and Saturdays before Palm Sunday, a penitential psalm on
#     the Sundays, then Holy Week follows Luke's account day by day, and Luke 24 on Easter.
ash = NEXT_EASTER - dt.timedelta(days=46)
holy = {   # days after Ash Wednesday -> (name, reading)
    39: ("Palm Sunday", "Psalm 118; Luke 19:28-48"),
    40: ("Monday", "Luke 20"),
    41: ("Tuesday", "Luke 21"),
    42: ("Wednesday", "Luke 22:1-6; Psalm 41"),
    43: ("Maundy Thursday", "Luke 22:7-62"),
    44: ("Good Friday", "Luke 22:63-23:49; Psalm 22"),
    45: ("Holy Saturday", "Luke 23:50-56; Psalm 16"),
    46: ("Easter Day", "Luke 24"),
}
before = [i for i in range(39) if i == 0 or (ash + dt.timedelta(days=i)).weekday() != 6]
portions = iter(verse_split("Luke", 1, 19, len(before), last_verse=27))
sunday_psalms = iter(["Psalm 6", "Psalm 32", "Psalm 38", "Psalm 102", "Psalm 130"])
rows = []
for i in range(47):
    day = ash + dt.timedelta(days=i)
    if i in holy:
        name_, reading = holy[i]
    elif i == 0:
        name_, reading = "Ash Wednesday", "Psalm 51; " + next(portions)
    elif day.weekday() == 6:
        name_, reading = f"{(i + 3) // 7}{['st', 'nd', 'rd', 'th', 'th'][(i + 3) // 7 - 1]} Sunday in Lent", next(sunday_psalms)
    else:
        name_, reading = f"{day:%A}", next(portions)
    rows.append(["[ ]", name_, reading])   # Lent always starts on a Wednesday, so day names hold every year
assert next(portions, None) is None and next(sunday_psalms, None) is None and len(before) == 34
write("Lent with Luke.md", {"name": "Lent with Luke", "mode": "dated", "start": "Ash Wednesday", "days": "daily"},
      "Lent with Luke",
      ["<!-- Starts on Ash Wednesday, worked out from the date of Easter each year. -->", ""]
      + table(["Done", "Day", "Reading"], rows))

# 18. Chronological Bible in a Year: the books in roughly the order their events happened
#     (by book and section; Job with the patriarchs, Chronicles beside Samuel and Kings,
#     the prophets beside the kings they spoke to, the epistles within Acts) (yearly)
def ch(b, a=1, z=None):
    return [(b, c) for c in range(a, (z or COUNTS[b]) + 1)]


chrono = (ch("Genesis", 1, 11) + ch("Job") + ch("Genesis", 12) + ch("Exodus") + ch("Leviticus") + ch("Numbers")
          + ch("Deuteronomy") + ch("Psalms", 90, 90) + ch("Joshua") + ch("Judges") + ch("Ruth") + ch("1 Samuel")
          + ch("2 Samuel") + ch("1 Chronicles") + ch("Psalms", 1, 89) + ch("Psalms", 91) + ch("1 Kings", 1, 11)
          + ch("2 Chronicles", 1, 9) + ch("Proverbs") + ch("Ecclesiastes") + ch("Song of Solomon")
          + ch("1 Kings", 12) + ch("2 Kings", 1, 14) + ch("2 Chronicles", 10, 25) + ch("Jonah") + ch("Amos")
          + ch("Hosea") + ch("Joel") + ch("2 Kings", 15, 20) + ch("2 Chronicles", 26, 32) + ch("Isaiah", 1, 39)
          + ch("Micah") + ch("2 Kings", 21, 23) + ch("2 Chronicles", 33, 35) + ch("Nahum") + ch("Zephaniah")
          + ch("Habakkuk") + ch("Isaiah", 40) + ch("Jeremiah") + ch("2 Kings", 24) + ch("2 Chronicles", 36)
          + ch("Lamentations") + ch("Obadiah") + ch("Ezekiel") + ch("Daniel") + ch("Ezra", 1, 6) + ch("Haggai")
          + ch("Zechariah") + ch("Esther") + ch("Ezra", 7) + ch("Nehemiah") + ch("Malachi")
          + ch("Matthew") + ch("Mark") + ch("Luke") + ch("John") + ch("Acts", 1, 14) + ch("James")
          + ch("Galatians") + ch("Acts", 15, 18) + ch("1 Thessalonians") + ch("2 Thessalonians") + ch("Acts", 19, 20)
          + ch("1 Corinthians") + ch("2 Corinthians") + ch("Romans") + ch("Acts", 21) + ch("Ephesians")
          + ch("Philippians") + ch("Colossians") + ch("Philemon") + ch("1 Timothy") + ch("Titus") + ch("1 Peter")
          + ch("Hebrews") + ch("2 Timothy") + ch("2 Peter") + ch("Jude") + ch("1 John") + ch("2 John")
          + ch("3 John") + ch("Revelation"))
assert len(chrono) == 1189 and set(chrono) == set(chapters(*ORDER)), (len(chrono), len(set(chrono)))
write("Chronological Bible in a Year.md", {"name": "Chronological Bible in a Year", "mode": "yearly"},
      "Chronological Bible in a Year",
      ["<!-- An approximate historical order, by book and section: Job with the patriarchs,",
       "     Psalm 90 (a prayer of Moses) after Deuteronomy, the other psalms with David,",
       "     Chronicles beside Samuel and Kings, each prophet with the kings of his time,",
       "     Esther between Ezra 6 and 7, and the letters at their place in Acts. -->", ""]
      + by_month(split(chrono, 365)))

# 19-20. The Old and New Testaments as plain lists: one chapter per row, with a checkbox
write("Old Testament Checklist.md", {"name": "Old Testament Checklist", "mode": "checklist"},
      "Old Testament Checklist", table(["Done", "Chapter"], [["[ ]", fmt([c])] for c in chapters(*OT)]))
write("New Testament Checklist.md", {"name": "New Testament Checklist", "mode": "checklist"},
      "New Testament Checklist", table(["Done", "Chapter"], [["[ ]", fmt([c])] for c in chapters(*NT)]))
write("Whole Bible Checklist.md", {"name": "Whole Bible Checklist", "mode": "checklist"},
      "Whole Bible Checklist", table(["Done", "Chapter"], [["[ ]", fmt([c])] for c in chapters(*ORDER)]))

for f in sorted(out.glob("*.md")):
    print(f.name)
