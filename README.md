# Daily-Reading

A Windows app for reading the Bible on a schedule. It opens to today's reading, lets
you follow any of the included reading plans (or your own), and can show the
Authorized (King James) Version, plus the ESV, NASB and NIV with free API keys, and any
Bibles you add as XML files.

- [Getting started](#getting-started)
- [Reading](#reading)
- [Translations and API keys](#translations-and-api-keys)
- [More translations (XML bibles)](#more-translations-xml-bibles)
- [Schedules](#schedules)
- [Settings](#settings)
- [Themes](#themes)
- [Where things are saved](#where-things-are-saved)
- [Building from source](#building-from-source)
- [Known limitations](#known-limitations)

---

## Getting started

The app is a portable install: everything it needs is in one `Daily-Reading` folder,
which can be copied anywhere (another computer, a USB stick) and run from there. It's
also available as `Daily-Reading.zip`: unzip it anywhere and run
`Daily-Reading\Daily-Reading.exe`.

```
Daily-Reading.exe
_internal/                    the app's own files (Python, the page); leave as is
Daily-Reading_themes/         themes (.css files)
Daily-Reading_schedules/      reading plans (.md files)
Daily-Reading_settings.json   your settings (made by the app)
Daily-Reading_keys.txt        optional: your API keys (see below)
Daily-Reading_bibles/         optional: more translations as XML files (see below)
LICENSE
```

When giving the folder to someone else, leave out `Daily-Reading_keys.txt` (your keys),
`Daily-Reading_bibles` unless every bible in it is free to share, and
`Daily-Reading_settings.json` too if they should start with the default settings.

Run `Daily-Reading.exe`. It opens to today's reading in the schedule you used last (the
built-in **Weekday Yearly** schedule the first time). Both folders are optional: without
the themes folder only the built-in Default theme is offered, and without the schedules
folder only Weekday Yearly is.

The window has three parts:

- **Left:** the **More translations** dropdown (when you've added XML bibles), the
  translation toggle (AV / ESV / NASB / NIV), Old/New Testament, the books, and the
  chapters of the current book.
- **Middle:** the text, with the current book and chapter in the bar at the top.
- **Right:** the schedule: the schedule picker, weeks or sections, and the readings.

The gear in the bottom-right corner opens **Settings**.

---

## Reading

**Two ways of loading text:**

- **From the schedule:** click a row to load that day's readings, and only those, in
  order, starting with the first. Click one reading in the row to start at that one.
  **Today** (or **Next** for a checklist) goes to the current day.
- **From the navigation on the left:** click a book or chapter to read around it. A few
  chapters are loaded at a time, and more load as you scroll in either direction.

While you drag the reading pane's scrollbar, nothing new loads until you let go, so the
scrollbar stays put; the wheel, keyboard and touchpad load as you go.

**Part of a chapter.** A schedule can ask for verses ("Psalm 119:33-72"). Then only those
verses are shown, with a note above them (*Verses 33–72 · show the whole chapter*).
Several parts of one chapter on the same day are combined. Browsing from the navigation
always shows whole chapters.

**The top bar** always shows the book and chapter you're reading; the matching chapter
is highlighted on the left.

**Copying.** Selected verses copy one per line with their numbers in brackets, and a
"Book N" line where a new chapter starts:

```
John 3
[16] For God so loved the world, ...
[17] For God sent not his Son ...
```

Text from the ESV, NASB or NIV ends with the translation's name, e.g. "(ESV)", as the
publishers ask; text from an XML bible ends with its name too.

**Marks in the text:**

- *Italics* are words the translators supplied (AV and NASB).
- Small capitals are used for LORD and for quotations of the Old Testament (NASB, NIV).
- A small raised **+** in the NASB marks a verb in the historical present: a past event
  told in the present tense (hover it for the explanation).

**Footnotes.** Turn on **Settings > Reading Text > Footnotes** to see the translators'
footnotes as small raised letters (*a*, *b*, *c* … through each chapter); click one to read
the note, and click anywhere else (or press Esc) to close it. They come from the ESV, NASB
and NIV, and from XML bibles that include them: among the added ones, the Berean Standard
Bible, Free Bible Version, World Messianic Bible, Brenton and LXX2012 Septuagints,
Etheridge, the Unlocked Literal Bible and a few with only a handful. The AV has none.
A verse a translation leaves out with only a note about it ("not in the earliest
manuscripts") shows up only while footnotes are on. Copied text never includes the
letters. The markers' color can be set too (**Footnote color**).

---

## Translations and API keys

| Translation | Where it comes from | Needs |
|---|---|---|
| **AV** (Authorized/King James Version) | built into the app | nothing; works offline |
| **ESV** (English Standard Version) | Crossway's ESV API | a free ESV API key |
| **NASB** (New American Standard Bible 1995) | API.Bible | a free API.Bible key |
| **NIV** (New International Version 2011) | API.Bible | the same API.Bible key |

The ESV, NASB and NIV are copyrighted, so they aren't included in the app. They're read
a chapter at a time from their publishers' services using **your own** key, which keeps
the app free to share. They need an internet connection.

### Getting keys

- **ESV:** sign in or create an account at
  [api.esv.org](https://api.esv.org/account/create-application/), create an application
  (non-commercial), and copy its key (the letters and numbers after "Token").
- **NASB and NIV:** sign up at [api.bible](https://api.bible/sign-up), create an app and
  include the NASB and NIV in it. Once the app is approved, copy its API key from your
  dashboard. One key covers both.

### Adding keys

Any of these works:

1. **Click the translation.** Without a key, the reading pane shows a page explaining
   what's needed, with a link to get a key and a box to paste it in.
2. **Settings > API keys** has a box for each key, to add, replace or remove one.
3. **A text file.** Create `Daily-Reading_keys.txt` next to `Daily-Reading.exe`:

   ```
   ESV = your ESV key
   API.Bible = your API.Bible key
   ```

   `:` works instead of `=`, a pasted `Authorization: Token ...` line counts as the ESV
   key, "NASB" or "NIV" can name the API.Bible key, and `#` starts a comment. A key in
   this file is used instead of one saved in the app (its box in Settings says so).
   Changes to the file are noticed when you switch back to the app. The file travels
   with the folder, so **leave it out when you share the app.**

A key is checked with the service before it's saved. Translations without a key are
dimmed in the toggle.

### Good to know

- **Limits.** Free plans have request limits (the ESV allows 5,000 requests a day; check
  your API.Bible dashboard for your plan). The app makes one request per chapter, so
  normal reading stays far below them.
- **Caching.** The ESV's terms allow keeping at most 500 verses, so the app keeps only a
  few hundred verses of each online translation in memory and nothing on disk.
- **Usage reporting.** API.Bible's licence requires reporting which chapters are shown
  ("FUMS"). The app does this in the background; it sends no personal information, only
  a random ID for this installation.
- **Copyright notices** for the ESV, NASB or NIV appear below the text.
- **Errors.** If a chapter can't be loaded (no connection, a key that's no longer
  accepted), the chapter says why, with **Try again** and **Show the AV instead**.

---

## More translations (XML bibles)

Any number of other translations can be added as XML files. Put them in a folder named
`Daily-Reading_bibles` next to `Daily-Reading.exe`:

```
Daily-Reading.exe
Daily-Reading_bibles/
    World English Bible.xml
    Young's Literal Translation (1898).xml
```

A **More translations** dropdown then appears above the AV / ESV / NASB / NIV buttons,
listing each bible by its file name (without `.xml`), so rename a file to change how it's
listed. Picking one shows it in the reading pane; clicking one of the four buttons goes
back. The choice is remembered like the others. Without the folder, or with no valid
bibles in it, there's no dropdown.

Bibles added, removed or renamed while the app is open show up when you switch back to
the app. If the one you're reading is removed, the app goes back to the AV.

### The file format

The files are **Zefania XML**, the format most free Bible downloads use (search for
"Zefania XML bible"). A minimal file:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<XMLBIBLE biblename="My Translation">
  <BIBLEBOOK bnumber="1" bname="Genesis">
    <CHAPTER cnumber="1">
      <VERS vnumber="1">In the beginning God created the heaven and the earth.</VERS>
      <VERS vnumber="2">And the earth was without form, and void; ...</VERS>
    </CHAPTER>
  </BIBLEBOOK>
  <BIBLEBOOK bnumber="19" bname="Psalms">
    <CHAPTER cnumber="3">
      <CAPTION vref="1">A Psalm of David, when he fled from Absalom his son.</CAPTION>
      <VERS vnumber="1">LORD, how are they increased that trouble me! ...</VERS>
    </CHAPTER>
  </BIBLEBOOK>
</XMLBIBLE>
```

- **Books** are identified by `bnumber`, in the usual order: 1 = Genesis, 39 = Malachi,
  40 = Matthew, 66 = Revelation. `bname` is optional and can be in any language. Books
  numbered above 66 (the Apocrypha) are ignored.
- **Chapters** (`cnumber`) and **verses** (`vnumber`) are numbered from 1.
- **Missing books or chapters** are fine: a bible with only the New Testament, say, shows
  "*… doesn't include Genesis*" where those chapters would be.
- **Inside a verse:** `<STYLE fs="italic">` (or `css="font-style:italic"`) shows in
  italics, `<STYLE fs="divineName">` in small capitals; footnotes (`<NOTE>…</NOTE>`, placed
  where the marker belongs) are shown when Footnotes is on, except cross-references
  (`<NOTE type="crossReference">`);
  any other markup is ignored and its text kept.
- **`<CAPTION vref="1">`** (a psalm's title) is shown at the start of that verse.
- **`<INFORMATION><rights>…</rights></INFORMATION>`**, if present, is shown below the
  text as the copyright notice.
- Tag names can be upper or lower case. Save the file as UTF-8 (or UTF-16).

A file is listed if it ends in `.xml` and starts with `<XMLBIBLE>` and `<BIBLEBOOK>`;
the rest is read the first time you pick it (under a second for a whole Bible). If it
turns out to be broken, the chapter says what's wrong.

**Making your own** from another source means producing that structure: one
`BIBLEBOOK` per book with its number, one `CHAPTER` per chapter and one `VERS` per verse.
Remember to escape `&` as `&amp;` and `<` as `&lt;` in the text.

**Converting from other formats.** `tools/make_xml_bible.py` (needs Python) converts the
two most common free formats:

- **USFM**, e.g. the "USFM" zip from [ebible.org](https://ebible.org) (unzip it first);
- **SWORD modules** from [crosswire.org](https://www.crosswire.org/sword/modules/)
  (the unzipped folder with `mods.d` and `modules` in it).

```
python tools/make_xml_bible.py engbsb_usfm "Daily-Reading_bibles\Berean Standard Bible.xml" --name "Berean Standard Bible" --rights "Public domain."
```

It keeps the verses, psalm titles, italics, small capitals and footnotes, and leaves out
cross-references, section headings and Strong's numbers. `--rights` sets the line shown
below the text; for translations whose licence asks for a credit (Creative Commons ones,
for example), put the copyright and licence there. `--drop-hebrew-numbers` removes notes
like "(3-2)" that some Jewish translations put in the text to give the Hebrew verse
number. Run `python tools/make_xml_bible.py --help` for the rest.

### Bibles with different numbering

Some translations number chapters and verses differently from the KJV: the Septuagint
and the Latin Vulgate number most psalms one lower (their Psalm 22 is the KJV's 23),
the Septuagint orders Jeremiah 25–51 and Exodus 35–40 differently, and so on. The app
navigates, follows schedules and switches translations by the KJV's numbers, so such a
bible would show the wrong passage. `tools/renumber_xml_bible.py` fixes that:

```
python tools/renumber_xml_bible.py --check Daily-Reading_bibles
python tools/renumber_xml_bible.py "Daily-Reading_bibles\Some Bible.xml"
```

The first lists which bibles (and books) need it; the second renumbers one (the original
is copied to `backups\` first). It finds where each verse belongs by matching its
wording against the AV, keeping runs of verses together, and only changes the books
that need it. Each verse keeps its own number as `orig="22:1"`.

In the app, a renumbered chapter shows the translation's **own** numbers: a note under
the heading (*Psalm 22 in this translation*), the verse numbers in the margin, and
"115:1" where its own chapter changes partway through (the KJV's Psalm 116 is the
Vulgate's 114 and 115). Hover a verse number to see both. The top bar, navigation and
schedules keep using the KJV's numbers, so switching translations stays on the same
passage. Copied text uses the translation's own numbers.

Verses with no KJV counterpart are left out and listed when renumbering: the Greek
additions to Esther and Daniel in Catholic Bibles, Psalm 151 in the Septuagint. In the
Septuagint's Exodus 35–40, which is shorter and arranged differently, some KJV verses
stay empty and a few may sit a verse or two away from where they belong.

**Copyright.** Many Bibles available as XML are copyrighted and meant for personal use.
`Daily-Reading_bibles` is never copied into the built app or `Daily-Reading.zip`, so
think twice before handing the folder to someone else.

---

## Schedules

Pick a schedule from the dropdown at the top of the Schedule panel. The built-in
**Weekday Yearly** schedule is always there; any `.md` file in the
`Daily-Reading_schedules` folder is another schedule. The dropdown groups them:

- **Follows the calendar:** picks the reading from today's date.
- **Seasons and set dates:** starts on a particular day.
- **Checklists (at your own pace):** goes to the first day you haven't ticked off.

### Included schedules

| Schedule | Kind | What it is |
|---|---|---|
| Weekday Yearly (built in) | calendar | the whole Bible on weekdays over a year: Old Testament, Psalm and New Testament columns |
| Anglican Psalter | calendar (monthly) | the 1662 Prayer Book's psalms for morning and evening, by day of the month |
| Bible in a Year | calendar (yearly) | cover to cover, 3–4 chapters a day, by date |
| Chronological Bible in a Year | calendar (yearly) | the books in roughly the order their events happened |
| New Testament on Weekdays | calendar (weekly) | a chapter each weekday for a year |
| Old Testament on Weekdays | calendar (weekly) | 3–4 chapters each weekday for a year |
| Proverbs a Day | calendar (monthly) | chapter N on day N of the month |
| Advent | season | December 1–25: from the first promises to the birth of Jesus |
| Lent with Luke | season | Ash Wednesday to Easter through Luke's Gospel |
| Holy Week | season | Palm Sunday to Easter through the Gospel accounts |
| Bible in 90 Days | checklist | about 13 chapters a day |
| Gospels in 40 Days | checklist | Matthew to John |
| Horner's Ten Lists | checklist | a chapter from each of ten lists every day |
| New Testament in 90 Days | checklist | about 3 chapters a day |
| Paul's Letters in 30 Days | checklist | Romans to Philemon, by letter |
| Psalm 119 in 22 Days | checklist | one 8-verse section (one Hebrew letter) a day |
| Psalms and Proverbs in a Month | checklist | five psalms and a chapter of Proverbs a day |
| Psalms of Ascent | checklist | Psalms 120–134 |
| Wisdom Books in 12 Weeks | checklist | Job to Song of Solomon |
| Old / New Testament / Whole Bible Checklist | checklist | every chapter, one per row |

### Checkboxes

Schedules can have checkboxes, either a **Done** column (one per day) or one before each
reading in a cell. Tick them in the app or in a text editor; they're saved **in the
schedule file itself**, so progress goes wherever the file goes. A day with a checkbox
per reading counts as done when all of them are ticked. Checkable schedules show your
progress ("12 of 40 read"), and finished weeks or sections are marked.

**Mark all read / Clear** next to the progress does the whole plan at once, and the same
links beside each week's or section's heading do just that part (handy for starting a
plan over). When more than one day would change, the link asks you to click again to
confirm.

When you tick a box, the app changes just that one character in the file, and only if
that line of the file still matches what the app shows; if the file was edited
elsewhere in the meantime, it reloads instead and asks you to try again. Changes made in
a text editor show up when you switch back to the app.

### Writing your own

A schedule is a Markdown file: an optional settings block, then tables of readings.

```markdown
---
name: My Plan
mode: checklist
---
## Week 1
| Done | Day | Reading                    |
|------|-----|----------------------------|
| [ ]  | 1   | Genesis 1-3                |
| [ ]  | 2   | Genesis 4-5; Psalm 1       |
| [x]  | 3   | Matthew 5:1-16, 43-48      |
```

**Settings** (all optional):

| Setting | Values |
|---|---|
| `name` | the name in the dropdown (otherwise the first `# Title`, or the file name) |
| `mode` | see below |
| `start` | for `dated`: when the first reading is (see below) |
| `days` | for `dated`: `weekdays` (Monday–Friday; Saturday shows Friday's reading, Sunday Monday's) or `daily` |

**Modes:**

| Mode | How today's reading is chosen |
|---|---|
| `weekly` | like Weekday Yearly: `## Week N` is week N of the year; a week's 5 rows are Monday–Friday (7 rows: Sunday–Saturday) |
| `monthly` | row N is day N of the month; later days repeat the last row |
| `yearly` | row N is day N of the year; February 29 repeats February 28 |
| `dated` | the first row is the `start` date, then one row per day or weekday |
| `checklist` | the first day that isn't ticked off |

Without a `mode`, a schedule with a `start` is `dated`, one with checkboxes is a
`checklist`, and anything else is `weekly`.

**Start dates** (`dated` mode):

- a date: `2027-01-04`
- the same day every year: `12-01`, `Dec 1`
- a day worked out from Easter each year: `Ash Wednesday`, `Palm Sunday`,
  `Maundy Thursday`, `Good Friday`, `Easter`, `Ascension`, `Pentecost`, `Trinity Sunday`
- the first Sunday of Advent: `Advent Sunday`
- any of these plus or minus days: `Easter-7`, `Pentecost+1`

A yearly start uses the season that's under way or coming next. Before it starts the
panel says "Begins …" (showing the first reading); during it, "Day N of M".

**Layout.** `##` headings divide a schedule into weeks (`## Week 3`), months, books or
any sections you like; the panel shows them as buttons. Leave the headings out for one
long list. A table's first row is its column headings. A column of day numbers or dates
is fine: it's shown as labels.

**References.** These become links:

| Written | Reads |
|---|---|
| `Genesis 1`, `Genesis 1-3` | chapters |
| `Psalm 23, 24, 27` | several chapters of one book |
| `Jude`, `Lamentations` | a whole book |
| `1 Cor 13`, `Ps 119`, `Jn 3`, `Gen. 1`, `I Samuel 3`, `Song of Songs 2` | common abbreviations and forms |
| `John 3:16-21` | verses of one chapter |
| `John 3:16, 18-20` | after a verse, plain numbers are more verses of that chapter |
| `Genesis 1:26-2:3` | across chapters |
| `Jude 3-4` | in a one-chapter book, numbers are verses (`Jude 1` is the whole book) |

Separate readings with `;`. Anything that can't be read is listed under
"⚠ problems in this schedule" (hover it for details) rather than being linked to the
wrong place. `Phil` is Philippians (use `Phm` for Philemon), `Jn` is John and `Jon` is
Jonah.

**Checkboxes.** `[ ]` or `[x]` (or `[X]`). A column headed `Done`, `✓`, `Read` and the
like, or one containing only checkboxes, gives one checkbox per day.

**Comments.** Text between `<!--` and `-->` is ignored, so a file can explain itself.

Files can be saved as UTF-8 (recommended), UTF-16 or ANSI; the app keeps whichever
encoding and line endings the file has.

---

## Settings

Open Settings with the gear in the bottom-right corner. Every setting has a ↺ button to
go back to the theme's value, and **Reset to theme defaults** resets them all.

| Section | Settings |
|---|---|
| **Appearance** | Theme; **Save current look as theme…** |
| **API keys** | the ESV key and the NASB/NIV key (hover the heading for the keys-file option) |
| **Reading Text** | font, size (12–32 px), line spacing (1–3), verse spacing (0–3 em), chapter spacing (0.5–8 em), text width (36–140 characters), footnotes (hidden or shown) and their color |
| **Verse Numbers** | style (in the margin, superscript, or hidden), size, horizontal and vertical position, color, font |
| **Book & Chapter** | book name color, chapter number color, and one font for both (in the text and the top bar) |
| **Colors** | background, text, strong text, accent, text on accent, links, book list, chapter list, schedule, buttons, borders, scrollbar |
| **More colors** | hovers, the translation toggle, control borders, muted and faint text, link underline, the schedule table and today's row, scrollbar hover and track, and whether built-in controls (dropdowns, pickers) are drawn light or dark |
| **Interface** | UI scale (75–160%, applied when you let go of the slider) and UI font |

Colors in the other sections (verse numbers, book, chapter) choose from the main colors:
Text, Strong text, Accent or Links. In **More colors**, anything you haven't set follows
the main colors when you change those (for example, the accent's hover shade follows the
accent).

Settings are kept between launches and apply on top of whichever theme is chosen.

**Reset** (at the bottom of Settings) has two buttons; each asks you to click again to
confirm:

- **Reset all settings** puts *everything* back to the defaults: the look, the theme, the
  translation and the schedule (it deletes `Daily-Reading_settings.json` and reloads).
  Ticked boxes in schedules and your API keys are kept. **Reset to theme defaults**, above
  it, only resets the look.
- **Delete app data** deletes the `Daily-Reading` folder in `%APPDATA%`: API keys you
  saved in the app (keys in `Daily-Reading_keys.txt` aren't touched), the random ID used
  for API.Bible's usage reporting, and settings, if they had to be kept there. Nothing in
  the app folder is touched. Use it before passing on a computer, or to start over.

---

## Themes

Each `.css` file in `Daily-Reading_themes` is a theme; the **Default** theme is built in.
27 themes are included.

**Making one:** adjust Settings until it looks right, then **Save current look as
theme…** and give it a name. Everything a theme can set can be set in Settings, so a
saved theme is complete. Saving with an existing theme's name asks before replacing it.

**By hand:** a theme is a CSS file like this (the `Theme:` line names it):

```css
/*
 * Theme: My Theme
 */
:root {
  --bg-main: #f6f1ea;
  --text-main: #222222;
  --accent: #5c4f42;
  --font-text: Georgia, "Times New Roman", serif;
  --text-size: 18px;
}
```

Anything a theme leaves out comes from the Default theme. The easiest way to see every
setting is to open a saved theme or one of the included ones. A theme file added to the
folder appears in the list when you switch back to the app.

---

## Where things are saved

| What | Where |
|---|---|
| Settings, theme, translation and schedule | `Daily-Reading_settings.json` in the app folder |
| Schedule progress (checkmarks) | inside each schedule's `.md` file |
| Saved themes | `Daily-Reading_themes` in the app folder |
| API keys in a file | `Daily-Reading_keys.txt` in the app folder (used first if present) |
| API keys entered in the app | `%APPDATA%\Daily-Reading\config.json` (on this computer only) |
| XML bibles | `Daily-Reading_bibles` in the app folder (added by you) |

So the app folder carries everything except keys entered in the app, which stay on the
computer; that way giving someone the folder never gives away your keys by accident.
**Settings > Reset > Delete app data** removes the `%APPDATA%\Daily-Reading` folder.
If the app folder can't be written to (installed in Program Files, for example),
settings are saved in `%APPDATA%\Daily-Reading\settings.json` instead.

---

## Building from source

Requires Windows, Python 3, and:

```
pip install pywebview pyinstaller
```

**Files:**

| File | Purpose |
|---|---|
| `av.md` | the Authorized Version text (`### Book`, `#### Chapter N`, `[N] verse`; `*word*` for italics) |
| `schedule.md` | the built-in Weekday Yearly schedule |
| `template.html` | the whole interface (HTML, CSS and JavaScript) |
| `build.py` | builds `index.html` from the template, the AV text and the built-in schedule |
| `app.py` | the desktop app (pywebview): themes, API keys, online text, schedule files |
| `bible_api.py` | the ESV API and API.Bible: keys, fetching chapters, usage reporting |
| `schedules.py` | listing and reading schedule files, and saving checkmarks |
| `local_bibles.py` | listing and reading the XML bibles in `Daily-Reading_bibles` |
| `make_exe.py` | builds the portable `Daily-Reading` folder (see below) |
| `Daily-Reading_themes/`, `Daily-Reading_schedules/` | the themes and schedules (edit these, not the copies in the built `Daily-Reading` folder) |
| `tools/make_schedules.py` | regenerates the included schedules from `av.md`'s chapter and verse counts (only its own files) |
| `tools/make_xml_bible.py` | converts a USFM folder or SWORD module into an XML bible for `Daily-Reading_bibles` |
| `tools/renumber_xml_bible.py` | puts an XML bible with different numbering (Septuagint, Vulgate) under the KJV's numbers, keeping its own |
| `tools/dev_server.py` | runs the page in an ordinary browser with the app's real Python code, on test copies |
| `tools/test_schedules.py`, `tools/test_make_exe.py` | tests for saving checkmarks and for the build's copy/backup steps |
| `tools/check_versification.py` | compares verse numbering of the online translations with the AV (needs keys) |

**Run without building the exe:**

```
python build.py
python app.py
```

**Build the exe:**

```
python make_exe.py
```

This rebuilds `index.html` and builds the portable `Daily-Reading` folder next to
`make_exe.py`: the exe and `_internal` (PyInstaller), the themes and schedules (exact
copies of the project's), this README and the LICENSE. It also makes
`Daily-Reading.zip` of that folder, without your settings, keys and XML bibles, ready
to share. Close the app first.

- The project's `Daily-Reading_bibles` folder is **not** copied into the build (many
  XML bibles are copyrighted). When running from source (`python app.py`) the app uses
  it directly.
- Your own files in the `Daily-Reading` folder (`Daily-Reading_settings.json`,
  `Daily-Reading_keys.txt`, a `Daily-Reading_bibles` folder you put there, anything
  else) are kept.
- If a theme or schedule there has changes the project doesn't (a theme saved, or boxes
  ticked, while using the built app), it's backed up to `backups\<date-time>\` first and
  listed, so you can copy it into the project.
- PyInstaller's working files and `.spec` go to a temporary folder, and `__pycache__`
  folders are removed afterwards, so nothing else is left in the project folder.

The app is built as a folder rather than a single exe: it starts in a second or two
(a single-file exe unpacks itself every time it runs) and antivirus programs trust it more.
`_internal` holds what the exe runs: Python, the libraries (pywebview and the .NET bridge
it uses for WebView2), the app's code, the page and the icon.

---

## Known limitations

- **Overnight.** If the app is left open past midnight and you're still on the day it
  last showed, it moves to the new day when you come back to the window (or after
  10 minutes of not using it). If you've moved elsewhere, it leaves you there.
- **Verse numbering.** The ESV and NIV leave out some verses the AV has (e.g.
  Matthew 17:21, Acts 8:37), and the NASB and NIV split 3 John 14 into 14–15. Those
  numbers are simply missing or extra; your place is kept at the nearest verse. XML
  bibles with a different numbering are placed under the KJV's numbers (see
  [Bibles with different numbering](#bibles-with-different-numbering)); verse ranges in
  schedules always use the AV's numbers.
- **A schedule open in a text editor.** If a schedule has unsaved edits in an editor and
  you tick boxes in the app, saving in the editor afterwards undoes those ticks.
- **Synced or read-only folders.** If OneDrive (or similar) is syncing a schedule, or the
  folder is read-only, saving a checkmark can fail; the app says so and you can retry.
- **Renaming a schedule file** makes the app fall back to Weekday Yearly once (schedules
  are remembered by file name); pick it again from the dropdown.
- **Weekly schedules around New Year** keep the week numbering of the year that's ending
  until the first full week of the new year.
- **Online translations** need a connection; the AV always works offline.

---

Licensed under the GNU General Public License v3; see [LICENSE](LICENSE).
