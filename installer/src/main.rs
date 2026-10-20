//! MH4U Port installer: installs the latest MH4U Port release (core + chosen monsters) into an MHGU emulator mod
//! folder or an Atmosphère SD card, updates and uninstalls it (src/core.rs). Without arguments it opens the window;
//! with arguments it runs from the command line (CI tests, scripted installs):
//!
//!   mh4uport-installer --list [--repo OWNER/NAME | --source DIR]
//!   mh4uport-installer --target DIR (--install all|NAME,NAME | --uninstall-all) [--repo OWNER/NAME | --source DIR]
//!
//! --source DIR installs from a local folder holding manifest.json and the zips (tools/release.py package output).
#![cfg_attr(all(windows, not(debug_assertions)), windows_subsystem = "windows")]

mod core;

use crate::core::{cache_dir, detect, Installer, Manifest, Source, Target, DEFAULT_REPO};
use slint::{Model, ModelRc, SharedString, VecModel};
use std::cell::RefCell;
use std::path::PathBuf;
use std::rc::Rc;
use std::sync::{Arc, Mutex};

slint::include_modules!();

const USAGE: &str = "usage: mh4uport-installer [--list | --target DIR (--install all|NAME,... | --uninstall-all)] \
                     [--repo OWNER/NAME | --source DIR]";

fn release(args: &[String]) -> Result<(Source, Manifest), String> {
    let get = |k: &str| args.iter().position(|a| a == k).and_then(|i| args.get(i + 1).cloned());
    let source = match get("--source") {
        Some(d) => Source::Local(PathBuf::from(d)),
        None => Source::github_latest(&get("--repo").unwrap_or_else(|| DEFAULT_REPO.to_string()))?,
    };
    let manifest = source.manifest(&cache_dir())?;
    Ok((source, manifest))
}

fn cli(args: Vec<String>) -> i32 {
    let get = |k: &str| args.iter().position(|a| a == k).and_then(|i| args.get(i + 1).cloned());
    let (source, manifest) = match release(&args) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: {e}");
            return 1;
        }
    };
    if args.iter().any(|a| a == "--list") {
        println!("release {}: core {}", source.label(), manifest.core.version);
        for m in &manifest.monsters {
            println!("  monster {} {} ({})", m.name, m.version, m.title);
        }
        for t in detect() {
            println!("  target {}", t.label);
        }
        return 0;
    }
    let Some(dir) = get("--target") else {
        eprintln!("{USAGE}");
        return 2;
    };
    let want: Vec<String> = if args.iter().any(|a| a == "--uninstall-all") {
        Vec::new()
    } else {
        match get("--install").as_deref() {
            Some("all") => manifest.monsters.iter().map(|m| m.name.clone()).collect(),
            Some(list) => list.split(',').map(str::to_string).collect(),
            None => {
                eprintln!("{USAGE}");
                return 2;
            }
        }
    };
    for w in &manifest.warnings {
        eprintln!("note: {w}");
    }
    let target = Target::custom(&PathBuf::from(dir));
    let mut last = String::new();
    let mut log = |s: &str, _: f32| {
        if s != last {
            println!("{s}");
            last = s.to_string();
        }
    };
    let mut inst = Installer { target: &target, source: &source, manifest: &manifest, cache: cache_dir(), log: &mut log };
    match inst.apply(&want) {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("error: {e}");
            1
        }
    }
}

fn rows_for(target: &Target, m: &Manifest) -> Vec<MonsterRow> {
    let rec = target.record(&m.mod_name);
    let none = rec.monsters.is_empty();
    m.monsters
        .iter()
        .map(|p| MonsterRow {
            name: p.name.clone().into(),
            title: p.title.clone().into(),
            installed: rec.monsters.get(&p.name).map(|i| i.version.clone()).unwrap_or_default().into(),
            latest: p.version.clone().into(),
            selected: none || rec.monsters.contains_key(&p.name),
        })
        .collect()
}

type Release = Arc<Mutex<Option<(Arc<Source>, Manifest)>>>;

