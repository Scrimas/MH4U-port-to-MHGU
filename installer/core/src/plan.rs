//! What one wanted set of monsters means for one place: the packages to add, update and remove. The core always comes
//! along, each monster brings the packages it requires (maps, later shared utilities), and a required package leaves
//! with the last monster that needs it. A release is one matched set: a place on an older release has every package
//! it keeps moved to this one.

use crate::manifest::{Kind, Manifest};
use crate::record::{Record, State};
use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Action {
    Add,
    Update { from: String },
    Remove { version: String },
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Change {
    pub package: String,
    pub title: String,
    pub kind: Kind,
    pub action: Action,
    /// The release's version of the package ("" for a package gone from the release).
    pub version: String,
    /// Download size (0 for a removal).
    pub size: u64,
    /// A required package: the wanted monsters that need it.
    pub needed_by: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlacePlan {
    /// Mod files without a record are removed first, then everything is installed fresh.
    pub replace_hand_install: bool,
    /// What a release before 2.0.0 left (places.rs legacy), removed with the install (apply.rs plan_for fills it).
    pub legacy: Vec<std::path::PathBuf>,
    pub changes: Vec<Change>,
    /// The packages the place holds afterwards (the record's), in install order.
    pub keep: Vec<String>,
    /// The release the record names now ("" = none).
    pub from_release: String,
    pub to_release: String,
}

impl PlacePlan {
    /// Nothing to do: no change and the record already names this release.
    pub fn is_empty(&self) -> bool {
        self.changes.is_empty()
            && !self.replace_hand_install
            && self.legacy.is_empty()
            && self.from_release == self.to_release
    }

    pub fn download_size(&self) -> u64 {
        self.changes.iter().map(|c| c.size).sum()
    }

    pub fn removals(&self) -> impl Iterator<Item = &Change> {
        self.changes.iter().filter(|c| matches!(c.action, Action::Remove { .. }))
    }

    /// The packages to extract from their zips (added, updated, or all when replacing a hand install).
    pub fn to_extract(&self) -> Vec<String> {
        if self.replace_hand_install {
            return self.keep.clone();
        }
        self.changes.iter().filter(|c| !matches!(c.action, Action::Remove { .. })).map(|c| c.package.clone()).collect()
    }
}

/// Same version and same files: nothing to download.
fn up_to_date(r: &Record, m: &Manifest, name: &str) -> bool {
    match (r.packages.get(name), m.package(name)) {
        (Some(i), Some(p)) => i.version == p.version && i.files == p.files,
        _ => false,
    }
}

/// The plan of one place for `wanted` monsters; `remove_all`: the mod leaves the place, core included.
pub fn plan(m: &Manifest, wanted: &BTreeSet<String>, state: &State, remove_all: bool) -> PlacePlan {
    let keep = if remove_all { vec![] } else { m.closure(wanted) };
    let needed_by = |n: &str| -> Vec<String> {
        m.needed_by(n).into_iter().filter(|p| wanted.contains(&p.name)).map(|p| p.shown_title()).collect()
    };
    let change = |n: &str, action: Action| {
        let p = m.package(n);
        Change {
            package: n.to_string(),
            title: p.map_or_else(|| n.to_string(), |p| p.shown_title()),
            kind: p.map_or(Kind::Utility, |p| p.kind),
            size: if matches!(action, Action::Remove { .. }) { 0 } else { p.map_or(0, |p| p.size) },
            version: p.map_or_else(String::new, |p| p.version.clone()),
            needed_by: if p.is_some_and(|p| p.kind != Kind::Core && p.kind != Kind::Monster) {
                needed_by(n)
            } else {
                vec![]
            },
            action,
        }
    };
    let mut changes = vec![];
    let (replace, from) = match state {
        State::Recorded(r) => {
            for n in &keep {
                match r.packages.get(n) {
                    None => changes.push(change(n, Action::Add)),
                    Some(i) if !up_to_date(r, m, n) => {
                        changes.push(change(n, Action::Update { from: i.version.clone() }))
                    }
                    Some(_) => {}
                }
            }
            for (n, i) in &r.packages {
                if !keep.contains(n) {
                    let mut c = change(n, Action::Remove { version: i.version.clone() });
                    c.kind = i.kind;
                    changes.push(c);
                }
            }
            (false, r.release.clone())
        }
        State::HandInstalled => {
            changes.extend(keep.iter().map(|n| change(n, Action::Add)));
            (true, String::new())
        }
        State::Empty | State::Unreadable(_) => {
            changes.extend(keep.iter().map(|n| change(n, Action::Add)));
            (false, String::new())
        }
    };
    let to = if keep.is_empty() { String::new() } else { m.release.clone() };
    PlacePlan { replace_hand_install: replace, legacy: vec![], changes, keep, from_release: from, to_release: to }
}

/// The monsters to show switched on: those the ticked places hold (any of them), else every monster of the release.
pub fn initial_wanted<'a>(m: &Manifest, records: impl Iterator<Item = &'a Record>) -> BTreeSet<String> {
    let have: BTreeSet<String> = records.flat_map(|r| r.monsters().map(String::from).collect::<Vec<_>>()).collect();
    if have.is_empty() {
        m.monsters().map(|p| p.name.clone()).collect()
    } else {
        have.into_iter().filter(|n| m.package(n).is_some()).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::tests::sample;
    use crate::record::of;

    fn set(n: &[&str]) -> BTreeSet<String> {
        n.iter().map(|s| s.to_string()).collect()
    }

    fn actions(p: &PlacePlan) -> Vec<(String, &'static str)> {
        p.changes
            .iter()
            .map(|c| {
                let a = match c.action {
                    Action::Add => "add",
                    Action::Update { .. } => "update",
                    Action::Remove { .. } => "remove",
                };
                (c.package.clone(), a)
            })
            .collect()
    }

    #[test]
    fn a_fresh_place_gets_core_monsters_and_their_maps() {
        let m = sample();
        let p = plan(&m, &set(&["gogmazios"]), &State::Empty, false);
        assert_eq!(
            actions(&p),
            [("core".into(), "add"), ("battlequarters".into(), "add"), ("gogmazios".into(), "add")]
        );
        assert_eq!(p.changes[1].needed_by, ["gogmazios"]);
        assert_eq!(p.to_release, "1.10.0");
        assert!(!p.is_empty());
    }

    #[test]
    fn a_shared_map_stays_until_its_last_monster_leaves() {
        let m = sample();
        let r = of(&m, &m.closure(&set(&["dalamadur", "shah"])));
        let p = plan(&m, &set(&["shah"]), &State::Recorded(r.clone()), false);
        assert_eq!(actions(&p), [("dalamadur".into(), "remove")]);
        let p = plan(&m, &set(&[]), &State::Recorded(r), false);
        assert_eq!(
            actions(&p),
            [("dalamadur".into(), "remove"), ("shah".into(), "remove"), ("speartip_crag".into(), "remove")]
        );
    }

    #[test]
    fn an_older_release_moves_whole_to_this_one() {
        let m = sample();
        let mut r = of(&m, &m.closure(&set(&["gogmazios", "monoblos"])));
        r.release = "1.9.5".into();
        r.packages.get_mut("gogmazios").unwrap().version = "1.1.6".into();
        r.packages.get_mut("core").unwrap().files[0].sha256 = "11".into();
        let p = plan(&m, &set(&["gogmazios", "monoblos"]), &State::Recorded(r.clone()), false);
        assert_eq!(actions(&p), [("core".into(), "update"), ("gogmazios".into(), "update")]);
        assert_eq!(p.changes[1].action, Action::Update { from: "1.1.6".into() });
        // nothing changed but the release: only the record moves
        let mut r2 = of(&m, &m.closure(&set(&["monoblos"])));
        r2.release = "1.9.5".into();
        let p = plan(&m, &set(&["monoblos"]), &State::Recorded(r2), false);
        assert!(p.changes.is_empty() && !p.is_empty());
        // a package the release no longer has leaves
        r.packages.insert("old_monster".into(), r.packages["monoblos"].clone());
        let p = plan(&m, &set(&["gogmazios", "monoblos"]), &State::Recorded(r), false);
        assert!(actions(&p).contains(&("old_monster".into(), "remove")));
    }

    #[test]
    fn a_hand_install_is_replaced_and_up_to_date_is_empty() {
        let m = sample();
        let p = plan(&m, &set(&["monoblos"]), &State::HandInstalled, false);
        assert!(p.replace_hand_install);
        assert_eq!(p.to_extract(), ["core", "monoblos"]);
        let r = of(&m, &m.closure(&set(&["monoblos"])));
        assert!(plan(&m, &set(&["monoblos"]), &State::Recorded(r.clone()), false).is_empty());
        let all = plan(&m, &set(&["monoblos"]), &State::Recorded(r), true);
        assert_eq!(actions(&all), [("core".into(), "remove"), ("monoblos".into(), "remove")]);
        assert!(all.keep.is_empty() && all.to_release.is_empty());
    }

    #[test]
    fn the_switches_start_from_what_is_installed() {
        let m = sample();
        assert_eq!(initial_wanted(&m, std::iter::empty()).len(), 4);
        let a = of(&m, &m.closure(&set(&["monoblos"])));
        let b = of(&m, &m.closure(&set(&["gogmazios"])));
        assert_eq!(initial_wanted(&m, [&a, &b].into_iter()), set(&["gogmazios", "monoblos"]));
    }
}
