"""board_order.py : where each ported quest sits on its star board, among GU's quests (NEWSAVE_MAPREWORK.md C10).

  board_order.py show          print every ported quest's anchor (the GU quest it follows) and the rule that chose it
  board_order.py html OUT      write a preview of the boards with the ported quests in place (local review page)

  import board_order
  board_order.anchors()        # {ported quest ID: GU quest ID it follows}

GU's boards (C: GU v1.4 quest_group, 1509 entries; 0x3bab28 walks the list and 0x3bb318 puts each quest on its board)
show their quests in list order, a hand-made order in blocks: tours first, key quests, mixed hunts, multi-monster
blocks, one block of single-monster hunts, then rare species and variants, then elder dragons and final bosses. A
ported quest is appended to the list, so without an anchor it shows last. The rule, from GU's own layout:
- a quest of kind multi-monster (questData +0x10 = 5) follows the board's last multi-monster quest;
- an elder dragon's quests (its stand-in, allocations.toml standin_id, is one of Kushala Daora, Chameleos, Teostra)
  follow the board's last quest of those three, before the final bosses;
- any other quest follows the board's last regular quest of its base species (its stand-in: the closest GU monster),
  so a monster's quests stay together, in their own order; a key quest (quest_group unlock group set) is never an
  anchor: GU's progression stays as it is;
- with no such quest on the board: the end of the board's single-monster block (its longest run of regular hunts of
  one or two monsters, from 5 quests), else the end of its regular quests (before its first rare species or variant
  quest, else before its last block of elder dragons). GU placed its own later quests the same way: 10770 / 10771 and
  11472..11483 inside the single-monster blocks, 10772..10774 next to their rare species;
- allocations.toml `board_after = [[quest, GU quest], ...]` in a monster's entry overrides the rule for a quest.
Event and special lists (IDs from 20000) are not part of a board's order. Several ported quests on one anchor keep
registry order, then each monster's quest order.
"""
import html, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc, paths                                 # noqa: E402
sys.path.insert(0, paths.GU_PY)
from romfs import RomFS                             # noqa: E402
from quest4u import arc_files                       # noqa: E402

KINDS = {0: 'hunt', 1: 'slay', 2: 'capture', 3: 'gather / deliver', 4: 'other', 5: 'multi-monster'}
KIND_MULTI, KIND_GATHER, OBJ_TOUR = 5, 3, 7
ELDER_TRIO = {'Kushala Daora', 'Chameleos', 'Teostra'}
RARE = {'Silver Rathalos', 'Gold Rathian', 'Furious Rajang', 'Savage Deviljho', 'Chaotic Gore Magala'}
FINAL = ELDER_TRIO | {'Kirin', 'Lao-Shan Lung', 'Nakarkos', 'Akantor', 'Ukanlos', 'Amatsu', 'Alatreon', 'Fatalis',
                      'Crimson Fatalis', 'White Fatalis', 'Raging Brachydios'}
REGULAR_MAX = 20000                                 # board IDs: village < 10000, hub 10000..19999


def gu_names(R):
    """{GU em ID: English name} (GU's registry pairs, tools/gulib/monster-index.csv)"""
    import csv
    img = open(paths.GU_MAIN, 'rb').read()
    pairs = {}
    for i in range(alloc.GU_COUNT):
        em, idx = struct.unpack_from('<II', img, alloc.GU_PAIRS + 8 * i)
        pairs[idx] = em
    out = {}
    for row in csv.DictReader(open(os.path.join(paths.GU_PY, 'monster-index.csv'), encoding='utf-8')):
        idx = int(row['index']) - 1
        if idx in pairs: out.setdefault(pairs[idx], row['monster'])
    return out


def quest_info(qid, d, names, standins=None):
    """a questData's board fields: dict(qid, hub, star, kind, tour, bosses = [names])"""
    bosses = [struct.unpack_from('<H', d, 0x64 + 13 * k)[0] for k in range(5)]
    nm = [(standins or {}).get(b) or names.get(b, 'em%d' % b) for b in bosses if b]
    return dict(qid=qid, hub=qid >= 10000, star=d[0x12], kind=d[0x10], tour=d[0x10] == KIND_GATHER and d[0x1F] ==
                OBJ_TOUR, bosses=nm, grp=0)


