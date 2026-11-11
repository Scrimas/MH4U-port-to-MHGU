"""name_em068_01.py : Tidal Najarala's name -> data file section NAME (gen/NAME-ui.sec, tools/portdata.py).

  name_em068_01.py           write the section

monsterName_<lang>.gmd entry k = registry index k, but entry 137 already starts the GMD's second list, so ported indexes take
an unused 'dummyN' entry, which module/items.c renames in the loaded GMD and the name_index hook returns for index 146 (and for a
save slot she leases, module/save.c). The first list's 7 dummies (105..111) are taken: hers is the second list's dummy7, entry
227 (a string past GU's 268 would not do: the Notes detail page reads the entry as a byte, 0x5b2298, C). Names = 4U emName[93] per
language.
Chinese (chT, chS): lang/zh_TW.toml / zh_CN.toml [monsters], added by portdata.pack (4U has none).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/tidal_najarala
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, gmd, portdata
from items4u import LANGS, msg4u

NAME, EM4U = 'tidal_najarala', 93


def main():
    entry = alloc.monster(NAME)['name_entry']
    rom = RomFS(paths.GU_ROMFS)
    names = []
    for lang in LANGS:
        s0 = gmd.gmd_strings(rom.read('/nativeNX/%s/GUI/06_msg/monsterName_%s.gmd' % (lang, lang)))
        assert s0[entry] == 'dummy%d' % (entry - 220), (lang, s0[entry])
        n = msg4u(lang)['emName'][EM4U]
        assert n and '\0' not in n and '\n' not in n, (lang, n)
        names.append(n)
    sec = portdata.name_section(NAME, entry, names, rom)
    print('wrote', portdata.write_section(NAME, sec, 'ui'), '(name entry %d = %s)' % (entry, ' / '.join(names)))


if __name__ == '__main__':
    main()
