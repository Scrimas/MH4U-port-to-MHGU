"""shots_seltas.py : the Desert Seltas' and the Desert Seltas Queen's own 4U shots as copies of GU's shell families
(module/seltas_shots.c swaps a copy in for each of their posts that 4U gives its own shot). Called by build_seltas_arc.py.

4U (v1.1, read 2026-11-09, C): the Seltas class posts uShell012 through 0x661f6c(mgr, this, subtype, ..) and uShell001
through 0x661bec(mgr, this, &data, kind, ..). Where it tests the species (W+0x1c0 == 25) the Desert Seltas takes his own
subtypes: uShell012 56 / 58 for the Seltas' 6 / 7 (0x77f618 = 7/2 7/13, 0x7802e0 = 7/7 7/12), 57 / 59 for 13 / 24
(0x7819d4 = 7/57 7/61, 0x781eb8 = 7/58 7/62); uShell001 117 / 118 for 36 / 74 (0x787270 mode 0, from 7/52 7/60 7/63;
its modes 1 / 2 post 90 / 91 for both species). The Queen (W+0x1c0 == 26 test) takes uShell001 kind 92 where the normal
Queen's is 1 (0x78e688 = 7/9 7/15 7/34 7/79, three shots, and 0x796928 = 7/56).
Per subtype / kind (asserted below): uShell012 flight / impact effects 0x1027488 / 0x10278d8 {group, element, -, -, s32
mask}, record 0x10290b0 (u32) -> 0x1028958 (40 B); uShell001 flight / wall / ground 0x1017980 / 0x1018140 / 0x1017d60,
record 0x101ae30 -> 0x1019f30 (monsters/dalamadur/module/dala_shell001.c). EFL by (group, element): table 0xef895c.
Their shots differ from the species' only in the effects (group 70 = em094 / 71 = em095 for 36 / 37) and in the
record bytes +0x10 +0x11 +0x13 +0x14 (+0x08 +0x18 for 57 vs 13); life and sound are the species'.
GU (C): shell ids 0x13b = em076_00_shell37 (def file 0x8a8e), 0x139 = em076_00_shell00 (0x8a8c), 0x127 =
em069_00_shell00 (0x8a7a); the def is cached per id for every monster (0x48c388), so a Desert copy must not change
GU's files (quest 11140 has a normal Seltas next to him). GU's kinds post their effects from list 2 of the def's PEL
(0x4a1e50: {slot, id}): shell37 ids 0 / 1 (flight, kinds 0-5 / 6-8) and 11 / 21 (impact), shell00 1 / 21, the Queen's
shell00 10 / 21. GU's hit entries are 4U's records converted: shell37 0 = record 5 (subtype 6), 1 = 12 (13); shell00
0 = uShell001 33 (kind 36), 1 = 92 (90, shared). So each copy = GU's def with its PEL (and hit data) on ours: a PEL
with GU's list-2 records of those ids on their 4U EFLs (mask: 4U's; -1 = all), hit entries with the bytes where the
Desert record differs from GU's source record. GU's kind files (ef / snd / hit / sh) stay shared: they name no PEL.
Colour (0.1.6, C unless marked; the user on 0.1.5: his spit on her back is green): the species' 4U shot EFLs em025_001 /
002 / 005 carry a colour block for a code colour (header +0x2c word 0 bit 4, +0xc byte 2 set: tools/efl4u2gu.py
efl_colour_block), theirs (em094_201..203, em095_020 / 021) none, so 4U draws their shots in their EFLs' own colours.
GU moved the species' code colours into its list-2 records: em076_00u ids 0 / 11 sand aa9650, ids 1 / 21 green 788c46,
mode +0x71 3 (RGB lerp, alpha kept) at factor +0x68 1.0; records 0 and 1 differ only in id, element mask and that colour.
GU's own kinds draw them (S: through the kinds, the record's +0x70 is 0): shell37 kinds 6-8 (4U subtype 13, his 7/57
on her back) and shell00 (7/52) take the green. Our records keep GU's bytes but white at factor 0 (NEUTRAL): no tint
in either mode, their EFL colours as in 4U. The Queen's records carry GU's default black at 0.5 (as GU's normal
Queen's); neutral too, by the same 4U rule (her EFLs have no colour block either).
4U's code colours themselves (C, 0.1.8): uShell001 init 0xc4c54c hands the setter 0xc48378 the colour of its kind from
the table 0x10ba3fc, which the static initializer 0xd34794 fills: kinds 36 / 90 = 788c46 green, 74 / 91 / 117 / 118
white. So their own kinds take no colour in 4U, also where an EFL had a colour block.
The ground splash (0.1.8, C; the user on 0.1.7 with a picture: green splashes and a green puddle on the ground when
he fires from her back): GU's Seltas shell class (table slot at 0x17ee9d0 = 0xfdca90) posts, at a ground hit (its mode
1), GU's shell 0x13a = em076_00_shell01 as the splash: kind 3 for a shell of kind 3 (7/63's shots, modes 1 / 2 of
0xfd7c78: list-2 id 999, nothing drawn), kind 2 for every other (his volley 7/52 7/60, kinds 0..2) = em076_00u id 20,
em076_00_002 in green at 1.0. The 0.1.3 swap never reached it (its post is 0xfdcbec, not one of the class's shots).
4U has no second shell there: uShell001 draws its ground effect itself (0x1017d60: kinds 117 / 118 -> (70, 11) =
em094_202, mask 1 / 2; the species' 36 / 74 -> em025_002 = GU's em076_00_002). So their copy = GU's shell01 def on a
PEL whose ids 10 / 20 are em094_202 (GU's masks), neutral. Its 4 hit entries match no 4U uShell001 / uShell012 record
(GU's own, not traced in 4U) but carry the species' shot status bytes (below): theirs get his (build_status_hits).
The other ground posts (0.1.10, C; the user on 0.1.9: on her back the shots are still green where they land; the 0.1.9
test log, quest 11372, named each effect post): (a) his 7/57 shots (shell37) took GU's def of 0x13a with kind 1 =
em076_00u id 20, the green em076_00_002. That post is not the shell class's: GU's Seltas class has a shell callback
(0xfc6a30, table word 0x17ecf48) that posts the shell id the unit keeps at this+0xcac8 (0x13a) with a kind from a table,
requests 0xfc6c08 / 0xfc6df0, owner = the shot's owner. The module marks both for the Desert Seltas, so they take the
0x13a copy above (em094_202, his own ground effect; S: GU's species maps that child to em076_00_002 = 4U em025_002,
the species' uShell001 ground effect, so his own is em094_202). (b) her shots (7/9: GU shell 0x127, our copy) hit the
ground through GU's Queen shell class 0xf9dc80, which posts 0x128 = em069_00_shell01 kind 2 (request 0xf9dda4): GU's
def, em069_00u id 20 = em069_00_012, the normal Queen's hit effect (4U kind 1's ground effect em026_021). 4U's kind 92
draws (71, 17) = em095_021 at the ground and at a wall (asserted in check_4u): their copy below has ids 20 / 21 on
em095_021 (GU's masks), neutral, GU's hit data (as her 0x127 copy). GU's other 0x128 posts (her dig, buried move,
call, 2/20: list 1 of the def = em069_00c common dust) keep GU's def: environment effects (the user's rule).
Status (0.1.8; the user asked which attacks give an ailment): a shot record's +0x10 / +0x11 / +0x13 flags and +0x14
value. Every Desert shot record (uShell012 38..41, uShell001 89 / 90) has +0x10 = 4, value 4 where the species' have
+0x11 = 8 or 1 or +0x13 = 8, value 0 (C, bytes); all else equal but +0x08 / +0x18 (C). Flag 4 = paralysis (S: the
same flag on GU Najarala's paralysing attack rows, monsters/shrouded_nerscylla/notes/plan.md, and on Tigerstripe's).
The Queen's shot record 1 has none. Their body attacks: 4U's records equal the species' (asserted in
build_seltas_arc.py), and GU's equal 4U's but for its byte 26 on five of his and its retune bytes 28 / 31 (C).
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'tools'))
import paths   # noqa: E402
sys.path.insert(0, paths.GU_PY)
import arcpack, efl4u2gu   # noqa: E402

MEM4 = open(os.path.join(paths.DUMP, 'exefs_v11', 'mem.bin'), 'rb').read()
BASE4 = 0x100000
T_PEL, T_HDS, T_DEF = 0x5a525c16, 0x4eb68cee, 0x4aa69872
EFL_TABLE = 0xef895c
U012_FX, U012_HIT, U012_RECT, U012_REC = 0x1027488, 0x10278d8, 0x10290b0, 0x1028958
U001_FX, U001_WALL, U001_GROUND, U001_RECT, U001_REC = 0x1017980, 0x1018140, 0x1017d60, 0x101ae30, 0x1019f30
ALL = 0xFFFFFFFF
SAFE = set(range(0x24)) - {0x12, 0x19, 0x1c}       # HDS bytes taken from the 4U record as they are (hds rule)


def u32(a): return struct.unpack_from('<I', MEM4, a - BASE4)[0]
def rec40(table, k): return MEM4[table + 40 * k - BASE4:table + 40 * k + 40 - BASE4]


def efl(group, element):
    p = u32(u32(EFL_TABLE + 4 * group) + 4 * element) - BASE4
    return MEM4[p:MEM4.index(b'\0', p)].decode('ascii')


def fx(table, k):
    """{group, element, mask} of a per-kind effect entry (8 B)"""
    b = MEM4[table + 8 * k - BASE4:table + 8 * k + 8 - BASE4]
    return b[0], b[1], struct.unpack_from('<i', b, 4)[0]


# the families: GU id, GU def, our def (same length), our PEL (same length as GU's), list-2 records {id: (EFL, mask or
# None = GU's)}, hit entries {GU entry: (4U table, GU's source record, the Desert record)}, the module's file ID
FAMILIES = {
    'desert_seltas': [
        dict(id=0x13b, gu='shell\\em\\em076_00_shell37\\em076_00_37', ours='shell\\em\\em076_01_shell37\\em076_01_37',
             gu_pel='effect\\pel\\em\\em076_00u', pel='effect\\pel\\em\\em076_01a',
             records={0: ('em094_201', ALL), 1: ('em094_201', ALL), 11: ('em094_203', ALL), 21: ('em094_203', ALL)},
             hits={0: (U012_REC, 5, 38), 1: (U012_REC, 12, 39)}, fid=0x10a1c),
        dict(id=0x139, gu='shell\\em\\em076_00_shell00\\em076_00_00', ours='shell\\em\\em076_01_shell00\\em076_01_00',
             gu_pel='effect\\pel\\em\\em076_00u', pel='effect\\pel\\em\\em076_01b',
             records={1: ('em094_201', None), 21: ('em094_203', None)},
             hits={0: (U001_REC, 33, 89)}, fid=0x10a1d),
        # the volley's ground splash (docstring "The ground splash"): 4U's ground effect of his kinds 117 / 118
        dict(id=0x13a, gu='shell\\em\\em076_00_shell01\\em076_00_01', ours='shell\\em\\em076_01_shell01\\em076_01_01',
             gu_pel='effect\\pel\\em\\em076_00u', pel='effect\\pel\\em\\em076_01d',
             records={10: ('em094_202', None), 20: ('em094_202', None)},
             hits={}, status=(U001_REC, 89), fid=0x10a1e),
    ],
    'desert_seltas_queen': [
        dict(id=0x127, gu='shell\\em\\em069_00_shell00\\em069_00_00', ours='shell\\em\\em069_01_shell00\\em069_01_00',
             gu_pel='effect\\pel\\em\\em069_00u', pel='effect\\pel\\em\\em069_01a',
             records={10: ('em095_020', ALL), 21: ('em095_021', ALL)}, hits={}, fid=0x10a59),
        # her shots' ground splash (docstring "The other ground posts" b): 4U kind 92's ground effect
        dict(id=0x128, gu='shell\\em\\em069_00_shell01\\em069_00_01', ours='shell\\em\\em069_01_shell01\\em069_01_01',
             gu_pel='effect\\pel\\em\\em069_00u', pel='effect\\pel\\em\\em069_01b',
             records={20: ('em095_021', None), 21: ('em095_021', None)}, hits={}, fid=0x10a5a),
    ],
}


def check_4u():
    """the 4U facts the families stand on (module docstring)"""
    for normal, desert in ((6, 56), (7, 58), (13, 57), (24, 59)):
        assert fx(U012_FX, normal)[:2] == (36, 1) and fx(U012_HIT, normal)[:2] == (36, 5), normal
        assert fx(U012_FX, desert) == (70, 10, -1) and fx(U012_HIT, desert) == (70, 12, -1), desert
    assert [u32(U012_RECT + 4 * s) for s in (6, 7, 13, 24, 56, 57, 58, 59)] == [5, 6, 12, 20, 38, 39, 40, 41]
    for normal, desert, mask in ((36, 117, 1), (74, 118, 2)):
        assert (fx(U001_FX, normal), fx(U001_WALL, normal), fx(U001_GROUND, normal)) == ((36, 1, mask), (36, 5, mask), (36, 2, mask))
        assert (fx(U001_FX, desert), fx(U001_WALL, desert), fx(U001_GROUND, desert)) == ((70, 10, mask), (70, 12, mask), (70, 11, mask))
    assert [u32(U001_RECT + 4 * k) for k in (36, 74, 117, 118, 90)] == [33, 69, 89, 90, 92]
    assert fx(U001_FX, 1) == (37, 16, -1) and fx(U001_FX, 92) == (71, 16, -1)
    assert fx(U001_WALL, 1) == (37, 17, -1) and fx(U001_WALL, 92) == (71, 17, -1) and fx(U001_GROUND, 92) == (71, 17, -1)
    assert fx(U001_GROUND, 1) == (37, 17, -1) and efl(37, 17) == 'effect\\efl\\em\\em026\\em026_021'
    assert u32(U001_RECT + 4 * 1) == u32(U001_RECT + 4 * 92) == 1, 'the Queen\'s kinds 1 / 92 share record 1'
    assert (efl(70, 10), efl(70, 11), efl(70, 12)) == tuple('effect\\efl\\em\\em094\\em094_%03d' % n for n in (201, 202, 203))
    assert (efl(71, 16), efl(71, 17)) == ('effect\\efl\\em\\em095\\em095_020', 'effect\\efl\\em\\em095\\em095_021')


def check_colours():
    """the 4U facts of the docstring "Colour": the species' shot EFLs take a code colour, theirs have no colour block"""
    def efls(name):
        _, src = arcpack.read(open(os.path.join(paths.DUMP, 'romfs', 'data', name + '.arc'), 'rb').read())
        return {p: d for p, t, d in src if t == efl4u2gu.T['EFL']}
    em025, em094, em095 = efls('em025'), efls('em094'), efls('em095')
    for k in (1, 2, 5):
        b = efl4u2gu.efl_colour_block(em025[efl(36, k)])
        assert b and b[0] & 0x10 and (b[3] >> 16) & 0xFF, ('the species\' shot EFL without its code colour', efl(36, k))
    for p, S in [(efl(70, k), em094) for k in (10, 11, 12)] + [(efl(71, k), em095) for k in (16, 17)]:
        assert efl4u2gu.efl_colour_block(S[p]) is None, ('their shot EFL has a colour block', p)


