//! The saves of the install places: finding them, the migration level each character carries, the release's ID
//! remaps (manifest `migrations`) and the cleaning of removed monsters' gear (manifest `cleaning`). Reading and writing
//! go through the vendored parser of MHGU_Editor (installer/vendor/mhgu-save: the save container, item stores,
//! equipment box and its all-copies write); every write is preceded by a snapshot of the whole save (every copy) in
//! the installer's backup folder, and every backup is kept.
//!
//! Offsets below are relative to a character base (MHGU_Editor docs/11-save-map.md, C): the reserved block of
//! sUserInfo (+0x3684..+0x43f8) sits at character offset 0x50BE; the core keeps the items-obtained bits of IDs 3008.. at
//! its sUserInfo +0x3700 (module/items.c) and its store at +0x3900 (module/save.c, notes/save-store.md).
//!
//! The migration level is the store's version-2 header word at +12 (version 1 has 0 there and no level; the core reads
//! both and migrates 1 -> 2 at character load). Steps above a character's level are applied in order, then its level is
//! the last step's. A store that is neither empty nor version 1 or 2 is another tool's data: never written.

use crate::i18n::{tr, trf};
use crate::places::{Kind, Place, TITLE_ID};
use mhgu_save::equipment::{self as eq, Entry, Kind as EqKind, Owner};
use mhgu_save::items::{self, Store};
use mhgu_save::save::FILE_SIZE;
use mhgu_save::{Save, store};
use serde::Deserialize;
use std::collections::{BTreeMap, HashMap};
use std::path::{Path, PathBuf};

const RESERVED: usize = 0x50BE; // sUserInfo +0x3684
const STORE: usize = RESERVED + (0x3900 - 0x3684);
const STORE_SIZE: usize = 0x43F8 - 0x3900;
const STORE_MAGIC: u32 = 0x5334_484D; // "MH4S"
const STORE_HDR: usize = 16;
const STORE_REC: usize = 12;
const OBTAINED_EXT: usize = RESERVED + (0x3700 - 0x3684);
const OBTAINED_EXT_FIRST: u16 = 3008;
const OBTAINED_EXT_BITS: usize = 512 * 8;
const NONE: u16 = 0xFFFF;

// ------------------------------------------------------------------------------------------ manifest data

/// One migration step of the manifest (tools/release.py from migrations.toml): old -> new IDs.
#[derive(Clone, Debug, Default, Deserialize, PartialEq, Eq)]
pub struct Step {
    pub step: u32,
    #[serde(default)]
    pub release: String,
    /// item IDs (box, pouch, loadouts, items obtained, decorations in gear)
    #[serde(default)]
    pub items: Vec<(u16, u16)>,
    /// armor IDs (an armor series record: every part of the series, and layered looks)
    #[serde(default)]
    pub armor: Vec<(u16, u16)>,
    /// weapon class, old ID, new ID
    #[serde(default)]
    pub weapons: Vec<(u8, u16, u16)>,
    /// decorations are items: as `items`
    #[serde(default)]
    pub decorations: Vec<(u16, u16)>,
    /// quest IDs (cleared flags): not done by this installer, a step with some cannot be applied
    #[serde(default)]
    pub quests: Vec<(u32, u32)>,
    /// save slots (hunt tallies): not done by this installer, a step with some cannot be applied
    #[serde(default)]
    pub save_slots: Vec<(u16, u16)>,
}

impl Step {
    pub fn supported(&self) -> bool {
        self.quests.is_empty() && self.save_slots.is_empty()
    }
}

/// What a package owns in a save (manifest `cleaning`): its items (inclusive ranges: materials, decorations), its
/// armor series IDs and its weapons (class, ID).
#[derive(Clone, Debug, Default, Deserialize, PartialEq, Eq)]
pub struct Owned {
    #[serde(default)]
    pub items: Vec<(u16, u16)>,
    #[serde(default)]
    pub armor: Vec<u16>,
    #[serde(default)]
    pub weapons: Vec<(u8, u16)>,
}

impl Owned {
    pub fn add(&mut self, o: &Owned) {
        self.items.extend(&o.items);
        self.armor.extend(&o.armor);
        self.weapons.extend(&o.weapons);
    }
    fn item(&self, id: u16) -> bool {
        id != 0 && self.items.iter().any(|&(a, b)| (a..=b).contains(&id))
    }
    fn gear(&self, e: &Entry) -> bool {
        match e.kind() {
            k if k.is_armor() => self.armor.contains(&e.id()),
            EqKind::Weapon(c) => self.weapons.contains(&(c, e.id())),
            _ => false,
        }
    }
    pub fn is_empty(&self) -> bool {
        self.items.is_empty() && self.armor.is_empty() && self.weapons.is_empty()
    }
}

/// The migration steps of a manifest, in order.
pub fn steps(m: &crate::manifest::Manifest) -> Result<Vec<Step>, String> {
    let mut v: Vec<Step> = m
        .migrations
        .iter()
        .map(|j| serde_json::from_value(j.clone()).map_err(|e| trf("Invalid manifest: {}", &[&e])))
        .collect::<Result<_, _>>()?;
    v.sort_by_key(|s| s.step);
    Ok(v)
}

