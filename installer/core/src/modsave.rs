//! The mod's own save files (core 3.0.0, notes/mod-save-format.md): the split of one character's slot into GU's
//! vanilla bytes and the file `mhgu_de_<slot>.bin`, and the merge back. The third implementation, byte for byte the
//! same as tools/modsave.py (the reference) and module/modsave.c (the game): tools/test_modsave.py runs all three on
//! the same slots and compares the files and the slots. Every function works on one slot's bytes (`SLOT_SIZE`, the
//! character's base in GU's file at 0x24 + the slot pointer, MHGU_Editor docs/11-save-map.md).

pub const SLOT_SIZE: usize = 0x11F8C4;
/// each file's fixed size, the budget: created at that size, only the bytes in use matter
pub const FILE_SIZE: usize = 0x8000;
pub const HEADER: usize = 32;
/// the reserved block (sUserInfo +0x3684) in the slot; the link record at its start
pub const RESERVED: usize = 0x50BE;
pub const LINK_N: usize = 16;
/// link states: the file holds the rest / the last save could not write the file (GU's slot holds everything)
pub const SPLIT: u8 = 1;
pub const FULL: u8 = 2;

const BOX: usize = 0x278;
const BOX_N: usize = 2300;
const POUCH: usize = 0x27BF;
const POUCH_N: usize = 32;
const LOADOUTS: usize = 0x17CF;
const LOADOUT_N: usize = 24;
const LOADOUT_SZ: usize = 170;
const LOADOUT_ITEMS: usize = 42;
const OBTAINED: usize = 0x22497;
const EQBOX: usize = 0x62EE;
const EQBOX_N: usize = 2000;
const ENTRY: usize = 36;
const WORN: usize = 0x23B39;
const MYSETS: usize = 0x208C8;
const MYSET_N: usize = 40;
const MYSET: usize = 0x88;
const WORN_CACHE: usize = 0x10C;
const CARD_GEAR: usize = 0xC7211;
const CARD_HISTORY: usize = 0xC7AD5;
const HISTORY_N: usize = 10;
const HISTORY: usize = 160;
const MELDING: usize = 0x227A7;
const MELDING_N: usize = 10;
const MELDING_SZ: usize = 420;
const RESERVED_N: usize = 3444;
const QUEST_MAP_BITS: u32 = 0x800;
const NONE: u32 = 0xFFFF;

// GU v1.4's own table counts: what is past them is the mod's
const ITEM_FIRST_ADDED: u32 = 2977;
const DECO_LO: u32 = 2889;
const DECO_HI: u32 = 2899;
const ARMOR: u32 = 1287;
const DECO_CREATE: u32 = 275;
const STARTER_CLASS: u32 = 1;
const STARTER_ID: u32 = 1;
const WEAPONS: [u32; 15] = [137, 129, 132, 127, 109, 0, 110, 127, 110, 115, 108, 126, 112, 83, 81];
const ARMOR_CREATE: [u32; 5] = [563, 554, 538, 517, 548];
const WEAPON_CREATE: [u32; 15] = [95, 82, 84, 86, 84, 0, 98, 82, 81, 80, 90, 86, 75, 66, 63];
const WEAPON_CLASS: [usize; 2] = [0x240, 0x23B47];
const QUEST_MAPS: [usize; 3] = [0x2C77, 0x2D77, 0x2E77];
const REGISTER: [(usize, usize); 2] = [(0x11D05A, 2), (0x11D05E, 4)];
const TALLIES: [(usize, usize); 3] = [(0x5EA6, 2), (0x5FB8, 2), (0x60CA, 4)];
const LINK_MAGIC: &[u8; 4] = b"MHDL";
const BASIS: u32 = 0x811C_9DC5;

const K_ITEM: u8 = 1;
const K_GEAR: u8 = 2;
const K_BYTES: u8 = 3;
const K_REGION: u8 = 4;
const K_BITS: u8 = 5;
const K_QUESTS: u8 = 6;
const K_ASIDE: u8 = 7;

/// A quest list index that is the mod's, and its quest (the manifest's `save_format.quests`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Quest {
    pub index: u32,
    pub id: u32,
}

/// The link record of a slot.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Link {
    pub id: u32,
    pub generation: u32,
    pub state: u8,
}

/// A file's header fields.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Header {
    pub used: usize,
    pub link: u32,
    pub generation: u32,
    pub slot_hash: u32,
}

/// What a merge did.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Stats {
    /// the slot's hash matched the file's: unchanged since the split
    pub exact: bool,
    /// records put back, put back elsewhere, left as GU's slot has them, without a place (kept for the next file)
    pub placed: u32,
    pub moved: u32,
    pub kept: u32,
    pub aside: u32,
}

// ------------------------------------------------------------------------------------------ helpers

pub fn fnv(p: &[u8], mut h: u32) -> u32 {
    for &x in p {
        h = (h ^ x as u32).wrapping_mul(0x0100_0193);
    }
    h
}

