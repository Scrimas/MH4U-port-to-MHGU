//! Equipment box (hunter and Palico) and talismans (docs/07-equipment.md).
//!
//! Entry, 36 bytes:
//!   +0x00 u16  type (bits 0-4), level - 1 (bits 5-9), transmog source level - 1 (bits 10-14), bit 15 kept
//!   +0x02 u16  equipment ID
//!   +0x04 u16  transmog appearance ID (armor; 0 = own look)
//!   +0x06 3 x u16 decoration item IDs
//!   +0x0C 24 B talisman: skill IDs u8 x2, points i8 x2 (+0x0E), slots u8 (+0x10), u16 charm item ID 353-356 (+0x12; its low byte is the tier 97-100, the high byte 1)

use crate::save::Save;

pub const BOX: usize = 0x62EE;
pub const BOX_N: usize = 2000;
pub const PALICO_BOX: usize = 0x17C2E;
pub const PALICO_BOX_N: usize = 1000;
pub const ENTRY: usize = 36;
/// Box indices of the worn gear (weapon, head, chest, arms, waist, legs, talisman; 0xFFFF none).
pub const WORN: usize = 0x23B39;
/// My Sets: 40 records of 0x88 bytes, name at +0x06 (24 B), box indices like WORN at +0x30.
pub const MY_SETS: usize = 0x208C8;
pub const MY_SETS_N: usize = 40;
pub const MY_SET: usize = 0x88;
/// Weapon class of the Insect Glaive (type code 20).
pub const INSECT_GLAIVE: u8 = 13;