/// What package `name` owns in a save, from the manifest.
pub fn owned(m: &crate::manifest::Manifest, name: &str) -> Owned {
    m.cleaning.get(name).and_then(|j| serde_json::from_value(j.clone()).ok()).unwrap_or_default()
}

// ------------------------------------------------------------------------------------------ the store

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum StoreState {
    Empty,
    V1,
    V2(u32),
    /// another tool's data or a newer format: left alone
    Foreign,
}

fn fnv(mut h: u32, b: &[u8]) -> u32 {
    for &x in b {
        h = (h ^ x as u32).wrapping_mul(16_777_619);
    }
    h
}

fn store_records(b: &[u8]) -> usize {
    let n = u16::from_le_bytes([b[6], b[7]]) as usize;
    n.min((STORE_SIZE - STORE_HDR) / STORE_REC)
}

/// The check word: v1 = FNV-1a of version + count and the records (module/save.c), v2 = of version + count, the level
/// and the records.
fn check_word(b: &[u8], version: u16) -> u32 {
    let n = store_records(b);
    let h = fnv(2_166_136_261, &b[4..8]);
    let h = if version >= 2 { fnv(h, &b[12..16]) } else { h };
    fnv(h, &b[STORE_HDR..STORE_HDR + n * STORE_REC])
}

pub fn store_state(s: &Save, base: usize) -> StoreState {
    let b = s.get(base + STORE, STORE_SIZE);
    let w = |o: usize| u32::from_le_bytes(b[o..o + 4].try_into().unwrap());
    if w(0) == 0 {
        return if b.iter().all(|&x| x == 0) { StoreState::Empty } else { StoreState::Foreign };
    }
    let version = u16::from_le_bytes([b[4], b[5]]);
    let n = u16::from_le_bytes([b[6], b[7]]) as usize;
    if w(0) != STORE_MAGIC || n > (STORE_SIZE - STORE_HDR) / STORE_REC || w(8) != check_word(b, version) {
        return StoreState::Foreign;
    }
    match version {
        1 if w(12) == 0 => StoreState::V1,
        2 => StoreState::V2(w(12)),
        _ => StoreState::Foreign,
    }
}

/// The character's migration level, None when its store is another tool's.
pub fn level(s: &Save, base: usize) -> Option<u32> {
    match store_state(s, base) {
        StoreState::Empty | StoreState::V1 => Some(0),
        StoreState::V2(l) => Some(l),
        StoreState::Foreign => None,
    }
}

/// Write the level: the store becomes version 2 (an empty one gets a header without records).
fn set_level(s: &mut Save, base: usize, level: u32) {
    let mut b = s.get(base + STORE, STORE_SIZE).to_vec();
    if store_state(s, base) == StoreState::Empty {
        b[0..4].copy_from_slice(&STORE_MAGIC.to_le_bytes());
        b[6..8].copy_from_slice(&0u16.to_le_bytes());
    }
    b[4..6].copy_from_slice(&2u16.to_le_bytes());
    b[12..16].copy_from_slice(&level.to_le_bytes());
    let c = check_word(&b, 2);
    b[8..12].copy_from_slice(&c.to_le_bytes());
    s.put(base + STORE, &b);
}

// ------------------------------------------------------------------------------------------ remaps

fn obtained(s: &Save, base: usize, id: u16) -> bool {
    if id < OBTAINED_EXT_FIRST {
        id > 0 && s.bit(base + items::OBTAINED, id as usize)
    } else {
        let k = (id - OBTAINED_EXT_FIRST) as usize;
        k < OBTAINED_EXT_BITS && s.bit(base + OBTAINED_EXT, k)
    }
}

fn set_obtained(s: &mut Save, base: usize, id: u16, v: bool) {
    if id == 0 {
    } else if id < OBTAINED_EXT_FIRST {
        s.set_bit(base + items::OBTAINED, id as usize, v);
    } else if ((id - OBTAINED_EXT_FIRST) as usize) < OBTAINED_EXT_BITS {
        s.set_bit(base + OBTAINED_EXT, (id - OBTAINED_EXT_FIRST) as usize, v);
    }
}

/// What a migration or a cleaning changed in one character.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Counts {
    pub items: usize,
    pub gear: usize,
    pub worn: usize,
    pub sets: usize,
    pub layered: usize,
}

impl Counts {
    pub fn add(&mut self, o: &Counts) {
        self.items += o.items;
        self.gear += o.gear;
        self.worn += o.worn;
        self.sets += o.sets;
        self.layered += o.layered;
    }
    pub fn total(&self) -> usize {
        self.items + self.gear + self.worn + self.sets + self.layered
    }
}

