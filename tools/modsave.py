"""modsave.py : the mod's own save files (notes/mod-save-format.md), the reference the module (module/modsave.c) and
the installer follow byte for byte.

One file per character, `mhgu_de_<slot 1..3>.bin`, next to GU's `system` in the game's own save. GU's file keeps only
vanilla data: the split takes every added thing out of a character's slot and keeps it in that file; the merge puts it
back. Offsets are relative to a character's base in GU's file (MHGU_Editor docs/11-save-map.md, the installer's
mhgu-save crate). GU's own table counts (v1.4) decide what is added; nothing depends on which packages are installed.

  python3 tools/modsave.py check SYSTEM                       added things left in each slot of a GU `system` file
  python3 tools/modsave.py split SYSTEM OUTDIR                 (on copies) GU's file cleaned + mhgu_de_N.bin per slot
  python3 tools/modsave.py merge SYSTEM DIR OUT                 the files of DIR merged back into a copy of SYSTEM
  python3 tools/modsave.py unpack FILE                          a mod file as text (lossless)
  python3 tools/modsave.py pack TEXT OUT                        text back to a file (the check word recomputed)
  python3 tools/modsave.py test [SYSTEM]                        round trips (synthetic, and SYSTEM's slots if given)
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ------------------------------------------------------------------------------------------------ GU's file

CONTAINER = 0x24                # GU's file header {u32 0, version, 4, 0}, u32, one blob entry {key, type 0xc, size, 0}
SLOT_PTR = 0x10                 # in the blob: u32 offset of slot k at +0x10 + 4k (relative to the blob)
SLOT_USED = 0x04                # in the blob: u8 used per slot
SLOT_SIZE = 0x11F8C4            # one character's bytes
SLOTS = 3

# a character's fields (offsets from its base)
BOX, BOX_N = 0x278, 2300        # 19-bit stacks: u12 item ID, u7 count
POUCH, POUCH_N = 0x27BF, 32
LOADOUTS, LOADOUT_N, LOADOUT_SZ, LOADOUT_ITEMS = 0x17CF, 24, 170, 42   # 24 x {name 42 B, 32 x (u16 ID, u16 count)}
OBTAINED = 0x22497              # items obtained, bit = item ID, 3008 bits
OBTAINED_BITS = 3008
EQBOX, EQBOX_N, ENTRY = 0x62EE, 2000, 36
WORN = 0x23B39                  # 7 x u16 box index: weapon, head, chest, arms, waist, legs, talisman (0xFFFF none)
WEAPON_CLASS = (0x240, 0x23B47)  # u8 the current weapon class (15 = Prowler): the slot header's, the player record's
WORN_CACHE = 0x10C              # the slot header's 7 x 44 B {u32, the worn piece's 36-B entry, u32}: the slot select
CARD_GEAR = 0xC7211             # the own Guild Card's equipment, 7 x 44 B {u16 type, u16 ID, 4 B, 3 x u16 jewels at
                                # +8, .., u16 look at +0x28}: a snapshot, shown to other players
CARD_HISTORY, HISTORY_N, HISTORY = 0xC7AD5, 10, 160   # the card's quest history: +0x06 u16 quest ID, names, highlights
REGISTER = ((0x11D05A, 2), (0x11D05E, 4))             # the Item Register touch panels: u16 item IDs
MELDING, MELDING_N, MELDING_SZ = 0x227A7, 10, 420     # Melding Pot orders: +4 3 x 36-B talisman entries
TALLIES = ((0x5EA6, 2), (0x5FB8, 2), (0x60CA, 4))     # hunts, captures, sizes (137 entries each): GU's dummy entries
DUMMIES = (105, 7)                                    # 105..111 hold the six oldest monsters' numbers (D2)
MYSETS, MYSET_N, MYSET = 0x208C8, 40, 0x88   # +0x30 7 x u16 box index, +0x3E 7 x 3 x u16 decoration copies
QUEST_MAPS = (0x2C77, 0x2D77, 0x2E77)        # cleared, seen, failed: bit = quest list index, 0x100 bytes each
QUEST_MAP_BITS = 0x800
SMITHY_ARMOR = 0x3907           # 5 parts x {listed 288 B, NEW 288 B}
SMITHY_WEAPON = 0x36AF          # 15 types x {listed 20 B, NEW 20 B}
WEAPON_IDS = 0x45DF             # 15 types x 1024 bits by weapon ID (the Smithy's list builder)
RESERVED, RESERVED_N = 0x50BE, 3444          # sUserInfo +0x3684..+0x43f7: copied raw by GU, the mod's own block
LINK_N = 16                     # the link record at RESERVED: "MHDL", u32 link, u32 generation, u8 state, 3 x 0
NONE = 0xFFFF

# GU v1.4's own counts: an ID at or past them is added (allocations.toml pools for items and decorations)
GU_ITEM_FIRST_ADDED = 2977      # 2977..2990 DUMMY materials, 2991.. appended
GU_DECO_DUMMY = (2889, 2899)    # DUMMY decorations
GU_ARMOR = 1287                 # armorSeriesData records (box entry ID of armor)
GU_WEAPONS = (137, 129, 132, 127, 109, 0, 110, 127, 110, 115, 108, 126, 112, 83, 81)   # weaponNNBaseData; 05 has none
GU_ARMOR_CREATE = (563, 554, 538, 517, 548)                                           # armorCreateA00..A04
GU_WEAPON_CREATE = (95, 82, 84, 86, 84, 0, 98, 82, 81, 80, 90, 86, 75, 66, 63)       # weaponCreateW00..W14
GU_DECO_CREATE = 275            # decoCreate records
GU_QUESTS = 1509                # quest_group entries; the appended quests follow
STARTER = (1, 1)                # (weapon class, ID) put in when the box has no vanilla weapon left to hold

# ------------------------------------------------------------------------------------------------ the mod's file

MAGIC, VERSION, HEADER = b'MHDE', 1, 32
FILE_SIZE = 0x8000              # each file is created once at this size and never grows (the budget)
LINK_MAGIC = b'MHDL'
SPLIT, FULL = 1, 2              # link states: the slot is clean and its file holds the rest / the slot holds everything
K_ITEM, K_GEAR, K_BYTES, K_REGION, K_BITS, K_QUESTS, K_ASIDE = 1, 2, 3, 4, 5, 6, 7
KIND_NAMES = {K_ITEM: 'item', K_GEAR: 'gear', K_BYTES: 'bytes', K_REGION: 'region', K_BITS: 'bits',
              K_QUESTS: 'quests', K_ASIDE: 'aside'}
STORES = ('box', 'pouch', 'loadout')


def fnv(data, h=0x811C9DC5):
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def item_added(i):
    return i >= GU_ITEM_FIRST_ADDED or GU_DECO_DUMMY[0] <= i <= GU_DECO_DUMMY[1]


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def getbits(b, o, bit, n):
    v = int.from_bytes(b[o + (bit >> 3): o + ((bit + n + 7) >> 3)], 'little')
    return (v >> (bit & 7)) & ((1 << n) - 1)


def setbits(b, o, bit, n, val):
    lo, hi = o + (bit >> 3), o + ((bit + n + 7) >> 3)
    v = int.from_bytes(b[lo:hi], 'little')
    m = ((1 << n) - 1) << (bit & 7)
    v = (v & ~m) | ((val << (bit & 7)) & m)
    b[lo:hi] = v.to_bytes(hi - lo, 'little')


def kind_of(e):
    """('armor', part) / ('weapon', class) / ('talisman', 0) / ('empty', 0) / ('other', code) of a box entry"""
    c = u16(e, 0) & 0x1F
    if c == 0: return 'empty', 0
    if 1 <= c <= 5: return 'armor', c
    if c == 6: return 'talisman', 0
    if 7 <= c <= 21: return 'weapon', c - 7
    return 'other', c


def entry_added(e):
    k, c = kind_of(e)
    i = u16(e, 2)
    return (k == 'armor' and i >= GU_ARMOR) or (k == 'weapon' and i >= GU_WEAPONS[c])


def entry_clean(e):
    """a vanilla piece without its added decorations (the others stay packed from the first field) and its added
    layered look (back to its own look)"""
    e = bytearray(e)
    d = [u16(e, 6 + 2 * k) for k in range(3)]
    keep = [x for x in d if x and not item_added(x)] + [0, 0, 0]
    struct.pack_into('<3H', e, 6, *keep[:3])
    if kind_of(e)[0] == 'armor' and u16(e, 4) >= GU_ARMOR:
        struct.pack_into('<H', e, 4, 0)
        struct.pack_into('<H', e, 0, u16(e, 0) & ~(0x1F << 10))
    return bytes(e)


def starter_entry():
    e = bytearray(ENTRY)
    struct.pack_into('<HH', e, 0, 7 + STARTER[0], STARTER[1])
    return bytes(e)


def bit_ranges():
    """(offset, first added bit, bits) of every bit array keyed by an ID GU's tables end before"""
    r = [(OBTAINED, GU_ITEM_FIRST_ADDED, OBTAINED_BITS)]
    for p in range(5):
        r.append((SMITHY_ARMOR + 576 * p, 4 * GU_ARMOR_CREATE[p], 288 * 8))        # listed: 4 x create record + sub
        # NEW: gear.c traced 0x524a70 as asked by armor ID, MHGU_Editor names it by create record: only bits past
        # both bounds are taken, so no vanilla mark is ever touched
        r.append((SMITHY_ARMOR + 576 * p + 288, max(GU_ARMOR, 4 * GU_ARMOR_CREATE[p]), 288 * 8))
    for t in range(15):
        r.append((SMITHY_WEAPON + 40 * t, GU_WEAPON_CREATE[t], 160))              # listed: by create record
        r.append((SMITHY_WEAPON + 40 * t + 20, max(GU_WEAPONS[t], GU_WEAPON_CREATE[t]), 160))   # NEW (see armor)
        r.append((WEAPON_IDS + 128 * t, GU_WEAPONS[t], 1024))                     # the list builder's, by weapon ID
    r += [(0x4D5F, GU_ARMOR, 5248),                                               # the list builder's, by armor ID
          (0x31A7, GU_DECO_CREATE, 288), (0x31CB, GU_DECO_CREATE, 288),           # decorations listed / NEW
          (0x32B7, 123, 128), (0x32C7, 123, 128)]                                 # Hunter's Notes, large / NEW
    r += [(0x11CFD4 + 12 * k, 89, 96) for k in range(3)]                          # Meownster hunts per rank, by em
    return r