fn rd16(b: &[u8], o: usize) -> u32 {
    b[o] as u32 | (b[o + 1] as u32) << 8
}
fn rd32(b: &[u8], o: usize) -> u32 {
    rd16(b, o) | rd16(b, o + 2) << 16
}
fn wr16(b: &mut [u8], o: usize, v: u32) {
    b[o] = v as u8;
    b[o + 1] = (v >> 8) as u8;
}
fn wr32(b: &mut [u8], o: usize, v: u32) {
    wr16(b, o, v);
    wr16(b, o + 2, v >> 16);
}
fn any(b: &[u8]) -> bool {
    b.iter().any(|&x| x != 0)
}
fn getbit(s: &[u8], o: usize, b: u32) -> bool {
    s[o + (b >> 3) as usize] >> (b & 7) & 1 != 0
}
fn setbit(s: &mut [u8], o: usize, b: u32, v: bool) {
    let p = &mut s[o + (b >> 3) as usize];
    let m = 1u8 << (b & 7);
    *p = if v { *p | m } else { *p & !m };
}
fn getbits(s: &[u8], o: usize, b: u32, n: u32) -> u32 {
    (0..n).fold(0, |v, i| v | (getbit(s, o, b + i) as u32) << i)
}
fn setbits(s: &mut [u8], o: usize, b: u32, n: u32, v: u32) {
    for i in 0..n {
        setbit(s, o, b + i, v >> i & 1 != 0);
    }
}

fn item_added(i: u32) -> bool {
    i >= ITEM_FIRST_ADDED || (DECO_LO..=DECO_HI).contains(&i)
}

/// entry kind: 0 empty, 1 armor (part), 2 talisman, 3 weapon (class), 4 other
fn kind_of(e: &[u8]) -> (u32, u32) {
    let t = rd16(e, 0) & 0x1F;
    match t {
        0 => (0, 0),
        1..=5 => (1, t),
        6 => (2, 0),
        7..=21 => (3, t - 7),
        _ => (4, t),
    }
}

fn entry_added(e: &[u8]) -> bool {
    let (k, c) = kind_of(e);
    let i = rd16(e, 2);
    (k == 1 && i >= ARMOR) || (k == 3 && i >= WEAPONS[c as usize])
}

/// 3 x u16: the vanilla ones kept packed from the first
fn jewels_clean(j: &mut [u8]) {
    let d: Vec<u32> = (0..3).map(|x| rd16(j, 2 * x)).filter(|&v| v != 0 && !item_added(v)).collect();
    for x in 0..3 {
        wr16(j, 2 * x, d.get(x).copied().unwrap_or(0));
    }
}

fn entry_clean(e: &[u8]) -> [u8; ENTRY] {
    let mut out = [0u8; ENTRY];
    out.copy_from_slice(&e[..ENTRY]);
    jewels_clean(&mut out[6..12]);
    if kind_of(&out).0 == 1 && rd16(&out, 4) >= ARMOR {
        wr16(&mut out, 4, 0);
        let v = rd16(&out, 0) & !(0x1F << 10);
        wr16(&mut out, 0, v);
    }
    out
}

fn starter_entry() -> [u8; ENTRY] {
    let mut e = [0u8; ENTRY];
    wr16(&mut e, 0, 7 + STARTER_CLASS);
    wr16(&mut e, 2, STARTER_ID);
    e
}

const BIT_RANGES: usize = 1 + 10 + 45 + 8;

/// the bit maps keyed by an added ID: (offset, first added bit, bits), the order of tools/modsave.py bit_ranges()
fn bit_range(k: usize) -> (usize, u32, u32) {
    if k == 0 {
        return (OBTAINED, ITEM_FIRST_ADDED, 3008);
    }
    let k = k - 1;
    if k < 10 {
        let p = k / 2;
        let listed = 4 * ARMOR_CREATE[p];
        let first = if k & 1 == 1 { listed.max(ARMOR) } else { listed };
        return (0x3907 + 576 * p + if k & 1 == 1 { 288 } else { 0 }, first, 288 * 8);
    }
    let k = k - 10;
    if k < 45 {
        let (t, w) = (k / 3, k % 3);
        return match w {
            0 => (0x36AF + 40 * t, WEAPON_CREATE[t], 160),
            1 => (0x36AF + 40 * t + 20, WEAPONS[t].max(WEAPON_CREATE[t]), 160),
            _ => (0x45DF + 128 * t, WEAPONS[t], 1024),
        };
    }
    match k - 45 {
        0 => (0x4D5F, ARMOR, 5248),
        1 => (0x31A7, DECO_CREATE, 288),
        2 => (0x31CB, DECO_CREATE, 288),
        3 => (0x32B7, 123, 128),
        4 => (0x32C7, 123, 128),
        n @ 5..=7 => (0x11CFD4 + 12 * (n - 5), 89, 96),
        _ => (0, 0, 0),
    }
}

// ------------------------------------------------------------------------------------------ split

struct Out<'a> {
    f: Vec<u8>,
    cap: usize,
    left: u32,
    slot: &'a mut [u8],
    clean: bool,
}

