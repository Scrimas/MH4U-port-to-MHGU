#!/usr/bin/env python3
"""i18n.py : keep the installer's translation catalogs in step with its source (modelled on MHGU_Editor's
tools/i18n.py). Pure stdlib plus GNU gettext (msginit, msgmerge, msgattrib, msgfmt).

  python3 installer/tools/i18n.py           extract the strings, write the template, merge every catalog
  python3 installer/tools/i18n.py --check   fail when the template is out of date or a catalog is invalid; print how
                                            much of each catalog is translated

Strings come from installer/gui/ui/**.slint (@tr("text")) and installer/{gui,core}/src/**.rs (tr("text"),
trf("text", ...)). Writes installer/gui/lang/mhgu-de-installer.pot and gui/lang/<code>/LC_MESSAGES/mhgu-de-installer.po
(the codes of gui/src/i18n.rs LANGS). A new catalog starts empty; an entry left untranslated shows in English.
"""
import os, re, subprocess, sys, tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
LANG = os.path.join(ROOT, 'gui', 'lang')
DOMAIN = 'mhgu-de-installer'
POT = os.path.join(LANG, DOMAIN + '.pot')
PLURALS = {
    'fr': 'nplurals=2; plural=(n > 1);',
    'de': 'nplurals=2; plural=(n != 1);',
    'es': 'nplurals=2; plural=(n != 1);',
    'it': 'nplurals=2; plural=(n != 1);',
    'zh_TW': 'nplurals=1; plural=0;',
    'zh_CN': 'nplurals=1; plural=0;',
}
STR = r'"((?:[^"\\]|\\.)*)"'


def unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c != '\\':
            out.append(c); i += 1; continue
        n = s[i + 1]
        if n == 'n': out.append('\n'); i += 2
        elif n == 't': out.append('\t'); i += 2
        elif n == 'u':
            j = s.index('}', i); out.append(chr(int(s[i + 3:j], 16))); i = j + 1
        elif n == '\n':
            i += 2
            while i < len(s) and s[i] in ' \t\n': i += 1
        else: out.append(n); i += 2
    return ''.join(out)


def files(top, ext):
    for d, _, fs in sorted(os.walk(top)):
        for f in sorted(fs):
            if f.endswith(ext): yield os.path.join(d, f)


def extract():
    """[(msgid, [file])] in order of first use"""
    found = {}
    def add(s, path):
        found.setdefault(s, set()).add(os.path.relpath(path, ROOT).replace(os.sep, '/'))
    for p in files(os.path.join(ROOT, 'gui', 'ui'), '.slint'):
        t = open(p, encoding='utf-8').read()
        for m in re.finditer(r'@tr\(\s*' + STR, t):
            add(unescape(m.group(1)), p)
    for top in (os.path.join(ROOT, 'core', 'src'), os.path.join(ROOT, 'gui', 'src')):
        for p in files(top, '.rs'):
            t = open(p, encoding='utf-8').read()
            for m in re.finditer(r'\btrf?\(\s*' + STR, t):
                add(unescape(m.group(1)), p)
            for m in re.finditer(r'\btrn\(\s*' + STR + r'\s*,\s*' + STR, t):   # trn("one", "many", n): both
                add(unescape(m.group(1)), p)
                add(unescape(m.group(2)), p)
    return list(found.items())


def po_str(s):
    s = s.replace('\\', '\\\\').replace('"', '\\"').replace('\t', '\\t')
    if '\n' not in s:
        return '"%s"' % s
    parts = s.split('\n')
    return '""\n' + '\n'.join('"%s\\n"' % p for p in parts[:-1]) + ('\n"%s"' % parts[-1] if parts[-1] else '')


def template(entries):
    out = ['# Strings of the MHGU Definitive Edition Installer, extracted by installer/tools/i18n.py.',
           'msgid ""', 'msgstr ""',
           '"Project-Id-Version: %s\\n"' % DOMAIN,
           '"PO-Revision-Date: 2026-11-09 00:00+0000\\n"',
           '"Content-Type: text/plain; charset=UTF-8\\n"',
           '"Content-Transfer-Encoding: 8bit\\n"', '']
    for s, locs in entries:
        out.append('#: ' + ' '.join(sorted(locs)))
        if '{' in s:
            out.append('#. placeholders: {} in order, {0} {1} by position')
        out += ['msgid ' + po_str(s), 'msgstr ""', '']
    return '\n'.join(out)


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.exit('%s failed:\n%s' % (a[0], r.stderr))
    return r.stderr


def set_plural(po, code):
    t = open(po, encoding='utf-8').read()
    hdr = '"Plural-Forms: %s\\n"' % PLURALS[code]
    if '"Plural-Forms:' in t:
        t = re.sub(r'"Plural-Forms:[^\n]*', lambda _: hdr, t, count=1)
    else:
        t = t.replace('"Content-Transfer-Encoding: 8bit\\n"', '"Content-Transfer-Encoding: 8bit\\n"\n' + hdr, 1)
    open(po, 'w', encoding='utf-8').write(t)


def main(check):
    pot = template(extract())
    if check:
        old = open(POT, encoding='utf-8').read() if os.path.exists(POT) else ''
        if old != pot:
            sys.exit('installer/gui/lang/%s.pot is out of date: run installer/tools/i18n.py' % DOMAIN)
    else:
        os.makedirs(LANG, exist_ok=True)
        open(POT, 'w', encoding='utf-8').write(pot)
    for code in PLURALS:
        po = os.path.join(LANG, code, 'LC_MESSAGES', DOMAIN + '.po')
        if not check:
            if os.path.exists(po):
                run('msgmerge', '--quiet', '--update', '--backup=none', '--no-fuzzy-matching', '--no-wrap',
                    '--add-location=file', po, POT)
                run('msgattrib', '--no-obsolete', '--no-wrap', '-o', po, po)
            else:
                os.makedirs(os.path.dirname(po), exist_ok=True)
                run('msginit', '--no-translator', '--no-wrap', '-l', code + '.UTF-8', '-i', POT, '-o', po)
            set_plural(po, code)
        with tempfile.TemporaryDirectory() as d:
            stats = run('msgfmt', '--check', '--statistics', '-o', os.path.join(d, 'x.mo'), po).strip()
        print('%-6s %s' % (code, stats))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a not in ([], ['--check']): sys.exit(__doc__)
    main(a == ['--check'])