def list2_records(pel):
    """{record id: (path, 162 bytes after the path)} of a PEL's list 2"""
    n, body = efl4u2gu.pel_lists(pel)[2]
    out, i = {}, 0
    for _ in range(n):
        L = body[i]
        path = body[i + 1:i + 1 + L].decode('ascii')
        rest = body[i + 1 + L:i + 1 + L + 162]
        out[struct.unpack_from('<H', rest, 2 + 0x30)[0]] = (path, rest)
        i += 1 + L + 162
    return out


PEL_RGBA, PEL_FACTOR = 0x60, 0x68            # the record's colour and its lerp factor (tools/efl4u2gu.py PEL colour notes)
NEUTRAL = (b'\xff\xff\xff\xff', 0.0)          # white at factor 0: no tint (docstring "Colour")


def build_pel(gu_pel, records, notes):
    """PEL v15: lists 0 / 1 empty, list 2 = GU's records of these ids on our EFLs, without GU's tint (NEUTRAL)"""
    gu = list2_records(gu_pel)
    body = b''
    for rid, (name, mask) in sorted(records.items()):
        path, rest = gu[rid]
        rest = bytearray(rest)
        if mask is not None:
            struct.pack_into('<I', rest, 2 + 0x48, mask)
        old = (rest[2 + PEL_RGBA:2 + PEL_RGBA + 4].hex(), struct.unpack_from('<f', rest, 2 + PEL_FACTOR)[0])
        rest[2 + PEL_RGBA:2 + PEL_RGBA + 4] = NEUTRAL[0]
        struct.pack_into('<f', rest, 2 + PEL_FACTOR, NEUTRAL[1])
        notes.append('  PEL list 2 id %d: GU tint %s at %.1f -> none (their 4U EFL has no colour block)' % (rid, old[0], old[1]))
        new = ('effect\\efl\\em\\%s\\%s' % (name[:5], name)).encode('ascii')
        body += bytes([len(new)]) + new + bytes(rest)
        notes.append('  PEL list 2 id %d: GU %s -> %s, mask %08x' % (rid, path.split('\\')[-1], name, struct.unpack_from('<I', rest, 2 + 0x48)[0]))
    return b'PEL\0' + struct.pack('<IIII', 15, 0, 0, len(records)) + body


