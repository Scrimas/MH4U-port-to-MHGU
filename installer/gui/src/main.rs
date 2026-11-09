//! MH4U Port Installer: the window. The state lives on the UI thread (STATE); downloads, installs and the release
//! list run on worker threads that hand their results back through `slint::invoke_from_event_loop`. Everything that
//! decides what goes where is in mh4uport-core.
// Windows: a window app, no console
#![cfg_attr(windows, windows_subsystem = "windows")]

mod i18n;

use mh4uport_core::apply;
use mh4uport_core::i18n::{tr, trf, trn};
use mh4uport_core::manifest::{Kind, Manifest};
use mh4uport_core::places::{self, Custom, Place};
use mh4uport_core::plan::{Action, PlacePlan, initial_wanted};
use mh4uport_core::record::{self, State};
use mh4uport_core::selfupdate::{self, Update};
use mh4uport_core::settings::{self, Settings};
use mh4uport_core::source::{Release, Source, mod_releases};
use slint::{ComponentHandle, Image, ModelRc, Rgba8Pixel, SharedPixelBuffer, SharedString, VecModel};
use std::cell::RefCell;
use std::collections::{BTreeSet, HashMap};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

slint::include_modules!();

/// What the confirm dialog confirms.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Pending {
    None,
    Install,
    RemoveAll,
    Prereleases,
}

/// The progress of the running install, per package.
#[derive(Default)]
struct Progress {
    package: String,
    done: u64,
    total: u64,
    text: String,
}

struct App {
    settings: Settings,
    source: Source,
    places: Vec<Place>,
    states: Vec<State>,
    releases: Vec<Release>,
    release: Option<Release>,
    manifest: Option<Manifest>,
    icons: HashMap<String, Image>,
    wanted: BTreeSet<String>,
    /// the plans of the ticked places, (place index, state, plan)
    plans: Vec<(usize, State, PlacePlan)>,
    update: Option<Update>,
    pending: Pending,
    busy: bool,
    done_places: Vec<String>,
    progress: Progress,
    cancel: Arc<AtomicBool>,
    quit_when_done: bool,
}

thread_local! {
    static STATE: RefCell<Option<App>> = const { RefCell::new(None) };
    static UI: RefCell<Option<slint::Weak<AppWindow>>> = const { RefCell::new(None) };
}

fn with<R>(f: impl FnOnce(&mut App, &AppWindow) -> R) -> Option<R> {
    let ui = UI.with_borrow(|w| w.as_ref().and_then(|w| w.upgrade()))?;
    STATE.with_borrow_mut(|s| s.as_mut().map(|a| f(a, &ui)))
}

/// Run `f` on the UI thread (from a worker).
fn later(f: impl FnOnce(&mut App, &AppWindow) + Send + 'static) {
    let _ = slint::invoke_from_event_loop(move || {
        with(f);
    });
}

fn human(n: u64) -> String {
    let mb = n as f64 / 1_000_000.0;
    if mb >= 100.0 {
        format!("{mb:.0} MB")
    } else if mb >= 1.0 {
        format!("{mb:.1} MB")
    } else {
        format!("{} KB", (n / 1000).max(1))
    }
}

fn open_url(url: &str) {
    #[cfg(windows)]
    let r = std::process::Command::new("explorer").arg(url).spawn();
    #[cfg(not(windows))]
    let r = std::process::Command::new("xdg-open").arg(url).spawn();
    let _ = r;
}

fn monogram(title: &str) -> String {
    let words: Vec<&str> = title.split_whitespace().collect();
    let s: String = if words.len() >= 2 {
        words.iter().take(2).filter_map(|w| w.chars().next()).collect()
    } else {
        title.chars().take(2).collect()
    };
    s.to_uppercase()
}

fn line(text: impl Into<SharedString>, tone: i32, head: bool) -> Line {
    Line { text: text.into(), tone, head }
}

fn model<T: Clone + 'static>(v: Vec<T>) -> ModelRc<T> {
    ModelRc::new(VecModel::from(v))
}

// ------------------------------------------------------------------------------------------ loading

/// What the loader thread brings back.
struct Loaded {
    releases: Vec<Release>,
    picked: Result<Option<(Release, Manifest)>, String>,
    icons: Vec<(String, u32, u32, Vec<u8>)>,
}