impl Out<'_> {
    /// a record header into the file when the record fits (its payload follows); false: past the budget
    fn put(&mut self, kind: u8, len: usize) -> bool {
        if self.f.len() + 4 + len > self.cap {
            self.left += 1;
            return false;
        }
        self.f.extend([kind, 0]);
        self.f.extend((len as u16).to_le_bytes());
        true
    }

    /// bytes: (offset, n, original, vanilla); the vanilla bytes go to the slot
    fn bytes(&mut self, o: usize, van: &[u8]) {
        let n = van.len();
        if !self.put(K_BYTES, 6 + 2 * n) {
            return;
        }
        self.f.extend((o as u32).to_le_bytes());
        self.f.extend((n as u16).to_le_bytes());
        self.f.extend_from_slice(&self.slot[o..o + n]);
        self.f.extend_from_slice(van);
        if self.clean {
            self.slot[o..o + n].copy_from_slice(van);
        }
    }

    fn region(&mut self, o: usize, n: usize) {
        if !self.put(K_REGION, 6 + n) {
            return;
        }
        self.f.extend((o as u32).to_le_bytes());
        self.f.extend((n as u16).to_le_bytes());
        self.f.extend_from_slice(&self.slot[o..o + n]);
        if self.clean {
            self.slot[o..o + n].fill(0);
        }
    }
}