# ------------------------------------------------------------------------------------------------ quest bits

def quest_bits(reg=None):
    """[(list index, quest ID)] of the quest list entries that are the mod's: the renamed GU slots (quest_slots, at
    their index in GU's quest_group) and the appended block from index 1509 (module/quest.c quest_group_append: every
    quest_append monster's quests in registry order, each followed by the tours listed after it)"""
    sys.path.insert(0, HERE)
    import alloc
    reg = reg or alloc.load()
    ms = alloc.monsters(reg)
    out, n = [], GU_QUESTS
    slots = gu_quest_indexes()
    for m in ms:
        for q, s in zip(m.get('quests', []), m.get('quest_slots', [])) if not m.get('quest_append') else ():
            if s in slots: out.append((slots[s], q))
    tours = alloc.tours(reg)
    for mi, m in enumerate(ms):
        if not m.get('quest_append'): continue
        for q in m.get('quests', []):
            if q: out.append((n, q)); n += 1
        for t in tours:
            if t['after'] == m['name']: out.append((n, t['quest'])); n += 1
    return sorted(out)


_gu_idx = None


def gu_quest_indexes():
    """{quest ID: first list index} of GU's quest_group (RomFS village/common.arc)"""
    global _gu_idx
    if _gu_idx is None:
        sys.path.insert(0, HERE)
        import paths
        sys.path.insert(0, os.path.join(HERE, 'gulib'))
        from build_assets import RomFS, arc
        R = RomFS(paths.GU_ROMFS)
        qg = [v for k, v in arc(R.read('/nativeNX/loc/arc/village/common.arc')).items() if k.endswith('quest_group')][0]
        qg = qg[1] if isinstance(qg, tuple) else qg
        _gu_idx = {}
        for i in range(struct.unpack_from('<I', qg, 4)[0]):
            _gu_idx.setdefault(struct.unpack_from('<I', qg, 8 + 7 * i)[0], i)
    return _gu_idx


