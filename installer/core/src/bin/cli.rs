//! mhgu-de-cli: the installer without its window (installer/tests/cli_test.py, scripts).
//!
//!   mhgu-de-cli places                                   the install places found, with what each holds
//!   mhgu-de-cli releases [--pre]                         the mod releases this installer can install
//!   mhgu-de-cli install --place KIND:PATH ... [--monsters a,b | all | none] [--pre] [--replace] [--yes]
//!                       [--clean unequip | worn | all | none] [--anyway]
//!   mhgu-de-cli remove --place KIND:PATH ... [--yes]     the mod leaves those places (core included)
//!
//! KIND: ryujinx, yuzu, recomp, sdcard, folder (PATH = that place's root, places.rs). --monsters default: what the
//! places hold, else all. A hand-extracted install (or the mod's folder from before 2.0.0, `MH4U Port`) is replaced
//! only with --replace (exit 3 otherwise). The places' saves get the release's migrations, and the gear of removed
//! monsters is cleaned (--clean, default unequip: saves.rs), after a backup ($MHGU_DE_BACKUPS); a save that cannot be
//! migrated stops the install unless --anyway (exit 4). Releases come from GitHub, or from $MHGU_DE_RELEASES (a folder
//! with releases.json, source.rs); downloads are cached in $MHGU_DE_CACHE. Exit 0 done, 1 error, 2 usage, 3 needs
//! --replace, 4 needs --anyway.

use mhgu_de_core::apply;
use mhgu_de_core::manifest::Manifest;
use mhgu_de_core::places::{self, Kind, Place};
use mhgu_de_core::plan::{Action, initial_wanted};
use mhgu_de_core::record::State;
use mhgu_de_core::saves::{self, Clean, Need, Owned};
use mhgu_de_core::source::{Source, mod_releases};
use std::collections::BTreeSet;
use std::path::PathBuf;
use std::process::exit;
use std::sync::atomic::AtomicBool;

fn usage() -> ! {
    eprintln!(
        "{}",
        include_str!("cli.rs")
            .lines()
            .skip(2)
            .take(13)
            .map(|l| l.trim_start_matches("//!").trim_start_matches(' '))
            .collect::<Vec<_>>()
            .join("\n")
    );
    exit(2)
}