fn load(src: Source, prereleases: bool) -> Loaded {
    let releases = match src.releases() {
        Ok(r) => r,
        Err(e) => return Loaded { releases: vec![], picked: Err(e), icons: vec![] },
    };
    let Some(rel) = mod_releases(&releases, prereleases).into_iter().next() else {
        return Loaded { releases, picked: Ok(None), icons: vec![] };
    };
    let picked = rel
        .asset("manifest.json")
        .ok_or_else(|| tr("The release has no manifest.json"))
        .and_then(|a| src.bytes(a))
        .and_then(|b| Manifest::parse(&b));
    let mut icons = vec![];
    if let Ok(m) = &picked
        && let Some(a) = m.icons.as_ref().and_then(|n| rel.asset(n))
        && let Ok(z) = src.bytes(a)
        && let Ok(entries) = mh4uport_core::zipread::entries(&z)
    {
        for e in entries {
            let Some(name) = e.name.strip_suffix(".png") else { continue };
            let Ok(png) = mh4uport_core::zipread::read(&z, &e) else { continue };
            if let Ok(img) = image::load_from_memory_with_format(&png, image::ImageFormat::Png) {
                let rgba = img.to_rgba8();
                icons.push((name.to_string(), rgba.width(), rgba.height(), rgba.into_raw()));
            }
        }
    }
    Loaded { releases, picked: picked.map(|m| Some((rel, m))), icons }
}

fn start_loading(app: &mut App, ui: &AppWindow) {
    app.manifest = None;
    app.release = None;
    ui.set_status(tr("Looking for the latest release…").into());
    ui.set_status_error(false);
    refresh(app, ui);
    let (src, pre) = (app.source.clone(), app.settings.prereleases);
    std::thread::spawn(move || {
        let l = load(src, pre);
        later(move |app, ui| loaded(app, ui, l));
    });
}

fn loaded(app: &mut App, ui: &AppWindow, l: Loaded) {
    app.releases = l.releases;
    for (name, w, h, px) in l.icons {
        let buf = SharedPixelBuffer::<Rgba8Pixel>::clone_from_slice(&px, w, h);
        app.icons.insert(name, Image::from_rgba8(buf));
    }
    match l.picked {
        Ok(Some((rel, m))) => {
            if mh4uport_core::version::older(mh4uport_core::VERSION, &m.installer_min) {
                ui.set_status(
                    trf(
                        "Release {} needs installer {} or newer: update the installer first.",
                        &[&m.release, &m.installer_min],
                    )
                    .into(),
                );
                ui.set_status_error(true);
            } else {
                ui.set_status("".into());
                app.release = Some(rel);
                app.manifest = Some(m);
            }
        }
        Ok(None) => {
            ui.set_status(tr("No release of the mod can be installed by this installer yet.").into());
            ui.set_status_error(false);
        }
        Err(e) => {
            ui.set_status(trf("Could not read the releases: {}", &[&e]).into());
            ui.set_status_error(true);
        }
    }
    if app.settings.check_updates {
        app.update = selfupdate::available(&app.releases, mh4uport_core::VERSION);
    }
    reread_places(app);
    if let Some(m) = &app.manifest {
        let ticked: Vec<&State> = app
            .places
            .iter()
            .zip(&app.states)
            .filter(|(p, _)| app.settings.ticked.contains(&p.id()))
            .map(|(_, s)| s)
            .collect();
        app.wanted = initial_wanted(m, ticked.into_iter().filter_map(State::record));
    }
    refresh(app, ui);
    // snapshots (MH4UPORT_SNAPSHOT): open a dialog first
    match std::env::var("MH4UPORT_SNAPSHOT_OPEN").as_deref() {
        Ok("review") => review(app, ui, false),
        Ok("settings") => ui.set_dialog(3),
        Ok("about") => ui.set_dialog(4),
        _ => {}
    }
}

fn reread_places(app: &mut App) {
    app.places = places::detect(&app.settings.custom);
    let mod_folder = app.manifest.as_ref().map_or("MH4U Port".to_string(), |m| m.mod_folder.clone());
    app.states = app.places.iter().map(|p| record::read(p, &mod_folder)).collect();
    // a ticked place that is gone from the list stays ticked in the settings (an SD card taken out)
}

// ------------------------------------------------------------------------------------------ the models

fn place_sub(p: &Place, s: &State) -> (String, bool) {
    let untested = if p.untested() { tr("Untested") + " · " } else { String::new() };
    let (t, warn) = match s {
        _ if !p.found() => (tr("Not found"), false),
        State::Empty => (tr("Found · nothing installed"), false),
        State::HandInstalled => (tr("Extracted by hand: replaced when you install"), true),
        State::Unreadable(_) => (tr("Its install record is unreadable"), true),
        State::Recorded(r) => {
            let n = r.monsters().count();
            (trf("Release {} · {}", &[&r.release, &trn("{} monster", "{} monsters", n)]), false)
        }
    };
    (untested + &t, warn || p.untested())
}

