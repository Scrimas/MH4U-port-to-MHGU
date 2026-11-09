//! The install record `mh4uport-install.json`, kept in each place (places.rs record_path): the release installed and,
//! per package, its version and files with their sha256. It drives updates and removals; a mod folder without one is a
//! hand-extracted install (replaced after asking).

use crate::i18n::trf;
use crate::manifest::{FileEntry, Kind, Manifest};
use crate::places::{Layout, Place, TITLE_ID};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::path::Path;

pub const FILE: &str = "mh4uport-install.json";
pub const SCHEMA: u32 = 1;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Installed {
    pub version: String,
    pub kind: Kind,
    pub files: Vec<FileEntry>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Record {
    pub schema: u32,
    /// The release the place holds (`1.10.0`, `1.11.0-pre.1`).
    pub release: String,
    pub packages: BTreeMap<String, Installed>,
}

impl Record {
    pub fn new(release: &str) -> Record {
        Record { schema: SCHEMA, release: release.into(), packages: BTreeMap::new() }
    }

    /// The monsters it holds.
    pub fn monsters(&self) -> impl Iterator<Item = &str> {
        self.packages.iter().filter(|(_, p)| p.kind == Kind::Monster).map(|(n, _)| n.as_str())
    }
}

/// What a place holds.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum State {
    /// Nothing of the mod.
    Empty,
    /// Installed by this app.
    Recorded(Record),
    /// Mod files without a record: extracted by hand (or by the old installer).
    HandInstalled,
    /// A record this app cannot read (a newer installer's): left alone.
    Unreadable(String),
}

impl State {
    pub fn record(&self) -> Option<&Record> {
        match self {
            State::Recorded(r) => Some(r),
            _ => None,
        }
    }
}

/// The state of a place.
pub fn read(place: &Place, mod_folder: &str) -> State {
    let path = place.record_path(mod_folder);
    if let Ok(b) = std::fs::read(&path) {
        return match serde_json::from_slice::<Record>(&b) {
            Ok(r) if r.schema <= SCHEMA => State::Recorded(r),
            Ok(_) => State::Unreadable(trf("{} was written by a newer installer", &[&path.display()])),
            Err(e) => State::Unreadable(trf("{} is damaged ({})", &[&path.display(), &e])),
        };
    }
    let hand = match place.layout(mod_folder) {
        Layout::ModFolder(d) => std::fs::read_dir(&d).is_ok_and(|mut rd| rd.next().is_some()),
        Layout::Atmosphere(r) => {
            let c = r.join("atmosphere/contents").join(TITLE_ID);
            c.join("romfs/nativeNX/mh4uport").is_dir()
                || c.join("exefs/subsdk1").is_file()
                || r.join("atmosphere/exefs_patches").join(mod_folder).is_dir()
        }
    };
    if hand { State::HandInstalled } else { State::Empty }
}

/// Write a record: a temporary file first, then renamed over the old one.
pub fn write(path: &Path, r: &Record) -> Result<(), String> {
    let err = |e: std::io::Error| trf("Could not write {} ({})", &[&path.display(), &e]);
    if let Some(d) = path.parent() {
        std::fs::create_dir_all(d).map_err(err)?;
    }
    let tmp = path.with_extension("json.tmp");
    let mut text = serde_json::to_string_pretty(r).expect("a record serialises");
    text.push('\n');
    std::fs::write(&tmp, text).map_err(err)?;
    std::fs::rename(&tmp, path).map_err(err)
}

/// The record of a finished install: `packages` (names) of manifest `m`.
pub fn of(m: &Manifest, packages: &[String]) -> Record {
    let mut r = Record::new(&m.release);
    for n in packages {
        if let Some(p) = m.package(n) {
            r.packages
                .insert(n.clone(), Installed { version: p.version.clone(), kind: p.kind, files: p.files.clone() });
        }
    }
    r
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::places::Kind as PlaceKind;
    use std::path::PathBuf;

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("mh4u-record-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn a_record_round_trips() {
        let d = tmp("rt");
        let m = crate::manifest::tests::sample();
        let r = of(&m, &["core".into(), "gogmazios".into(), "battlequarters".into()]);
        let place = Place { kind: PlaceKind::Folder, name: String::new(), root: d.clone(), custom: true };
        assert_eq!(read(&place, "MH4U Port"), State::Empty);
        write(&place.record_path("MH4U Port"), &r).unwrap();
        assert_eq!(read(&place, "MH4U Port"), State::Recorded(r.clone()));
        assert_eq!(r.monsters().collect::<Vec<_>>(), ["gogmazios"]);
        std::fs::write(place.record_path("MH4U Port"), "{").unwrap();
        assert!(matches!(read(&place, "MH4U Port"), State::Unreadable(_)));
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn mod_files_without_a_record_are_a_hand_install() {
        let d = tmp("hand");
        let place = Place { kind: PlaceKind::Folder, name: String::new(), root: d.clone(), custom: true };
        std::fs::create_dir_all(d.join("MH4U Port/romfs")).unwrap();
        assert_eq!(read(&place, "MH4U Port"), State::HandInstalled);
        let sd = Place { kind: PlaceKind::SdCard, name: String::new(), root: d.join("sd"), custom: true };
        std::fs::create_dir_all(d.join("sd/atmosphere/contents/0100770008DD8000/romfs/nativeNX/other")).unwrap();
        assert_eq!(read(&sd, "MH4U Port"), State::Empty, "another mod's files are not ours");
        std::fs::create_dir_all(d.join("sd/atmosphere/contents/0100770008DD8000/romfs/nativeNX/mh4uport")).unwrap();
        assert_eq!(read(&sd, "MH4U Port"), State::HandInstalled);
        std::fs::remove_dir_all(&d).unwrap();
    }
}
