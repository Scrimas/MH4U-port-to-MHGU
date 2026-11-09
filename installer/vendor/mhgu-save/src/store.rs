//! Finding the save on disk, snapshots, and writing every copy.
//!
//! Ryujinx keeps the title's savedata as `<save-id>/0/` and `<save-id>/1/` (a
//! double-commit scheme), each with `system` and `system_backup`. All four files are
//! written with the same body; each keeps its own header (the entry key at 0x14, the
//! JAMCRC of the file name, differs between them and is left alone). See docs/01-container.md.

use crate::save::{Error, FILE_SIZE, Save};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

/// Bytes before this offset are the container header and are never written.
pub const HEADER: usize = 0x24;
pub const FILES: [&str; 2] = ["system", "system_backup"];

#[derive(Debug, Clone)]
pub struct Location {
    /// The file the user opened.
    pub opened: PathBuf,
    /// Every copy that will be written: `0/system`, `0/system_backup`, `1/system`, ...
    pub copies: Vec<PathBuf>,
    /// Folder holding `0/` and `1/`, when the opened file sits in that layout.
    pub save_dir: Option<PathBuf>,
    /// Fingerprint of each copy (None: missing) when it was opened or last written. A
    /// write refuses when one changed: the game saved meanwhile. Empty: not checked.
    seen: Vec<Option<u64>>,
}

fn fingerprint(b: &[u8]) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut h = std::collections::hash_map::DefaultHasher::new();
    b.hash(&mut h);
    h.finish()
}

impl Location {
    pub fn of(opened: &Path) -> Location {
        let opened = opened.to_path_buf();
        let commit = opened.parent().and_then(|p| p.file_name()).and_then(|n| n.to_str());
        let save_dir = match commit {
            Some("0") | Some("1") => opened.parent().and_then(Path::parent).map(Path::to_path_buf),
            _ => None,
        };
        let mut copies = vec![];
        match &save_dir {
            Some(d) => {
                for c in ["0", "1"] {
                    for f in FILES {
                        let p = d.join(c).join(f);
                        if p.is_file() {
                            copies.push(p);
                        }
                    }
                }
            }
            None => {
                copies.push(opened.clone());
                // the sibling is a copy only when the opened file is one of the pair
                let other = match opened.file_name().and_then(|n| n.to_str()) {
                    Some("system") => Some("system_backup"),
                    Some("system_backup") => Some("system"),
                    _ => None,
                };
                if let (Some(dir), Some(other)) = (opened.parent(), other) {
                    let p = dir.join(other);
                    if p.is_file() {
                        copies.push(p);
                    }
                }
            }
        }
        if !copies.contains(&opened) {
            copies.insert(0, opened.clone());
        }
        Location { opened, copies, save_dir, seen: vec![] }
    }

    /// Where `p` sits relative to the save: `0/system`, or the bare file name.
    fn rel(&self, p: &Path) -> PathBuf {
        match &self.save_dir {
            Some(d) => p.strip_prefix(d).unwrap_or(p).to_path_buf(),
            None => PathBuf::from(p.file_name().unwrap_or(p.as_os_str())),
        }
    }
}

/// How the copies on disk relate to the opened one.
#[derive(Debug, Clone, PartialEq)]
pub enum CopyState {
    Same,
    /// Body differs from the opened file (an older or newer commit).
    Differs,
    Missing,
    WrongSize(usize),
}

/// Each copy of a save and how it relates to the opened one.
pub type Copies = Vec<(PathBuf, CopyState)>;

pub fn open(path: &Path) -> Result<(Save, Location, Copies), Error> {
    let save = Save::from_bytes(fs::read(path).map_err(|e| Error::File(path.to_path_buf(), e))?)?;
    let mut loc = Location::of(path);
    let mut states = vec![];
    for p in &loc.copies {
        let b = fs::read(p).ok();
        loc.seen.push(b.as_deref().map(fingerprint));
        states.push((p.clone(), copy_state(&save, b.as_deref())));
    }
    Ok((save, loc, states))
}