/// The split of one slot: the mod file (its bytes in use: pad to `FILE_SIZE` to write it) and the records the budget
/// left in the slot, or None when the slot cannot be split (the hunter holds an added weapon and the box has neither
/// a vanilla weapon nor an empty entry). With `clean`, the slot loses what the file holds and gets the link record
/// "split"; without, the slot is not changed. `aside` = records a merge could not place, appended as aside records.
pub fn split(
    slot: &mut [u8],
    q: &[Quest],
    link: u32,
    generation: u32,
    aside: &[u8],
    cap: usize,
    clean: bool,
) -> Option<(Vec<u8>, u32)> {
    assert_eq!(slot.len(), SLOT_SIZE);
    if cap < HEADER {
        return None;
    }
    let added: Vec<bool> = (0..EQBOX_N).map(|i| entry_added(&slot[EQBOX + ENTRY * i..])).collect();
    let empty0: Vec<bool> = (0..EQBOX_N).map(|i| !any(&slot[EQBOX + ENTRY * i..EQBOX + ENTRY * (i + 1)])).collect();
    let is_added = |b: u32| b != NONE && (b as usize) < EQBOX_N && added[b as usize];
    // the worn gear (before the file, which borrows the slot)
    let worn: Vec<u32> = (0..7).map(|k| rd16(slot, WORN + 2 * k)).collect();
    let mut van = worn.clone();
    let mut placeholder = NONE;
    let mut worn_rec: Option<([u8; 14], Option<usize>, Vec<(usize, u8)>)> = None;
    if worn.iter().any(|&b| is_added(b)) {
        let mut starter_at = None;
        let mut cls_new = 0;
        for v in van.iter_mut().skip(1) {
            if is_added(*v) {
                *v = NONE;
            }
        }
        if is_added(worn[0]) {
            let (_, wcls) = kind_of(&slot[EQBOX + ENTRY * worn[0] as usize..]);
            let mut got = NONE;
            'pass: for pass in 0..2 {
                for j in 0..EQBOX_N {
                    let (k, c) = kind_of(&slot[EQBOX + ENTRY * j..]);
                    if k == 3 && !added[j] && (pass == 1 || c == wcls) {
                        got = j as u32;
                        cls_new = c;
                        break 'pass;
                    }
                }
            }
            if got == NONE {
                let j = (0..EQBOX_N).find(|&j| empty0[j])?; // nothing for the hunter to hold
                got = j as u32;
                starter_at = Some(j);
                cls_new = STARTER_CLASS;
            }
            van[0] = got;
        }
        let mut v = [0u8; 14];
        for (k, &b) in van.iter().enumerate() {
            wr16(&mut v, 2 * k, b);
        }
        let mut cls = vec![];
        if van[0] != worn[0] {
            for &o in &WEAPON_CLASS {
                if slot[o] as u32 != cls_new {
                    cls.push((o, cls_new as u8));
                }
            }
            placeholder = van[0];
        }
        worn_rec = Some((v, starter_at, cls));
    }
    let mut w = Out { f: vec![0u8; HEADER], cap, left: 0, slot, clean };
    if let Some((v, starter_at, cls)) = worn_rec {
        w.bytes(WORN, &v);
        if let Some(j) = starter_at {
            w.bytes(EQBOX + ENTRY * j, &starter_entry());
        }
        for (o, b) in cls {
            w.bytes(o, &[b]);
        }
    }
    // the slot header's copies of the worn pieces
    for k in 0..7 {
        let o = WORN_CACHE + 44 * k + 4;
        if !any(&w.slot[o..o + ENTRY]) {
            continue;
        }
        let e = if entry_added(&w.slot[o..]) {
            if k == 0 && placeholder != NONE {
                let p = EQBOX + ENTRY * placeholder as usize;
                if !any(&w.slot[p..p + ENTRY]) { starter_entry() } else { entry_clean(&w.slot[p..]) }
            } else {
                [0u8; ENTRY]
            }
        } else {
            entry_clean(&w.slot[o..])
        };
        if e[..] != w.slot[o..o + ENTRY] {
            w.bytes(o, &e);
        }
    }
    // the own Guild Card's equipment snapshot
    for k in 0..7 {
        let o = CARD_GEAR + 44 * k;
        if !any(&w.slot[o..o + 44]) {
            continue;
        }
        let mut cg = [0u8; 44];
        cg.copy_from_slice(&w.slot[o..o + 44]);
        let mut e36 = [0u8; ENTRY];
        e36[..4].copy_from_slice(&cg[..4]);
        if entry_added(&e36) {
            cg = [0; 44];
        } else {
            jewels_clean(&mut cg[8..14]);
            if kind_of(&e36).0 == 1 && rd16(&cg, 0x28) >= ARMOR {
                wr16(&mut cg, 0x28, 0);
            }
        }
        if cg[..] != w.slot[o..o + 44] {
            w.bytes(o, &cg);
        }
    }
    // the card's quest history
    for k in 0..HISTORY_N {
        let o = CARD_HISTORY + HISTORY * k;
        let id = rd16(w.slot, o + 6);
        if q.iter().any(|x| x.id == id) {
            w.bytes(o, &[0u8; HISTORY]);
        }
    }
    // the Item Register touch panels
    for &(o0, n) in &REGISTER {
        for j in 0..n {
            let o = o0 + 2 * j;
            let id = rd16(w.slot, o);
            if id != 0 && item_added(id) {
                w.bytes(o, &[0, 0]);
            }
        }
    }
    // the Melding Pot's talismans
    for k in 0..MELDING_N {
        for j in 0..3 {
            let o = MELDING + MELDING_SZ * k + 4 + ENTRY * j;
            if !any(&w.slot[o..o + ENTRY]) {
                continue;
            }
            let e = entry_clean(&w.slot[o..]);
            if e[..] != w.slot[o..o + ENTRY] {
                w.bytes(o, &e);
            }
        }
    }
    // the dummy entries' tallies (D2)
    for &(o0, sz) in &TALLIES {
        let (o, n) = (o0 + sz * 105, sz * 7);
        if any(&w.slot[o..o + n]) {
            w.region(o, n);
        }
    }
    // My Sets
    for k in 0..MYSET_N {
        let o = MYSETS + MYSET * k;
        let mut v = [0u8; MYSET];
        v.copy_from_slice(&w.slot[o..o + MYSET]);
        for j in 0..7 {
            if is_added(rd16(&v, 0x30 + 2 * j)) {
                wr16(&mut v, 0x30 + 2 * j, NONE);
                v[0x3E + 6 * j..0x3E + 6 * j + 6].fill(0);
            }
            jewels_clean(&mut v[0x3E + 6 * j..0x3E + 6 * j + 6]);
        }
        if v[..] != w.slot[o..o + MYSET] {
            w.bytes(o, &v);
        }
    }
    // the reserved block past the link record: runs of non-zero bytes, gaps under 8 zeros inside a run
    let (lo, hi) = (RESERVED + LINK_N, RESERVED + RESERVED_N);
    let mut a = lo;
    while a < hi {
        if w.slot[a] == 0 {
            a += 1;
            continue;
        }
        let (mut b, mut z) = (a, 0);
        while b < hi && z < 8 {
            z = if w.slot[b] != 0 { 0 } else { z + 1 };
            b += 1;
        }
        b -= z;
        w.region(a, b - a);
        a = b;
    }
    // bit maps: runs of set bits
    for k in 0..BIT_RANGES {
        let (o, first, n) = bit_range(k);
        let mut b = first;
        while b < n {
            if !getbit(w.slot, o, b) {
                b += 1;
                continue;
            }
            let mut x = b;
            while x < n && x - b < 0xFFFF && getbit(w.slot, o, x) {
                x += 1;
            }
            if w.put(K_BITS, 8) {
                w.f.extend((o as u32).to_le_bytes());
                w.f.extend((b as u16).to_le_bytes());
                w.f.extend(((x - b) as u16).to_le_bytes());
                if clean {
                    for y in b..x {
                        setbit(w.slot, o, y, false);
                    }
                }
            }
            b = x;
        }
    }
    // quest bits by quest ID
    for (k, &map) in QUEST_MAPS.iter().enumerate() {
        let set: Vec<u32> =
            q.iter().filter(|x| x.index < QUEST_MAP_BITS && getbit(w.slot, map, x.index)).map(|x| x.id).collect();
        if set.is_empty() || !w.put(K_QUESTS, 3 + 4 * set.len()) {
            continue;
        }
        w.f.push(k as u8);
        w.f.extend((set.len() as u16).to_le_bytes());
        for id in &set {
            w.f.extend(id.to_le_bytes());
        }
        if clean {
            for x in q.iter().filter(|x| x.index < QUEST_MAP_BITS) {
                setbit(w.slot, map, x.index, false);
            }
        }
    }
    // gear
    for (i, &is) in added.iter().enumerate() {
        let o = EQBOX + ENTRY * i;
        if is {
            if !w.put(K_GEAR, 2 + ENTRY) {
                continue;
            }
            w.f.extend((i as u16).to_le_bytes());
            w.f.extend_from_slice(&w.slot[o..o + ENTRY]);
            if clean {
                w.slot[o..o + ENTRY].fill(0);
            }
        } else if kind_of(&w.slot[o..]).0 != 0 {
            let e = entry_clean(&w.slot[o..]);
            if e[..] != w.slot[o..o + ENTRY] {
                w.bytes(o, &e);
            }
        }
    }
    // items
    for (k, &(o, n)) in [(BOX, BOX_N), (POUCH, POUCH_N)].iter().enumerate() {
        for i in 0..n as u32 {
            let id = getbits(w.slot, o, 19 * i, 12);
            let cnt = getbits(w.slot, o, 19 * i + 12, 7);
            if id == 0 || !item_added(id) || !w.put(K_ITEM, 6) {
                continue;
            }
            w.f.push(k as u8);
            w.f.extend((i as u16).to_le_bytes());
            w.f.extend((id as u16).to_le_bytes());
            w.f.push(cnt as u8);
            if clean {
                setbits(w.slot, o, 19 * i, 19, 0);
            }
        }
    }
    for k in 0..LOADOUT_N {
        for j in 0..32 {
            let o = LOADOUTS + LOADOUT_SZ * k + LOADOUT_ITEMS + 4 * j;
            let id = rd16(w.slot, o);
            if id == 0 || !item_added(id) || !w.put(K_ITEM, 6) {
                continue;
            }
            let cnt = rd16(w.slot, o + 2);
            w.f.push(2);
            w.f.extend(((32 * k + j) as u16).to_le_bytes());
            w.f.extend((id as u16).to_le_bytes());
            w.f.push(cnt as u8);
            if clean {
                w.slot[o..o + 4].fill(0);
            }
        }
    }
    // records the last merge could not place
    let mut i = 0;
    while i + 4 <= aside.len() {
        let n = 4 + rd16(aside, i + 2) as usize;
        if i + n > aside.len() {
            break;
        }
        if w.put(K_ASIDE, n) {
            w.f.extend_from_slice(&aside[i..i + n]);
        }
        i += n;
    }
    if clean {
        set_link(w.slot, Link { id: link, generation, state: SPLIT });
    }
    let slot_hash = if clean { fnv(w.slot, BASIS) } else { 0 };
    let (mut f, left) = (w.f, w.left);
    let n = f.len() as u32;
    f[0..4].copy_from_slice(b"MHDE");
    wr16(&mut f, 4, 1);
    wr16(&mut f, 6, 0);
    wr32(&mut f, 8, n);
    wr32(&mut f, 16, link);
    wr32(&mut f, 20, generation);
    wr32(&mut f, 24, slot_hash);
    wr32(&mut f, 28, 0);
    let c = fnv(&f[16..], fnv(&f[0..12], BASIS));
    wr32(&mut f, 12, c);
    Some((f, left))
}