fn map_items(s: &mut Save, base: usize, map: &HashMap<u16, u16>, n: &mut Counts) {
    for store in [Store::Box, Store::Pouch] {
        let mut v = items::all(s, base, store);
        let mut hit = false;
        for st in v.iter_mut().filter(|st| map.contains_key(&st.id)) {
            st.id = map[&st.id];
            n.items += 1;
            hit = true;
        }
        if hit {
            items::set_all(s, base, store, &v);
        }
    }
    for k in 0..items::LOADOUT_N {
        let mut l = items::loadout(s, base, k);
        let mut hit = false;
        for it in l.items.iter_mut().filter(|(id, _)| map.contains_key(id)) {
            it.0 = map[&it.0];
            n.items += 1;
            hit = true;
        }
        if hit {
            items::set_loadout(s, base, k, &l);
        }
    }
    let had: Vec<(u16, u16)> = map.iter().filter(|(o, _)| obtained(s, base, **o)).map(|(o, n)| (*o, *n)).collect();
    for &(o, _) in &had {
        set_obtained(s, base, o, false);
    }
    for &(_, nw) in &had {
        set_obtained(s, base, nw, true);
    }
    n.items += had.len();
}

/// Apply one step to one character.
fn apply_step(s: &mut Save, base: usize, st: &Step, n: &mut Counts) {
    let items_map: HashMap<u16, u16> = st.items.iter().chain(&st.decorations).copied().collect();
    let armor: HashMap<u16, u16> = st.armor.iter().copied().collect();
    let weapons: HashMap<(u8, u16), u16> = st.weapons.iter().map(|&(c, o, nw)| ((c, o), nw)).collect();
    if !items_map.is_empty() {
        map_items(s, base, &items_map, n);
    }
    for i in 0..eq::BOX_N {
        let mut e = eq::get(s, base, Owner::Hunter, i);
        if e.is_empty() {
            continue;
        }
        let before = e.clone();
        let id = e.id();
        let new_id = match e.kind() {
            k if k.is_armor() => armor.get(&id).copied(),
            EqKind::Weapon(c) => weapons.get(&(c, id)).copied(),
            _ => None,
        };
        if let Some(v) = new_id {
            e.raw[2..4].copy_from_slice(&v.to_le_bytes());
        }
        if let Some(&v) = armor.get(&e.transmog()).filter(|_| e.transmog() != 0) {
            e.set_transmog(v, e.transmog_level());
            n.layered += 1;
        }
        for (k, d) in e.decos().into_iter().enumerate() {
            if let Some(&v) = items_map.get(&d) {
                e.set_deco(k, v);
            }
        }
        if e != before {
            n.gear += 1;
            eq::set(s, base, Owner::Hunter, i, &e);
        }
    }
    // My Sets keep copies of their pieces' decorations
    for k in 0..eq::MY_SETS_N {
        let rec = base + eq::MY_SETS + eq::MY_SET * k + 0x3E;
        for j in 0..21 {
            let d = s.u16(rec + 2 * j);
            if let Some(&v) = items_map.get(&d) {
                s.set_u16(rec + 2 * j, v);
                n.sets += 1;
            }
        }
    }
}

// ------------------------------------------------------------------------------------------ cleaning

/// What happens to the gear of the monsters that leave (their models leave with them; their records and items stay
/// readable, the core always installs every data file).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Clean {
    /// Their items, armor, weapons and decorations removed from the boxes, pouch, loadouts and gear.
    RemoveAll,
    /// Only the pieces worn now are deleted (data loss); the boxes keep the rest.
    RemoveWorn,
    /// Worn pieces taken off, My Sets entries cleared: nothing deleted.
    Unequip,
}