fn copy_state(save: &Save, b: Option<&[u8]>) -> CopyState {
    match b {
        None => CopyState::Missing,
        Some(b) if b.len() != FILE_SIZE => CopyState::WrongSize(b.len()),
        Some(b) if b[HEADER..] == save.original()[HEADER..] => CopyState::Same,
        Some(_) => CopyState::Differs,
    }
}

/// The first copy that changed on disk since it was opened or last written.
pub fn changed_on_disk(loc: &Location) -> Option<PathBuf> {
    if loc.seen.len() != loc.copies.len() {
        return None;
    }
    loc.copies
        .iter()
        .zip(&loc.seen)
        .find(|(p, s)| fs::read(p).ok().as_deref().map(fingerprint) != **s)
        .map(|(p, _)| p.clone())
}

/// The copy of the opened file in snapshot `snap`.
pub fn snapshot_file(loc: &Location, snap: &Path) -> PathBuf {
    snap.join(loc.rel(&loc.opened))
}

/// Copies every file of the save (both commit folders) into `dest/<timestamp>/`.
pub fn snapshot(loc: &Location, dest_root: &Path, stamp: &str) -> std::io::Result<PathBuf> {
    let dest = dest_root.join(stamp);
    for p in &loc.copies {
        let to = dest.join(loc.rel(p));
        fs::create_dir_all(to.parent().unwrap())?;
        fs::copy(p, &to)?;
    }
    Ok(dest)
}

/// Writes every (file, bytes) pair through a temporary file each, then renames them all
/// and reads each back: nothing is renamed until every temporary file is on disk. On any
/// failure the temporary files left are removed; a failure after the first rename is
/// `PartlyWritten`, naming the files already replaced.
fn replace_all(files: &[(PathBuf, Vec<u8>)], body_from: usize) -> Result<(), Error> {
    let tmp = |p: &Path| p.with_extension("mhgu-editor-tmp");
    let clean = |from: usize| {
        for (p, _) in &files[from..] {
            let _ = fs::remove_file(tmp(p));
        }
    };
    for (p, b) in files {
        let t = tmp(p);
        let r = fs::File::create(&t).and_then(|mut f| {
            f.write_all(b)?;
            f.sync_all()
        });
        if let Err(e) = r {
            clean(0);
            return Err(Error::File(t, e));
        }
    }
    for (k, (p, b)) in files.iter().enumerate() {
        let r = fs::rename(tmp(p), p).and_then(|_| fs::read(p)).and_then(|r| {
            match r.get(body_from..) == b.get(body_from..) {
                true => Ok(()),
                false => Err(std::io::Error::other("read-back mismatch")),
            }
        });
        if let Err(e) = r {
            clean(k);
            return Err(match k {
                0 => Error::File(p.clone(), e),
                _ => Error::PartlyWritten(p.clone(), e, files[..k].iter().map(|(p, _)| p.clone()).collect()),
            });
        }
    }
    // the renames themselves are durable once the folder is synced (not on Windows)
    #[cfg(unix)]
    for d in files.iter().filter_map(|(p, _)| p.parent()) {
        let _ = fs::File::open(d).and_then(|f| f.sync_all());
    }
    Ok(())
}

/// Copies a snapshot made by `snapshot` back over the save: every file it holds goes back
/// to its place, whole (headers too), through a temporary file and a rename. Files of
/// the wrong size are refused before anything is written. Returns the files restored.
pub fn restore(loc: &Location, snap: &Path) -> Result<Vec<PathBuf>, Error> {
    let mut files = vec![];
    for p in &loc.copies {
        let from = snap.join(loc.rel(p));
        if !from.is_file() {
            continue;
        }
        let b = fs::read(&from).map_err(|e| Error::File(from.clone(), e))?;
        if b.len() != FILE_SIZE {
            return Err(Error::CopySize(from, b.len()));
        }
        files.push((p.clone(), b));
    }
    if files.is_empty() {
        return Err(Error::File(snap.to_path_buf(), std::io::Error::other("no save files in this snapshot")));
    }
    replace_all(&files, 0)?;
    Ok(files.into_iter().map(|(p, _)| p).collect())
}