fn ticked(app: &App) -> Vec<usize> {
    (0..app.places.len())
        .filter(|&i| app.settings.ticked.contains(&app.places[i].id()) && app.places[i].found())
        .collect()
}

/// The row texts of one package from the plans of the ticked places: (version, tone, removal?).
fn status(app: &App, name: &str, version: &str) -> (String, i32, bool) {
    let (mut add, mut upd, mut rem, mut repair) = (false, None, None, false);
    for (_, _, plan) in &app.plans {
        for c in plan.changes.iter().filter(|c| c.package == name) {
            match &c.action {
                Action::Add => add = true,
                Action::Update { from } if *from == c.version => repair = true,
                Action::Update { from } => upd = Some(from.clone()),
                Action::Remove { version } => rem = Some(version.clone()),
            }
        }
    }
    let held = app
        .plans
        .iter()
        .any(|(_, s, p)| p.keep.iter().any(|k| k == name) && s.record().is_some_and(|r| r.packages.contains_key(name)));
    if let Some(from) = upd {
        (format!("{from} → {version}"), 1, false)
    } else if add {
        (trf("new · {}", &[&version]), 1, false)
    } else if repair {
        (trf("repair · {}", &[&version]), 1, false)
    } else if let Some(v) = rem {
        (trf("{} → none", &[&v]), 2, true)
    } else {
        (version.to_string(), if held { 3 } else { 0 }, false)
    }
}

fn row_progress(app: &App, name: &str) -> f32 {
    if app.busy && app.progress.package == name && app.progress.total > 0 {
        app.progress.done as f32 / app.progress.total as f32
    } else {
        -1.0
    }
}

