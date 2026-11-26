"""Online Bible texts: the ESV (Crossway's ESV API) and the NASB and NIV (API.Bible).

Nothing copyrighted ships with the app. Each user enters their own API keys (on the page
shown for a translation without a key, or Settings > API keys); they're saved in
%APPDATA%\\Daily-Reading\\config.json, never in the program, so the .exe can be shared.
A Daily-Reading_keys.txt next to the .exe, if present, supplies keys too and wins. Chapters are fetched as they're shown, and the
page keeps only the few it needs (the ESV API allows caching at most 500 verses).
"""
import html
import json
import os
import re
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "Daily-Reading"
TIMEOUT = 20

ESV_URL = "https://api.esv.org/v3/passage/text/"
ESV_NOTICE = ("Scripture quotations marked “ESV” are from the ESV® Bible (The Holy Bible, English "
              "Standard Version®), © 2001 by Crossway, a publishing ministry of Good News Publishers. "
              "Used by permission. All rights reserved. ESV Text Edition: 2016. esv.org")

API_BIBLE_URL = "https://rest.api.bible/v1"
FUMS_URL = "https://fums.api.bible/f3"
# Translation id -> API.Bible Bible id
API_BIBLE_IDS = {
    "nasb": "b8ee27bcd1cae43a-01",   # New American Standard Bible 1995
    "niv": "78a9f6124f344018-01",    # New International Version 2011
}
ONLINE = {"esv": "esv", "nasb": "apibible", "niv": "apibible"}   # translation -> key it needs


# ---- settings file -------------------------------------------------------------------

def config_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Daily-Reading", "config.json")


def load_config():
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(data):
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


KEYS_FILE_NAME = "Daily-Reading_keys.txt"


def read_keys_file(path):
    """Keys from Daily-Reading_keys.txt (next to the .exe), one per line, e.g.

        ESV = 0123456789abcdef...
        API.Bible = AbCdEf...

    Names are forgiving: "esv" (or a pasted "Authorization: Token ..." line) is the ESV
    key; "api.bible", "apibible", "nasb" or "niv" is the API.Bible key. "#" starts a comment.
    Returns {"esv": key, "apibible": key} for the keys found."""
    keys = {}
    if not path:
        return keys
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except OSError:
        return keys
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if re.match(r"^authorization\s*:", line, re.I):
            name, value = "esv", line
        else:
            m = re.match(r"^([A-Za-z. _-]+?)\s*[:=]\s*(.+)$", line)
            if not m:
                continue
            name, value = m.group(1).lower().replace(" ", ""), m.group(2)
        kind = "esv" if "esv" in name else "apibible" if any(s in name for s in ("bible", "nasb", "niv")) else None
        key = clean_key(kind, value) if kind else None
        if kind and key:
            keys[kind] = key
    return keys


def clean_key(kind, key):
    """Accept a key as pasted, e.g. "Authorization: Token abc123" for the ESV."""
    key = str(key or "").strip()
    if kind == "esv":
        key = re.sub(r"^(authorization\s*:\s*)?(token\s+)?", "", key, flags=re.I).strip()
    return key if re.fullmatch(r"[A-Za-z0-9_\-]{8,128}", key) else ("" if not key else None)


# ---- HTTP ----------------------------------------------------------------------------

class FetchError(Exception):
    pass


def http_get(url, headers, what):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise FetchError(f"Your key for {what} wasn't accepted, or doesn't include this translation.")
        if e.code == 404:
            raise FetchError(f"This chapter wasn't found at {what}.")
        if e.code == 429:
            raise FetchError(f"Too many requests to {what} for now; try again in a minute.")
        raise FetchError(f"Something went wrong at {what} (error {e.code}).")
    except (urllib.error.URLError, TimeoutError, OSError):
        raise FetchError(f"Couldn't reach {what}. Check the internet connection.")
    except ValueError:
        raise FetchError(f"The reply from {what} couldn't be read.")


def tidy(text):
    return re.sub(r"\s+", " ", text).strip()


# ---- ESV -----------------------------------------------------------------------------

def esv_query(key, q):
    params = urllib.parse.urlencode({
        "q": q,
        "include-passage-references": "false",
        "include-verse-numbers": "true",
        "include-first-verse-numbers": "true",
        "include-footnotes": "true",
        "include-footnote-body": "true",
        "include-headings": "false",
        "include-short-copyright": "false",
        "include-copyright": "false",
        "include-passage-horizontal-lines": "false",
        "include-heading-horizontal-lines": "false",
        "include-selahs": "true",
        "indent-poetry": "false",
    })
    return http_get(f"{ESV_URL}?{params}", {"Authorization": f"Token {key}"}, "the ESV API")