/// Clean one character of what `o` owns. Layered looks of their armor go back to the own look in every mode; a worn
/// weapon of theirs is swapped for another weapon of the box (a hunter always holds one): Err when there is none.
fn clean_character(s: &mut Save, base: usize, o: &Owned, mode: Clean, n: &mut Counts) -> Result<(), String> {
    let theirs: Vec<bool> = (0..eq::BOX_N).map(|i| o.gear(&eq::get(s, base, Owner::Hunter, i))).collect();
    let delete: Vec<bool> = match mode {
        Clean::RemoveAll => theirs.clone(),
        Clean::RemoveWorn => {
            let worn: Vec<usize> = (0..7).map(|k| s.u16(base + eq::WORN + 2 * k) as usize).collect();
            (0..eq::BOX_N).map(|i| theirs[i] && worn.contains(&i)).collect()
        }
        Clean::Unequip => vec![false; eq::BOX_N],
    };
    // worn: armor off, weapon swapped
    for k in 0..7 {
        let at = base + eq::WORN + 2 * k;
        let i = s.u16(at);
        if i == NONE || !theirs.get(i as usize).copied().unwrap_or(false) {
            continue;
        }
        let new = if k == 0 {
            let cur = eq::get(s, base, Owner::Hunter, i as usize).kind();
            let ok = |j: usize, same: bool| {
                let e = eq::get(s, base, Owner::Hunter, j);
                matches!(e.kind(), EqKind::Weapon(_)) && !theirs[j] && (!same || e.kind() == cur)
            };
            let j = (0..eq::BOX_N).find(|&j| ok(j, true)).or_else(|| (0..eq::BOX_N).find(|&j| ok(j, false)));
            j.map(|j| j as u16)
                .ok_or_else(|| tr("The hunter holds a weapon that leaves, and the box has no other weapon"))?
        } else {
            NONE
        };
        s.set_u16(at, new);
        n.worn += 1;
    }
    // My Sets: their pieces cleared (with the piece's decoration copies)
    for k in 0..eq::MY_SETS_N {
        let rec = base + eq::MY_SETS + eq::MY_SET * k;
        for j in 0..7 {
            let i = s.u16(rec + 0x30 + 2 * j);
            if i != NONE && theirs.get(i as usize).copied().unwrap_or(false) {
                s.set_u16(rec + 0x30 + 2 * j, NONE);
                for d in 0..3 {
                    s.set_u16(rec + 0x3E + 6 * j + 2 * d, 0);
                }
                n.sets += 1;
            }
        }
    }
    // the box: deleted pieces, layered looks, (RemoveAll) their decorations
    for (i, &del) in delete.iter().enumerate() {
        let mut e = eq::get(s, base, Owner::Hunter, i);
        if e.is_empty() {
            continue;
        }
        if del {
            eq::set(s, base, Owner::Hunter, i, &Entry { raw: [0; eq::ENTRY] });
            n.gear += 1;
            continue;
        }
        let before = e.clone();
        if e.transmog() != 0 && o.armor.contains(&e.transmog()) {
            e.set_transmog(0, 1);
            n.layered += 1;
        }
        if mode == Clean::RemoveAll {
            for k in (0..3).rev() {
                if o.item(e.decos()[k]) {
                    e.remove_deco(k);
                }
            }
        }
        if e != before {
            eq::set(s, base, Owner::Hunter, i, &e);
            if mode == Clean::RemoveAll {
                n.gear += 1;
            }
        }
    }
    if mode == Clean::RemoveAll {
        for store in [Store::Box, Store::Pouch] {
            let mut v = items::all(s, base, store);
            let before = v.len() - v.iter().filter(|st| o.item(st.id)).count();
            n.items += v.len() - before;
            v.retain(|st| !o.item(st.id));
            items::set_all(s, base, store, &v);
        }
        for k in 0..items::LOADOUT_N {
            let mut l = items::loadout(s, base, k);
            let mut hit = false;
            for it in l.items.iter_mut().filter(|(id, _)| o.item(*id)) {
                *it = (0, 0);
                n.items += 1;
                hit = true;
            }
            if hit {
                items::set_loadout(s, base, k, &l);
            }
        }
    }
    Ok(())
}

// ------------------------------------------------------------------------------------------ saves on disk

/// A save found in a place.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Found {
    /// the file opened (its copies are found from it, store.rs Location)
    pub file: PathBuf,
    /// "Ryujinx · 0000000000000002", "Eden · user 1", "SD card · JKSV …"
    pub label: String,
    /// a Switch backup tool's folder: the migrated copy goes into a new backup folder beside it
    pub backup_tool: Option<&'static str>,
}

fn is_save(p: &Path) -> bool {
    p.metadata().is_ok_and(|m| m.is_file() && m.len() == FILE_SIZE as u64)
}

fn sorted_dirs(p: &Path) -> Vec<PathBuf> {
    let Ok(rd) = std::fs::read_dir(p) else { return vec![] };
    let mut v: Vec<PathBuf> = rd.flatten().map(|e| e.path()).filter(|p| p.is_dir()).collect();
    v.sort();
    v
}

fn name_of(p: &Path) -> String {
    p.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default()
}

/// `system` files of the right size under `root`, at most `depth` folders down; a `1/` copy is left out when its `0/`
/// sibling is there (one save).
fn walk_saves(root: &Path, depth: usize) -> Vec<PathBuf> {
    let mut out = vec![];
    let mut stack = vec![(root.to_path_buf(), 0)];
    while let Some((d, k)) = stack.pop() {
        for sub in sorted_dirs(&d) {
            if k < depth {
                stack.push((sub, k + 1));
            }
        }
        let f = d.join("system");
        if is_save(&f) {
            out.push(f);
        }
    }
    out.retain(|p| {
        let commit = p.parent().and_then(|d| d.file_name()).is_some_and(|n| n == "1");
        !(commit && p.parent().and_then(|d| d.parent()).is_some_and(|d| is_save(&d.join("0/system"))))
    });
    out.sort();
    out
}

/// The recomp's save folder: `SaveLocation` of mhgurecomp.ini when set, else %APPDATA%\MHGURecomp\save /
/// ~/.local/share/MHGURecomp/save.
fn recomp_saves(root: &Path) -> PathBuf {
    if let Ok(t) = std::fs::read_to_string(root.join("mhgurecomp.ini"))
        && let Some(v) = t.lines().find_map(|l| {
            l.trim().strip_prefix("SaveLocation").map(|r| r.trim_start_matches([' ', '=']).trim().to_string())
        })
        && !v.is_empty()
    {
        return PathBuf::from(v);
    }
    let base = if cfg!(windows) { dirs::config_dir() } else { dirs::data_dir() };
    base.unwrap_or_default().join("MHGURecomp/save")
}