fn refresh(app: &mut App, ui: &AppWindow) {
    // places
    let rows: Vec<PlaceRow> = app
        .places
        .iter()
        .zip(&app.states)
        .map(|(p, s)| {
            let (sub, warn) = place_sub(p, s);
            PlaceRow {
                id: p.id().into(),
                name: p.name.clone().into(),
                sub: sub.into(),
                ticked: app.settings.ticked.contains(&p.id()) && p.found(),
                enabled: p.found() && !app.busy,
                warn,
            }
        })
        .collect();
    ui.set_places(model(rows));
    let custom: Vec<PlaceRow> = app
        .places
        .iter()
        .filter(|p| p.custom)
        .map(|p| PlaceRow {
            id: p.id().into(),
            name: p.name.clone().into(),
            sub: p.root.display().to_string().into(),
            ticked: false,
            enabled: true,
            warn: false,
        })
        .collect();
    ui.set_custom_places(model(custom));
    ui.set_version(mh4uport_core::VERSION.into());
    ui.set_set_prereleases(app.settings.prereleases);
    ui.set_set_check_updates(app.settings.check_updates);
    let mut langs: Vec<SharedString> = vec![tr("System language").into()];
    langs.extend(i18n::LANGS.iter().map(|(_, n)| SharedString::from(*n)));
    ui.set_languages(model(langs));
    ui.set_language_index(if app.settings.language.is_empty() {
        0
    } else {
        i18n::index_of(&app.settings.language) as i32 + 1
    });
    // update card
    match &app.update {
        Some(u) => {
            ui.set_update_shown(true);
            ui.set_update_title(trf("Installer {} is out", &[&u.version]).into());
            ui.set_update_sub(human(u.size()).into());
        }
        None => ui.set_update_shown(false),
    }
    let Some(m) = app.manifest.clone() else {
        ui.set_has_release(false);
        ui.set_release_line(tr("No release").into());
        ui.set_rows(model(vec![]));
        ui.set_list_sub("".into());
        ui.set_summary("".into());
        ui.set_summary_sub("".into());
        ui.set_action(tr("Install").into());
        ui.set_action_enabled(false);
        return;
    };
    ui.set_has_release(true);
    let pre = if m.prerelease { format!(" ({})", tr("pre-release")) } else { String::new() };
    ui.set_release_line(format!("{}{pre} ·", trf("Release {}", &[&m.release])).into());
    // plans of the ticked places
    let t = ticked(app);
    app.plans = t
        .iter()
        .map(|&i| {
            let (s, p) = apply::plan_for(&app.places[i], &m, &app.wanted, false);
            (i, s, p)
        })
        .collect();
    // rows: core, then each monster followed by the packages it is the first to require
    let mut rows = vec![];
    let mut shown: BTreeSet<String> = BTreeSet::new();
    let core = m.core();
    let (v, tone, _) = status(app, &core.name, &core.version);
    rows.push(PkgRow {
        title: tr("Core").into(),
        sub: tr("Needed by every monster").into(),
        sub_tone: 0,
        size: human(core.size).into(),
        version: v.into(),
        version_tone: tone,
        on: true,
        locked: true,
        dep: false,
        icon: Image::default(),
        has_icon: false,
        monogram: "C".into(),
        progress: row_progress(app, &core.name),
    });
    for p in m.monsters() {
        let (v, tone, removed) = status(app, &p.name, &p.version);
        let mut sub =
            if removed { tr("Will be removed · take off its gear in game first") } else { p.subtitle.clone() };
        let mut sub_tone = if removed { 2 } else { 0 };
        if app.busy && app.progress.package == p.name {
            sub = app.progress.text.clone();
            sub_tone = 1;
        }
        let icon = p.icon.as_ref().and_then(|_| app.icons.get(&p.name)).cloned();
        rows.push(PkgRow {
            title: p.title.clone().into(),
            sub: sub.into(),
            sub_tone,
            size: human(p.size).into(),
            version: v.into(),
            version_tone: tone,
            on: app.wanted.contains(&p.name),
            locked: app.busy,
            dep: false,
            has_icon: icon.is_some(),
            icon: icon.unwrap_or_default(),
            monogram: monogram(&p.title).into(),
            progress: row_progress(app, &p.name),
        });
        for r in &p.requires {
            let Some(d) = m.package(r) else { continue };
            if !shown.insert(r.clone()) {
                continue;
            }
            let (v, tone, _) = status(app, &d.name, &d.version);
            let others: Vec<String> =
                m.needed_by(r).into_iter().filter(|o| o.name != p.name).map(|o| o.title.clone()).collect();
            let kind = if d.kind == Kind::Map { tr("map") } else { tr("shared files") };
            let sub = if others.is_empty() { kind } else { trf("{} · also for {}", &[&kind, &others.join(", ")]) };
            rows.push(PkgRow {
                title: d.title.clone().into(),
                sub: if app.busy && app.progress.package == d.name {
                    app.progress.text.clone().into()
                } else {
                    sub.into()
                },
                sub_tone: if app.busy && app.progress.package == d.name { 1 } else { 0 },
                size: human(d.size).into(),
                version: v.into(),
                version_tone: tone,
                on: false,
                locked: true,
                dep: true,
                icon: Image::default(),
                has_icon: false,
                monogram: monogram(&d.title).into(),
                progress: row_progress(app, &d.name),
            });
        }
    }
    ui.set_rows(model(rows));
    let n = m.monsters().count();
    ui.set_list_sub(trf("{} in this release · each brings the map it needs", &[&n]).into());
    // summary and action
    let changes: usize =
        app.plans.iter().map(|(_, _, p)| p.changes.len() + usize::from(p.changes.is_empty() && !p.is_empty())).sum();
    let removals: usize = app.plans.iter().map(|(_, _, p)| p.removals().count()).sum();
    let download: u64 = download_set(app).iter().filter_map(|n| m.package(n)).map(|p| p.size).sum();
    if t.is_empty() {
        ui.set_summary(tr("Nothing ticked").into());
        ui.set_summary_sub(tr("· tick where to install").into());
        ui.set_action(tr("Install").into());
        ui.set_action_enabled(false);
    } else if changes == 0 {
        ui.set_summary(tr("Up to date").into());
        ui.set_summary_sub("".into());
        ui.set_action(tr("Up to date").into());
        ui.set_action_enabled(false);
    } else {
        let mut sub = format!("· {}", human(download));
        if removals > 0 {
            sub += &format!(" · {}", trn("{} removal", "{} removals", removals));
        }
        ui.set_summary(trn("{} change", "{} changes", changes).into());
        ui.set_summary_sub(sub.into());
        ui.set_action(trn("Install {} change", "Install {} changes", changes).into());
        ui.set_action_enabled(!app.busy);
    }
}

/// The packages to download for every ticked place's plan, once each.
fn download_set(app: &App) -> Vec<String> {
    app.plans.iter().flat_map(|(_, _, p)| p.to_extract()).collect::<BTreeSet<_>>().into_iter().collect()
}

// ------------------------------------------------------------------------------------------ actions

fn message(ui: &AppWindow, title: &str, lines: Vec<Line>) {
    ui.set_dialog_title(title.into());
    ui.set_dialog_lines(model(lines));
    ui.set_dialog(2);
}

