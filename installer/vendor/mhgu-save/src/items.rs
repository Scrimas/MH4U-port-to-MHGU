//! Item box, pouch and loadouts (docs/11-save-map.md; tools/items.py).
//!
//! A box or pouch slot is 19 bits of an LSB-first bit stream: item ID (12 bits), then
//! count (7 bits). ID 0 = empty.

use crate::save::Save;

pub const BOX: usize = 0x278;
pub const BOX_N: usize = 2300;
pub const POUCH: usize = 0x27BF;
pub const POUCH_N: usize = 32;
pub const LOADOUTS: usize = 0x17CF;
pub const LOADOUT_N: usize = 24;
pub const LOADOUT_SZ: usize = 170;
pub const LOADOUT_NAME: usize = 42;
pub const LOADOUT_ITEMS: usize = 32;
pub const MAX_ID: u16 = 0xFFF;
pub const MAX_COUNT: u8 = 99;
/// Items obtained, bit = item ID (sItem `+0x9c`, 94 x u32; CONFIRMED by the save
/// timeline). The game sets a bit when the item first enters the box or pouch, for IDs
/// 1-2990 (`0x1943d4`). The Smithy, the Palico smithy, the shop, the Trader and the talk
/// conditions read it: a Smithy entry needs its key materials obtained, and material
/// names show only once obtained (`0x6fa928`, `0x6ffd40`).
pub const OBTAINED: usize = 0x22497;
pub const OBTAINED_MAX_ID: u16 = 2990;

pub fn obtained(s: &Save, base: usize, id: u16) -> bool {
    (1..=OBTAINED_MAX_ID).contains(&id) && s.bit(base + OBTAINED, id as usize)
}