/// Every save of a place: Ryujinx `bis/user/save/<id>/0/system`, the yuzu family's
/// `nand/user/save/0000000000000000/<user>/0100770008DD8000/system`, the recomp's save folder, an SD card's newest JKSV /
/// Checkpoint backup of MHGU; a folder place has none.
pub fn find(p: &Place) -> Vec<Found> {
    let found = |file: PathBuf, label: String| Found { file, label, backup_tool: None };
    match p.kind {
        Kind::Ryujinx => sorted_dirs(&p.root.join("bis/user/save"))
            .into_iter()
            .map(|d| (d.join("0/system"), name_of(&d)))
            .filter(|(f, _)| is_save(f))
            .map(|(f, id)| found(f, format!("{} · {id}", p.name)))
            .collect(),
        Kind::Yuzu => sorted_dirs(&p.root.join("nand/user/save/0000000000000000"))
            .into_iter()
            .map(|u| (u.join(TITLE_ID).join("system"), name_of(&u)))
            .filter(|(f, _)| is_save(f))
            .map(|(f, u)| found(f, format!("{} · {}", p.name, &u[..u.len().min(8)])))
            .collect(),
        Kind::Recomp => walk_saves(&recomp_saves(&p.root), 3).into_iter().map(|f| found(f, p.name.clone())).collect(),
        Kind::SdCard => {
            let mut out = vec![];
            for (tool, dir) in [("JKSV", p.root.join("JKSV")), ("Checkpoint", p.root.join("switch/Checkpoint/saves"))] {
                for game in sorted_dirs(&dir).into_iter().filter(|g| {
                    let n = name_of(g).to_lowercase();
                    n.contains("monster hunter") || n.contains(&TITLE_ID.to_lowercase())
                }) {
                    // the newest backup (folder time), not one made by this installer already
                    let newest = sorted_dirs(&game)
                        .into_iter()
                        .filter(|b| is_save(&b.join("system")) && !name_of(b).contains("MH4U Port"))
                        .max_by_key(|b| b.metadata().and_then(|m| m.modified()).ok());
                    if let Some(b) = newest {
                        out.push(Found {
                            file: b.join("system"),
                            label: format!("{} · {tool} · {}", p.name, name_of(&b)),
                            backup_tool: Some(tool),
                        });
                    }
                }
            }
            out
        }
        Kind::Folder => vec![],
    }
}

/// What a save needs, read without writing.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Need {
    Nothing,
    /// steps to apply (their numbers), per character slot (1-based) with work
    Migrate(Vec<(usize, Vec<u32>)>),
    /// cannot be migrated: why
    Blocked(String),
}

fn open(f: &Path) -> Result<(Save, store::Location), String> {
    store::open(f).map(|(s, l, _)| (s, l)).map_err(|e| trf("{} cannot be read ({})", &[&f.display(), &e]))
}

/// What `f` needs for `steps` (sorted).
pub fn need(f: &Path, steps: &[Step]) -> Need {
    if steps.is_empty() {
        return Need::Nothing;
    }
    let (s, _) = match open(f) {
        Ok(x) => x,
        Err(e) => return Need::Blocked(e),
    };
    let mut out = vec![];
    for slot in (0..3).filter(|&k| s.slot_used(k)) {
        let Some(l) = level(&s, s.base(slot)) else {
            return Need::Blocked(trf(
                "character {} holds another tool's data where the mod keeps its own",
                &[&(slot + 1)],
            ));
        };
        if steps.last().is_some_and(|st| st.step < l) {
            return Need::Blocked(trf("character {} was migrated by a newer release", &[&(slot + 1)]));
        }
        let todo: Vec<&Step> = steps.iter().filter(|st| st.step > l).collect();
        if let Some(bad) = todo.iter().find(|st| !st.supported()) {
            return Need::Blocked(trf("step {} needs a newer installer", &[&bad.step]));
        }
        if !todo.is_empty() {
            out.push((slot + 1, todo.iter().map(|st| st.step).collect()));
        }
    }
    if out.is_empty() { Need::Nothing } else { Need::Migrate(out) }
}

/// A timestamp for backup folders: "2026-11-09_154200" (UTC).
pub fn stamp() -> String {
    let secs = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let (days, rem) = (secs / 86_400, secs % 86_400);
    // civil from days (H. Hinnant)
    let z = days as i64 + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = yoe + era * 400 + i64::from(m <= 2);
    format!("{y:04}-{m:02}-{d:02}_{:02}{:02}{:02}", rem / 3600, rem / 60 % 60, rem % 60)
}

/// What was done to one save.
#[derive(Clone, Debug, Default)]
pub struct Done {
    pub counts: Counts,
    /// the snapshot taken before writing
    pub backup: Option<PathBuf>,
    /// a Switch backup migrated: the new backup folder written beside it
    pub new_backup: Option<PathBuf>,
}