# ------------------------------------------------------------------------------------------------ split

def rec(kind, payload, flags=0):
    return struct.pack('<BBH', kind, flags, len(payload)) + payload


def records_of(slot, quests):
    """every record of a slot, in the budget's order, each with the change it makes to the slot:
    [(record bytes, [(offset, vanilla bytes)])]"""
    s = slot
    out = []
    # gear first decides what the worn gear and My Sets lose
    added = [entry_added(s[EQBOX + ENTRY * i: EQBOX + ENTRY * (i + 1)]) for i in range(EQBOX_N)]
    empty0 = [not any(s[EQBOX + ENTRY * i: EQBOX + ENTRY * (i + 1)]) for i in range(EQBOX_N)]
    # worn
    worn = [u16(s, WORN + 2 * k) for k in range(7)]
    if any(w != NONE and w < EQBOX_N and added[w] for w in worn):
        van = list(worn)
        for k in range(1, 7):
            if van[k] != NONE and van[k] < EQBOX_N and added[van[k]]: van[k] = NONE
        extra = []
        if worn[0] != NONE and worn[0] < EQBOX_N and added[worn[0]]:
            cls = kind_of(s[EQBOX + ENTRY * worn[0]: EQBOX + ENTRY * (worn[0] + 1)])[1]
            def vanilla_weapon(same):
                for j in range(EQBOX_N):
                    e = s[EQBOX + ENTRY * j: EQBOX + ENTRY * (j + 1)]
                    k, c = kind_of(e)
                    if k == 'weapon' and not added[j] and (not same or c == cls): return j, c
                return None
            got = vanilla_weapon(True) or vanilla_weapon(False)
            if got is None:                                     # a starter weapon in the first entry empty before
                j = empty0.index(True) if True in empty0 else None
                if j is None: return None                       # nothing to hold: the slot can't be split
                o = EQBOX + ENTRY * j
                extra.append((rec(K_BYTES, struct.pack('<IH', o, ENTRY) + bytes(s[o:o + ENTRY]) + starter_entry()),
                              [(o, starter_entry())]))
                got = (j, STARTER[0])
            van[0] = got[0]
            for o in WEAPON_CLASS:
                if s[o] != got[1]:
                    extra.append((rec(K_BYTES, struct.pack('<IH', o, 1) + bytes([s[o], got[1]])), [(o, bytes([got[1]]))]))
        o, vb = WORN, struct.pack('<7H', *van)
        out.append((rec(K_BYTES, struct.pack('<IH', o, 14) + bytes(s[o:o + 14]) + vb), [(o, vb)]))
        out += extra
        placeholder = None if van[0] == worn[0] else van[0]
    else:
        placeholder = None
    # the slot header's copies of the worn pieces (the slot select shows them before any character loads)
    for k in range(7):
        o = WORN_CACHE + 44 * k + 4
        e = bytes(s[o:o + ENTRY])
        if not any(e): continue
        if entry_added(e):
            if k == 0 and placeholder is not None:
                p = EQBOX + ENTRY * placeholder
                v = starter_entry() if not any(s[p:p + ENTRY]) else entry_clean(bytes(s[p:p + ENTRY]))
            else:
                v = bytes(ENTRY)
        else:
            v = entry_clean(e)
        if v != e:
            out.append((rec(K_BYTES, struct.pack('<IH', o, ENTRY) + e + v), [(o, v)]))
    # the own Guild Card's equipment snapshot (44-B entries: type, ID, jewels at +8, look at +0x28)
    for k in range(7):
        o = CARD_GEAR + 44 * k
        c = bytearray(s[o:o + 44])
        if not any(c): continue
        e36 = bytearray(ENTRY)
        e36[0:4] = c[0:4]
        if entry_added(e36):
            v = bytes(44)
        else:
            d = [u16(c, 8 + 2 * x) for x in range(3)]
            keep = [x for x in d if x and not item_added(x)] + [0, 0, 0]
            struct.pack_into('<3H', c, 8, *keep[:3])
            if kind_of(e36)[0] == 'armor' and u16(c, 0x28) >= GU_ARMOR: struct.pack_into('<H', c, 0x28, 0)
            v = bytes(c)
        if v != bytes(s[o:o + 44]):
            out.append((rec(K_BYTES, struct.pack('<IH', o, 44) + bytes(s[o:o + 44]) + v), [(o, v)]))
    # the card's quest history: a record of one of the mod's quests goes whole
    mine = {q for _, q in quests}
    for k in range(HISTORY_N):
        o = CARD_HISTORY + HISTORY * k
        if u16(s, o + 6) in mine:
            out.append((rec(K_BYTES, struct.pack('<IH', o, HISTORY) + bytes(s[o:o + HISTORY]) + bytes(HISTORY)),
                        [(o, bytes(HISTORY))]))
    # the Item Register touch panels
    for o0, n in REGISTER:
        for x in range(n):
            o = o0 + 2 * x
            if u16(s, o) and item_added(u16(s, o)):
                out.append((rec(K_BYTES, struct.pack('<IH', o, 2) + bytes(s[o:o + 2]) + bytes(2)), [(o, bytes(2))]))
    # the Melding Pot's talismans (their jewels)
    for k in range(MELDING_N):
        for j in range(3):
            o = MELDING + MELDING_SZ * k + 4 + ENTRY * j
            e = bytes(s[o:o + ENTRY])
            v = entry_clean(e) if any(e) else e
            if v != e:
                out.append((rec(K_BYTES, struct.pack('<IH', o, ENTRY) + e + v), [(o, v)]))
    # the dummy entries' hunts, captures and sizes (D2)
    for o0, w in TALLIES:
        o, n = o0 + w * DUMMIES[0], w * DUMMIES[1]
        if any(s[o:o + n]):
            out.append((rec(K_REGION, struct.pack('<IH', o, n) + bytes(s[o:o + n])), [(o, bytes(n))]))
    # My Sets
    for k in range(MYSET_N):
        o = MYSETS + MYSET * k
        v = bytearray(s[o:o + MYSET])
        for j in range(7):
            i = u16(v, 0x30 + 2 * j)
            if i != NONE and i < EQBOX_N and added[i]:
                struct.pack_into('<H', v, 0x30 + 2 * j, NONE)
                struct.pack_into('<3H', v, 0x3E + 6 * j, 0, 0, 0)
            d = [u16(v, 0x3E + 6 * j + 2 * x) for x in range(3)]
            keep = [x for x in d if x and not item_added(x)] + [0, 0, 0]
            struct.pack_into('<3H', v, 0x3E + 6 * j, *keep[:3])
        if bytes(v) != bytes(s[o:o + MYSET]):
            out.append((rec(K_BYTES, struct.pack('<IH', o, MYSET) + bytes(s[o:o + MYSET]) + bytes(v)), [(o, bytes(v))]))
    # the reserved block past the link record: runs of non-zero bytes (gaps under 8 zero bytes stay inside a run)
    lo, hi = RESERVED + LINK_N, RESERVED + RESERVED_N
    i = lo
    while i < hi:
        if not s[i]: i += 1; continue
        j, z = i, 0
        while j < hi and z < 8:
            z = z + 1 if not s[j] else 0
            j += 1
        j -= z
        out.append((rec(K_REGION, struct.pack('<IH', i, j - i) + bytes(s[i:j])), [(i, bytes(j - i))]))
        i = j
    # bit arrays keyed by an added ID: runs of set bits
    for o, first, n in bit_ranges():
        b = first
        while b < n:
            if not getbits(s, o, b, 1): b += 1; continue
            e = b
            while e < n and e - b < 0xFFFF and getbits(s, o, e, 1): e += 1
            cnt = e - b
            out.append((rec(K_BITS, struct.pack('<IHH', o, b, cnt)),
                        [('bits', o, b, cnt)]))
            b = e
    # quest bits by quest ID
    for m, o in enumerate(QUEST_MAPS):
        ids = [q for idx, q in quests if idx < QUEST_MAP_BITS and getbits(s, o, idx, 1)]
        if ids:
            out.append((rec(K_QUESTS, struct.pack('<BH', m, len(ids)) + b''.join(struct.pack('<I', q) for q in ids)),
                        [('qbits', o, [idx for idx, q in quests if idx < QUEST_MAP_BITS and getbits(s, o, idx, 1)])]))
    # gear: added pieces whole, vanilla pieces with added decorations or looks patched
    for i in range(EQBOX_N):
        o = EQBOX + ENTRY * i
        e = bytes(s[o:o + ENTRY])
        if added[i]:
            out.append((rec(K_GEAR, struct.pack('<H', i) + e), [(o, bytes(ENTRY))]))
        elif kind_of(e)[0] != 'empty':
            c = entry_clean(e)
            if c != e:
                out.append((rec(K_BYTES, struct.pack('<IH', o, ENTRY) + e + c), [(o, c)]))
    # items: box, pouch, loadouts
    for st, (o, n) in enumerate(((BOX, BOX_N), (POUCH, POUCH_N))):
        for i in range(n):
            iid, cnt = getbits(s, o, 19 * i, 12), getbits(s, o, 19 * i + 12, 7)
            if iid and item_added(iid):
                out.append((rec(K_ITEM, struct.pack('<BHHB', st, i, iid, cnt)), [('stack', o, i)]))
    for k in range(LOADOUT_N):
        for j in range(32):
            o = LOADOUTS + LOADOUT_SZ * k + LOADOUT_ITEMS + 4 * j
            iid, cnt = u16(s, o), u16(s, o + 2)
            if iid and item_added(iid):
                out.append((rec(K_ITEM, struct.pack('<BHHB', 2, 32 * k + j, iid, cnt & 0xFF)), [(o, bytes(4))]))
    return out


