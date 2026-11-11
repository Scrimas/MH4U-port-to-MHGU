"""fonts.py : the installer's fallback fonts into installer/gui/assets/fonts/. On a Linux system without fontconfig, or
whose fontconfig has no font, the window takes them (gui/src/fonts.rs; packaging/build.py puts them in the AppImage):
  Inter.ttf             Latin, Greek, Cyrillic, punctuation, arrows, and the installer's characters it has
                        (Inter 4.1, optical size pinned at 14 as Slint's own copy)
  NotoSansSymbols.ttf   the installer's symbols that Inter lacks (the gear)
  NotoSansSC.ttf        the zh_CN catalog's characters that Inter lacks, and the sources' (the language list's names)
  NotoSansTC.ttf        the same for zh_TW
  Inter-OFL.txt, NotoSansSymbols-OFL.txt, NotoSansCJK-OFL.txt   their licences (SIL Open Font License 1.1)
Each font is cut to what the installer shows (fontTools' subsetter, weights kept): a few hundred KB in all. Run it
again when a translation or the window gains a character they lack (gui's test fonts::tests::every_character says
which); gui/assets/fonts/fonts.conf is not made here.

  python3 installer/packaging/fonts.py

Needs: fontTools (pip install fonttools), the network (the sources below, pinned by checksum).
"""
import hashlib, io, os, sys, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
INST = os.path.dirname(HERE)
OUT = os.path.join(INST, 'gui', 'assets', 'fonts')
GF = 'https://raw.githubusercontent.com/google/fonts/'
SOURCES = {
    'inter': ('https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip',
              '9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e'),
    'symbols': (GF + '8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/notosanssymbols/NotoSansSymbols%5Bwght%5D.ttf',
                'f7e7e04b4a24b6c78893d50cbfd2b2f6cae49617ab047bfef668d252adb128f7'),
    'symbols-ofl': (GF + '8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/notosanssymbols/OFL.txt',
                    'b118dd41337806a5d4797052c77caf3bd096aed783e5eb21b4d11154351e1ac0'),
    'sc': (GF + 'a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf',
           'a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da'),
    'tc': (GF + '3be1884c48c3e45b52ecc725676a08f87776373e/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf',
           '864727d210d54f2537bbe23b3a839436c3992af72de9322af5270897246bd44f'),
    'cjk-ofl': (GF + 'a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/OFL.txt',
                '1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9'),
}
# Inter keeps what it has of these whole: text the installer does not write (folder and file names) shows too
RANGES = ((0x20, 0x7e), (0xa0, 0x24f), (0x370, 0x3ff), (0x400, 0x4ff), (0x1e00, 0x1eff), (0x2000, 0x206f),
          (0x20a0, 0x20cf), (0x2190, 0x21ff), (0x2200, 0x22ff))


def chars(path):
    """The characters a file can put in the window (gui/src/fonts.rs's test reads them the same way): a catalog's
    lines but its # comments, a source file whole; no control characters."""
    text = open(path, encoding='utf-8').read()
    if path.endswith('.po'):
        text = '\n'.join(l for l in text.splitlines() if not l.startswith('#'))
    return {ord(c) for c in text if ord(c) >= 0x20 and c != '﻿'}


def sources():
    """The window's text that is not a translation: the .slint files, the gui and core Rust sources."""
    out = set()
    for d, ext in (('gui/ui', '.slint'), ('gui/src', '.rs'), ('core/src', '.rs')):
        for root, _, files in os.walk(os.path.join(INST, d)):
            for f in files:
                if f.endswith(ext):
                    out |= chars(os.path.join(root, f))
    return out


def catalogs():
    lang = os.path.join(INST, 'gui', 'lang')
    return {c: chars(os.path.join(lang, c, 'LC_MESSAGES', 'mhgu-de-installer.po')) for c in sorted(os.listdir(lang))
            if os.path.isfile(os.path.join(lang, c, 'LC_MESSAGES', 'mhgu-de-installer.po'))}