/// Whether the slot holds anything of the mod's (a record to split, or an added weapon held with no way to swap it).
pub fn holds_added(slot: &[u8], q: &[Quest]) -> bool {
    let mut s = slot.to_vec();
    match split(&mut s, q, 0, 0, &[], usize::MAX, false) {
        Some((f, _)) => f.len() > HEADER,
        None => true,
    }
}

// ------------------------------------------------------------------------------------------ link

pub fn link(slot: &[u8]) -> Option<Link> {
    let p = &slot[RESERVED..RESERVED + LINK_N];
    (&p[..4] == LINK_MAGIC).then(|| Link { id: rd32(p, 4), generation: rd32(p, 8), state: p[12] })
}

pub fn set_link(slot: &mut [u8], l: Link) {
    let p = &mut slot[RESERVED..RESERVED + LINK_N];
    p[..4].copy_from_slice(LINK_MAGIC);
    wr32(p, 4, l.id);
    wr32(p, 8, l.generation);
    p[12] = l.state;
    p[13..16].fill(0);
}

// ------------------------------------------------------------------------------------------ merge

/// The file's header, when it is a valid file (magic, size, check word, every record inside the bytes used).
pub fn parse(f: &[u8]) -> Option<Header> {
    if f.len() < HEADER || &f[..4] != b"MHDE" {
        return None;
    }
    let n = rd32(f, 8) as usize;
    if n < HEADER || n > f.len() || rd32(f, 12) != fnv(&f[16..n], fnv(&f[..12], BASIS)) {
        return None;
    }
    let mut o = HEADER;
    while o < n {
        if o + 4 > n || o + 4 + rd16(f, o + 2) as usize > n {
            return None;
        }
        o += 4 + rd16(f, o + 2) as usize;
    }
    Some(Header { used: n, link: rd32(f, 16), generation: rd32(f, 20), slot_hash: rd32(f, 24) })
}

/// The records of a file in order, aside records unwrapped: (kind, flags, payload).
fn records(f: &[u8], used: usize) -> Vec<(u8, u8, &[u8])> {
    let mut out = vec![];
    let mut o = HEADER;
    while o + 4 <= used {
        let (mut kind, mut flags, len) = (f[o], f[o + 1], rd16(f, o + 2) as usize);
        let mut p = &f[o + 4..o + 4 + len];
        o += 4 + len;
        if kind == K_ASIDE && len >= 4 {
            let n = rd16(p, 2) as usize;
            if 4 + n > p.len() {
                continue; // a damaged aside record (parse checks the outer one only)
            }
            (kind, flags) = (p[0], p[1]);
            p = &p[4..4 + n];
        }
        out.push((kind, flags, p));
    }
    out
}