fn review(app: &mut App, ui: &AppWindow, remove_all: bool) {
    let Some(m) = app.manifest.clone() else { return };
    let plans: Vec<(usize, State, PlacePlan)> = if remove_all {
        ticked(app)
            .into_iter()
            .map(|i| {
                let (s, p) = apply::plan_for(&app.places[i], &m, &app.wanted, true);
                (i, s, p)
            })
            .collect()
    } else {
        app.plans.clone()
    };
    let mut lines = vec![];
    let mut monster_leaves = false;
    for (i, s, p) in &plans {
        if p.is_empty() {
            continue;
        }
        lines.push(line(app.places[*i].name.clone(), 0, true));
        if let State::Unreadable(why) = s {
            lines.push(line(why.clone(), 2, false));
        }
        if p.replace_hand_install {
            lines.push(line(
                tr("An MH4U Port folder extracted by hand is there: it is removed, then installed fresh."),
                2,
                false,
            ));
        }
        for c in &p.changes {
            let what = match &c.action {
                Action::Add => trf("+ {} {} (new)", &[&c.title, &c.version]),
                Action::Update { from } if *from == c.version => {
                    trf("↻ {} {} (repaired: files were missing)", &[&c.title, &c.version])
                }
                Action::Update { from } => trf("↑ {} {} → {}", &[&c.title, from, &c.version]),
                Action::Remove { version } => trf("− {} {} (removed)", &[&c.title, version]),
            };
            let what =
                if c.needed_by.is_empty() { what } else { trf("{} · for {}", &[&what, &c.needed_by.join(", ")]) };
            monster_leaves |= c.kind == Kind::Monster && matches!(c.action, Action::Remove { .. });
            lines.push(line(what, if matches!(c.action, Action::Remove { .. }) { 2 } else { 0 }, false));
        }
        if p.changes.is_empty() {
            lines.push(line(trf("Moves to release {} (nothing to download)", &[&m.release]), 0, false));
        }
    }
    if lines.is_empty() {
        return;
    }
    lines.push(line(tr("Before you go on"), 0, true));
    if monster_leaves {
        lines.push(line(
            tr("A monster you remove takes its armor and weapon models with it: take its gear off in game first."),
            2,
            false,
        ));
    }
    if m.prerelease {
        lines.push(line(tr("This is a pre-release: it may contain bugs. Use it at your own discretion."), 2, false));
    }
    if !app.settings.warned_online {
        lines.push(line(tr("Online, everyone in the group needs the same release and the same monsters."), 0, false));
    }
    for w in &m.warnings {
        lines.push(line(w.clone(), 2, false));
    }
    let running = places::running_emulators();
    if !running.is_empty() {
        lines.push(line(
            trf("Close {} first: the game must not run while its files change.", &[&running.join(", ")]),
            2,
            false,
        ));
    }
    if !remove_all {
        let size: u64 = download_set(app).iter().filter_map(|n| m.package(n)).map(|p| p.size).sum();
        lines.push(line(trf("Download: {}", &[&human(size)]), 0, false));
    }
    app.pending = if remove_all { Pending::RemoveAll } else { Pending::Install };
    ui.set_dialog_title(if remove_all { tr("Remove the mod") } else { tr("Install these changes?") }.into());
    ui.set_confirm_label(if remove_all { tr("Remove") } else { tr("Install") }.into());
    ui.set_dialog_lines(model(lines));
    ui.set_dialog(1);
}