fn fail(e: String) -> ! {
    eprintln!("error: {e}");
    exit(1)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let flag = |f: &str| args.iter().any(|a| a == f);
    let values = |f: &str| -> Vec<String> { args.windows(2).filter(|w| w[0] == f).map(|w| w[1].clone()).collect() };
    let pre = flag("--pre");
    match args.first().map(String::as_str) {
        Some("places") => {
            for p in places::detect(&[]) {
                println!("{}\t{}\t{}", p.kind.key(), p.name, p.root.display());
            }
        }
        Some("releases") => {
            let all = Source::mods().releases().unwrap_or_else(|e| fail(e));
            for r in mod_releases(&all, pre) {
                println!("{}\t{}\t{}", r.tag, if r.prerelease { "pre-release" } else { "release" }, r.day());
            }
        }
        Some(cmd @ ("install" | "remove")) => {
            let places: Vec<Place> = values("--place")
                .iter()
                .map(|s| {
                    let (k, p) = s.split_once(':').unwrap_or_else(|| usage());
                    let kind = Kind::from_key(k).unwrap_or_else(|| usage());
                    Place { kind, name: p.to_string(), root: PathBuf::from(p), custom: true }
                })
                .collect();
            if places.is_empty() {
                usage();
            }
            let src = Source::mods();
            let all = src.releases().unwrap_or_else(|e| fail(e));
            let rel =
                mod_releases(&all, pre).into_iter().next().unwrap_or_else(|| fail("no release to install".into()));
            let ma = rel.asset("manifest.json").unwrap();
            let m = Manifest::parse(&src.bytes(ma).unwrap_or_else(|e| fail(e))).unwrap_or_else(|e| fail(e));
            let states: Vec<State> = places.iter().map(|p| mhgu_de_core::record::read(p, &m.mod_folder)).collect();
            let wanted: BTreeSet<String> = match values("--monsters").first().map(String::as_str) {
                Some("all") => m.monsters().map(|p| p.name.clone()).collect(),
                Some("none") => BTreeSet::new(),
                Some(list) => list.split(',').map(str::to_string).collect(),
                None => initial_wanted(&m, states.iter().filter_map(State::record)),
            };
            if let Some(bad) = wanted.iter().find(|n| m.monsters().all(|p| &p.name != *n)) {
                fail(format!("{bad} is no monster of release {}", m.release));
            }
            let remove_all = cmd == "remove";
            let plans: Vec<_> = places.iter().map(|p| apply::plan_for(p, &m, &wanted, remove_all)).collect();
            println!("release {}", m.release);
            for (p, (state, plan)) in places.iter().zip(&plans) {
                println!("{} ({}): {}", p.name, p.root.display(), if plan.is_empty() { "up to date" } else { "" });
                if let State::Unreadable(why) = state {
                    fail(why.clone());
                }
                for old in &plan.legacy {
                    println!("  remove {} (the mod from before 2.0.0)", old.display());
                }
                if plan.replace_hand_install {
                    println!("  replace the hand-extracted install");
                    if !flag("--replace") {
                        eprintln!("{}: a hand-extracted install is there: run again with --replace", p.root.display());
                        exit(3);
                    }
                }
                for c in &plan.changes {
                    let what = match &c.action {
                        Action::Add => format!("add {}", c.version),
                        Action::Update { from } if *from == c.version => format!("repair {}", c.version),
                        Action::Update { from } => format!("update {from} -> {}", c.version),
                        Action::Remove { version } => format!("remove {version}"),
                    };
                    let by = if c.needed_by.is_empty() {
                        String::new()
                    } else {
                        format!(" (for {})", c.needed_by.join(", "))
                    };
                    println!("  {} {what}{by}", c.package);
                }
            }
            // saves: migrations of the release, cleaning of the monsters that leave
            let steps = saves::steps(&m).unwrap_or_else(|e| fail(e));
            let fmt = saves::format(&m);
            let clean = match values("--clean").first().map(String::as_str) {
                None | Some("unequip") => Some(Clean::Unequip),
                Some("worn") => Some(Clean::RemoveWorn),
                Some("all") => Some(Clean::RemoveAll),
                Some("none") => None,
                _ => usage(),
            };
            let mut save_jobs = vec![];
            let mut blocked = 0;
            for (p, (_, plan)) in places.iter().zip(&plans) {
                let mut leaving = Owned::default();
                for c in plan.removals().filter(|c| c.kind == mhgu_de_core::manifest::Kind::Monster) {
                    leaving.add(&saves::owned(&m, &c.package));
                }
                let held = std::collections::BTreeMap::from([("leaving".to_string(), leaving.clone())]);
                for f in saves::find(p) {
                    let need = saves::need(&f.file, &steps, fmt.as_deref());
                    let cleans = clean.is_some()
                        && !leaving.is_empty()
                        && !saves::holds(&f.file, &held, fmt.as_deref()).is_empty();
                    match &need {
                        Need::Blocked(why) => {
                            println!("  save {}: cannot be migrated ({why})", f.label);
                            blocked += 1;
                        }
                        Need::Migrate(v) => {
                            let steps: Vec<(usize, &Vec<u32>)> =
                                v.iter().filter(|w| !w.steps.is_empty()).map(|w| (w.slot, &w.steps)).collect();
                            let split: Vec<usize> = v.iter().filter(|w| w.split).map(|w| w.slot).collect();
                            let mut what = String::new();
                            if !steps.is_empty() {
                                what += &format!(" migrate {steps:?}");
                            }
                            if !split.is_empty() {
                                what += &format!(" split {split:?}");
                            }
                            println!("  save {}:{what}", f.label)
                        }
                        Need::Nothing if cleans => println!("  save {}: clean", f.label),
                        Need::Nothing => {}
                    }
                    if !matches!(need, Need::Blocked(_)) && (matches!(need, Need::Migrate(_)) || cleans) {
                        save_jobs.push((f, clean.filter(|_| cleans).map(|c| (leaving.clone(), c))));
                    }
                }
            }
            if blocked > 0 && !flag("--anyway") {
                eprintln!("{blocked} save(s) cannot be migrated: run again with --anyway to install without them");
                exit(4);
            }
            if plans.iter().all(|(_, p)| p.is_empty()) && save_jobs.is_empty() {
                return;
            }
            if !flag("--yes") {
                fail("add --yes to apply".into());
            }
            let need: Vec<String> =
                plans.iter().flat_map(|(_, p)| p.to_extract()).collect::<BTreeSet<_>>().into_iter().collect();
            let cancel = AtomicBool::new(false);
            let cache = mhgu_de_core::settings::cache_dir();
            let zips = apply::fetch(&src, &rel, &m, &need, &cache, &|_, _, _| {}, &cancel).unwrap_or_else(|e| fail(e));
            for (p, (state, plan)) in places.iter().zip(&plans) {
                if !plan.is_empty() {
                    apply::install(p, &m, state, plan, &zips, &|_, _, _| {}, &cancel).unwrap_or_else(|e| fail(e));
                    println!("{}: done", p.name);
                }
            }
            apply::prune_cache(&cache, &m.release);
            for (f, clean) in &save_jobs {
                let done = saves::apply(
                    f,
                    &steps,
                    clean.as_ref().map(|(o, c)| (o, *c)),
                    &saves::backup_dir(),
                    &m.release,
                    fmt.as_deref(),
                )
                .unwrap_or_else(|e| fail(format!("{}: {e}", f.label)));
                let backup = done.backup.map(|b| b.display().to_string()).unwrap_or_default();
                println!("save {}: {} change(s), backup {backup}", f.label, done.counts.total());
            }
        }
        // the mod's save files, one slot at a time, for tools/test_modsave.py (the three implementations compared):
        //   modsave split SLOT QUESTS LINK GENERATION FILE_OUT SLOT_OUT [--compute]   exit 5: not split
        //   modsave merge SLOT FILE QUESTS SLOT_OUT                                    prints the counts
        // SLOT = one character's bytes (modsave::SLOT_SIZE), QUESTS = JSON [[list index, quest ID], ...]
        Some("modsave") => modsave_cmd(&args[1..]),
        _ => usage(),
    }
}

