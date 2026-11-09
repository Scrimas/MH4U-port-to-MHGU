#!/usr/bin/env python3
"""vendor_save.py : refresh installer/vendor/mhgu-save, the part of MHGU_Editor's save parser (app/core, crate
mhgu-save) the installer uses for save migration and cleaning.

  python3 installer/tools/vendor_save.py <MHGU_Editor checkout>

Copies MODULES verbatim from <checkout>/app/core/src (no local edits: the installer's own code is in
installer/core/src/saves.rs), writes their lib.rs and Cargo.toml, and VENDORED.toml (the editor's commit and each
file's sha256). Only modules that do not reach the editor's data tables (app/core/src/data.rs, ../data/*.csv: GU
tables, which this repo does not hold) are taken; a module that names one is refused.
"""
import hashlib, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'vendor', 'mhgu-save')
MODULES = ['save', 'items', 'equipment', 'store']      # save container, item stores, equipment box, safe writes


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = os.path.join(sys.argv[1], 'app', 'core', 'src')
    commit = subprocess.run(['git', '-C', sys.argv[1], 'rev-parse', 'HEAD'], capture_output=True, text=True,
                            check=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', sys.argv[1], 'status', '--porcelain', '--', 'app/core/src'], capture_output=True,
                           text=True, check=True).stdout.strip()
    os.makedirs(os.path.join(OUT, 'src'), exist_ok=True)
    sums = []
    for m in MODULES:
        t = open(os.path.join(src, m + '.rs'), encoding='utf-8').read()
        uses = set(re.findall(r'crate::(\w+)', t)) | set(re.findall(r'super::(\w+)', t)) - {'tests'}
        bad = sorted(u for u in uses if u not in MODULES and u not in ('Save', 'Error'))
        if bad or 'include_str!' in t or 'include_bytes!' in t:
            sys.exit('%s.rs reaches %s: not vendored (it would need the editor\'s data tables)' % (m, bad or 'a data file'))
        with open(os.path.join(OUT, 'src', m + '.rs'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(t)
        sums.append((m + '.rs', hashlib.sha256(t.encode()).hexdigest()))
    with open(os.path.join(OUT, 'src', 'lib.rs'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('//! Vendored from MHGU_Editor app/core (crate mhgu-save) by installer/tools/vendor_save.py: do not edit,\n'
                '//! refresh with that script (installer/vendor/VENDORED.toml names the commit).\n\n'
                + ''.join('pub mod %s;\n' % m for m in sorted(MODULES)) + '\npub use save::{Error, Save};\n')
    with open(os.path.join(OUT, 'Cargo.toml'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('# Vendored from MHGU_Editor app/core by installer/tools/vendor_save.py (do not edit)\n'
                '[package]\nname = "mhgu-save"\ndescription = "Read and edit Monster Hunter Generations Ultimate (Switch) '
                'saves (the part of MHGU_Editor\'s parser the installer uses)"\nversion = "0.0.0"\nedition = "2024"\n'
                'license = "GPL-3.0-or-later"\n\n[lints.rust]\ndead_code = "allow"\n')
    with open(os.path.join(OUT, '..', 'VENDORED.toml'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('# installer/vendor: copies of other projects, refreshed by installer/tools/vendor_save.py\n'
                '[mhgu-save]\nfrom = "https://github.com/Scrimas/MHGU-Save-editor app/core/src"\ncommit = "%s"%s\n'
                'files = [\n%s]\n' % (commit, '\nuncommitted = true   # the checkout had local changes' if dirty else '',
                                       ''.join('    ["%s", "%s"],\n' % s for s in sums)))
    print('vendored %s from %s%s' % (', '.join(MODULES), commit[:12], ' (with local changes)' if dirty else ''))


if __name__ == '__main__':
    main()