fn start_install(app: &mut App, ui: &AppWindow, remove_all: bool) {
    let running = places::running_emulators();
    if !running.is_empty() {
        message(
            ui,
            &tr("Close the game first"),
            vec![line(trf("{} is running: close it, then install again.", &[&running.join(", ")]), 2, false)],
        );
        return;
    }
    let (Some(m), Some(rel)) = (app.manifest.clone(), app.release.clone()) else { return };
    let jobs: Vec<(Place, State, PlacePlan)> = ticked(app)
        .into_iter()
        .map(|i| {
            let (s, p) = apply::plan_for(&app.places[i], &m, &app.wanted, remove_all);
            (app.places[i].clone(), s, p)
        })
        .filter(|(_, _, p)| !p.is_empty())
        .collect();
    if jobs.is_empty() {
        return;
    }
    app.busy = true;
    app.cancel.store(false, Ordering::Relaxed);
    app.progress = Progress::default();
    app.done_places = jobs.iter().filter(|(_, _, p)| !p.keep.is_empty()).map(|(p, _, _)| p.name.clone()).collect();
    ui.set_phase(1);
    ui.set_progress(0.0);
    ui.set_progress_text(tr("Starting…").into());
    refresh(app, ui);
    let (src, cancel) = (app.source.clone(), app.cancel.clone());
    let need: Vec<String> =
        jobs.iter().flat_map(|(_, _, p)| p.to_extract()).collect::<BTreeSet<_>>().into_iter().collect();
    let total: u64 = need.iter().filter_map(|n| m.package(n)).map(|p| p.size).sum();
    std::thread::spawn(move || {
        let base = std::sync::Mutex::new((String::new(), 0u64));
        let res = (|| {
            let zips = apply::fetch(
                &src,
                &rel,
                &m,
                &need,
                &settings::cache_dir(),
                &|pkg, done, size| {
                    // bytes of the packages before this one + this one's
                    let mut b = base.lock().unwrap();
                    if b.0 != pkg {
                        if !b.0.is_empty() {
                            let prev = m.package(&b.0).map_or(0, |p| p.size);
                            b.1 += prev;
                        }
                        b.0 = pkg.to_string();
                    }
                    let all = b.1 + done;
                    let (pkg, title) = (pkg.to_string(), m.package(pkg).map_or_else(String::new, |p| p.title.clone()));
                    later(move |app, ui| {
                        app.progress = Progress {
                            package: pkg,
                            done,
                            total: size,
                            text: trf("Downloading · {} / {}", &[&human(done), &human(size)]),
                        };
                        ui.set_progress(if total > 0 { all as f32 / total as f32 * 0.9 } else { 0.0 });
                        ui.set_progress_text(
                            trf("Downloading {} · {} / {}", &[&title, &human(all), &human(total)]).into(),
                        );
                        refresh(app, ui);
                    });
                },
                &cancel,
            )?;
            let n = jobs.len();
            for (k, (place, state, plan)) in jobs.iter().enumerate() {
                let name = place.name.clone();
                later(move |app, ui| {
                    app.progress = Progress::default();
                    ui.set_progress(0.9 + 0.1 * k as f32 / n as f32);
                    ui.set_progress_text(trf("Installing into {} ({} of {})", &[&name, &(k + 1), &n]).into());
                    refresh(app, ui);
                });
                apply::install(place, &m, state, plan, &zips, &|_, _, _| {}, &cancel)
                    .map_err(|e| trf("{}: {}", &[&place.name, &e]))?;
            }
            Ok::<(), String>(())
        })();
        later(move |app, ui| finished(app, ui, res, remove_all));
    });
}

fn finished(app: &mut App, ui: &AppWindow, res: Result<(), String>, remove_all: bool) {
    app.busy = false;
    app.progress = Progress::default();
    reread_places(app);
    if app.quit_when_done {
        let _ = slint::quit_event_loop();
        return;
    }
    match res {
        Ok(()) => {
            if !remove_all {
                app.settings.warned_online = true;
                let _ = settings::save(&app.settings);
            }
            ui.set_phase(2);
            ui.set_done_sub(if app.done_places.is_empty() {
                tr("The mod was removed.").into()
            } else {
                trf("Start MHGU in {}", &[&app.done_places.join(", ")]).into()
            });
        }
        Err(e) => {
            ui.set_phase(0);
            let cancelled = e == tr("Cancelled");
            message(
                ui,
                &if cancelled { tr("Cancelled") } else { tr("The install failed") },
                vec![line(
                    if cancelled {
                        tr(
                            "Nothing was changed in the places not yet reached; a place being installed keeps its old files.",
                        )
                    } else {
                        e
                    },
                    if cancelled { 0 } else { 2 },
                    false,
                )],
            );
        }
    }
    refresh(app, ui);
}

fn add_folder(app: &mut App, ui: &AppWindow) {
    let Some(dir) = rfd::FileDialog::new().set_title(tr("Where to install")).pick_folder() else { return };
    let kind = places::kind_of_folder(&dir);
    let c = Custom { kind, path: dir };
    if !app.settings.custom.contains(&c) {
        app.settings.custom.push(c.clone());
    }
    let p = Place { kind: c.kind, name: String::new(), root: c.path.clone(), custom: true };
    if !app.settings.ticked.contains(&p.id()) {
        app.settings.ticked.push(p.id());
    }
    let _ = settings::save(&app.settings);
    reread_places(app);
    refresh(app, ui);
    if kind == places::Kind::Recomp {
        message(
            ui,
            "MHGU PC Recomp",
            vec![line(
                tr(
                    "The mod has never been tested in MHGU PC Recomp: it is installed into its mods folder, use it at your own discretion.",
                ),
                2,
                false,
            )],
        );
    }
}