def apply_change(s, ch):
    if ch[0] == 'bits':
        _, o, b, n = ch
        for x in range(b, b + n): setbits(s, o, x, 1, 0)
    elif ch[0] == 'qbits':
        _, o, idxs = ch
        for x in idxs: setbits(s, o, x, 1, 0)
    elif ch[0] == 'stack':
        _, o, i = ch
        setbits(s, o, 19 * i, 19, 0)
    else:
        o, b = ch
        s[o:o + len(b)] = b


def split(slot, quests, link, generation, aside=(), budget=FILE_SIZE, clean=True):
    """(mod file bytes, number of records left in the slot by the budget). With clean, the slot (a bytearray) loses
    what the file holds and gets the link record "split"; aside = records a merge could not place, carried over."""
    rs = records_of(slot, quests)
    if rs is None:
        return None, 0
    body, left = bytearray(), 0
    for r, chs in rs:
        if HEADER + len(body) + len(r) > budget:
            left += 1
            continue
        body += r
        if clean:
            for ch in chs: apply_change(slot, ch)
    for r in aside:
        a = rec(K_ASIDE, r)
        if HEADER + len(body) + len(a) <= budget: body += a
        else: left += 1
    if clean:
        slot[RESERVED:RESERVED + LINK_N] = LINK_MAGIC + struct.pack('<IIB3x', link, generation, SPLIT)
    h = fnv(bytes(slot)) if clean else 0
    return finish(body, link, generation, h), left


