//! The bundled fallback fonts (gui/assets/fonts, made by packaging/fonts.py; packaging/build.py puts them in the
//! AppImage's usr/share/mhgu-de-installer/fonts). On Linux, Slint finds its fonts through fontconfig, loaded at start
//! (gui/Cargo.toml): without fontconfig the window would show no text, and with a fontconfig that has no font it would
//! not open (fontique 0.11 unwraps fontconfig's empty match). There, the window takes the bundled ones.

/// The fonts, in the order Slint falls back through them (the Chinese one of the window's language first).
#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
pub const FILES: [&str; 4] = ["Inter.ttf", "NotoSansSymbols.ttf", "NotoSansSC.ttf", "NotoSansTC.ttf"];

/// What the system has: fonts, no fontconfig, or a fontconfig without fonts.
#[cfg(target_os = "linux")]
#[derive(PartialEq)]
enum System {
    Fonts,
    NoFontconfig,
    NoFonts,
}

/// Asked to fontconfig the way fontique (Slint's font lookup) will: the same library, loaded the same way.
#[cfg(target_os = "linux")]
fn system() -> System {
    use fontconfig_sys::{FcSetSystem, statics::LIB_RESULT};
    let Ok(fc) = LIB_RESULT.as_ref() else { return System::NoFontconfig };
    // SAFETY: fontconfig's own calls: a config of our own, its font set read while the config lives, then destroyed
    let fonts = unsafe {
        let config = (fc.FcInitLoadConfigAndFonts)();
        if config.is_null() {
            return System::NoFonts;
        }
        let set = (fc.FcConfigGetFonts)(config, FcSetSystem);
        let n = if set.is_null() { 0 } else { (*set).nfont };
        (fc.FcConfigDestroy)(config);
        n
    };
    if fonts > 0 { System::Fonts } else { System::NoFonts }
}

/// Before the window and before any other thread: when the system has no font, the bundled ones, through Slint's
/// SLINT_FONT_PATH (unless the person set their own fonts), and through FONTCONFIG_FILE (gui/assets/fonts/fonts.conf)
/// when fontconfig has none. `lang`: the window's language at start (LANGS' code).
#[cfg(target_os = "linux")]
pub fn fallback(lang: &str) {
    let system = system();
    if system == System::Fonts {
        return;
    }
    let why = if system == System::NoFontconfig { "no fontconfig" } else { "fontconfig has no font" };
    let exe = std::env::current_exe().ok();
    let Some(dir) = exe
        .as_deref()
        .and_then(|e| Some(e.parent()?.parent()?.join("share/mhgu-de-installer/fonts")))
        .filter(|d| d.is_dir())
    else {
        eprintln!("fonts: {why}, and no bundled fonts (the AppImage's usr/share/mhgu-de-installer/fonts)");
        return;
    };
    let mut files = FILES;
    if lang == "zh_TW" {
        files.swap(2, 3);
    }
    let own = std::env::var_os("SLINT_FONT_PATH").is_some() || std::env::var_os("SLINT_DEFAULT_FONT").is_some();
    // SAFETY: main calls this before the window and before any thread: nothing reads the environment meanwhile
    unsafe {
        if system == System::NoFonts {
            std::env::set_var("FONTCONFIG_FILE", dir.join("fonts.conf"));
        }
        if !own && let Ok(paths) = std::env::join_paths(files.iter().map(|f| dir.join(f))) {
            std::env::set_var("SLINT_FONT_PATH", paths);
        }
    }
    eprintln!("fonts: {why}, the bundled fonts ({})", dir.display());
}

#[cfg(test)]
mod tests {
    use skrifa::MetadataProvider;
    use std::collections::BTreeSet;
    use std::path::{Path, PathBuf};

    const GUI: &str = env!("CARGO_MANIFEST_DIR");

    /// packaging/fonts.py's chars(): a catalog's lines but its # comments, a source file whole; no control characters.
    fn chars(path: &Path) -> BTreeSet<char> {
        let text = std::fs::read_to_string(path).unwrap();
        let keep = |c: &char| *c >= ' ' && *c != '\u{feff}';
        if path.extension().is_some_and(|e| e == "po") {
            text.lines().filter(|l| !l.starts_with('#')).flat_map(str::chars).filter(keep).collect()
        } else {
            text.chars().filter(keep).collect()
        }
    }

    fn files(dir: &Path, ext: &str, out: &mut Vec<PathBuf>) {
        for e in std::fs::read_dir(dir).unwrap().flatten() {
            let p = e.path();
            if p.is_dir() {
                files(&p, ext, out);
            } else if p.extension().is_some_and(|e| e == ext) {
                out.push(p);
            }
        }
    }

    /// Every character the window can show from the installer's own text (the .slint files, the gui and core
    /// sources, each catalog) is in the fonts it falls back through: run packaging/fonts.py again when this fails.
    #[test]
    fn every_character() {
        let gui = Path::new(GUI);
        let fonts: Vec<Vec<u8>> =
            super::FILES.iter().map(|f| std::fs::read(gui.join("assets/fonts").join(f)).unwrap()).collect();
        let has = |i: usize, c: char| skrifa::FontRef::new(&fonts[i]).unwrap().charmap().map(c).is_some();
        let mut src = vec![];
        files(&gui.join("ui"), "slint", &mut src);
        files(&gui.join("src"), "rs", &mut src);
        files(&gui.join("../core/src"), "rs", &mut src);
        let mut missing = vec![];
        for p in &src {
            for c in chars(p) {
                if !(0..4).any(|i| has(i, c)) {
                    missing.push(format!("{} U+{:04X} {c}", p.display(), c as u32));
                }
            }
        }
        for (code, _) in crate::i18n::LANGS.iter().skip(1) {
            // Inter, Noto Sans Symbols, and the language's own Chinese font
            let own: &[usize] = match *code {
                "zh_CN" => &[0, 1, 2],
                "zh_TW" => &[0, 1, 3],
                _ => &[0, 1],
            };
            for c in chars(&gui.join("lang").join(code).join("LC_MESSAGES/mhgu-de-installer.po")) {
                if !own.iter().any(|&i| has(i, c)) {
                    missing.push(format!("{code} U+{:04X} {c}", c as u32));
                }
            }
        }
        assert!(missing.is_empty(), "no bundled font has (packaging/fonts.py):\n{}", missing.join("\n"));
    }
}