fn update_now(app: &mut App, ui: &AppWindow) {
    let Some(u) = app.update.clone() else { return };
    let Some(old) = selfupdate::target() else {
        message(
            ui,
            &tr("Update the installer"),
            vec![line(
                tr("This copy cannot replace itself: download the new installer from its release page."),
                0,
                false,
            )],
        );
        open_url(&u.release.page);
        return;
    };
    ui.set_update_busy(true);
    ui.set_update_progress(0.0);
    let (src, cancel) = (app.source.clone(), app.cancel.clone());
    std::thread::spawn(move || {
        let r = selfupdate::install(
            &src,
            &u,
            &old,
            &|d, t| {
                let f = if t > 0 { d as f32 / t as f32 } else { 0.0 };
                later(move |_, ui| ui.set_update_progress(f));
            },
            &cancel,
        );
        later(move |app, ui| {
            ui.set_update_busy(false);
            match r {
                Ok(done) => {
                    app.settings.update_leftover = done.aside.clone();
                    let _ = settings::save(&app.settings);
                    if selfupdate::restart(&done.file).is_ok() {
                        let _ = slint::quit_event_loop();
                    } else {
                        message(
                            ui,
                            &tr("Update the installer"),
                            vec![line(trf("Installed: start {}", &[&done.file.display()]), 0, false)],
                        );
                    }
                }
                Err(e) => message(ui, &tr("Update the installer"), vec![line(e, 2, false)]),
            }
        });
    });
}