fn aside_put(a: &mut Vec<u8>, kind: u8, flags: u8, p: &[u8]) {
    a.extend([kind, flags]);
    a.extend((p.len() as u16).to_le_bytes());
    a.extend_from_slice(p);
}

/// The merge: the file's records back into the slot (notes/mod-save-format.md "The merge"). Returns what it did and
/// the records without a place (aside records for the next split), or None when `f` is not a valid file.
pub fn merge(slot: &mut [u8], f: &[u8], q: &[Quest]) -> Option<(Stats, Vec<u8>)> {
    assert_eq!(slot.len(), SLOT_SIZE);
    let h = parse(f)?;
    let mut st = Stats { exact: fnv(slot, BASIS) == h.slot_hash, ..Default::default() };
    let mut aside = vec![];
    let mut moved = vec![NONE; EQBOX_N];
    let recs = records(f, h.used);
    let empty = |s: &[u8], j: usize| !any(&s[EQBOX + ENTRY * j..EQBOX + ENTRY * (j + 1)]);
    // gear first: the references follow a piece that had to move
    for &(kind, fl, p) in &recs {
        if kind != K_GEAR || p.len() < 2 + ENTRY {
            continue;
        }
        let i = rd16(p, 0) as usize;
        if i >= EQBOX_N {
            aside_put(&mut aside, kind, fl, p);
            continue;
        }
        if slot[EQBOX + ENTRY * i..EQBOX + ENTRY * (i + 1)] == p[2..2 + ENTRY] {
            moved[i] = i as u32;
            continue;
        }
        let j = if empty(slot, i) { Some(i) } else { (0..EQBOX_N).find(|&j| empty(slot, j)) };
        let Some(j) = j else {
            aside_put(&mut aside, kind, fl, p);
            continue;
        };
        slot[EQBOX + ENTRY * j..EQBOX + ENTRY * (j + 1)].copy_from_slice(&p[2..2 + ENTRY]);
        moved[i] = j as u32;
        st.placed += 1;
        st.moved += (j != i) as u32;
    }
    for &(kind, fl, p) in &recs {
        let n = p.len();
        match kind {
            K_BYTES => {
                let (at, m) = if n >= 6 { (rd32(p, 0) as usize, rd16(p, 4) as usize) } else { (0, usize::MAX / 4) };
                if n < 6 + 2 * m || at + m > SLOT_SIZE {
                    aside_put(&mut aside, kind, fl, p);
                    continue;
                }
                let (orig, van) = (&p[6..6 + m], &p[6 + m..6 + 2 * m]);
                if slot[at..at + m] == *orig {
                    continue;
                }
                if slot[at..at + m] != *van {
                    st.kept += 1;
                    continue;
                }
                slot[at..at + m].copy_from_slice(orig);
                if at == WORN && m == 14 {
                    for x in 0..7 {
                        let b = rd16(orig, 2 * x) as usize;
                        if b < EQBOX_N && moved[b] != NONE {
                            wr16(slot, at + 2 * x, moved[b]);
                        }
                    }
                } else if (MYSETS..MYSETS + MYSET * MYSET_N).contains(&at) && m == MYSET {
                    for x in 0..7 {
                        let b = rd16(orig, 0x30 + 2 * x) as usize;
                        if b < EQBOX_N && moved[b] != NONE {
                            wr16(slot, at + 0x30 + 2 * x, moved[b]);
                        }
                    }
                }
                st.placed += 1;
            }
            K_REGION => {
                let (at, m) = if n >= 6 { (rd32(p, 0) as usize, rd16(p, 4) as usize) } else { (0, usize::MAX / 4) };
                if n < 6 + m || at + m > SLOT_SIZE {
                    aside_put(&mut aside, kind, fl, p);
                    continue;
                }
                if slot[at..at + m] == p[6..6 + m] {
                    continue;
                }
                if any(&slot[at..at + m]) {
                    st.kept += 1;
                    continue;
                }
                slot[at..at + m].copy_from_slice(&p[6..6 + m]);
                st.placed += 1;
            }
            K_BITS => {
                if n < 8 || rd32(p, 0) as usize + ((rd16(p, 4) + rd16(p, 6) + 7) >> 3) as usize > SLOT_SIZE {
                    aside_put(&mut aside, kind, fl, p);
                    continue;
                }
                let (at, b, m) = (rd32(p, 0) as usize, rd16(p, 4), rd16(p, 6));
                for x in b..b + m {
                    setbit(slot, at, x, true);
                }
                st.placed += 1;
            }
            K_QUESTS => {
                let (m, c) = if n >= 3 { (p[0] as usize, rd16(p, 1) as usize) } else { (3, 0) };
                if n < 3 + 4 * c || m > 2 {
                    aside_put(&mut aside, kind, fl, p);
                    continue;
                }
                for x in 0..c {
                    let id = rd32(p, 3 + 4 * x);
                    match q.iter().find(|e| e.id == id).filter(|e| e.index < QUEST_MAP_BITS) {
                        Some(e) => setbit(slot, QUEST_MAPS[m], e.index, true),
                        None => {
                            let mut one = [m as u8, 1, 0, 0, 0, 0, 0];
                            wr32(&mut one, 3, id);
                            aside_put(&mut aside, K_QUESTS, 0, &one);
                        }
                    }
                }
                st.placed += 1;
            }
            K_ITEM => {
                if n < 6 {
                    aside_put(&mut aside, kind, fl, p);
                    continue;
                }
                let (s_, at, id, cnt) = (p[0], rd16(p, 1), rd16(p, 3), p[5] as u32);
                let j;
                if s_ < 2 {
                    let (base, cap) = if s_ == 1 { (POUCH, POUCH_N as u32) } else { (BOX, BOX_N as u32) };
                    if at >= cap {
                        aside_put(&mut aside, kind, fl, p);
                        continue;
                    }
                    if getbits(slot, base, 19 * at, 12) == id && getbits(slot, base, 19 * at + 12, 7) == cnt {
                        continue;
                    }
                    let free = if getbits(slot, base, 19 * at, 12) == 0 {
                        Some(at)
                    } else {
                        (0..cap).find(|&j| getbits(slot, base, 19 * j, 12) == 0)
                    };
                    let Some(f) = free else {
                        aside_put(&mut aside, kind, fl, p);
                        continue;
                    };
                    setbits(slot, base, 19 * f, 12, id);
                    setbits(slot, base, 19 * f + 12, 7, cnt);
                    j = f;
                } else {
                    if s_ != 2 || at >= 32 * LOADOUT_N as u32 {
                        aside_put(&mut aside, kind, fl, p);
                        continue;
                    }
                    let lo = LOADOUTS + LOADOUT_SZ * (at / 32) as usize + LOADOUT_ITEMS + 4 * (at % 32) as usize;
                    if rd16(slot, lo) == id && rd16(slot, lo + 2) == cnt {
                        continue;
                    }
                    if rd16(slot, lo) != 0 {
                        aside_put(&mut aside, kind, fl, p);
                        continue;
                    }
                    wr16(slot, lo, id);
                    wr16(slot, lo + 2, cnt);
                    j = at;
                }
                st.placed += 1;
                st.moved += (j != at) as u32;
            }
            K_GEAR => {}
            _ => aside_put(&mut aside, kind, fl, p), // a kind this release doesn't know: kept
        }
    }
    let mut i = 0;
    while i + 4 <= aside.len() {
        st.aside += 1;
        i += 4 + rd16(&aside, i + 2) as usize;
    }
    Some((st, aside))
}

