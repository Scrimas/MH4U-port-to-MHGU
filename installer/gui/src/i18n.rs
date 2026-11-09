//! Interface languages, MHGU_Editor's set. The .slint files' @tr() strings and the Rust side's tr() (core and gui)
//! share one gettext catalog per language, gui/lang/<code>/LC_MESSAGES/mhgu-de-installer.po (installer/tools/i18n.py
//! keeps them in step): Slint bundles them at build time, the Rust side parses them here. English is the source text;
//! an entry left untranslated shows in English.

use std::collections::HashMap;
use std::sync::RwLock;

/// The lang/ folder (gettext locale) and the language's own name, English first.
pub const LANGS: [(&str, &str); 7] = [
    ("en", "English"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("it", "Italiano"),
    ("zh_TW", "繁體中文"),
    ("zh_CN", "简体中文"),
];

macro_rules! po {
    ($c:literal) => {
        include_str!(concat!("../lang/", $c, "/LC_MESSAGES/mhgu-de-installer.po"))
    };
}

/// The catalogs in LANGS order (English has none).
const PO: [&str; 7] = ["", po!("fr"), po!("de"), po!("es"), po!("it"), po!("zh_TW"), po!("zh_CN")];

static CATALOG: RwLock<Option<HashMap<String, String>>> = RwLock::new(None);

fn unquote(s: &str) -> Option<String> {
    let s = s.trim().strip_prefix('"')?.strip_suffix('"')?;
    let mut out = String::with_capacity(s.len());
    let mut it = s.chars();
    while let Some(c) = it.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        match it.next() {
            Some('n') => out.push('\n'),
            Some('t') => out.push('\t'),
            Some(o) => out.push(o),
            None => {}
        }
    }
    Some(out)
}

/// msgid -> msgstr of a catalog (singular entries; a plural entry's first form), translated entries only.
fn parse(po: &str) -> HashMap<String, String> {
    let mut map = HashMap::new();
    let (mut id, mut msg, mut field) = (String::new(), String::new(), 0);
    let mut flush = |id: &mut String, msg: &mut String| {
        if !id.is_empty() && !msg.is_empty() {
            map.insert(std::mem::take(id), std::mem::take(msg));
        }
        id.clear();
        msg.clear();
    };
    for line in po.lines().map(str::trim) {
        if let Some(r) = line.strip_prefix("msgid ") {
            flush(&mut id, &mut msg);
            id = unquote(r).unwrap_or_default();
            field = 1;
        } else if line.starts_with("msgid_plural ") {
            field = 0;
        } else if let Some(r) = line.strip_prefix("msgstr[0] ").or_else(|| line.strip_prefix("msgstr ")) {
            msg = unquote(r).unwrap_or_default();
            field = 2;
        } else if line.starts_with("msgstr[") {
            field = 0;
        } else if line.starts_with('"') {
            let more = unquote(line).unwrap_or_default();
            match field {
                1 => id.push_str(&more),
                2 => msg.push_str(&more),
                _ => {}
            }
        }
    }
    flush(&mut id, &mut msg);
    map
}

fn lookup(s: &str) -> Option<String> {
    CATALOG.read().ok()?.as_ref()?.get(s).cloned()
}

/// The system's language among LANGS (Chinese by script: Traditional for Hant, Taiwan, Hong Kong, Macao).
pub fn system() -> usize {
    let Some(loc) = sys_locale::get_locale() else { return 0 };
    let mut code = loc.replace('-', "_");
    if code.starts_with("zh") {
        let hant = ["Hant", "TW", "HK", "MO"].iter().any(|t| code.split(['_', '.', '@']).any(|p| p == *t));
        code = if hant { "zh_TW" } else { "zh_CN" }.into();
    }
    let short = code.split(['_', '.', '@']).next().unwrap_or_default().to_string();
    LANGS.iter().position(|(c, _)| *c == code || *c == short).unwrap_or(0)
}

/// Use language `i` of LANGS for both the window and the Rust strings.
pub fn set(i: usize) {
    mhgu_de_core::i18n::set_lookup(lookup);
    let i = i.min(LANGS.len() - 1);
    if let Ok(mut c) = CATALOG.write() {
        *c = Some(parse(PO[i]));
    }
    let _ = slint::select_bundled_translation(LANGS[i].0);
}

/// The index of a settings language code ("" = the system's).
pub fn index_of(code: &str) -> usize {
    if code.is_empty() { system() } else { LANGS.iter().position(|(c, _)| *c == code).unwrap_or(0) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catalog_entries_parse() {
        let po = "msgid \"\"\nmsgstr \"\"\n\"Plural-Forms: x\\n\"\n\nmsgid \"Install\"\nmsgstr \"Installer\"\n\nmsgid \"\"\n\"two \"\n\"lines\"\nmsgstr \"deux \\\"lignes\\\"\"\n\nmsgid \"Untranslated\"\nmsgstr \"\"\n";
        let m = parse(po);
        assert_eq!(m.get("Install").map(String::as_str), Some("Installer"));
        assert_eq!(m.get("two lines").map(String::as_str), Some("deux \"lignes\""));
        assert!(!m.contains_key("Untranslated") && !m.contains_key(""));
        for (i, p) in PO.iter().enumerate() {
            let _ = parse(p);
            assert!(i == 0 || p.contains("Plural-Forms"), "{} has its header", LANGS[i].0);
        }
    }
}