/// Tier code of talisman rarity `id` (Pawn 1 … Creator 10), as in every talisman of the
/// analysed save: 1-2 Mystery, 3-4 Shining, 5-7 Timeworn, 8-10 Enduring.
pub fn talisman_tier(id: u16) -> u8 {
    match id {
        0..=2 => 97,
        3..=4 => 98,
        5..=7 => 99,
        _ => 100,
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Empty,
    Head,
    Chest,
    Arms,
    Waist,
    Legs,
    Talisman,
    /// Weapon class 0-14 in the order of the game's weapon tables (type code - 7).
    Weapon(u8),
    Other(u8),
}

impl Kind {
    pub fn from_code(c: u8) -> Kind {
        match c {
            0 => Kind::Empty,
            1 => Kind::Head,
            2 => Kind::Chest,
            3 => Kind::Arms,
            4 => Kind::Waist,
            5 => Kind::Legs,
            6 => Kind::Talisman,
            7..=21 => Kind::Weapon(c - 7),
            c => Kind::Other(c),
        }
    }
    pub fn code(self) -> u8 {
        match self {
            Kind::Empty => 0,
            Kind::Head => 1,
            Kind::Chest => 2,
            Kind::Arms => 3,
            Kind::Waist => 4,
            Kind::Legs => 5,
            Kind::Talisman => 6,
            Kind::Weapon(w) => {
                assert!(w < 15, "weapon class {w}");
                7 + w
            }
            Kind::Other(c) => {
                assert!(c < 32, "box type {c} does not fit 5 bits");
                c
            }
        }
    }
    pub fn is_armor(self) -> bool {
        matches!(self, Kind::Head | Kind::Chest | Kind::Arms | Kind::Waist | Kind::Legs)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Talisman {
    pub skills: [u8; 2],
    pub points: [i8; 2],
    pub slots: u8,
    pub tier: u8,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    pub raw: [u8; ENTRY],
}

impl Entry {
    fn w(&self, o: usize) -> u16 {
        u16::from_le_bytes([self.raw[o], self.raw[o + 1]])
    }
    fn set_w(&mut self, o: usize, v: u16) {
        self.raw[o..o + 2].copy_from_slice(&v.to_le_bytes());
    }
    pub fn kind(&self) -> Kind {
        Kind::from_code((self.w(0) & 0x1F) as u8)
    }
    pub fn is_empty(&self) -> bool {
        self.raw.iter().all(|&b| b == 0)
    }
    /// In-game level (1-based).
    pub fn level(&self) -> u8 {
        ((self.w(0) >> 5) & 0x1F) as u8 + 1
    }
    pub fn set_level(&mut self, lv: u8) {
        let lv = lv.clamp(1, 32) - 1;
        let v = (self.w(0) & !(0x1F << 5)) | ((lv as u16) << 5);
        self.set_w(0, v);
    }
    pub fn id(&self) -> u16 {
        self.w(2)
    }
    pub fn transmog(&self) -> u16 {
        self.w(4)
    }
    pub fn transmog_level(&self) -> u8 {
        ((self.w(0) >> 10) & 0x1F) as u8 + 1
    }
    /// Look of armor piece `id` at in-game level `lv`; `id` 0 restores the own look.
    pub fn set_transmog(&mut self, id: u16, lv: u8) {
        self.set_w(4, id);
        let lv = if id == 0 { 0 } else { lv.clamp(1, 32) - 1 };
        let v = (self.w(0) & !(0x1F << 10)) | ((lv as u16) << 10);
        self.set_w(0, v);
    }
    pub fn decos(&self) -> [u16; 3] {
        [self.w(6), self.w(8), self.w(10)]
    }
    pub fn set_deco(&mut self, k: usize, item: u16) {
        assert!(k < 3, "decoration slot {k}");
        self.set_w(6 + 2 * k, item);
    }
    /// The game keeps decorations packed from the first field, one field each whatever
    /// its size (every decorated entry of the analysed saves). Puts `item` in the first
    /// free field; false when all three are taken.
    pub fn add_deco(&mut self, item: u16) -> bool {
        match self.decos().iter().position(|&d| d == 0) {
            Some(k) => {
                self.set_deco(k, item);
                true
            }
            None => false,
        }
    }
    /// Takes out decoration field `k`; the ones after it move up, so they stay packed.
    pub fn remove_deco(&mut self, k: usize) {
        let mut v: Vec<u16> =
            self.decos().into_iter().enumerate().filter(|&(j, d)| j != k && d != 0).map(|(_, d)| d).collect();
        v.resize(3, 0);
        for (j, d) in v.into_iter().enumerate() {
            self.set_deco(j, d);
        }
    }
    pub fn talisman(&self) -> Option<Talisman> {
        (self.kind() == Kind::Talisman).then(|| Talisman {
            skills: [self.raw[0x0C], self.raw[0x0D]],
            points: [self.raw[0x0E] as i8, self.raw[0x0F] as i8],
            slots: self.raw[0x10],
            tier: self.raw[0x12],
        })
    }
    pub fn set_talisman(&mut self, t: Talisman) {
        self.raw[0x0C] = t.skills[0];
        self.raw[0x0D] = t.skills[1];
        self.raw[0x0E] = t.points[0] as u8;
        self.raw[0x0F] = t.points[1] as u8;
        self.raw[0x10] = t.slots.min(3);
        self.raw[0x12] = t.tier;
        self.raw[0x13] = 1;
    }
    /// A fresh level-1 entry of `kind`/`id` (bit 15 and the rest zero), shaped like the
    /// game's own: a talisman gets the tier of its rarity, an Insect Glaive byte +0x0C = 1
    /// (every glaive of the analysed save has it; most likely its Kinsect).
    pub fn new(kind: Kind, id: u16) -> Entry {
        let mut e = Entry { raw: [0; ENTRY] };
        e.set_w(0, kind.code() as u16);
        e.set_w(2, id);
        match kind {
            Kind::Talisman => {
                e.raw[0x12] = talisman_tier(id);
                e.raw[0x13] = 1;
            }
            Kind::Weapon(INSECT_GLAIVE) => e.raw[0x0C] = 1,
            _ => {}
        }
        e
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Owner {
    Hunter,
    Palico,
}

impl Owner {
    fn at(self) -> (usize, usize) {
        match self {
            Owner::Hunter => (BOX, BOX_N),
            Owner::Palico => (PALICO_BOX, PALICO_BOX_N),
        }
    }
    // the number of entries of a box, never empty
    #[allow(clippy::len_without_is_empty)]
    pub fn len(self) -> usize {
        self.at().1
    }
}

pub fn get(s: &Save, base: usize, owner: Owner, i: usize) -> Entry {
    let (off, n) = owner.at();
    assert!(i < n);
    Entry { raw: s.get(base + off + ENTRY * i, ENTRY).try_into().unwrap() }
}

pub fn set(s: &mut Save, base: usize, owner: Owner, i: usize, e: &Entry) {
    let (off, n) = owner.at();
    assert!(i < n);
    s.put(base + off + ENTRY * i, &e.raw);
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Use {
    Worn,
    /// My Set number (1-based) and name.
    MySet(usize, String),
}

/// What refers to hunter box entry `i` by index: the worn gear and the My Sets. Such an
/// entry must not be replaced or removed, or the set points at the wrong piece.
pub fn uses(s: &Save, base: usize, i: usize) -> Vec<Use> {
    let has = |at: usize| (0..7).any(|k| s.u16(at + 2 * k) as usize == i);
    let mut v = vec![];
    if has(base + WORN) {
        v.push(Use::Worn);
    }
    for k in 0..MY_SETS_N {
        let rec = base + MY_SETS + MY_SET * k;
        if has(rec + 0x30) {
            v.push(Use::MySet(k + 1, s.str(rec + 0x06, 24)));
        }
    }
    v
}

/// The first empty entry that nothing refers to.
pub fn free_slot(s: &Save, base: usize, owner: Owner) -> Option<usize> {
    (0..owner.len())
        .find(|&i| get(s, base, owner, i).is_empty() && (owner == Owner::Palico || uses(s, base, i).is_empty()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn level_and_transmog_bits() {
        let mut e = Entry::new(Kind::Head, 321);
        e.set_level(7);
        e.set_transmog(55, 3);
        assert_eq!(e.kind(), Kind::Head);
        assert_eq!(e.level(), 7);
        assert_eq!(e.transmog(), 55);
        assert_eq!(e.transmog_level(), 3);
        e.set_transmog(0, 9);
        assert_eq!(e.transmog_level(), 1);
        assert_eq!(e.level(), 7);
        assert_eq!(Entry::new(Kind::Weapon(11), 1).kind(), Kind::Weapon(11));
        let t = Entry::new(Kind::Talisman, 6).talisman().unwrap();
        assert_eq!((t.tier, t.slots, t.skills), (99, 0, [0, 0]));
        assert_eq!(
            Entry::new(Kind::Weapon(INSECT_GLAIVE), 11).raw[..0x0E],
            [0x14, 0, 0x0b, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]
        );
    }

    #[test]
    fn decorations_stay_packed() {
        let mut e = Entry::new(Kind::Head, 1);
        assert!(e.add_deco(2700) && e.add_deco(2701) && e.add_deco(2702));
        assert!(!e.add_deco(2703));
        e.remove_deco(0);
        assert_eq!(e.decos(), [2701, 2702, 0]);
        assert!(e.add_deco(2650));
        assert_eq!(e.decos(), [2701, 2702, 2650]);
        e.remove_deco(1);
        assert_eq!(e.decos(), [2701, 2650, 0]);
    }
}