/// A file ready to write: the bytes in use, then zeros up to `FILE_SIZE` (the size the game creates it at and never
/// grows: its write fails past the end).
pub fn padded(f: &[u8]) -> Vec<u8> {
    let mut v = f.to_vec();
    v.resize(FILE_SIZE.max(f.len()), 0);
    v
}

#[cfg(test)]
mod tests {
    use super::*;

    const Q: [Quest; 2] = [Quest { index: 1509, id: 10542 }, Quest { index: 40, id: 10501 }];

    /// a slot holding one of each kind (no game data: numbers only)
    pub(crate) fn synthetic() -> Vec<u8> {
        let mut s = vec![0u8; SLOT_SIZE];
        setbits(&mut s, BOX, 0, 12, 100); // a GU item
        setbits(&mut s, BOX, 12, 7, 5);
        setbits(&mut s, BOX, 19, 12, 2991); // an added item
        setbits(&mut s, BOX, 31, 7, 3);
        setbits(&mut s, POUCH, 19 * 4, 12, 2980);
        setbits(&mut s, POUCH, 19 * 4 + 12, 7, 1);
        wr16(&mut s, LOADOUTS + LOADOUT_ITEMS, 2995);
        wr16(&mut s, LOADOUTS + LOADOUT_ITEMS + 2, 2);
        let e = |t: u32, id: u32| {
            let mut e = [0u8; ENTRY];
            wr16(&mut e, 0, t);
            wr16(&mut e, 2, id);
            e
        };
        s[EQBOX..EQBOX + ENTRY].copy_from_slice(&e(7 + 4, 200)); // an added weapon, class 4
        s[EQBOX + ENTRY..EQBOX + 2 * ENTRY].copy_from_slice(&e(7 + 4, 3)); // a GU weapon of the class
        let mut h = e(1, 1300); // an added head
        wr16(&mut h, 6, 2890); // an added jewel
        s[EQBOX + 2 * ENTRY..EQBOX + 3 * ENTRY].copy_from_slice(&h);
        let mut c = e(2, 40); // a GU chest with a jewel of each
        wr16(&mut c, 6, 2891);
        wr16(&mut c, 8, 1500);
        s[EQBOX + 3 * ENTRY..EQBOX + 4 * ENTRY].copy_from_slice(&c);
        for k in 0..7 {
            wr16(&mut s, WORN + 2 * k, NONE);
        }
        wr16(&mut s, WORN, 0);
        wr16(&mut s, WORN + 2, 2);
        wr16(&mut s, WORN + 4, 3);
        s[WEAPON_CLASS[0]] = 4;
        s[WEAPON_CLASS[1]] = 4;
        wr16(&mut s, MYSETS + 0x30, 0);
        setbit(&mut s, OBTAINED, 2991, true);
        setbit(&mut s, OBTAINED, 2992, true);
        setbit(&mut s, 0x4D5F, 1300, true);
        setbit(&mut s, QUEST_MAPS[0], 1509, true);
        setbit(&mut s, QUEST_MAPS[0], 40, true);
        setbit(&mut s, QUEST_MAPS[0], 39, true); // a GU quest
        s[RESERVED + 0x3900 - 0x3684..RESERVED + 0x3900 - 0x3684 + 4].copy_from_slice(b"MH4S");
        wr16(&mut s, TALLIES[0].0 + 2 * 106, 7);
        wr16(&mut s, CARD_HISTORY + 6, 10542);
        s[CARD_HISTORY + 8] = 1;
        s
    }

