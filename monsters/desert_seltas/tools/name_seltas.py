"""name_seltas.py : Desert Seltas' and Desert Seltas Queen's names -> data file section NAME of each entry (gen/[<entry>/]NAME-ui.sec, tools/portdata.py).

  name_seltas.py           write the sections

monsterName_<lang>.gmd entry k = registry index k, but entry 137 already starts the GMD's second list, so ported indexes take an unused 'dummyN'
entry, which module/items.c renames in the loaded GMD and the name_index hook returns for the registry index (and for a save slot it leases,
module/save.c). Theirs are the second list's dummy5 (225) and dummy4 (224) (a string past GU's 268 would not do: the Notes detail page reads the entry
as a byte, 0x5b2298, C). Names = 4U emName[94] / [95] per language.
Chinese (chT, chS): lang/zh_TW.toml / zh_CN.toml [monsters], added by portdata.pack (4U has none).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/desert_seltas
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import paths
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS
import alloc, gmd, portdata
from items4u import LANGS, msg4u

ENTRIES = {'desert_seltas': 94, 'desert_seltas_queen': 95}


def main():
    rom = RomFS(paths.GU_ROMFS)
    for name, em4u in ENTRIES.items():
        entry = alloc.monster(name)['name_entry']
        names = []
        for lang in LANGS:
            s0 = gmd.gmd_strings(rom.read('/nativeNX/%s/GUI/06_msg/monsterName_%s.gmd' % (lang, lang)))
            assert s0[entry] == 'dummy%d' % (entry - 220), (lang, s0[entry])
            n = msg4u(lang)['emName'][em4u]
            assert n and '\0' not in n and '\n' not in n, (lang, n)
            names.append(n)
        sec = portdata.name_section(name, entry, names, rom)
        print('wrote', portdata.write_section(name, sec, 'ui'), '(name entry %d = %s)' % (entry, ' / '.join(names)))


if __name__ == '__main__':
    main()
