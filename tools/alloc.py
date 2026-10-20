"""alloc.py : the central ID registry (allocations.toml at the repo root) of every ported monster.

  alloc.py               check: values inside their pools, no two monsters overlap, registry order consistent
  alloc.py show          print every monster's allocations
  alloc.py header OUT    write the C header (module/build.py writes module/out/alloc.h)

  import alloc
  m = alloc.monster('gogmazios')         # dict of its allocations (allocations.toml [[monster]])
  alloc.offset('gogmazios', 'kireaji')   # records the monsters before it append to that table (0 for the first)
"""
import os, struct, sys, tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths

TOML = os.path.join(paths.ROOT, 'allocations.toml')
GU_PAIRS, GU_COUNT = 0x1597EA4, 137      # GU registry (id, index) pairs (module/build.py REG_TABLES)
RANGES = ('file_ids', 'items', 'decorations')           # [first, last] per monster
LISTS = ('quests', 'quest_slots', 'bgm_ids')            # explicit values per monster
SCALARS = ('save_index', 'name_entry', 'ui_icon')       # one value per monster, unique
ORDERED = ('registry_index', 'notes_entry')             # consecutive in [[monster]] order


def load(path=TOML):
    with open(path, 'rb') as f:
        return tomllib.load(f)


def monsters(reg=None):
    return (reg or load())['monster']


def monster(name, reg=None):
    for m in monsters(reg):
        if m['name'] == name: return m
    raise KeyError('no monster %r in allocations.toml' % name)


def offset(name, table, sub=None, reg=None):
    """records the monsters listed before `name` append to `table` (weapons: sub = 'w00'..)"""
    n = 0
    for m in monsters(reg):
        if m['name'] == name: return n
        a = m.get('append', {}).get(table, 0)
        n += a.get(sub, 0) if isinstance(a, dict) else a
    raise KeyError(name)


def values(m, key):
    v = m.get(key)
    if v is None: return []
    if key in RANGES: return list(range(v[0], v[1] + 1))
    return list(v) if isinstance(v, list) else [v]


def check(reg=None, gu_main=paths.GU_MAIN):
    reg = reg or load()
    pools, ms, errs = reg['pools'], reg['monster'], []
    seen = {}
    for k, m in enumerate(ms):
        for key in ('name', 'em_id', 'registry_index'):
            if key not in m: errs.append('%s: missing %s' % (m.get('name', k), key))
        for key in ORDERED:
            if key in m and m[key] != pools[key][0] + k:
                errs.append('%s: %s %d, expected %d (consecutive in [[monster]] order)' %
                            (m['name'], key, m[key], pools[key][0] + k))
        for key in RANGES + LISTS + SCALARS + ORDERED:
            taken = {}
            for v in values(m, key):
                lo, hi = (pools[key][0], pools[key][-1]) if key not in ('quests', 'quest_slots') else (None, None)
                if key in ('quests', 'quest_slots') and v not in pools[key]:
                    errs.append('%s: %s %d not in the pool %s' % (m['name'], key, v, pools[key]))
                elif lo is not None and not lo <= v <= hi:
                    errs.append('%s: %s %#x outside the pool [%#x, %#x]' % (m['name'], key, v, lo, hi))
                if (key, v) in seen: taken.setdefault(seen[key, v], []).append(v)
                seen[key, v] = m['name']
            for other, vs in taken.items():
                errs.append('%s: %s %#x..%#x (%d values) already taken by %s' % (m['name'], key, vs[0], vs[-1],
                                                                                  len(vs), other))
        em = m.get('em_id', 0) & 0xff
        if not pools['em_number'][0] <= em <= pools['em_number'][1] and m.get('em_id', 0) >> 8 == 0:
            errs.append('%s: em number %d is a GU monster (variant 0)' % (m['name'], em))
        for key, v in (('em_id', m.get('em_id')), ('stage folder', (m.get('stage_alias') or [0, None])[1])):
            if v is None: continue
            if (key, v) in seen: errs.append('%s: %s %#x already taken by %s' % (m['name'], key, v, seen[key, v]))
            seen[key, v] = m['name']
        sa = m.get('stage_alias')
        if sa and not pools['stage_folder'][0] <= sa[1] <= pools['stage_folder'][1]:
            errs.append('%s: stage folder %d outside the pool' % (m['name'], sa[1]))
        for key, models in (('armor model', m.get('armor_models', [])),
                            *(('w%s model' % c[1:], [v]) for c, v in m.get('weapon_models', {}).items())):
            for v in models:
                if (key, v) in seen and seen[key, v] != m['name']:
                    errs.append('%s: %s %d already taken by %s' % (m['name'], key, v, seen[key, v]))
                seen[key, v] = m['name']
        if len(m.get('quest_slots', [])) != len(m.get('quests', [])):
            errs.append('%s: one quest_slot per quest' % m['name'])
    if gu_main and os.path.exists(gu_main):        # the em IDs must be free in GU's own registry
        img = open(gu_main, 'rb').read()
        gu_ids = {struct.unpack_from('<I', img, GU_PAIRS + 8 * i)[0] for i in range(GU_COUNT)}
        for m in ms:
            if m.get('em_id') in gu_ids: errs.append('%s: em_id %#x is a GU monster' % (m['name'], m['em_id']))
    return errs