pub fn set_obtained(s: &mut Save, base: usize, id: u16, v: bool) {
    if (1..=OBTAINED_MAX_ID).contains(&id) {
        s.set_bit(base + OBTAINED, id as usize, v);
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Stack {
    pub id: u16,
    pub count: u8,
}

impl Stack {
    pub fn is_empty(&self) -> bool {
        self.id == 0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Store {
    Box,
    Pouch,
}

impl Store {
    fn at(self) -> (usize, usize) {
        match self {
            Store::Box => (BOX, BOX_N),
            Store::Pouch => (POUCH, POUCH_N),
        }
    }
    // the number of slots of a store, never empty
    #[allow(clippy::len_without_is_empty)]
    pub fn len(self) -> usize {
        self.at().1
    }
}

pub fn get(s: &Save, base: usize, store: Store, i: usize) -> Stack {
    let (off, n) = store.at();
    assert!(i < n);
    Stack { id: s.bits(base + off, 19 * i, 12) as u16, count: s.bits(base + off, 19 * i + 12, 7) as u8 }
}

pub fn set(s: &mut Save, base: usize, store: Store, i: usize, st: Stack) {
    let (off, n) = store.at();
    assert!(i < n);
    // an ID that does not fit the 12-bit field would become another item: empty instead
    let st = if st.id == 0 || st.id > MAX_ID || st.count == 0 { Stack::default() } else { st };
    s.set_bits(base + off, 19 * i, 12, st.id as u32);
    s.set_bits(base + off, 19 * i + 12, 7, st.count.min(MAX_COUNT) as u32);
}

pub fn all(s: &Save, base: usize, store: Store) -> Vec<Stack> {
    (0..store.len()).map(|i| get(s, base, store, i)).collect()
}

pub fn set_all(s: &mut Save, base: usize, store: Store, v: &[Stack]) {
    for i in 0..store.len() {
        set(s, base, store, i, v.get(i).copied().unwrap_or_default());
    }
}

/// Merge stacks of the same item and move used slots to the front, sorted by item ID.
/// Returns the new slot list. Box: stacks of up to 99, overflow kept as extra stacks
/// while slots remain. Pouch: one stack per item of at most `max(id)` (its carry limit);
/// the excess is dropped.
pub fn compact(v: &[Stack], sort: bool, store: Store, max: impl Fn(u16) -> u8) -> Vec<Stack> {
    let mut order: Vec<u16> = vec![];
    let mut totals: std::collections::HashMap<u16, u32> = Default::default();
    for st in v.iter().filter(|s| !s.is_empty()) {
        if !totals.contains_key(&st.id) {
            order.push(st.id);
        }
        *totals.entry(st.id).or_default() += st.count as u32;
    }
    if sort {
        order.sort_unstable();
    }
    let mut out = vec![];
    for id in order {
        let m = max(id).clamp(1, MAX_COUNT) as u32;
        let mut t = if store == Store::Pouch { totals[&id].min(m) } else { totals[&id] };
        while t > 0 && out.len() < v.len() {
            let c = t.min(m);
            out.push(Stack { id, count: c as u8 });
            t -= c;
        }
    }
    out.resize(v.len(), Stack::default());
    out
}

/// The Fill box dialog's categories (data/item-fill.csv, tools/item_fill.py), in the
/// order its tabs list them. DERIVED: an editor grouping; the items the game never keeps
/// in the box (supply, quest, appraised and carried items) are in none.
pub const FILL: [&str; 23] = [
    "low", "high", "g", "hyper", "deviant", "ore", "bone", "plant", "bug", "fish", "heal", "tool", "food", "ammo",
    "coating", "extract", "deco1", "deco2", "deco3", "scrap", "ticket", "trade", "other",
];

/// Put one stack of `count` of each item of `ids` that the box does not hold yet into its
/// empty slots, from the first, in the order given; marks each one obtained, as the game
/// does when an item first enters the box. Stops when the box is full. Returns how many
/// were put in. DERIVED.
pub fn fill(s: &mut Save, base: usize, ids: &[u16], count: u8) -> usize {
    let v = all(s, base, Store::Box);
    let held: std::collections::HashSet<u16> = v.iter().map(|x| x.id).collect();
    let mut empty = v.iter().enumerate().filter(|(_, x)| x.is_empty()).map(|(i, _)| i);
    let mut seen = std::collections::HashSet::new();
    let mut n = 0;
    for &id in ids.iter().filter(|&&id| id != 0 && !held.contains(&id)) {
        if !seen.insert(id) {
            continue;
        }
        let Some(i) = empty.next() else { break };
        set(s, base, Store::Box, i, Stack { id, count: count.clamp(1, MAX_COUNT) });
        set_obtained(s, base, id, true);
        n += 1;
    }
    n
}

#[derive(Debug, Clone, PartialEq)]
pub struct Loadout {
    pub name: String,
    pub items: Vec<(u16, u16)>,
}

fn loadout_at(base: usize, k: usize) -> usize {
    assert!(k < LOADOUT_N, "loadout {k} out of range");
    base + LOADOUTS + LOADOUT_SZ * k
}

pub fn loadout(s: &Save, base: usize, k: usize) -> Loadout {
    let o = loadout_at(base, k);
    Loadout {
        name: s.str(o, LOADOUT_NAME),
        items: (0..LOADOUT_ITEMS)
            .map(|j| (s.u16(o + LOADOUT_NAME + 4 * j), s.u16(o + LOADOUT_NAME + 4 * j + 2)))
            .collect(),
    }
}

pub fn set_loadout(s: &mut Save, base: usize, k: usize, l: &Loadout) {
    let o = loadout_at(base, k);
    s.set_str(o, LOADOUT_NAME, &l.name);
    for j in 0..LOADOUT_ITEMS {
        let (id, c) = l.items.get(j).copied().unwrap_or((0, 0));
        let (id, c) = if id == 0 || id > MAX_ID || c == 0 { (0, 0) } else { (id, c.min(MAX_COUNT as u16)) };
        s.set_u16(o + LOADOUT_NAME + 4 * j, id);
        s.set_u16(o + LOADOUT_NAME + 4 * j + 2, c);
    }
}

/// Loadout `from` moves to place `to`, the loadouts between shifting one place.
pub fn move_loadout(s: &mut Save, base: usize, from: usize, to: usize) {
    assert!(from < LOADOUT_N && to < LOADOUT_N, "loadout {from} -> {to}");
    s.move_record(base + LOADOUTS, LOADOUT_SZ, from, to);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::save::{SLOT1_BASE, blank};

    #[test]
    fn slots_pack_at_the_field_limits() {
        let mut s = blank();
        set(&mut s, SLOT1_BASE, Store::Box, 1, Stack { id: MAX_ID, count: 127 });
        assert_eq!(get(&s, SLOT1_BASE, Store::Box, 1), Stack { id: MAX_ID, count: MAX_COUNT });
        assert_eq!(get(&s, SLOT1_BASE, Store::Box, 0), Stack::default());
        assert_eq!(get(&s, SLOT1_BASE, Store::Box, 2), Stack::default());
        // too big for 12 bits: the slot is emptied, not turned into item ID & 0xFFF
        set(&mut s, SLOT1_BASE, Store::Box, 1, Stack { id: MAX_ID + 2, count: 5 });
        assert_eq!(get(&s, SLOT1_BASE, Store::Box, 1), Stack::default());
        set(&mut s, SLOT1_BASE, Store::Pouch, POUCH_N - 1, Stack { id: 7, count: 3 });
        assert_eq!(
            all(&s, SLOT1_BASE, Store::Box).iter().filter(|x| !x.is_empty()).count(),
            0,
            "pouch apart from the box"
        );
    }

    #[test]
    fn moving_a_loadout_keeps_its_items() {
        let mut s = blank();
        let l = Loadout { name: "Capture".into(), items: vec![(5, 2)] };
        set_loadout(&mut s, SLOT1_BASE, 1, &l);
        move_loadout(&mut s, SLOT1_BASE, 1, LOADOUT_N - 1);
        let r = loadout(&s, SLOT1_BASE, LOADOUT_N - 1);
        assert_eq!((r.name.as_str(), r.items[0]), ("Capture", (5, 2)));
        assert_eq!(loadout(&s, SLOT1_BASE, 1), loadout(&blank(), SLOT1_BASE, 2), "the next one moved up");
    }

    #[test]
    fn loadout_round_trip_and_bounds() {
        let mut s = blank();
        let l = Loadout { name: "Hunt".into(), items: vec![(1, 5), (0x1000, 3), (2, 200)] };
        set_loadout(&mut s, SLOT1_BASE, LOADOUT_N - 1, &l);
        let r = loadout(&s, SLOT1_BASE, LOADOUT_N - 1);
        assert_eq!(r.name, "Hunt");
        assert_eq!(&r.items[..3], &[(1, 5), (0, 0), (2, 99)]);
        assert_eq!(get(&s, SLOT1_BASE, Store::Pouch, 0), Stack::default(), "the last loadout ends before the pouch");
        assert!(std::panic::catch_unwind(|| loadout(&blank(), SLOT1_BASE, LOADOUT_N)).is_err());
    }

    #[test]
    fn fill_takes_empty_slots_and_skips_held_items() {
        let mut s = blank();
        set(&mut s, SLOT1_BASE, Store::Box, 0, Stack { id: 7, count: 1 });
        set(&mut s, SLOT1_BASE, Store::Box, 2, Stack { id: 9, count: 3 });
        assert_eq!(fill(&mut s, SLOT1_BASE, &[7, 12, 12, 0, 30], 99), 2);
        let v = all(&s, SLOT1_BASE, Store::Box);
        assert_eq!(
            &v[..4],
            &[
                Stack { id: 7, count: 1 },
                Stack { id: 12, count: 99 },
                Stack { id: 9, count: 3 },
                Stack { id: 30, count: 99 }
            ]
        );
        assert!(obtained(&s, SLOT1_BASE, 12) && obtained(&s, SLOT1_BASE, 30) && !obtained(&s, SLOT1_BASE, 7));
        // a full box takes nothing more
        let ids: Vec<u16> = (100..100 + BOX_N as u16).collect();
        assert_eq!(fill(&mut s, SLOT1_BASE, &ids, 1), BOX_N - 4);
        assert_eq!(fill(&mut s, SLOT1_BASE, &[5], 1), 0);
    }

    #[test]
    fn compact_merges_and_sorts() {
        let v = [Stack { id: 5, count: 60 }, Stack::default(), Stack { id: 2, count: 1 }, Stack { id: 5, count: 60 }];
        let c = compact(&v, true, Store::Box, |_| MAX_COUNT);
        assert_eq!(
            c,
            vec![Stack { id: 2, count: 1 }, Stack { id: 5, count: 99 }, Stack { id: 5, count: 21 }, Stack::default()]
        );
    }

    #[test]
    fn compact_pouch_keeps_one_stack_at_carry_limit() {
        let v = [Stack { id: 29, count: 2 }, Stack { id: 10, count: 8 }, Stack { id: 10, count: 7 }, Stack::default()];
        let c = compact(&v, true, Store::Pouch, |id| if id == 29 { 1 } else { 10 });
        assert_eq!(
            c,
            vec![Stack { id: 10, count: 10 }, Stack { id: 29, count: 1 }, Stack::default(), Stack::default()]
        );
    }
}