# One-chapter books: the ESV API reads "Jude 1" as verse 1, so these are asked for by name.
ONE_CHAPTER_BOOKS = {"obadiah", "philemon", "2 john", "3 john", "jude"}


def esv_chapter(key, book_name, chapter):
    one = book_name.strip().lower() in ONE_CHAPTER_BOOKS and int(chapter) == 1
    data = esv_query(key, book_name if one else f"{book_name} {chapter}")
    passages = data.get("passages") or []
    parsed = data.get("parsed") or []
    if not passages or not parsed:
        raise FetchError("The ESV API didn't find this chapter.")
    # Verse ids are BBCCCVVV; make sure we got the chapter we asked for.
    if (parsed[0][0] // 1000) % 1000 != int(chapter):
        raise FetchError("The ESV API returned a different chapter.")
    body, notes = esv_footnotes(passages[0])
    parts = re.split(r"\[(\d+)\]", body)
    lead = tidy(parts[0])          # a psalm's title ("A Psalm of David."), shown with verse 1
    verses = []
    for i in range(1, len(parts), 2):
        text = tidy(parts[i + 1])
        if not verses and lead:
            text = f"{lead} {text}"
        verses.append([int(parts[i]), esv_markers(html.escape(text, quote=False), notes)])
    return {"verses": verses, "copyright": ESV_NOTICE}


ESV_MARKER = re.compile(r"\((\d{1,3})\)")


def esv_footnotes(passage):
    """Split the ESV's text into the passage and its footnotes. The text marks each note
    "(1)" where it applies; with include-footnote-body the notes follow under "Footnotes",
    one per paragraph: "(1) 1:5 Or has not understood it". Returns (text, {"1": note})."""
    m = re.search(r"\n\s*Footnotes\s*\n", passage)
    if not m:
        return passage, {}
    notes = {}
    for n, text in re.findall(r"\((\d{1,3})\)\s*(.*?)(?=\n\s*\(\d{1,3}\)|\Z)", passage[m.end():], re.S):
        text = re.sub(r"^\d+:\d+(?:[-–]\d+)?\s*", "", tidy(text))      # the verse it belongs to
        text = text.replace("*", "")                                   # italics, if marked
        if text:
            notes[n] = text
    return passage[:m.start()], notes


def esv_markers(text, notes):
    """Replace "(1)" in a verse with a footnote marker; markers without a note go."""
    def marker(m):
        note = notes.get(m.group(1))
        return footnote_marker(note) if note else ""
    return ESV_MARKER.sub(marker, text) if notes else ESV_MARKER.sub("", text) if re.search(r"\(\d{1,3}\)", text) else text


def footnote_marker(text):
    """The page shows a footnote as a small marker that opens the note (local_bibles.py
    makes the same marker for the XML bibles)."""
    return f'<sup class="fn" data-note="{html.escape(text, quote=True)}"></sup>'


# ---- API.Bible -----------------------------------------------------------------------

HISTORICAL_PRESENT = ('<span class="hist-present" title="Historical present: a past event '
                      'told in the present tense">+</span>')
ITALIC_STYLES = {"it", "add"}         # supplied words
SMALL_CAP_STYLES = {"sc", "nd"}         # small caps; nd = the divine name (LORD)
PSALM_LABEL = re.compile(r"^(psalm|book)\s+[\w]+$", re.I)


def render_items(items, out_verses, current, in_title, title_parts):
    """Walk API.Bible's JSON content, appending HTML to the verse each text belongs to."""
    for node in items:
        if node.get("type") == "text":
            text = html.escape(node.get("text", ""), quote=False)
            vid = (node.get("attrs") or {}).get("verseId")
            if vid:
                v = int(vid.split(".")[-1])
                out_verses.setdefault(v, []).append(text)
                current[0] = v
            elif in_title:
                title_parts.append(text)
            continue
        if node.get("type") != "tag":
            continue
        name, style = node.get("name"), (node.get("attrs") or {}).get("style", "")
        if name == "note":
            # A footnote (style "f"/"fe"; "x" is a cross-reference, left out), in the verse
            # it was in: the reference it starts with ("fr") is dropped.
            if style in ("f", "fe", "ef") and current[0] is not None and not in_title:
                text = note_text(node)
                if text:
                    out_verses.setdefault(current[0], []).append(footnote_marker(text))
            continue
        if name == "verse":
            continue                                   # the number itself
        if name == "char" and (style in ITALIC_STYLES or style in SMALL_CAP_STYLES):
            open_tag, close_tag = ("<em>", "</em>") if style in ITALIC_STYLES else ('<span class="sc">', "</span>")
            sub_verses, sub_title = {}, []
            render_items(node.get("items", []), sub_verses, current, in_title, sub_title)
            for v, parts in sub_verses.items():
                out_verses.setdefault(v, []).append(open_tag + "".join(parts) + close_tag)
            if sub_title:
                title_parts.append(open_tag + "".join(sub_title) + close_tag)
            continue
        render_items(node.get("items", []), out_verses, current, in_title, title_parts)


def note_text(node):
    """A footnote's text, without its reference ("1:5") or its caller."""
    def walk(n):
        if n.get("type") == "text":
            return n.get("text", "")
        if (n.get("attrs") or {}).get("style") in ("fr", "xo", "fv"):
            return " "
        return "".join(walk(c) for c in n.get("items") or [])
    try:
        return tidy(walk({"items": node.get("items") or []}))
    except (AttributeError, TypeError):
        return ""


def plain_text(node):
    if node.get("type") == "text":
        return node.get("text", "")
    return tidy("".join(plain_text(n) for n in node.get("items") or []))


def api_bible_chapter(key, translation, usfm, chapter):
    bible_id = API_BIBLE_IDS[translation]
    params = urllib.parse.urlencode({
        "content-type": "json", "include-notes": "true", "include-titles": "true",
        "include-chapter-numbers": "false", "include-verse-numbers": "true", "include-verse-spans": "false",
    })
    data = http_get(f"{API_BIBLE_URL}/bibles/{bible_id}/chapters/{usfm}.{int(chapter)}?{params}",
                    {"api-key": key}, "API.Bible")
    body = data.get("data") or {}
    verses, current, title = {}, [None], []
    for para in body.get("content") or []:
        style = (para.get("attrs") or {}).get("style", "")
        if style == "qa":
            continue      # Psalm 119's acrostic letters ("Aleph"): headings, not verse text
        before_first_verse = not verses
        # A psalm's title (before verse 1) is kept and shown with verse 1, as in the AV.
        is_title = before_first_verse and (style == "d" or (
            usfm == "PSA" and style == "ms" and not PSALM_LABEL.match(plain_text(para))))
        parts_before = {v: len(p) for v, p in verses.items()}
        render_items(para.get("items") or [], verses, current, is_title, title)
        if is_title:
            title.append(" ")
        # Lines of poetry are separate paragraphs; keep a space between them.
        for v, p in verses.items():
            if parts_before.get(v, 0) and len(p) > parts_before[v]:
                p.insert(parts_before[v], " ")
    if not verses:
        raise FetchError("API.Bible returned no verses for this chapter.")
    out = []
    for i, v in enumerate(sorted(verses)):
        text = tidy("".join(verses[v]))
        if i == 0 and tidy("".join(title)):
            text = f"{tidy(''.join(title))} {text}"
        if translation == "nasb":
            # The NASB marks verbs in the historical present with "*" ("*said"); shown as "+".
            # (not inside tags: a footnote marker carries its note in an attribute)
            text = re.sub(r"(<[^>]*>)|\*(?=\w)", lambda m: m.group(1) or HISTORICAL_PRESENT, text)
        out.append([v, text])
    return {"verses": out, "copyright": tidy(body.get("copyright", "")),
            "fumsToken": (data.get("meta") or {}).get("fumsToken")}


# ---- FUMS (API.Bible's usage reporting, required by its licence) ---------------------

def report_fums(tokens, device_id, session_id):
    tokens = [t for t in tokens if isinstance(t, str) and re.fullmatch(r"[A-Za-z0-9_\-=.]{10,2000}", t)]
    if not tokens:
        return
    query = urllib.parse.urlencode([("t", t) for t in tokens] +
                                   [("dId", device_id), ("sId", session_id), ("uId", device_id)])

    def send():
        try:
            req = urllib.request.Request(f"{FUMS_URL}?{query}", headers={"User-Agent": USER_AGENT})
            urllib.request.urlopen(req, timeout=TIMEOUT).close()
        except Exception:
            pass   # reporting must never get in the way of reading

    threading.Thread(target=send, daemon=True).start()


# ---- what the page calls -------------------------------------------------------------

class OnlineBibles:
    def __init__(self, keys_file=None):
        self._lock = threading.Lock()
        self.session_id = secrets.token_hex(16)
        self.keys_file = keys_file   # Daily-Reading_keys.txt next to the .exe; its keys win

    def _key(self, kind, cfg=None):
        """(key, from_file): the keys file is read each time, so edits apply without a restart."""
        file_key = read_keys_file(self.keys_file).get(kind)
        if file_key:
            return file_key, True
        cfg = cfg if cfg is not None else self._config()
        return cfg.get("esvKey" if kind == "esv" else "apiBibleKey"), False

    def _config(self):
        with self._lock:
            return load_config()

    def _device_id(self):
        """The random ID API.Bible's usage reporting asks for, made (and saved) the first
        time it's needed, so just looking at keys never creates the AppData folder."""
        with self._lock:
            cfg = load_config()
            if not cfg.get("deviceId"):
                cfg["deviceId"] = secrets.token_hex(16)
                try:
                    save_config(cfg)
                except OSError:
                    pass
            return cfg["deviceId"]

    def status(self):
        """Which keys are available (never the keys themselves), and which come from the file."""
        cfg = self._config()
        file_keys = read_keys_file(self.keys_file)
        return {
            "esv": bool(file_keys.get("esv") or cfg.get("esvKey")),
            "apibible": bool(file_keys.get("apibible") or cfg.get("apiBibleKey")),
            "fromFile": {"esv": "esv" in file_keys, "apibible": "apibible" in file_keys},
        }

    def set_key(self, kind, key):
        """Save (or with an empty key, remove) a key after checking it works.
        Returns {"ok", "message", "status"}."""
        if kind not in ("esv", "apibible"):
            return {"ok": False, "message": "Unknown key type."}
        if read_keys_file(self.keys_file).get(kind):
            return {"ok": False, "status": self.status(),
                    "message": f"This key comes from {KEYS_FILE_NAME} next to the app; edit or delete that file to change it."}
        key = clean_key(kind, key)
        if key is None:
            return {"ok": False, "message": "That doesn't look like an API key."}
        field = "esvKey" if kind == "esv" else "apiBibleKey"
        if key:
            try:
                if kind == "esv":
                    esv_query(key, "John 11:35")
                    message = "ESV key saved."
                else:
                    available, errors = [], []
                    for tr, bible_id in API_BIBLE_IDS.items():
                        try:
                            http_get(f"{API_BIBLE_URL}/bibles/{bible_id}", {"api-key": key}, "API.Bible")
                            available.append(tr.upper())
                        except FetchError as err:
                            errors.append(str(err))
                    if not available:
                        raise FetchError(errors[0] if errors else "API.Bible didn't accept that key.")
                    message = f"API.Bible key saved ({' and '.join(available)} available)."
            except FetchError as err:
                return {"ok": False, "message": str(err), "status": self.status()}
        else:
            message = "Key removed."
        with self._lock:
            cfg = load_config()
            if key:
                cfg[field] = key
            else:
                cfg.pop(field, None)
            try:
                save_config(cfg)
            except OSError as err:
                return {"ok": False, "message": f"Couldn't save the key: {err.strerror or err}"}
        return {"ok": True, "message": message, "status": self.status()}

    def get_chapter(self, translation, usfm, book_name, chapter):
        """{"ok": True, "verses": [[n, html], ...], "copyright", "fumsToken"?} or
        {"ok": False, "error", "needsKey"?}."""
        kind = ONLINE.get(translation)
        if not kind or not re.fullmatch(r"[1-3A-Z]{3}", str(usfm)) or not str(chapter).isdigit():
            return {"ok": False, "error": "Unknown translation or chapter."}
        key, _ = self._key(kind)
        if not key:
            return {"ok": False, "needsKey": True,
                    "error": f"Add your {'ESV API' if kind == 'esv' else 'API.Bible'} key in Settings."}
        try:
            if kind == "esv":
                result = esv_chapter(key, str(book_name), int(chapter))
            else:
                result = api_bible_chapter(key, translation, usfm, int(chapter))
        except FetchError as err:
            return {"ok": False, "error": str(err)}
        return {"ok": True, **result}

    def report_fums(self, tokens):
        if isinstance(tokens, list) and tokens:
            report_fums(tokens[:50], self._device_id(), self.session_id)
        return True