def fetch(key):
    url, sha = SOURCES[key]
    print('   ', url, flush=True)
    data = urllib.request.urlopen(url).read()
    if hashlib.sha256(data).hexdigest() != sha:
        sys.exit('%s: sha256 %s, not the pinned %s' % (url, hashlib.sha256(data).hexdigest(), sha))
    return data


def main():
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
    except ImportError:
        sys.exit('fonts.py needs fontTools (pip install fonttools)')
    def load(data, **axes):
        """The font, its weights cut to the window's (400 to 700, 400 the default: Noto Sans SC and TC start at Thin,
        their names follow) and its other axes pinned; recalcTimestamp off: the same sources and characters give the
        same files."""
        out = io.BytesIO()
        font = TTFont(io.BytesIO(data), recalcTimestamp=False)
        instancer.instantiateVariableFont(font, dict(axes, wght=(400, 400, 700)), updateFontNames=True).save(out)
        # saved and read back: the subsetter needs the tables as a file has them
        return TTFont(io.BytesIO(out.getvalue()), recalcTimestamp=False)

    inter_zip = zipfile.ZipFile(io.BytesIO(fetch('inter')))
    fonts = {'inter': load(inter_zip.read('InterVariable.ttf'), opsz=14), 'symbols': load(fetch('symbols')),
             'sc': load(fetch('sc')), 'tc': load(fetch('tc'))}
    cmap = {k: set(f.getBestCmap()) for k, f in fonts.items()}

    src, cats = sources(), catalogs()
    every = src.union(*cats.values())
    take = {'inter': {c for lo, hi in RANGES for c in range(lo, hi + 1)} | every, 'symbols': set(), 'sc': set(),
            'tc': set()}
    take['inter'] &= cmap['inter']
    rest = every - take['inter']
    # Noto Sans Symbols: what neither Chinese font has (they draw their own punctuation)
    take['symbols'] = {c for c in rest if c in cmap['symbols'] and c not in cmap['sc'] | cmap['tc']}
    rest -= take['symbols']
    missing = []
    for code, chs in cats.items():
        font = {'zh_CN': 'sc', 'zh_TW': 'tc'}.get(code)
        left = chs & rest
        if font:
            take[font] |= left & cmap[font]
            left -= cmap[font]
        missing += ['%s U+%04X %s' % (code, c, chr(c)) for c in sorted(left)]
    # the sources' own (the language list's 简体中文, 繁體中文): from whichever Chinese font has them, both if both
    for c in src & rest:
        if c not in cmap['sc'] | cmap['tc']:
            missing.append('sources U+%04X %s' % (c, chr(c)))
        take['sc' if c in cmap['sc'] else 'tc'].add(c)
        if c in cmap['sc'] and c in cmap['tc']:
            take['tc'].add(c)
    if missing:
        sys.exit('no font has:\n  ' + '\n  '.join(missing))

    os.makedirs(OUT, exist_ok=True)
    names = {'inter': 'Inter.ttf', 'symbols': 'NotoSansSymbols.ttf', 'sc': 'NotoSansSC.ttf', 'tc': 'NotoSansTC.ttf'}
    for k, font in fonts.items():
        opts = subset.Options()
        opts.hinting = False          # Slint's renderers do not use TrueType hinting
        opts.name_IDs = ['*']
        opts.name_languages = ['*']
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=sorted(take[k]))
        sub.subset(font)
        out = os.path.join(OUT, names[k])
        font.save(out)
        print('%9d %s (%d characters)' % (os.path.getsize(out), os.path.relpath(out, INST), len(take[k])))
    for name, data in (('Inter-OFL.txt', inter_zip.read('LICENSE.txt')),
                       ('NotoSansSymbols-OFL.txt', fetch('symbols-ofl')), ('NotoSansCJK-OFL.txt', fetch('cjk-ofl'))):
        with open(os.path.join(OUT, name), 'wb') as f:
            f.write(data.replace(b'\r\n', b'\n'))


if __name__ == '__main__':
    main()
