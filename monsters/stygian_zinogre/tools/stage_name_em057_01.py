"""stage_name_em057_01.py : the board name of Heaven's Mount -> data file section TXTA (gen/*-stagename.sec,
tools/portdata.py). His stage-24 quests (m10607 m10930 m11010) run on the alias of the Ruined Pinnacle
(allocations.toml stage_alias), and GU's boards name a quest's stage from its stage number (questMessage 116 "Ruined
Pinnacle"); module/stage_alias.c shows this string instead for them (allocations.toml [monster.append] stage_name).

  stage_name_em057_01.py          write the section
  stage_name_em057_01.py show     print it only

Text = 4U's own board name, mapName[5] of core_common (index k -> stage m0k; eng "H. Mount", the abbreviated form 4U
shows, as GU's "V. Hollow"; 4U ships no longer name) (C).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MON = os.path.dirname(HERE)                         # monsters/stygian_zinogre
ROOT = os.path.dirname(os.path.dirname(MON))
sys.path.insert(0, os.path.join(ROOT, 'tools'))     # core converters + paths.py
import alloc, portdata                              # noqa: E402
from items4u import LANGS, msg4u, gu_text           # noqa: E402

NAME = 'stygian_zinogre'
STAGE_4U = 5                                        # Heaven's Mount = 4U m05
GU_QUEST_MESSAGE = 120                              # module/build.py: GU's questMessage strings


def main():
    assert alloc.monster(NAME).get('append', {}).get('stage_name') == 1, 'allocations.toml stage_name = 1'
    base = GU_QUEST_MESSAGE + alloc.offset(NAME, 'stage_name')
    sec = portdata.txta([('questMessage', base, [[gu_text(msg4u(lang)['mapName'][STAGE_4U])] for lang in LANGS])])
    if sys.argv[1:] == ['show']:
        print(sec.tag, portdata.decode(sec.tag, sec.bytes()))
        return
    print('wrote', portdata.write_section(NAME, sec, 'stagename'))


if __name__ == '__main__':
    main()
