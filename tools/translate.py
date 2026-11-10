"""translate.py : the mod's own translations, lang/<code>.toml, for the text 4U cannot give (4U has no Chinese).

  translate.py check [CODE ...]       every key the data files and quests need: missing, stale (its English changed
                                      since it was translated) and unused ones, characters GU's own text of that
                                      language never uses (its font may lack them); exit 1 on a missing or stale key
  translate.py worksheet CODE [FILE]  a local sheet for a translator (default dump/translate/<code>.json, never
                                      committed: it holds the English): each distinct English string once, with
                                      what it is, the keys that use it and its current translation
  translate.py apply CODE [FILE]      the filled sheet -> lang/<code>.toml [text] / [items] / [quests] (every key
                                      of a string, with its source hash)

lang/<code>.toml (codes: installer/gui/src/i18n.rs LANGS) holds only translations, keyed by stable IDs, never the
English or 4U text they translate:
  [monsters]  <allocations.toml entry> = "<name>"              (data file NAME)
  [maps]      <map package> = { board = "<board name>", full = "<full name>" }   board: the quest board's name (the
              installer shows it); English, French, German, Italian and Spanish take theirs from 4U, so their files
              hold only `full` (unused for now)
  [text]      "<GMD>.<string index>" = { text = "...", en = "<hash>" }   data file TXTA strings (gear, skills, Notes,
              itemData, the stage name)
  [items]     "<GU item ID>.name" / ".desc" = { text, en }    data file ITEM records
  [quests]    "<quest ID>.<field>" = { text, en }             questData GMDs (fields: QUEST_FIELDS)
`en` = the first 8 hex digits of the English string's SHA-1 when it was translated: a changed English string makes
the key stale. Line breaks are GU's \\r\\n, written "\\r\\n" in TOML. The data file languages chT / chS come from
zh_TW / zh_CN (portdata.py ZH, packed by portdata.pack); a key a file lacks shows English.
"""
import glob, hashlib, json, os, struct, sys, tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths

ROOT = paths.ROOT
LANG_DIR = os.path.join(ROOT, 'lang')
GAME = {'zh_TW': 'chT', 'zh_CN': 'chS'}     # translated code -> GU text language (portdata.ZH order)
QUEST_FIELDS = ('title', 'client', 'desc', 'other', 'obj', 'fail', 'sub')   # questData GMD string order
_CACHE = {}


def src_hash(en):
    return hashlib.sha1(en.encode('utf-8')).hexdigest()[:8]


def load(code):
    """lang/<code>.toml as a dict (empty without the file)"""
    if code not in _CACHE:
        p = os.path.join(LANG_DIR, code + '.toml')
        _CACHE[code] = tomllib.load(open(p, 'rb')) if os.path.exists(p) else {}
    return _CACHE[code]


def text(code, table, key, en=None):
    """the translation of key in [table] (a plain string or {text, en}), None without one"""
    v = load(code).get(table, {}).get(key)
    if isinstance(v, dict):
        v = v.get('text')
    return v or None


def game_text(lang, table, key, en, missing=None):
    """the string of GU language lang (chT / chS) for key: its translation, else the English (key added to missing)"""
    code = {v: k for k, v in GAME.items()}[lang]
    t = text(code, table, key)
    if t is None and missing is not None:
        missing.append('%s [%s] %s' % (code, table, key))
    return t if t is not None else en


# ---- the keys the mod needs ----
def needed():
    """[(table, key, English)] of every string the data files and quests carry (their source sections and arcs)"""
    import alloc, portdata
    out = []
    for m in alloc.monsters():
        e = m['name']
        d = portdata.sec_dir(e)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not f.endswith('.sec'):
                continue
            b = open(os.path.join(d, f), 'rb').read()
            tag, body = b[:4].decode(), b[4:]
            if tag == 'NAME':
                out.append(('monsters', e, portdata.decode(tag, body)['name'][0]))
            elif tag == 'TXTA':
                for t in portdata.decode(tag, body):
                    for i, en in enumerate(t['text'][0]):
                        if en: out.append(('text', '%s.%d' % (t['gmd'], t['base'] + i), en))
            elif tag == 'ITEM':
                for gu, name, desc in item_texts(body, 0):
                    out += [('items', '%d.name' % gu, name), ('items', '%d.desc' % gu, desc)]
    seen, uniq = set(), []
    for t, k, en in out + quest_texts():
        if (t, k) not in seen:
            seen.add((t, k))
            uniq.append((t, k, en))
    return uniq


def item_texts(body, lang):
    """[(GU item ID, name, description)] of an ITEM section in language index lang"""
    n = struct.unpack_from('<I', body, 0)[0]
    base = 4 + 20 * n
    s = lambda k: (lambda o: body[o:body.index(b'\0', o)].decode())(struct.unpack_from('<I', body, base + 4 * k)[0])
    return [(struct.unpack_from('<H', body, 4 + 20 * i)[0], s(2 * (lang * n + i)), s(2 * (lang * n + i) + 1))
            for i in range(n)]


def quest_texts():
    """[('quests', '<ID>.<field>', English)] of every shipped quest arc's English questData GMD"""
    sys.path.insert(0, paths.GU_PY)
    import gmd
    from arc import arc_entries, arc_read
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'monsters', '*', 'romfs', 'nativeNX', 'loc', 'arc', 'quest', 'q*.arc'))):
        d = open(p, 'rb').read()
        for e in arc_entries(d):
            if e[0].startswith('eng\\quest\\questData\\questData_'):
                qid = int(e[0].rsplit('_', 2)[-2])
                for f, en in zip(QUEST_FIELDS, gmd.gmd_strings(arc_read(d, e))):
                    if en: out.append(('quests', '%d.%s' % (qid, f), en))
    return out


