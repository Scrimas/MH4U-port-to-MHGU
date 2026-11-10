//! Translations of the messages made here: the window sets the lookup (gui/src/i18n.rs reads its gettext catalogs);
//! without one (the command line, tests) the English text is used. installer/tools/i18n.py extracts every
//! `tr("...")` / `trf("...", ...)` of core/src and gui/src.

use std::fmt::Display;
use std::sync::{OnceLock, RwLock};

static LOOKUP: OnceLock<fn(&str) -> Option<String>> = OnceLock::new();
static LANG: RwLock<String> = RwLock::new(String::new());

/// Set once by the window, before any message is made.
pub fn set_lookup(f: fn(&str) -> Option<String>) {
    let _ = LOOKUP.set(f);
}

/// The window's language (a gui/src/i18n.rs LANGS code), for the names the manifest carries per language.
pub fn set_lang(code: &str) {
    if let Ok(mut l) = LANG.write() {
        *l = code.to_string();
    }
}

/// The window's language code, "en" until the window sets one (the command line, tests).
pub fn lang() -> String {
    LANG.read().ok().filter(|l| !l.is_empty()).map_or_else(|| "en".to_string(), |l| l.clone())
}

/// The translation of `s`, else `s`.
pub fn tr(s: &str) -> String {
    LOOKUP.get().and_then(|f| f(s)).unwrap_or_else(|| s.to_string())
}

/// `tr(s)` with its placeholders filled: `{}` in order, `{0}` `{1}` by position.
pub fn trf(s: &str, args: &[&dyn Display]) -> String {
    fill(&tr(s), args)
}

/// `trf` of `one` when n is 1, else of `many` (both extracted as their own entries: English-style plurals until a
/// catalog needs more forms); `{}` in either is n.
pub fn trn(one: &str, many: &str, n: usize) -> String {
    trf(if n == 1 { one } else { many }, &[&n])
}

pub fn fill(t: &str, args: &[&dyn Display]) -> String {
    let mut out = String::with_capacity(t.len() + 16);
    let (mut next, mut rest) = (0, t);
    while let Some(i) = rest.find('{') {
        out.push_str(&rest[..i]);
        let after = &rest[i + 1..];
        match after.find('}') {
            Some(j) if after[..j].chars().all(|c| c.is_ascii_digit()) => {
                let k = if j == 0 {
                    next += 1;
                    next - 1
                } else {
                    after[..j].parse().unwrap_or(usize::MAX)
                };
                match args.get(k) {
                    Some(a) => out.push_str(&a.to_string()),
                    None => out.push_str(&rest[i..i + j + 2]),
                }
                rest = &after[j + 1..];
            }
            _ => {
                out.push('{');
                rest = after;
            }
        }
    }
    out.push_str(rest);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn placeholders_fill_in_order_and_by_position() {
        assert_eq!(fill("{} of {}", &[&1, &3]), "1 of 3");
        assert_eq!(fill("{1} before {0}", &[&"a", &"b"]), "b before a");
        assert_eq!(fill("{x} {", &[&1]), "{x} {");
        assert_eq!(fill("{} {}", &[&1]), "1 {}");
    }
}
