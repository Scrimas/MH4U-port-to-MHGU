//! The AppImage's own fallback fonts (usr/share/mhgu-de-installer/fonts: packaging/fonts.py cuts them to the
//! installer's characters at each build, packaging/build.py puts them there). On Linux, Slint finds its fonts through
//! fontconfig, loaded at start (gui/Cargo.toml): without fontconfig the window would show no text, and with a fontconfig
//! that has no font it would not open (fontique 0.11 unwraps fontconfig's empty match). There, the window takes the
//! bundled ones.

/// The fonts (packaging/fonts.py NAMES), in the order Slint falls back through them (the Chinese one of the window's
/// language first).
#[cfg(target_os = "linux")]
const FILES: [&str; 4] = ["Inter.ttf", "NotoSansSymbols.ttf", "NotoSansSC.ttf", "NotoSansTC.ttf"];

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
/// SLINT_FONT_PATH (unless the person set their own fonts), and through FONTCONFIG_FILE (packaging/fonts.conf, beside
/// them) when fontconfig has none. `lang`: the window's language at start (LANGS' code).
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