def build_hits(gu_hds, hits, notes):
    d = bytearray(gu_hds)
    n = struct.unpack_from('<I', d, 8)[0]
    for k, (table, src, ours) in sorted(hits.items()):
        assert k < n and len(d) == 16 + 56 * n
        g, s4, o4 = d[16 + 56 * k:16 + 56 * k + 56], rec40(table, src), rec40(table, ours)
        same = [i for i in range(0x24) if i not in (0x19, 0x1c) and g[i] != (s4[i] & 3 if i == 0x12 else s4[i])]
        assert not same, ('GU hit entry %d is not 4U record %d converted' % (k, src), same)
        diff = [i for i in range(40) if s4[i] != o4[i]]
        assert set(diff) <= SAFE, ('record bytes outside the plain copy', diff)
        for i in diff:
            d[16 + 56 * k + i] = o4[i]
        notes.append('  hit entry %d: 4U record %d -> %d, bytes %s' % (k, src, ours, ' '.join('+%x %02x->%02x' % (i, s4[i], o4[i]) for i in diff)))
    return bytes(d)


# the status bytes of a hit record (docstring "Status"): +0x10 / +0x11 / +0x13 flags, +0x14 value (+0x12 is the type
# GU keeps as & 3, the same in all of them)
STATUS_AT = (0x10, 0x11, 0x13, 0x14)
SPECIES_SHOTS = ((U012_REC, (5, 6, 12, 20)), (U001_REC, (33, 69, 92, 93)))    # the species' shot records (subtypes 6 7 13 24, kinds 36 74 90 91)