fn main() {
    let mut s = settings::load();
    if let Some(p) = s.update_leftover.clone()
        && selfupdate::cleanup(&p)
    {
        s.update_leftover = None;
        let _ = settings::save(&s);
    }
    if std::env::args().any(|a| a == "--version") {
        println!("{}", mh4uport_core::VERSION);
        return;
    }
    let ui = AppWindow::new().expect("the window opens");
    i18n::set(i18n::index_of(&s.language));
    // CI (.github/workflows/installer.yml): the window opens, then closes by itself (--smoke); MH4UPORT_SNAPSHOT=<png>
    // also draws it into that file first (a crash, a hang or no picture fails the job)
    let snapshot = std::env::var_os("MH4UPORT_SNAPSHOT").filter(|v| !v.is_empty());
    if snapshot.is_some() || std::env::args().any(|a| a == "--smoke") {
        let weak = ui.as_weak();
        slint::Timer::single_shot(std::time::Duration::from_secs(3), move || {
            if let (Some(path), Some(ui)) = (&snapshot, weak.upgrade())
                && let Ok(px) = ui.window().take_snapshot()
            {
                let _ =
                    image::save_buffer(path, px.as_bytes(), px.width(), px.height(), image::ExtendedColorType::Rgba8);
            }
            let _ = slint::quit_event_loop();
        });
    }
    UI.with_borrow_mut(|w| *w = Some(ui.as_weak()));
    STATE.with_borrow_mut(|st| {
        *st = Some(App {
            settings: s,
            source: Source::from_env(),
            places: vec![],
            states: vec![],
            releases: vec![],
            release: None,
            manifest: None,
            icons: HashMap::new(),
            wanted: BTreeSet::new(),
            plans: vec![],
            update: None,
            pending: Pending::None,
            busy: false,
            done_places: vec![],
            progress: Progress::default(),
            cancel: Arc::new(AtomicBool::new(false)),
            quit_when_done: false,
        })
    });
    with(|app, ui| {
        reread_places(app);
        // first start: tick every emulator found (not SD cards)
        if app.settings.ticked.is_empty() {
            app.settings.ticked = app
                .places
                .iter()
                .filter(|p| p.found() && matches!(p.kind, places::Kind::Ryujinx | places::Kind::Yuzu))
                .map(Place::id)
                .collect();
        }
        start_loading(app, ui)
    });

    ui.on_toggle_place(|i| {
        with(|app, ui| {
            let Some(p) = app.places.get(i as usize) else { return };
            if app.busy || !p.found() {
                return;
            }
            let id = p.id();
            if let Some(k) = app.settings.ticked.iter().position(|t| *t == id) {
                app.settings.ticked.remove(k);
            } else {
                app.settings.ticked.push(id);
            }
            let _ = settings::save(&app.settings);
            refresh(app, ui);
        });
    });
    ui.on_toggle_package(|i| {
        with(|app, ui| {
            let Some(m) = &app.manifest else { return };
            // row i: 0 = core, then the monsters and their maps in refresh()'s order
            let mut k = 0;
            let mut shown = BTreeSet::new();
            let mut hit = None;
            for p in m.monsters() {
                k += 1;
                if k == i as usize {
                    hit = Some(p.name.clone());
                }
                k += p.requires.iter().filter(|r| m.package(r).is_some() && shown.insert(r.to_string())).count();
            }
            if app.busy {
                return;
            }
            if let Some(n) = hit
                && !app.wanted.remove(&n)
            {
                app.wanted.insert(n);
            }
            refresh(app, ui);
        });
    });
    ui.on_add_folder(|| {
        with(add_folder);
    });
    ui.on_act(|| {
        with(|app, ui| review(app, ui, false));
    });
    ui.on_confirm(|| {
        with(|app, ui| {
            ui.set_dialog(0);
            match std::mem::replace(&mut app.pending, Pending::None) {
                Pending::Install => start_install(app, ui, false),
                Pending::RemoveAll => start_install(app, ui, true),
                Pending::Prereleases => {
                    app.settings.prereleases = true;
                    let _ = settings::save(&app.settings);
                    start_loading(app, ui);
                }
                Pending::None => {}
            }
        });
    });
    ui.on_close_dialog(|| {
        with(|app, ui| {
            app.pending = Pending::None;
            ui.set_dialog(0);
        });
    });
    ui.on_cancel(|| {
        with(|app, ui| {
            app.cancel.store(true, Ordering::Relaxed);
            ui.set_progress_text(tr("Cancelling…").into());
        });
    });
    ui.on_finish(|| {
        with(|app, ui| {
            ui.set_phase(0);
            refresh(app, ui);
        });
    });
    ui.on_whats_new(|| {
        with(|app, _| {
            if let Some(r) = &app.release {
                open_url(&r.page);
            }
        });
    });
    ui.on_open_settings(|| {
        with(|app, ui| {
            refresh(app, ui);
            ui.set_dialog(3);
        });
    });
    ui.on_open_about(|| {
        with(|_, ui| ui.set_dialog(4));
    });
    ui.on_toggle_prereleases(|| {
        with(|app, ui| {
            if app.settings.prereleases {
                app.settings.prereleases = false;
                let _ = settings::save(&app.settings);
                ui.set_dialog(0);
                start_loading(app, ui);
            } else {
                app.pending = Pending::Prereleases;
                ui.set_dialog_title(tr("Offer pre-releases?").into());
                ui.set_confirm_label(tr("Offer pre-releases").into());
                ui.set_dialog_lines(model(vec![
                    line(tr("Pre-releases are test builds of the next release. They may contain bugs, and they can change your save in ways a later release does not: use them at your own discretion."), 2, false),
                    line(tr("While this is on, the installer installs the newest pre-release when there is one."), 0, false),
                ]));
                ui.set_dialog(1);
            }
        });
    });
    ui.on_toggle_check_updates(|| {
        with(|app, ui| {
            app.settings.check_updates = !app.settings.check_updates;
            if !app.settings.check_updates {
                app.update = None;
            } else {
                app.update = selfupdate::available(&app.releases, mh4uport_core::VERSION);
            }
            let _ = settings::save(&app.settings);
            refresh(app, ui);
        });
    });
    ui.on_set_language(|i| {
        with(|app, ui| {
            app.settings.language = if i <= 0 {
                String::new()
            } else {
                i18n::LANGS[(i as usize - 1).min(i18n::LANGS.len() - 1)].0.to_string()
            };
            let _ = settings::save(&app.settings);
            i18n::set(i18n::index_of(&app.settings.language));
            refresh(app, ui);
        });
    });
    ui.on_remove_custom(|i| {
        with(|app, ui| {
            let custom: Vec<Place> = app.places.iter().filter(|p| p.custom).cloned().collect();
            let Some(p) = custom.get(i as usize) else { return };
            app.settings.custom.retain(|c| !(c.kind == p.kind && c.path == p.root));
            app.settings.ticked.retain(|t| *t != p.id());
            let _ = settings::save(&app.settings);
            reread_places(app);
            refresh(app, ui);
        });
    });
    ui.on_remove_everything(|| {
        with(|app, ui| {
            ui.set_dialog(0);
            review(app, ui, true);
        });
    });
    ui.on_update_now(|| {
        with(update_now);
    });
    ui.window().on_close_requested(|| {
        let busy = with(|app, _| {
            if app.busy {
                app.cancel.store(true, Ordering::Relaxed);
                app.quit_when_done = true;
            }
            app.busy
        });
        if busy == Some(true) {
            slint::CloseRequestResponse::KeepWindowShown
        } else {
            slint::CloseRequestResponse::HideWindow
        }
    });
    ui.run().expect("the event loop runs");
}