fn modsave_cmd(a: &[String]) {
    use mhgu_de_core::modsave;
    let read = |p: &str| std::fs::read(p).unwrap_or_else(|e| fail(format!("{p}: {e}")));
    let write = |p: &str, b: &[u8]| std::fs::write(p, b).unwrap_or_else(|e| fail(format!("{p}: {e}")));
    let quests = |p: &str| -> Vec<modsave::Quest> {
        let v: Vec<(u32, u32)> = serde_json::from_slice(&read(p)).unwrap_or_else(|e| fail(format!("{p}: {e}")));
        v.into_iter().map(|(index, id)| modsave::Quest { index, id }).collect()
    };
    let num = |s: &str| s.parse::<u32>().unwrap_or_else(|_| usage());
    match a.first().map(String::as_str) {
        Some("split") if a.len() >= 7 => {
            let mut slot = read(&a[1]);
            let q = quests(&a[2]);
            let clean = !a.iter().any(|x| x == "--compute");
            match modsave::split(&mut slot, &q, num(&a[3]), num(&a[4]), &[], modsave::FILE_SIZE, clean) {
                Some((f, left)) => {
                    write(&a[5], &f);
                    write(&a[6], &slot);
                    println!("{} bytes, {left} left", f.len());
                }
                None => exit(5),
            }
        }
        Some("merge") if a.len() >= 5 => {
            let mut slot = read(&a[1]);
            let f = read(&a[2]);
            let (st, aside) =
                modsave::merge(&mut slot, &f, &quests(&a[3])).unwrap_or_else(|| fail("not a valid file".into()));
            write(&a[4], &slot);
            println!(
                "{{\"exact\": {}, \"placed\": {}, \"moved\": {}, \"kept\": {}, \"aside\": {}, \"aside_bytes\": {}}}",
                st.exact,
                st.placed,
                st.moved,
                st.kept,
                st.aside,
                aside.len()
            );
        }
        _ => usage(),
    }
}