def finish(body, link, generation, slot_hash):
    used = HEADER + len(body)
    head = MAGIC + struct.pack('<HHI', VERSION, 0, used)
    tail = struct.pack('<IIII', link, generation, slot_hash, 0) + bytes(body)
    return head + struct.pack('<I', fnv(tail, fnv(head))) + tail


def link_of(slot):
    """(link, generation, state) of a slot's link record, or None"""
    b = bytes(slot[RESERVED:RESERVED + LINK_N])
    if b[:4] != LINK_MAGIC: return None
    return struct.unpack_from('<IIB', b, 4)


# ------------------------------------------------------------------------------------------------ read a file

def parse(f):
    """(header dict, [(kind, flags, payload)]) or raises ValueError"""
    if len(f) < HEADER or f[:4] != MAGIC: raise ValueError('not a mod file')
    ver, flags, used, word = struct.unpack_from('<HHII', f, 4)
    if used < HEADER or used > len(f): raise ValueError('bad size %d' % used)
    if word != fnv(f[16:used], fnv(f[:12])): raise ValueError('check word')
    link, gen, h, _ = struct.unpack_from('<IIII', f, 16)
    out, o = [], HEADER
    while o < used:
        if o + 4 > used: raise ValueError('truncated record')
        k, fl, n = struct.unpack_from('<BBH', f, o)
        if o + 4 + n > used: raise ValueError('truncated record')
        out.append((k, fl, bytes(f[o + 4:o + 4 + n])))
        o += 4 + n
    return dict(version=ver, flags=flags, used=used, link=link, generation=gen, slot_hash=h), out