    #[test]
    fn split_then_merge_gives_the_slot_back_byte_for_byte() {
        let orig = synthetic();
        let mut s = orig.clone();
        let (f, left) = split(&mut s, &Q, 0x1234_5679, 1, &[], FILE_SIZE, true).unwrap();
        assert_eq!(left, 0);
        assert!(!holds_added(&s, &Q), "nothing of the mod's left in GU's slot");
        assert_eq!(link(&s), Some(Link { id: 0x1234_5679, generation: 1, state: SPLIT }));
        assert_eq!(rd16(&s, WORN), 1, "the hunter holds the GU weapon of the class");
        assert!(getbit(&s, QUEST_MAPS[0], 39) && !getbit(&s, QUEST_MAPS[0], 1509));
        let h = parse(&f).unwrap();
        assert_eq!((h.used, h.link, h.generation), (f.len(), 0x1234_5679, 1));
        // the compute-only split writes the same records and leaves the slot alone
        let mut t = orig.clone();
        let (g, _) = split(&mut t, &Q, 0x1234_5679, 1, &[], FILE_SIZE, false).unwrap();
        assert_eq!(t, orig);
        assert_eq!((&g[..12], &g[16..24], &g[32..]), (&f[..12], &f[16..24], &f[32..]));
        let (st, aside) = merge(&mut s, &f, &Q).unwrap();
        assert!(st.exact && aside.is_empty() && st.moved == 0 && st.kept == 0, "{st:?}");
        s[RESERVED..RESERVED + LINK_N].fill(0);
        assert!(s == orig, "merge(split(x)) == x");
    }

    #[test]
    fn a_careful_merge_moves_what_found_its_place_taken() {
        let mut s = synthetic();
        let (f, _) = split(&mut s, &Q, 7, 1, &[], FILE_SIZE, true).unwrap();
        // without the mod: a GU item where the added one was, a GU piece in the added head's entry
        setbits(&mut s, BOX, 19, 12, 101);
        setbits(&mut s, BOX, 31, 7, 1);
        s[EQBOX + 2 * ENTRY] = 3;
        let (st, aside) = merge(&mut s, &f, &Q).unwrap();
        assert!(!st.exact && st.moved == 2 && aside.is_empty(), "{st:?}");
        assert_eq!(getbits(&s, BOX, 19, 12), 101, "GU's item kept");
        assert_eq!(getbits(&s, BOX, 19 * 2, 12), 2991, "the added item in the next free place");
        assert_eq!(rd16(&s, EQBOX + 4 * ENTRY + 2), 1300, "the head in the first empty entry");
        assert_eq!(rd16(&s, WORN + 2), 4, "and the worn head follows it");
    }

    #[test]
    fn damaged_files_are_refused_and_unknown_kinds_kept() {
        let mut s = synthetic();
        let (mut f, _) = split(&mut s, &Q, 7, 1, &[], FILE_SIZE, true).unwrap();
        assert!(parse(&f[..f.len() - 1]).is_none(), "cut short");
        let mut g = f.clone();
        g[40] ^= 1;
        assert!(parse(&g).is_none(), "check word");
        assert!(merge(&mut s.clone(), &g, &Q).is_none());
        // an unknown kind (9) appended: kept aside, and written back by the next split
        f.extend([9, 0, 2, 0, 0xAB, 0xCD]);
        let n = f.len() as u32;
        wr32(&mut f, 8, n);
        let c = fnv(&f[16..], fnv(&f[..12], BASIS));
        wr32(&mut f, 12, c);
        let (st, aside) = merge(&mut s, &f, &Q).unwrap();
        assert_eq!((st.aside, &aside[..]), (1, &[9u8, 0, 2, 0, 0xAB, 0xCD][..]));
        let (f2, _) = split(&mut s, &Q, 7, 2, &aside, FILE_SIZE, true).unwrap();
        assert!(f2.ends_with(&[7, 0, 6, 0, 9, 0, 2, 0, 0xAB, 0xCD]));
    }

    #[test]
    fn a_tiny_budget_leaves_the_rest_in_the_slot() {
        let orig = synthetic();
        let mut s = orig.clone();
        let (f, left) = split(&mut s, &Q, 7, 1, &[], HEADER + 30, true).unwrap();
        assert!(f.len() <= HEADER + 30 && left > 0);
        assert!(holds_added(&s, &Q), "what the budget left is still in the slot");
        merge(&mut s, &f, &Q).unwrap();
        s[RESERVED..RESERVED + LINK_N].fill(0);
        assert!(s == orig);
    }
}