def gu_boards(R, names):
    """{(hub, star): [quest_info in board order]} of GU's regular quests"""
    common = arc_files(R.read('/nativeNX/loc/arc/village/common.arc'))
    qg = [v for k, v in common.items() if k.endswith('quest_group')][0][1]
    assert struct.unpack_from('<f', qg, 0)[0] == 4.0
    boards, seen = {}, set()
    for i in range(struct.unpack_from('<I', qg, 4)[0]):
        qid, grp = struct.unpack_from('<IB', qg, 8 + 7 * i)
        if qid >= REGULAR_MAX or qid in seen: continue
        seen.add(qid)
        p = '/nativeNX/loc/arc/quest/q%07d.arc' % qid
        try: t = arc_files(R.read(p))
        except (KeyError, FileNotFoundError, OSError): continue      # a DUMMY entry: no quest file
        d = t.get('loc\\quest\\questData\\questData_%07d' % qid)
        if not d: continue
        q = quest_info(qid, d[1], names)
        q['grp'] = grp
        boards.setdefault((q['hub'], q['star']), []).append(q)
    return boards


def ported(reg, names):
    """[(monster entry, quest_info)] of every ported quest with a built questData, in registry then quest order"""
    out = []
    for m in alloc.monsters(reg):
        if m.get('companion_of'): continue
        # the boss records name stand-ins (allocations.toml standin_id / standin_alt): show the monster itself
        st = {m['standin_id']: m['title']} if m.get('standin_id') else {}
        for q in m.get('quests', []):
            p = os.path.join(paths.monster(m.get('package', m['name'])), 'romfs', 'nativeNX', 'loc', 'quest',
                             'questData', 'questData_%07d.ext' % q)
            if not os.path.exists(p): continue
            s = dict(st)
            alt = m.get('standin_alt')
            if alt and q in alt[1:]: s = {alt[0]: m['title']}   # its own boss record names the alt stand-in here
            out.append((m, quest_info(q, open(p, 'rb').read(), names, s)))
    return out


def single_block(board, least=5):
    """the board's single-monster block: its longest run of regular (no unlock group) hunts or captures of one or
    two monsters, not rare species, variants or elders; [] when shorter than `least`"""
    best, run = [], []
    for g in board:
        b = set(g['bosses'])
        if (not g['grp'] and not g['tour'] and g['kind'] != KIND_MULTI and 1 <= len(b) <= 2 and not b <= RARE
                and not b <= FINAL):
            run.append(g)
            if len(run) > len(best): best = list(run)
        else: run = []
    return best if len(best) >= least else []


def anchor_of(m, q, board, names):
    """(GU quest ID it follows, rule) for ported quest q of monster m on that board ([quest_info] in order)"""
    over = dict(map(tuple, m.get('board_after', [])))
    if q['qid'] in over:
        a = over[q['qid']]
        assert any(g['qid'] == a for g in board), (q['qid'], 'board_after %d is not on its board' % a)
        return a, 'board_after (allocations.toml)'
    base = names.get(m.get('standin_id'))
    if q['kind'] == KIND_MULTI:
        multi = [g for g in board if g['kind'] == KIND_MULTI]
        if multi: return multi[-1]['qid'], 'after the last multi-monster quest'
    if base in ELDER_TRIO:
        el = [g for g in board if g['bosses'] and set(g['bosses']) <= ELDER_TRIO]
        if el: return el[-1]['qid'], 'elder dragon: after the last Kushala Daora / Chameleos / Teostra quest'
    elif base:
        same = [g for g in board if g['bosses'] and set(g['bosses']) == {base} and not g['tour'] and not g['grp']]
        if same: return same[-1]['qid'], 'after the last %s quest (its base species)' % base
        run = single_block(board)
        if run: return run[-1]['qid'], 'no %s quest here: end of the single-monster block' % base
    for i, g in enumerate(board):
        if i and g['bosses'] and set(g['bosses']) <= RARE:
            return board[i - 1]['qid'], 'end of the regular quests: before the first rare species / variant'
    i = len(board)
    while i > 1 and board[i - 1]['bosses'] and set(board[i - 1]['bosses']) <= FINAL: i -= 1
    return board[i - 1]['qid'], 'end of the regular quests: before the last elder dragon block'


def plan(R=None, reg=None):
    """(gu boards, [(monster, quest_info, anchor, rule)]) of every ported quest with a questData"""
    R, reg = R or RomFS(paths.GU_ROMFS), reg or alloc.load()
    names = gu_names(R)
    boards = gu_boards(R, names)
    rows = []
    for m, q in ported(reg, names):
        board = boards.get((q['hub'], q['star']))
        assert board, (q['qid'], 'no GU board for star %d' % q['star'])
        a, why = anchor_of(m, q, board, names)
        rows.append((m, q, a, why))
    return boards, rows


def anchors(R=None, reg=None):
    return {q['qid']: a for _, q, a, _ in plan(R, reg)[1]}


def show():
    _, rows = plan()
    for m, q, a, why in rows:
        print('%-22s %6d %s%-2d %-16s -> after %6d  (%s)' % (m['name'], q['qid'], 'H' if q['hub'] else 'V', q['star'],
                                                            KINDS.get(q['kind'], q['kind']), a, why))


def board_title(hub, star):
    if not hub: return 'Village ★%d' % star
    return 'Hub G★%d' % (star - 10) if star > 10 else 'Hub ★%d' % star