# ------------------------------------------------------------------------------------------------ merge

def merge(slot, f, quests):
    """put a mod file back into a slot (a bytearray). Each record goes where the split took it if GU's slot still
    holds what the split left there, else to a free place of its kind; one that finds none is returned (aside), to
    be kept in the next file. Returns dict(exact, placed, moved, kept, aside=[record payloads])."""
    hd, rs = parse(f)
    rs = [(k, fl, p) if k != K_ASIDE else (p[0], p[1], p[4:4 + struct.unpack_from('<H', p, 2)[0]]) for k, fl, p in rs]
    exact = fnv(bytes(slot)) == hd['slot_hash']
    st = dict(exact=exact, placed=0, moved=0, kept=0, aside=[])
    moved = {}
    def entry(i): return bytes(slot[EQBOX + ENTRY * i: EQBOX + ENTRY * (i + 1)])
    for k, fl, p in rs:                                           # gear first: the references follow it
        if k != K_GEAR: continue
        i, e = struct.unpack_from('<H', p, 0)[0], p[2:2 + ENTRY]
        if entry(i) == e: moved[i] = i; continue
        j = i if not any(entry(i)) else next((x for x in range(EQBOX_N) if not any(entry(x))), None)
        if j is None: st['aside'].append(rec(k, p, fl)); continue
        slot[EQBOX + ENTRY * j: EQBOX + ENTRY * (j + 1)] = e
        moved[i] = j
        st['placed'] += 1
        st['moved'] += j != i
    for k, fl, p in rs:
        if k == K_BYTES:
            o, n = struct.unpack_from('<IH', p, 0)
            orig, van = bytearray(p[6:6 + n]), p[6 + n:6 + 2 * n]
            cur = bytes(slot[o:o + n])
            if cur == bytes(orig): continue
            if cur != van: st['kept'] += 1; continue            # GU's slot changed there: GU's wins
            if o == WORN:
                for x in range(7):
                    i = u16(orig, 2 * x)
                    if i in moved: struct.pack_into('<H', orig, 2 * x, moved[i])
            elif MYSETS <= o < MYSETS + MYSET * MYSET_N:
                for x in range(7):
                    i = u16(orig, 0x30 + 2 * x)
                    if i in moved: struct.pack_into('<H', orig, 0x30 + 2 * x, moved[i])
            slot[o:o + n] = orig
            st['placed'] += 1
        elif k == K_REGION:
            o, n = struct.unpack_from('<IH', p, 0)
            cur = bytes(slot[o:o + n])
            if cur == p[6:6 + n]: continue
            if any(cur): st['kept'] += 1; continue
            slot[o:o + n] = p[6:6 + n]
            st['placed'] += 1
        elif k == K_BITS:
            o, b, n = struct.unpack_from('<IHH', p, 0)
            for x in range(b, b + n): setbits(slot, o, x, 1, 1)
            st['placed'] += 1
        elif k == K_QUESTS:
            m, n = struct.unpack_from('<BH', p, 0)
            idx = {q: i for i, q in quests}
            for x in range(n):
                q = struct.unpack_from('<I', p, 3 + 4 * x)[0]
                if q in idx: setbits(slot, QUEST_MAPS[m], idx[q], 1, 1)
                else: st['aside'].append(rec(K_QUESTS, struct.pack('<BHI', m, 1, q)))
            st['placed'] += 1
        elif k == K_ITEM:
            s_, i, iid, cnt = struct.unpack_from('<BHHB', p, 0)
            if s_ < 2:
                o, n = ((BOX, BOX_N), (POUCH, POUCH_N))[s_]
                at = lambda x: (getbits(slot, o, 19 * x, 12), getbits(slot, o, 19 * x + 12, 7))
                if at(i) == (iid, cnt): continue
                j = i if at(i)[0] == 0 else next((x for x in range(n) if at(x)[0] == 0), None)
                if j is None: st['aside'].append(rec(k, p, fl)); continue
                setbits(slot, o, 19 * j, 12, iid); setbits(slot, o, 19 * j + 12, 7, cnt)
            else:
                lk, lj = divmod(i, 32)
                o = LOADOUTS + LOADOUT_SZ * lk + LOADOUT_ITEMS + 4 * lj
                if (u16(slot, o), u16(slot, o + 2)) == (iid, cnt): continue
                if u16(slot, o): st['aside'].append(rec(k, p, fl)); continue
                struct.pack_into('<HH', slot, o, iid, cnt)
                j = i
            st['placed'] += 1
            st['moved'] += j != i
        elif k != K_GEAR:
            st['aside'].append(rec(k, p, fl))                     # a kind this version doesn't know: kept
    return st


# ------------------------------------------------------------------------------------------------ check