def build_status_hits(gu_hds, table, ours, notes):
    """GU's own hit entries (no 4U record behind them) with the status bytes of their 4U record `ours` where GU's carry one of the species'"""
    species = {tuple(rec40(t, r)[i] for i in STATUS_AT) for t, rs in SPECIES_SHOTS for r in rs}
    want = tuple(rec40(table, ours)[i] for i in STATUS_AT)
    d = bytearray(gu_hds)
    n = struct.unpack_from('<I', d, 8)[0]
    assert len(d) == 16 + 56 * n
    for k in range(n):
        e = 16 + 56 * k
        old = tuple(d[e + i] for i in STATUS_AT)
        assert old in species, ('GU hit entry %d carries a status the species\' shots do not' % k, old)
        for i, v in zip(STATUS_AT, want):
            d[e + i] = v
        notes.append('  hit entry %d (GU\'s own): status %s -> 4U record %d\'s %s' % (k, ' '.join('%02x' % v for v in old), ours, ' '.join('%02x' % v for v in want)))
    return bytes(d)


def files(name, G, fid_next, notes):
    """(new arc entries in load order, [(path, type)] of the extra own files = the defs) for entry `name`;
    G = GU's arc {(path, type): bytes}; fid_next = the file ID the first extra file gets"""
    check_4u()
    check_colours()
    pels, hits, defs, extra = [], [], [], []
    for f in FAMILIES.get(name, []):
        assert len(f['ours']) == len(f['gu']) and len(f['pel']) == len(f['gu_pel'])
        notes.append('own shot family for GU shell 0x%x (%s):' % (f['id'], f['gu'].split('\\')[-1]))
        pels.append((f['pel'], T_PEL, build_pel(G[(f['gu_pel'], T_PEL)], f['records'], notes)))
        d = G[(f['gu'], T_DEF)]
        assert d.count(f['gu_pel'].encode('ascii')) == 1, f['gu']
        d = d.replace(f['gu_pel'].encode('ascii'), f['pel'].encode('ascii'))
        if f['hits'] or f.get('status'):
            gh, oh = f['gu'] + '_hitdata', f['ours'] + '_hitdata'
            assert d.count(gh.encode('ascii')) == 1
            d = d.replace(gh.encode('ascii'), oh.encode('ascii'))
            hd = build_hits(G[(gh, T_HDS)], f['hits'], notes) if f['hits'] else build_status_hits(G[(gh, T_HDS)], *f['status'], notes)
            hits.append((oh, T_HDS, hd))
        defs.append((f['ours'], T_DEF, d))
        assert fid_next + len(extra) == f['fid'], ('module/seltas_shots.c expects file ID 0x%x for %s' % (f['fid'], f['ours']))
        extra.append((f['ours'], T_DEF))
        notes.append('  def %s (file ID 0x%x)' % (f['ours'], f['fid']))
    return pels + hits + defs, extra
