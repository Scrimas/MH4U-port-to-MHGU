"""name_em057_01.py : Stygian Zinogre's name -> data file section NAME (gen/NAME-ui.sec, tools/portdata.py).

  name_em057_01.py           write the section

monsterName_<lang>.gmd entry k = registry index k, but entry 137 already starts the GMD's second list, so ported
indexes take an unused 'dummyN' entry (allocations.toml name_entry: 110 = 'dummy6', = the save slot, whose ID the
quest result's size record names), which module/items.c renames in the loaded GMD and the name_index hook returns for
index 143. Names = 4U emName[49] per language.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/stygian_zinogre
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, gmd, portdata
from items4u import LANGS, msg4u

NAME, EM4U = 'stygian_zinogre', 49


def main():
    entry = alloc.monster(NAME)['name_entry']
    rom = RomFS(paths.GU_ROMFS)
    names = []
    for lang in LANGS:
        s0 = gmd.gmd_strings(rom.read('/nativeNX/%s/GUI/06_msg/monsterName_%s.gmd' % (lang, lang)))
        assert s0[entry] == 'dummy%d' % (entry - 104), (lang, s0[entry])
        n = msg4u(lang)['emName'][EM4U]
        assert n and '\0' not in n and '\n' not in n, (lang, n)
        names.append(n)
    sec = portdata.Section('NAME')
    sec.u32(entry)
    for n in names: sec.str(n)
    print('wrote', portdata.write_section(NAME, sec, 'ui'), '(name entry %d = %s)' % (entry, ' / '.join(names)))


if __name__ == '__main__':
    main()