def check(slot, quests):
    """[text] of every added thing a slot still holds (the link record aside)"""
    rs = records_of(slot, quests)
    if rs is None: return ['the hunter holds an added weapon and the box has no free entry']
    out = []
    for r, _ in rs:
        out.append(describe(r[0], r[1], r[4:]))
    return out


def describe(k, fl, p):
    if k == K_ITEM:
        s_, i, iid, cnt = struct.unpack_from('<BHHB', p, 0)
        return 'item %s %d: %d x %d' % (STORES[s_] if s_ < 3 else s_, i, iid, cnt)
    if k == K_GEAR:
        i = struct.unpack_from('<H', p, 0)[0]
        kd, c = kind_of(p[2:])
        return 'gear %d: %s %d id %d raw %s' % (i, kd, c, u16(p, 4), p[2:].hex())
    if k == K_BYTES:
        o, n = struct.unpack_from('<IH', p, 0)
        return 'bytes %#x %d: %s -> %s' % (o, n, p[6:6 + n].hex(), p[6 + n:6 + 2 * n].hex())
    if k == K_REGION:
        o, n = struct.unpack_from('<IH', p, 0)
        return 'region %#x %d: %s' % (o, n, p[6:].hex())
    if k == K_BITS:
        o, b, n = struct.unpack_from('<IHH', p, 0)
        return 'bits %#x %d %d' % (o, b, n)
    if k == K_QUESTS:
        m, n = struct.unpack_from('<BH', p, 0)
        return 'quests %s %s' % (('cleared', 'seen', 'failed')[m], ' '.join(str(struct.unpack_from('<I', p, 3 + 4 * x)[0])
                                                                             for x in range(n)))
    if k == K_ASIDE:
        return 'aside ' + describe(p[0], p[1], p[4:])
    return 'kind %d flags %d %s' % (k, fl, p.hex())


def undescribe(line):
    """one unpack line back to (kind, flags, payload)"""
    w = line.split()
    if w[0] == 'aside':
        k, fl, p = undescribe(line[len('aside '):])
        return K_ASIDE, 0, rec(k, p, fl)
    if w[0] == 'item':
        cnt = int(w[5])
        return K_ITEM, 0, struct.pack('<BHHB', STORES.index(w[1]), int(w[2].rstrip(':')), int(w[3]), cnt)
    if w[0] == 'gear':
        return K_GEAR, 0, struct.pack('<H', int(w[1].rstrip(':'))) + bytes.fromhex(w[-1])
    if w[0] == 'bytes':
        o, n = int(w[1], 16), int(w[2].rstrip(':'))
        return K_BYTES, 0, struct.pack('<IH', o, n) + bytes.fromhex(w[3]) + bytes.fromhex(w[5])
    if w[0] == 'region':
        o, n = int(w[1], 16), int(w[2].rstrip(':'))
        return K_REGION, 0, struct.pack('<IH', o, n) + bytes.fromhex(w[3])
    if w[0] == 'bits':
        return K_BITS, 0, struct.pack('<IHH', int(w[1], 16), int(w[2]), int(w[3]))
    if w[0] == 'quests':
        ids = [int(x) for x in w[2:]]
        return K_QUESTS, 0, struct.pack('<BH', ('cleared', 'seen', 'failed').index(w[1]), len(ids)) + \
            b''.join(struct.pack('<I', q) for q in ids)
    if w[0] == 'kind':
        return int(w[1]), int(w[3]), bytes.fromhex(w[4]) if len(w) > 4 else b''
    raise ValueError('unknown line: ' + line)


def unpack(f):
    hd, rs = parse(f)
    lines = ['mhgu_de v%d link %08x generation %d slot_hash %08x' % (hd['version'], hd['link'], hd['generation'],
                                                                      hd['slot_hash'])]
    lines += [describe(k, fl, p) for k, fl, p in rs]
    lines.append('# %d of %d bytes used' % (hd['used'], FILE_SIZE))
    return '\n'.join(lines) + '\n'


def pack(text):
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith('#')]
    w = lines[0].split()
    link, gen, h = int(w[3], 16), int(w[5]), int(w[7], 16)
    body = b''.join(rec(*(lambda k, fl, p: (k, p, fl))(*undescribe(l))) for l in lines[1:])
    return finish(body, link, gen, h)


# ------------------------------------------------------------------------------------------------ GU's file

def slots(data):
    """[(k, char base in the file)] of the used slots of a GU `system` file"""
    blob = CONTAINER
    out = []
    for k in range(SLOTS):
        if data[blob + SLOT_USED + k]:
            out.append((k, blob + struct.unpack_from('<I', data, blob + SLOT_PTR + 4 * k)[0]))
    return out


