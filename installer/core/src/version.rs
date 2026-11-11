//! Versions of releases and packages: "1.10.0", "v1.10.0-pre.2", "installer-v1.0.0". A pre-release comes before its
//! release, pre.1 before pre.2.

use std::cmp::Ordering;
use std::fmt;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Version {
    pub major: u32,
    pub minor: u32,
    pub patch: u32,
    /// Some(n): a pre-release (`-pre.n`; any other suffix counts by its last number, else 0)
    pub pre: Option<u32>,
}

impl Version {
    pub fn parse(s: &str) -> Option<Version> {
        let s = s.trim();
        let s = s.strip_prefix("installer-").unwrap_or(s);
        let s = s.strip_prefix('v').unwrap_or(s);
        let s = s.split_once('+').map_or(s, |(a, _)| a);
        let (core, pre) = match s.split_once('-') {
            Some((c, p)) => {
                let digits: String = p.chars().rev().take_while(|c| c.is_ascii_digit()).collect();
                let n = digits.chars().rev().collect::<String>().parse().unwrap_or(0);
                (c, Some(n))
            }
            None => (s, None),
        };
        let n: Vec<u32> = core.split('.').map(|x| x.parse().ok()).collect::<Option<_>>()?;
        let (major, minor, patch) = match n[..] {
            [a] => (a, 0, 0),
            [a, b] => (a, b, 0),
            [a, b, c] => (a, b, c),
            _ => return None,
        };
        Some(Version { major, minor, patch, pre })
    }

    pub fn is_pre(&self) -> bool {
        self.pre.is_some()
    }
}

impl Ord for Version {
    fn cmp(&self, o: &Self) -> Ordering {
        (self.major, self.minor, self.patch).cmp(&(o.major, o.minor, o.patch)).then(match (self.pre, o.pre) {
            (None, None) => Ordering::Equal,
            (None, Some(_)) => Ordering::Greater,
            (Some(_), None) => Ordering::Less,
            (Some(a), Some(b)) => a.cmp(&b),
        })
    }
}

impl PartialOrd for Version {
    fn partial_cmp(&self, o: &Self) -> Option<Ordering> {
        Some(self.cmp(o))
    }
}

impl fmt::Display for Version {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}.{}.{}", self.major, self.minor, self.patch)?;
        match self.pre {
            Some(n) => write!(f, "-pre.{n}"),
            None => Ok(()),
        }
    }
}

/// a < b by version; an unreadable version is older than any readable one.
pub fn older(a: &str, b: &str) -> bool {
    Version::parse(a) < Version::parse(b)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(s: &str) -> Version {
        Version::parse(s).unwrap()
    }

    #[test]
    fn versions_compare_by_number_and_pre_release() {
        assert!(v("v1.10.0") > v("1.9.0"));
        assert!(v("1.10.0-pre.1") < v("1.10.0"));
        assert!(v("1.10.0-pre.2") > v("1.10.0-pre.1"));
        assert!(v("1.10.0-pre.1") > v("1.9.9"));
        assert_eq!(v("installer-v1.0.0"), v("1.0.0"));
        assert_eq!(v("1.0"), v("1.0.0"));
        assert_eq!(v("1.2.3+build"), v("1.2.3"));
        assert_eq!(Version::parse("latest"), None);
        assert!(older("garbage", "0.0.1"));
        assert_eq!(v("1.10.0-pre.3").to_string(), "1.10.0-pre.3");
    }
}