# ---- checks ----
_GU_CHARS = {}


def gu_chars(lang):
    """every character GU's own text of lang (chT / chS) uses (resident arc GMDs)"""
    if lang not in _GU_CHARS:
        import portdata
        sys.path.insert(0, paths.GU_PY)
        from romfs import RomFS
        _GU_CHARS[lang] = portdata.zh_text(RomFS(paths.GU_ROMFS), lang)[1]
    return _GU_CHARS[lang]


def check(codes=None):
    """{code: {'missing': [...], 'stale': [...], 'unused': [...], 'glyphs': [...]}}"""
    need = needed()
    out = {}
    for code in codes or sorted(GAME):
        tr = load(code)
        r = dict(missing=[], stale=[], unused=[], glyphs=[])
        keys = set()
        for table, key, en in need:
            keys.add((table, key))
            v = tr.get(table, {}).get(key)
            if v is None:
                r['missing'].append('[%s] %s' % (table, key))
            elif isinstance(v, dict) and v.get('en') and v['en'] != src_hash(en):
                r['stale'].append('[%s] %s' % (table, key))
        for table in ('text', 'items', 'quests', 'monsters'):
            r['unused'] += ['[%s] %s' % (table, k) for k in tr.get(table, {}) if (table, k) not in keys]
        if code in GAME:
            chars = gu_chars(GAME[code])
            for table, vals in tr.items():
                for k, v in vals.items():
                    s = ''.join(x for f, x in v.items() if f != 'en') if isinstance(v, dict) else v
                    bad = sorted(c for c in set(s) - chars if not c.isascii())
                    if bad: r['glyphs'].append('[%s] %s: %s' % (table, k, ''.join(bad)))
        out[code] = r
    return out


def kind(table, key):
    """what a key is, for the translator: the GMD or table and the field"""
    if table == 'text':
        return key.rsplit('.', 1)[0]
    return '%s %s' % (table, key.rsplit('.', 1)[-1]) if table in ('items', 'quests') else table


def worksheet(code, path=None):
    """dump/translate/<code>.json: one entry per distinct English string {id, kind, en, keys, text} (text = the
    current translation, '' without); a translator fills `text`, then `apply` writes lang/<code>.toml"""
    path = path or os.path.join(ROOT, 'dump', 'translate', code + '.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    groups = {}
    for table, key, en in needed():
        if table == 'monsters':
            continue                                  # names: hand-kept with their sources in lang/<code>.toml
        g = groups.setdefault((kind(table, key), en), dict(kind=kind(table, key), en=en, keys=[], text=''))
        g['keys'].append('%s:%s' % (table, key))
        g['text'] = g['text'] or text(code, table, key) or ''
    out = [dict(id=i, **g) for i, g in enumerate(groups.values())]
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return path, len(out), sum(1 for g in out if g['text'])


def toml_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\r', '\\r').replace('\n', '\\n') + '"'


def apply(code, sheet):
    """lang/<code>.toml [text] / [items] / [quests] from a filled worksheet (entries without text are left out); the
    file's head, [monsters] and [maps] are kept as they are"""
    en = {(table, key): e for table, key, e in needed()}
    vals = {}
    for g in json.load(open(sheet, encoding='utf-8')):
        if not g.get('text'):
            continue
        for k in g['keys']:
            table, key = k.split(':', 1)
            if (table, key) in en:
                vals.setdefault(table, {})[key] = g['text']
    p = os.path.join(LANG_DIR, code + '.toml')
    head = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
    for table in TRANSLATED:                          # drop the generated tables, keep the rest verbatim
        i = head.find('\n[%s]' % table)
        if i >= 0:
            j = head.find('\n[', i + 1)
            head = head[:i] + (head[j:] if j >= 0 else '\n')
    body = head.rstrip('\n') + '\n'
    for table in TRANSLATED:
        if table not in vals:
            continue
        body += '\n[%s]                     # generated by tools/translate.py apply: edit there or here, keep `en`\n' % table
        for key in sorted(vals[table], key=sort_key):
            body += '%s = { text = %s, en = "%s" }\n' % (toml_str(key), toml_str(vals[table][key]), src_hash(en[table, key]))
    tomllib.loads(body)
    open(p, 'w', encoding='utf-8').write(body)
    _CACHE.pop(code, None)
    return p, sum(len(v) for v in vals.values())


TRANSLATED = ('text', 'items', 'quests')


def sort_key(k):
    a, b = k.rsplit('.', 1)
    return (a, int(b)) if b.isdigit() else (a, b)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['worksheet'] and len(a) >= 2:
        print('wrote %s: %d strings, %d translated' % worksheet(a[1], a[2] if len(a) > 2 else None))
    elif a[:1] == ['apply'] and len(a) >= 2:
        print('wrote %s: %d keys' % apply(a[1], a[2] if len(a) > 2 else os.path.join(ROOT, 'dump', 'translate', a[1] + '.json')))
    elif a[:1] == ['check']:
        bad = 0
        for code, r in check(a[1:] or None).items():
            print('%s: %d missing, %d stale, %d unused, %d with unseen glyphs' % (
                code, len(r['missing']), len(r['stale']), len(r['unused']), len(r['glyphs'])))
            for k in ('stale', 'unused', 'glyphs'):
                for x in r[k][:20]: print('  %s %s' % (k, x))
            bad += len(r['missing']) + len(r['stale'])
        sys.exit(1 if bad else 0)
    else:
        sys.exit(__doc__)