/// Writes the edited body into every copy, keeping each file's own header. Every copy is
/// read and checked first (size, unchanged since open); then all are written together
/// (`replace_all`). Returns the files written.
pub fn write_all(save: &mut Save, loc: &mut Location) -> Result<Vec<PathBuf>, Error> {
    let check = loc.seen.len() == loc.copies.len();
    let mut files = vec![];
    for (k, p) in loc.copies.iter().enumerate() {
        let mut b = fs::read(p).map_err(|e| Error::File(p.clone(), e))?;
        if check && Some(fingerprint(&b)) != loc.seen[k] {
            return Err(Error::ChangedOnDisk(p.clone()));
        }
        if b.len() != FILE_SIZE {
            return Err(Error::CopySize(p.clone(), b.len()));
        }
        b[HEADER..].copy_from_slice(&save.bytes()[HEADER..]);
        files.push((p.clone(), b));
    }
    replace_all(&files, HEADER)?;
    loc.seen = files.iter().map(|(_, b)| Some(fingerprint(b))).collect();
    save.commit();
    Ok(files.into_iter().map(|(p, _)| p).collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fake(dir: &Path, nonce: u8, body: u8) {
        for c in ["0", "1"] {
            fs::create_dir_all(dir.join(c)).unwrap();
            for (k, f) in FILES.iter().enumerate() {
                let mut v = vec![body; FILE_SIZE];
                v[..HEADER].fill(0);
                v[0x34..0x40].copy_from_slice(&[0x78, 0xCC, 0x18, 0, 0x3C, 0xC5, 0x2A, 0, 0x00, 0xBE, 0x3C, 0]);
                v[0x14] = nonce + k as u8;
                fs::write(dir.join(c).join(f), v).unwrap();
            }
        }
    }

    #[test]
    fn writes_four_copies_and_keeps_headers() {
        let dir = std::env::temp_dir().join(format!("mhgu-store-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fake(&dir, 7, 0);
        let (mut s, mut loc, states) = open(&dir.join("0/system")).unwrap();
        assert_eq!(loc.copies.len(), 4);
        assert!(states.iter().all(|(_, st)| *st == CopyState::Same));
        let snap = snapshot(&loc, &dir.join("snap"), "t").unwrap();
        assert!(snap.join("1/system_backup").is_file());
        s.set_u16(0x18CC9C + 0x28, 0x1234);
        let w = write_all(&mut s, &mut loc).unwrap();
        assert_eq!(w.len(), 4);
        for (k, f) in FILES.iter().enumerate() {
            let b = fs::read(dir.join("1").join(f)).unwrap();
            assert_eq!(b[0x14], 7 + k as u8, "nonce untouched");
            assert_eq!(&b[0x18CC9C + 0x28..0x18CC9C + 0x2A], &[0x34, 0x12]);
        }
        assert!(!s.is_dirty());
        // the snapshot puts every file back, headers included
        let r = restore(&loc, &snap).unwrap();
        assert_eq!(r.len(), 4);
        for (k, f) in FILES.iter().enumerate() {
            let b = fs::read(dir.join("1").join(f)).unwrap();
            assert_eq!(b[0x14], 7 + k as u8);
            assert_eq!(&b[0x18CC9C + 0x28..0x18CC9C + 0x2A], &[0, 0]);
        }
        fs::remove_dir_all(&dir).unwrap();
    }

    fn tmp_dir(name: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("mhgu-store-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&d);
        d
    }

    #[test]
    fn write_refuses_a_save_changed_on_disk() {
        let dir = tmp_dir("changed");
        fake(&dir, 1, 0);
        let (mut s, mut loc, _) = open(&dir.join("0/system")).unwrap();
        // the game saves meanwhile: a new nonce in one copy
        let mut b = fs::read(dir.join("1/system")).unwrap();
        b[0x14] = 0x55;
        fs::write(dir.join("1/system"), &b).unwrap();
        assert_eq!(changed_on_disk(&loc), Some(dir.join("1/system")));
        s.set_u8(0x18CC9C + 0x28, 9);
        assert!(matches!(write_all(&mut s, &mut loc), Err(Error::ChangedOnDisk(p)) if p == dir.join("1/system")));
        assert_eq!(fs::read(dir.join("0/system")).unwrap()[0x18CC9C + 0x28], 0, "nothing written");
        // after a write the new bytes are what the next write expects
        let (mut s, mut loc, _) = open(&dir.join("0/system")).unwrap();
        s.set_u8(0x18CC9C + 0x28, 9);
        write_all(&mut s, &mut loc).unwrap();
        s.set_u8(0x18CC9C + 0x28, 10);
        write_all(&mut s, &mut loc).unwrap();
        assert_eq!(changed_on_disk(&loc), None);
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn write_checks_every_copy_before_writing_any() {
        let dir = tmp_dir("size");
        fake(&dir, 1, 0);
        let mut loc = Location::of(&dir.join("0/system"));
        let mut s = Save::from_bytes(fs::read(dir.join("0/system")).unwrap()).unwrap();
        fs::write(dir.join("1/system_backup"), b"short").unwrap();
        s.set_u8(0x18CC9C + 0x28, 9);
        assert!(matches!(write_all(&mut s, &mut loc), Err(Error::CopySize(p, 5)) if p == dir.join("1/system_backup")));
        for f in ["0/system", "0/system_backup", "1/system"] {
            assert_eq!(fs::read(dir.join(f)).unwrap()[0x18CC9C + 0x28], 0, "{f} untouched");
        }
        assert!(!dir.join("0/system.mhgu-editor-tmp").exists());
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn a_failed_rename_names_the_replaced_copies_and_leaves_no_temporary_file() {
        let dir = tmp_dir("rename");
        fs::create_dir_all(dir.join("b")).unwrap();
        fs::write(dir.join("a"), b"old a").unwrap();
        fs::write(dir.join("c"), b"old c").unwrap();
        // a folder where the second file goes: its rename fails
        let files: Vec<_> = ["a", "b", "c"].iter().map(|f| (dir.join(f), b"new".to_vec())).collect();
        assert!(
            matches!(replace_all(&files, 0), Err(Error::PartlyWritten(p, _, done)) if p == dir.join("b") && done == [dir.join("a")])
        );
        assert_eq!(fs::read(dir.join("a")).unwrap(), b"new");
        assert_eq!(fs::read(dir.join("c")).unwrap(), b"old c");
        for f in ["a", "b", "c"] {
            assert!(!dir.join(f).with_extension("mhgu-editor-tmp").exists(), "{f}: temporary file left");
        }
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn sibling_backup_only_for_the_pair() {
        let dir = tmp_dir("sibling");
        fs::create_dir_all(&dir).unwrap();
        for f in ["system", "system_backup", "old.bin"] {
            fs::write(dir.join(f), b"x").unwrap();
        }
        assert_eq!(Location::of(&dir.join("old.bin")).copies, vec![dir.join("old.bin")]);
        assert_eq!(Location::of(&dir.join("system")).copies, vec![dir.join("system"), dir.join("system_backup")]);
        assert_eq!(
            Location::of(&dir.join("system_backup")).copies,
            vec![dir.join("system_backup"), dir.join("system")]
        );
        fs::remove_dir_all(&dir).unwrap();
    }
}