def test(path=None):
    quests = quest_bits()
    bad = 0
    def roundtrip(name, slot):
        nonlocal bad
        orig = bytes(slot)
        s = bytearray(slot)
        f, left = split(s, quests, 0x1234, 1)
        if f is None: print('FAIL %s: no split' % name); bad += 1; return
        left_over = check(s, quests)
        if left_over and not left: print('FAIL %s: left in the slot: %s' % (name, left_over[:3])); bad += 1
        st = merge(s, f, quests)
        if bytes(s[:RESERVED]) + bytes(s[RESERVED + LINK_N:]) != orig[:RESERVED] + orig[RESERVED + LINK_N:]:
            diff = [i for i in range(len(orig)) if s[i] != orig[i] and not RESERVED <= i < RESERVED + LINK_N]
            print('FAIL %s: merge(split) differs at %d bytes, first %#x' % (name, len(diff), diff[0])); bad += 1
        elif not st['exact'] or st['aside']:
            print('FAIL %s: not exact (%s)' % (name, st)); bad += 1
        else:
            print('ok %s: %d bytes, %d records, %d placed' % (name, len(f), len(parse(f)[1]), st['placed']))
        if pack(unpack(f)) != f: print('FAIL %s: pack(unpack) differs' % name); bad += 1
    if path:
        data = open(path, 'rb').read()
        for k, base in slots(data):
            roundtrip('%s slot %d' % (os.path.basename(path), k + 1), bytearray(data[base:base + SLOT_SIZE]))
    syn = bytearray(SLOT_SIZE)                      # synthetic: one of each kind
    setbits(syn, BOX, 19 * 5, 12, 2980); setbits(syn, BOX, 19 * 5 + 12, 7, 7)
    setbits(syn, BOX, 19 * 6, 12, 100); setbits(syn, BOX, 19 * 6 + 12, 7, 3)
    struct.pack_into('<HH', syn, LOADOUTS + LOADOUT_SZ * 2 + LOADOUT_ITEMS + 4 * 3, 2995, 2)
    struct.pack_into('<HH', syn, EQBOX + ENTRY * 0, 7 + 2, 140)                      # an added hammer
    struct.pack_into('<HHH3H', syn, EQBOX + ENTRY * 1, 1, 10, 0, 2890, 300, 0)        # vanilla helm, an added jewel
    struct.pack_into('<HHH', syn, EQBOX + ENTRY * 2, 2 | (3 << 10), 20, 1290)        # vanilla mail, an added look
    struct.pack_into('<HH', syn, EQBOX + ENTRY * 3, 1, 1300)                         # an added helm
    struct.pack_into('<7H', syn, WORN, 0, 3, 2, NONE, NONE, NONE, NONE)
    for o in WEAPON_CLASS: syn[o] = 2
    struct.pack_into('<7H', syn, MYSETS + MYSET * 4 + 0x30, 0, 3, NONE, NONE, NONE, NONE, NONE)
    setbits(syn, OBTAINED, 2980, 1, 1)
    syn[RESERVED + 0x27C:RESERVED + 0x280] = b'MH4S'
    if quests: setbits(syn, QUEST_MAPS[0], quests[0][0], 1, 1)
    roundtrip('synthetic', syn)
    return bad


def main(a):
    if not a or a[0] not in ('check', 'split', 'merge', 'unpack', 'pack', 'test'):
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == 'unpack':
        sys.stdout.write(unpack(open(a[1], 'rb').read())); return
    if cmd == 'pack':
        open(a[2], 'wb').write(pack(open(a[1], encoding='utf-8').read())); return
    if cmd == 'test':
        sys.exit(1 if test(a[1] if len(a) > 1 else None) else 0)
    quests = quest_bits()
    data = bytearray(open(a[1], 'rb').read())
    if cmd == 'check':
        for k, base in slots(data):
            s = data[base:base + SLOT_SIZE]
            l = check(s, quests)
            print('slot %d: %s, %d added thing(s)' % (k + 1, 'link %s' % (link_of(s),) if link_of(s) else 'no link', len(l)))
            for x in l[:40]: print('  ' + x)
        return
    if cmd == 'split':
        os.makedirs(a[2], exist_ok=True)
        for k, base in slots(data):
            s = bytearray(data[base:base + SLOT_SIZE])
            f, left = split(s, quests, int.from_bytes(os.urandom(4), 'little') | 1, 1)
            if f is None: print('slot %d: not split (nothing for the hunter to hold)' % (k + 1)); continue
            data[base:base + SLOT_SIZE] = s
            open(os.path.join(a[2], 'mhgu_de_%d.bin' % (k + 1)), 'wb').write(f)
            print('slot %d: %d bytes, %d record(s) left in the slot by the budget' % (k + 1, len(f), left))
        open(os.path.join(a[2], 'system'), 'wb').write(data)
        return
    if cmd == 'merge':
        for k, base in slots(data):
            p = os.path.join(a[2], 'mhgu_de_%d.bin' % (k + 1))
            if not os.path.exists(p): continue
            s = bytearray(data[base:base + SLOT_SIZE])
            st = merge(s, open(p, 'rb').read(), quests)
            data[base:base + SLOT_SIZE] = s
            print('slot %d: %s' % (k + 1, st))
        open(a[3], 'wb').write(data)


if __name__ == '__main__':
    main(sys.argv[1:])
