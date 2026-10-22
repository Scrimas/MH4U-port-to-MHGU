"""name_em090.py : Dalamadur's and Shah Dalamadur's names -> data file sections NAME (gen/NAME-ui.sec of the two
head entries, tools/portdata.py; as tools of Tigerstripe: name_em067_01.py).

  name_em090.py           write the sections

monsterName_<lang>.gmd entry k = registry index k, but entry 137 already starts the GMD's second list, so ported
indexes take an unused 'dummyN' entry (allocations.toml name_entry), which module/items.c renames in the loaded GMD.
The tail halves share their head's entry (companions). Names = 4U emName[24] / [110] per language (C).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/dalamadur
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, gmd, portdata
from items4u import LANGS, msg4u

ENTRIES = {'dalamadur': 24, 'shah_dalamadur': 110}


def main():
    rom = RomFS(paths.GU_ROMFS)
    s0 = {lang: gmd.gmd_strings(rom.read('/nativeNX/%s/GUI/06_msg/monsterName_%s.gmd' % (lang, lang)))
          for lang in LANGS}
    for name, em4 in ENTRIES.items():
        entry = alloc.monster(name)['name_entry']
        names = []
        for lang in LANGS:
            assert s0[lang][entry] == 'dummy%d' % (entry - 104), (lang, s0[lang][entry])
            n = msg4u(lang)['emName'][em4]
            assert n and '\0' not in n and '\n' not in n, (lang, n)
            names.append(n)
        sec = portdata.Section('NAME')
        sec.u32(entry)
        for n in names: sec.str(n)
        print('wrote', portdata.write_section(name, sec, 'ui'), '(name entry %d = %s)' % (entry, ' / '.join(names)))


if __name__ == '__main__':
    main()