def write_html(out):
    boards, rows = plan()
    placed = {}
    for m, q, a, why in rows: placed.setdefault((q['hub'], q['star']), {}).setdefault(a, []).append((m, q, why))
    E = html.escape
    parts = []
    for key in sorted(placed, key=lambda k: (not k[0], k[1])):
        board = boards[key]
        items = []
        for g in board:
            tag = ('tour' if g['tour'] else 'multi' if g['kind'] == KIND_MULTI else
                   'final' if g['bosses'] and set(g['bosses']) <= FINAL else
                   'rare' if g['bosses'] and set(g['bosses']) <= RARE else 'key' if g['grp'] else '')
            items.append('<li class="gu %s"><span class="id">%d</span><span class="k">%s</span><span class="m">%s</span>'
                         '%s</li>' % (tag, g['qid'], E(KINDS.get(g['kind'], str(g['kind']))), E(', '.join(g['bosses'])),
                                      '<span class="tag">%s</span>' % tag if tag else ''))
            for m, q, why in placed[key].get(g['qid'], []):
                items.append('<li class="port"><span class="id">%d</span><span class="k">%s</span><span class="m">%s'
                             '</span><span class="why">%s</span></li>' % (
                                 q['qid'], E(KINDS.get(q['kind'], str(q['kind']))), E(', '.join(q['bosses'])), E(why)))
        n = sum(len(v) for v in placed[key].values())
        parts.append('<section><h2>%s <small>%d GU quests, %d ported</small></h2><ol>%s</ol></section>' % (
            E(board_title(*key)), len(board), n, ''.join(items)))
    page = PAGE % '\n'.join(parts)
    with open(out, 'w', encoding='utf-8') as f: f.write(page)
    print('wrote', out)


PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Board order preview</title>
<style>
:root { --bg:#f7f6f3; --fg:#1d1d1b; --mute:#6b6a66; --line:#dddbd5; --port:#e6f0ff; --portline:#3d6fd1;
        --tour:#e9f5e9; --multi:#f6efe2; --final:#f4e8f4; --rare:#fff6d9; --key:#eef0f2; }
@media (prefers-color-scheme: dark) { :root { --bg:#1b1b1a; --fg:#ecebe7; --mute:#9a9893; --line:#363532;
        --port:#1f2d47; --portline:#6f9bf0; --tour:#1f2e1f; --multi:#33291b; --final:#2f2130; --rare:#332c14;
        --key:#262829; } }
body { background:var(--bg); color:var(--fg); font:14px/1.45 system-ui, sans-serif; margin:0 auto;
       max-width:980px; padding:16px; }
h1 { font-size:20px; } h2 { font-size:17px; margin:28px 0 8px; } small { color:var(--mute); font-weight:400; }
.rule { border:1px solid var(--line); border-radius:8px; padding:8px 14px; }
ol { list-style:none; padding:0; margin:0; border:1px solid var(--line); border-radius:8px; overflow:hidden; }
li { display:flex; gap:10px; padding:3px 10px; border-top:1px solid var(--line); flex-wrap:wrap; }
li:first-child { border-top:0; }
.id { width:52px; font-variant-numeric:tabular-nums; color:var(--mute); } .k { width:110px; color:var(--mute); }
.m { flex:1; min-width:180px; } .tag, .why { color:var(--mute); font-size:12px; }
li.port { background:var(--port); border-left:4px solid var(--portline); font-weight:600; }
li.port .why { font-weight:400; flex-basis:100%%; padding-left:172px; }
li.tour { background:var(--tour); } li.multi { background:var(--multi); } li.final { background:var(--final); }
li.rare { background:var(--rare); } li.key { background:var(--key); }
@media (max-width:600px) { .k { width:70px; } li.port .why { padding-left:0; } }
</style></head><body>
<h1>Board order preview (C10)</h1>
<div class="rule"><p>Blue rows: ported quests in their proposed place, with the rule that chose it. Other rows: GU's
board in list order (tinted: tours, key quests, multi-monster, rare species / variants, elders and final bosses).</p>
<ul><li>multi-monster quest: after the board's last multi-monster quest;</li>
<li>elder dragon (stand-in Kushala Daora): after the last Kushala Daora / Chameleos / Teostra quest;</li>
<li>other: after the last regular quest of its base species (its stand-in), a monster's quests together; never
among the key quests;</li>
<li>no such quest: end of the board's single-monster block, else end of its regular quests (before rare species /
variants, else before the elders).</li></ul>
</div>
%s
</body></html>
'''


if __name__ == '__main__':
    a = sys.argv[1:]
    if a == ['show']: show()
    elif len(a) == 2 and a[0] == 'html': write_html(a[1])
    else: sys.exit(__doc__)