def header(reg=None):
    """C defines: <NAME>_<KEY> per monster, plus PORT_MONSTER_COUNT"""
    reg = reg or load()
    out = ['/* alloc.h: generated by tools/alloc.py from allocations.toml -- do not edit */', '#pragma once',
           '#define PORT_MONSTER_COUNT %du' % len(reg['monster'])]
    for m in reg['monster']:
        p = m['name'].upper()
        d = [('EM_ID', '0x%xu' % m['em_id']), ('INDEX', '%du' % m['registry_index'])]
        for key, c in (('donor_index', 'DONOR_INDEX'), ('save_index', 'SAVE_INDEX'), ('name_entry', 'NAME_ENTRY'),
                       ('ui_icon', 'UI_ICON'), ('mapicon_class', 'MAPICON'), ('notes_entry', 'NOTES_ENTRY')):
            if key in m: d.append((c, '%du' % m[key]))
        if 'standin_id' in m: d.append(('STANDIN_ID', '0x%xu' % m['standin_id']))
        if 'save_index' in m: d.append(('SAVE_ID', '0x%xu' % (0x1064 + m['save_index'] - 105)))
        if 'file_ids' in m: d += [('FILE_ID_FIRST', '0x%xu' % m['file_ids'][0]), ('FILE_ID_LAST', '0x%xu' % m['file_ids'][1])]
        for key, c in (('items', 'ITEM'), ('decorations', 'DECO')):
            if key in m: d += [(c + '_FIRST', '%du' % m[key][0]), (c + '_LAST', '%du' % m[key][1])]
        for key, c, f in (('quests', 'QUEST', '%du'), ('quest_slots', 'QUEST_SLOT', '%du'), ('bgm_ids', 'BGM_ID', '0x%xu')):
            for i, v in enumerate(m.get(key, [])): d.append(('%s%d' % (c, i), f % v))
        if 'stage_alias' in m: d += [('STAGE_FROM', '%du' % m['stage_alias'][0]), ('STAGE_FOLDER', '%du' % m['stage_alias'][1])]
        out.append('/* %s */' % m.get('title', m['name']))
        out += ['#define %s_%s %s' % (p, k, v) for k, v in d]
    return '\n'.join(out) + '\n'


def show(reg=None):
    for m in monsters(reg):
        print('%s (%s)' % (m['name'], m.get('title', '')))
        for k, v in m.items():
            if k in ('name', 'title'): continue
            print('  %-15s %s' % (k, ', '.join('%#x' % x if k in ('em_id', 'standin_id', 'file_ids', 'bgm_ids')
                                               else str(x) for x in v) if isinstance(v, list) else v))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['show']:
        show()
    elif a[:1] == ['header']:
        open(a[1], 'w').write(header())
    else:
        errs = check()
        for e in errs: print('ERROR', e)
        print('%d monster(s), %s' % (len(monsters()), 'OK' if not errs else '%d error(s)' % len(errs)))
        sys.exit(1 if errs else 0)