fn gui() -> Result<(), slint::PlatformError> {
    let ui = MainWindow::new()?;
    let found = detect();
    let mut labels: Vec<SharedString> = found.iter().map(|t| t.label.clone().into()).collect();
    if labels.is_empty() {
        labels.push("no emulator found: enter a folder below".into());
    }
    ui.set_target_labels(ModelRc::new(VecModel::from(labels)));
    let targets = Rc::new(RefCell::new(found));
    let current: Rc<RefCell<Option<Target>>> = Rc::new(RefCell::new(targets.borrow().first().cloned()));
    let release: Release = Arc::new(Mutex::new(None));
    let armed = Rc::new(RefCell::new(false));                 // second press confirms a removal

    let refresh = {
        let (weak, current, release) = (ui.as_weak(), current.clone(), release.clone());
        move || {
            let (Some(ui), Some(t)) = (weak.upgrade(), current.borrow().clone()) else { return };
            if let Some((_, m)) = release.lock().unwrap().as_ref() {
                ui.set_monsters(ModelRc::new(VecModel::from(rows_for(&t, m))));
            }
        }
    };

    {   // the latest release, off the UI thread
        let (weak, release) = (ui.as_weak(), release.clone());
        std::thread::spawn(move || {
            let res = release_latest();
            let _ = weak.upgrade_in_event_loop(move |ui| match res {
                Ok((s, m)) => {
                    ui.set_release_text(format!("Latest release: {} (core {})", s.label(), m.core.version).into());
                    ui.set_warnings(m.warnings.join("\n").into());
                    *release.lock().unwrap() = Some((Arc::new(s), m));
                    ui.set_ready(true);
                    ui.invoke_target_selected(ui.get_target_index());
                }
                Err(e) => ui.set_release_text(format!("Could not read the latest release: {e}").into()),
            });
        });
    }

    {
        let (targets, current, refresh) = (targets.clone(), current.clone(), refresh.clone());
        ui.on_target_selected(move |i| {
            if let Some(t) = targets.borrow().get(i as usize) {
                *current.borrow_mut() = Some(t.clone());
            }
            refresh();
        });
    }
    {
        let (weak, current, refresh) = (ui.as_weak(), current.clone(), refresh.clone());
        ui.on_use_path(move |p| {
            let p = PathBuf::from(p.trim());
            let Some(ui) = weak.upgrade() else { return };
            if !p.is_dir() {
                ui.set_status(format!("{} is not a folder", p.display()).into());
                return;
            }
            let t = Target::custom(&p);
            ui.set_status(format!("installing into {} ({:?})", t.label, t.layout).into());
            *current.borrow_mut() = Some(t);
            refresh();
        });
    }
    {
        let weak = ui.as_weak();
        ui.on_toggle(move |i, on| {
            let Some(ui) = weak.upgrade() else { return };
            let rows = ui.get_monsters();
            if let Some(mut r) = rows.row_data(i as usize) {
                r.selected = on;
                rows.set_row_data(i as usize, r);
            }
        });
    }
    let run = {
        let (weak, current, release, armed) = (ui.as_weak(), current.clone(), release.clone(), armed.clone());
        move |want: Vec<String>| {
            let Some(ui) = weak.upgrade() else { return };
            let Some(target) = current.borrow().clone() else {
                ui.set_status("choose where to install first".into());
                return;
            };
            let Some((source, manifest)) = release.lock().unwrap().clone() else { return };
            let rec = target.record(&manifest.mod_name);
            let removing: Vec<String> = rec.monsters.keys().filter(|k| !want.contains(k)).cloned().collect();
            if !removing.is_empty() && !*armed.borrow() {
                *armed.borrow_mut() = true;
                ui.set_status(format!("This removes {}: unequip its armor and weapons in game first. Press again \
                                       to confirm.", removing.join(", ")).into());
                return;
            }
            *armed.borrow_mut() = false;
            ui.set_busy(true);
            let weak = weak.clone();
            std::thread::spawn(move || {
                let w2 = weak.clone();
                let mut log = move |s: &str, f: f32| {
                    let s: SharedString = s.into();
                    let _ = w2.upgrade_in_event_loop(move |ui| {
                        ui.set_status(s);
                        ui.set_progress(f);
                    });
                };
                let mut inst = Installer { target: &target, source: &source, manifest: &manifest, cache: cache_dir(),
                                           log: &mut log };
                let res = inst.apply(&want);
                let rows = rows_for(&target, &manifest);
                let _ = weak.upgrade_in_event_loop(move |ui| {
                    ui.set_busy(false);
                    ui.set_monsters(ModelRc::new(VecModel::from(rows)));
                    match res {
                        Ok(()) => ui.set_status("Done. Start the game from your emulator.".into()),
                        Err(e) => ui.set_status(format!("Error: {e}").into()),
                    }
                });
            });
        }
    };
    {
        let (weak, run) = (ui.as_weak(), run.clone());
        ui.on_apply(move || {
            let Some(ui) = weak.upgrade() else { return };
            let want = ui.get_monsters().iter().filter(|r| r.selected).map(|r| r.name.to_string()).collect();
            run(want);
        });
    }
    ui.on_uninstall_all(move || run(Vec::new()));
    ui.run()
}

fn release_latest() -> Result<(Source, Manifest), String> {
    let s = Source::github_latest(DEFAULT_REPO)?;
    let m = s.manifest(&cache_dir())?;
    Ok((s, m))
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if !args.is_empty() {
        std::process::exit(cli(args));
    }
    if let Err(e) = gui() {
        eprintln!("error: {e}");
        std::process::exit(1);
    }
}