/// Migrate (`steps`, sorted) and clean (`clean`) save `f`, writing every copy after a snapshot into
/// `backups/<save>-<hash>/<stamp>-<release>/`. A Switch backup (JKSV / Checkpoint) is not changed: the result goes
/// into a new backup folder beside it. Nothing is written when there is nothing to change.
pub fn apply(
    f: &Found,
    steps: &[Step],
    clean: Option<(&Owned, Clean)>,
    backups: &Path,
    release: &str,
) -> Result<Done, String> {
    if let Need::Blocked(why) = need(&f.file, steps) {
        return Err(why);
    }
    let (mut s, mut loc) = open(&f.file)?;
    let mut done = Done::default();
    let slots: Vec<usize> = (0..3).filter(|&k| s.slot_used(k)).collect();
    for slot in slots {
        let base = s.base(slot);
        let lv = level(&s, base).unwrap_or(0);
        let todo: Vec<&Step> = steps.iter().filter(|st| st.step > lv).collect();
        for st in &todo {
            apply_step(&mut s, base, st, &mut done.counts);
        }
        if let Some(last) = todo.last() {
            set_level(&mut s, base, last.step);
        }
        if let Some((o, mode)) = clean.filter(|(o, _)| !o.is_empty()) {
            clean_character(&mut s, base, o, mode, &mut done.counts)
                .map_err(|e| trf("character {}: {}", &[&(slot + 1), &e]))?;
        }
    }
    if !s.is_dirty() {
        return Ok(done);
    }
    let key = {
        use sha2::{Digest, Sha256};
        let h = Sha256::digest(f.file.to_string_lossy().as_bytes());
        format!("{}-{}", name_of(f.file.parent().unwrap_or(Path::new(""))), crate::source::hex(&h[..4]))
    };
    let snap_name = format!("{}-{release}", stamp());
    let snap = store::snapshot(&loc, &backups.join(&key), &snap_name)
        .map_err(|e| trf("Could not back up {} ({})", &[&f.file.display(), &e]))?;
    done.backup = Some(snap);
    if f.backup_tool.is_some() {
        // a new backup folder beside the newest one, holding the migrated save
        let old = f.file.parent().ok_or_else(|| tr("The backup folder has no parent folder"))?;
        let new = old.with_file_name(format!("{} MH4U Port {release}", name_of(old)));
        copy_dir(old, &new).map_err(|e| trf("Could not write {} ({})", &[&new.display(), &e]))?;
        let (_, mut nloc) = open(&new.join("system"))?;
        store::write_all(&mut s, &mut nloc).map_err(|e| trf("Could not write {} ({})", &[&new.display(), &e]))?;
        done.new_backup = Some(new);
    } else {
        store::write_all(&mut s, &mut loc).map_err(|e| trf("Could not write {} ({})", &[&f.file.display(), &e]))?;
    }
    Ok(done)
}

fn copy_dir(from: &Path, to: &Path) -> std::io::Result<()> {
    std::fs::create_dir_all(to)?;
    for e in std::fs::read_dir(from)?.flatten() {
        let p = e.path();
        if p.is_dir() {
            copy_dir(&p, &to.join(e.file_name()))?;
        } else {
            std::fs::copy(&p, to.join(e.file_name()))?;
        }
    }
    Ok(())
}

/// The installer's folder for save backups: `<data>/mh4uport-installer/save-backups` ($MH4UPORT_BACKUPS for tests).
pub fn backup_dir() -> PathBuf {
    if let Some(d) = std::env::var_os("MH4UPORT_BACKUPS").filter(|v| !v.is_empty()) {
        return PathBuf::from(d);
    }
    dirs::data_dir().unwrap_or_else(std::env::temp_dir).join("mh4uport-installer/save-backups")
}

/// The gear (by package) a save holds of `owned`: what the removal popup shows.
pub fn holds(f: &Path, owned: &BTreeMap<String, Owned>) -> BTreeMap<String, usize> {
    let mut out = BTreeMap::new();
    let Ok((s, _)) = open(f) else { return out };
    for slot in (0..3).filter(|&k| s.slot_used(k)) {
        let base = s.base(slot);
        for i in 0..eq::BOX_N {
            let e = eq::get(&s, base, Owner::Hunter, i);
            for (name, o) in owned {
                if !e.is_empty() && o.gear(&e) {
                    *out.entry(name.clone()).or_default() += 1;
                }
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use mhgu_save::save::SLOT1_BASE;

    /// A save of zeros with valid slot pointers and slot 1 in use (no game data).
    fn blank() -> Vec<u8> {
        let mut v = vec![0u8; FILE_SIZE];
        for (s, b) in [0x18CC9Cu32, 0x2AC560, 0x3CBE24].iter().enumerate() {
            v[0x34 + 4 * s..0x38 + 4 * s].copy_from_slice(&(b - 0x24).to_le_bytes());
        }
        v[0x28] = 1;
        v
    }

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("mh4u-saves-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    /// A Ryujinx-style save folder <d>/<id>/{0,1}/{system,system_backup} holding `s`.
    fn write_ryujinx(d: &Path, s: &Save) -> PathBuf {
        for c in ["0", "1"] {
            std::fs::create_dir_all(d.join(c)).unwrap();
            for f in ["system", "system_backup"] {
                std::fs::write(d.join(c).join(f), s.bytes()).unwrap();
            }
        }
        d.join("0/system")
    }

    fn gear(s: &mut Save, i: usize, kind: EqKind, id: u16) {
        eq::set(s, SLOT1_BASE, Owner::Hunter, i, &Entry::new(kind, id));
    }

    #[test]
    fn the_store_level_reads_v1_and_writes_v2() {
        let mut s = Save::from_bytes(blank()).unwrap();
        let b = SLOT1_BASE;
        assert_eq!(store_state(&s, b), StoreState::Empty);
        assert_eq!(level(&s, b), Some(0));
        set_level(&mut s, b, 3);
        assert_eq!(store_state(&s, b), StoreState::V2(3));
        // a v1 store with one record (module/save.c's format) keeps its record through set_level
        let mut s1 = Save::from_bytes(blank()).unwrap();
        let mut blk = vec![0u8; STORE_SIZE];
        blk[0..4].copy_from_slice(&STORE_MAGIC.to_le_bytes());
        blk[4..6].copy_from_slice(&1u16.to_le_bytes());
        blk[6..8].copy_from_slice(&1u16.to_le_bytes());
        blk[16..28].copy_from_slice(&[0x65, 0x01, 3, 0, 1, 0, 0, 0, 0, 0, 0, 0]);
        let c = check_word(&blk, 1);
        blk[8..12].copy_from_slice(&c.to_le_bytes());
        s1.put(b + STORE, &blk);
        assert_eq!(store_state(&s1, b), StoreState::V1);
        set_level(&mut s1, b, 1);
        assert_eq!(store_state(&s1, b), StoreState::V2(1));
        assert_eq!(s1.get(b + STORE + 16, 12), &blk[16..28]);
        // another tool's bytes: left alone
        let mut s2 = Save::from_bytes(blank()).unwrap();
        s2.put(b + STORE + 100, &[1]);
        assert_eq!(level(&s2, b), None);
    }

    #[test]
    fn a_step_moves_items_gear_and_looks() {
        let mut s = Save::from_bytes(blank()).unwrap();
        let b = SLOT1_BASE;
        items::set(&mut s, b, Store::Box, 5, items::Stack { id: 2977, count: 4 });
        items::set(&mut s, b, Store::Pouch, 0, items::Stack { id: 2977, count: 1 });
        set_obtained(&mut s, b, 2977, true);
        set_obtained(&mut s, b, 3010, true);
        gear(&mut s, 0, EqKind::Weapon(5), 41);
        gear(&mut s, 1, EqKind::Head, 500);
        let mut e = Entry::new(EqKind::Chest, 12);
        e.set_transmog(500, 2);
        e.add_deco(2889);
        eq::set(&mut s, b, Owner::Hunter, 2, &e);
        let st = Step {
            step: 1,
            items: vec![(2977, 3050), (3010, 3011)],
            decorations: vec![(2889, 3060)],
            armor: vec![(500, 510)],
            weapons: vec![(5, 41, 60)],
            ..Default::default()
        };
        let mut n = Counts::default();
        apply_step(&mut s, b, &st, &mut n);
        assert_eq!(items::get(&s, b, Store::Box, 5), items::Stack { id: 3050, count: 4 });
        assert_eq!(items::get(&s, b, Store::Pouch, 0).id, 3050);
        assert!(obtained(&s, b, 3050) && !obtained(&s, b, 2977) && obtained(&s, b, 3011) && !obtained(&s, b, 3010));
        assert_eq!(eq::get(&s, b, Owner::Hunter, 0).id(), 60);
        assert_eq!(eq::get(&s, b, Owner::Hunter, 1).id(), 510);
        let e = eq::get(&s, b, Owner::Hunter, 2);
        assert_eq!((e.transmog(), e.transmog_level(), e.decos()[0]), (510, 2, 3060));
        assert_eq!(e.id(), 12, "a GU piece keeps its ID");
    }

    fn worn_set(s: &mut Save, idx: [u16; 7]) {
        for (k, i) in idx.iter().enumerate() {
            s.set_u16(SLOT1_BASE + eq::WORN + 2 * k, *i);
        }
    }

    #[test]
    fn cleaning_modes_and_layered_armor() {
        let b = SLOT1_BASE;
        let o = Owned { items: vec![(2977, 2985), (2889, 2892)], armor: vec![500], weapons: vec![(5, 41)] };
        let base = || {
            let mut s = Save::from_bytes(blank()).unwrap();
            gear(&mut s, 0, EqKind::Weapon(5), 41); // theirs, worn
            gear(&mut s, 1, EqKind::Head, 500); // theirs, worn
            gear(&mut s, 2, EqKind::Weapon(5), 7); // a GU weapon of the same class
            gear(&mut s, 3, EqKind::Chest, 500); // theirs, in the box only
            let mut e = Entry::new(EqKind::Legs, 9); // GU, worn, layered with theirs, a deco of theirs
            e.set_transmog(500, 1);
            e.add_deco(2889);
            eq::set(&mut s, b, Owner::Hunter, 4, &e);
            worn_set(&mut s, [0, 1, NONE, NONE, NONE, 4, NONE]);
            s.set_u16(b + eq::MY_SETS + 0x30 + 2, 1); // set 1: head (slot 1) = entry 1
            items::set(&mut s, b, Store::Box, 0, items::Stack { id: 2980, count: 3 });
            items::set(&mut s, b, Store::Box, 1, items::Stack { id: 100, count: 3 });
            s
        };
        let worn = |s: &Save| (0..7).map(|k| s.u16(b + eq::WORN + 2 * k)).collect::<Vec<_>>();
        // unequip: nothing deleted, the weapon swapped for the GU one, the look back to its own
        let mut s = base();
        clean_character(&mut s, b, &o, Clean::Unequip, &mut Counts::default()).unwrap();
        assert_eq!(worn(&s), [2, NONE, NONE, NONE, NONE, 4, NONE]);
        assert!(!eq::get(&s, b, Owner::Hunter, 0).is_empty() && !eq::get(&s, b, Owner::Hunter, 3).is_empty());
        assert_eq!(eq::get(&s, b, Owner::Hunter, 4).transmog(), 0);
        assert_eq!(eq::get(&s, b, Owner::Hunter, 4).decos()[0], 2889, "decorations stay");
        assert_eq!(s.u16(b + eq::MY_SETS + 0x32), NONE);
        assert_eq!(items::get(&s, b, Store::Box, 0).id, 2980);
        // worn only: the worn pieces deleted, the box keeps the chest
        let mut s = base();
        clean_character(&mut s, b, &o, Clean::RemoveWorn, &mut Counts::default()).unwrap();
        assert!(eq::get(&s, b, Owner::Hunter, 0).is_empty() && eq::get(&s, b, Owner::Hunter, 1).is_empty());
        assert!(!eq::get(&s, b, Owner::Hunter, 3).is_empty());
        // all: every piece, decoration and item of theirs
        let mut s = base();
        clean_character(&mut s, b, &o, Clean::RemoveAll, &mut Counts::default()).unwrap();
        assert!([0, 1, 3].iter().all(|&i| eq::get(&s, b, Owner::Hunter, i).is_empty()));
        assert_eq!(eq::get(&s, b, Owner::Hunter, 4).decos(), [0, 0, 0]);
        assert_eq!(items::get(&s, b, Store::Box, 0).id, 100, "their items removed, the box packed");
        // no other weapon: refused
        let mut s = base();
        eq::set(&mut s, b, Owner::Hunter, 2, &Entry { raw: [0; eq::ENTRY] });
        assert!(clean_character(&mut s, b, &o, Clean::Unequip, &mut Counts::default()).is_err());
    }

    #[test]
    fn a_save_on_disk_is_backed_up_migrated_and_found() {
        let d = tmp("disk");
        let mut s = Save::from_bytes(blank()).unwrap();
        items::set(&mut s, SLOT1_BASE, Store::Box, 0, items::Stack { id: 2977, count: 1 });
        let ryu = d.join("Ryujinx");
        let file = write_ryujinx(&ryu.join("bis/user/save/0000000000000002"), &s);
        let place = Place { kind: Kind::Ryujinx, name: "Ryujinx".into(), root: ryu.clone(), custom: true };
        let found = find(&place);
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].file, file);
        let steps = vec![Step { step: 1, items: vec![(2977, 3050)], ..Default::default() }];
        assert_eq!(need(&file, &steps), Need::Migrate(vec![(1, vec![1])]));
        let done = apply(&found[0], &steps, None, &d.join("backups"), "1.11.0").unwrap();
        let snap = done.backup.unwrap();
        assert!(snap.join("1/system_backup").is_file(), "every copy backed up");
        for c in ["0/system", "0/system_backup", "1/system", "1/system_backup"] {
            let s2 =
                Save::from_bytes(std::fs::read(ryu.join("bis/user/save/0000000000000002").join(c)).unwrap()).unwrap();
            assert_eq!(items::get(&s2, SLOT1_BASE, Store::Box, 0).id, 3050, "{c} written");
            assert_eq!(level(&s2, SLOT1_BASE), Some(1));
        }
        assert_eq!(need(&file, &steps), Need::Nothing, "migrated once");
        let unsupported = vec![Step { step: 2, quests: vec![(1, 2)], ..Default::default() }];
        assert!(matches!(need(&file, &unsupported), Need::Blocked(_)));
        // a Switch backup: the newest one is copied into a new folder, the original untouched
        let jk = d.join("sd/JKSV/Monster Hunter Generations Ultimate/User - 2026-11-01");
        std::fs::create_dir_all(&jk).unwrap();
        std::fs::write(jk.join("system"), s.bytes()).unwrap();
        let sd = Place { kind: Kind::SdCard, name: "SD".into(), root: d.join("sd"), custom: true };
        let f = find(&sd);
        assert_eq!(f.len(), 1);
        let done = apply(&f[0], &steps, None, &d.join("backups"), "1.11.0").unwrap();
        let new = done.new_backup.unwrap();
        assert_eq!(
            items::get(
                &Save::from_bytes(std::fs::read(new.join("system")).unwrap()).unwrap(),
                SLOT1_BASE,
                Store::Box,
                0
            )
            .id,
            3050
        );
        assert_eq!(
            items::get(
                &Save::from_bytes(std::fs::read(jk.join("system")).unwrap()).unwrap(),
                SLOT1_BASE,
                Store::Box,
                0
            )
            .id,
            2977
        );
        assert!(find(&sd)[0].file.starts_with(&jk), "the new folder is not offered again");
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn stamps_look_right() {
        let s = stamp();
        assert_eq!(s.len(), 17, "{s}");
        assert!(s.starts_with("20") && &s[10..11] == "_");
    }
}
