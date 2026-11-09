//! The release zips (tools/release.py write_zip: deflate, sorted, no zip64, no encryption): the central directory and
//! one entry's bytes. The sizes and sha256 of every file are checked against the manifest by the caller.

use crate::i18n::trf;

pub struct Entry {
    pub name: String,
    method: u16,
    comp_size: u64,
    pub size: u64,
    header: u64,
}

fn u16_at(b: &[u8], o: usize) -> Option<u16> {
    Some(u16::from_le_bytes(b.get(o..o + 2)?.try_into().ok()?))
}

fn u32_at(b: &[u8], o: usize) -> Option<u32> {
    Some(u32::from_le_bytes(b.get(o..o + 4)?.try_into().ok()?))
}

fn bad(what: &str) -> String {
    trf("Damaged zip file ({})", &[&what])
}

/// The entries of a zip held in memory, in central-directory order.
pub fn entries(z: &[u8]) -> Result<Vec<Entry>, String> {
    let lo = z.len().saturating_sub(22 + 65535);
    let eocd = (lo..z.len().saturating_sub(21))
        .rev()
        .find(|&i| u32_at(z, i) == Some(0x0605_4b50))
        .ok_or_else(|| bad("no end record"))?;
    let n = u16_at(z, eocd + 10).ok_or_else(|| bad("end record"))? as usize;
    let mut at = u32_at(z, eocd + 16).ok_or_else(|| bad("end record"))? as usize;
    let mut out = Vec::with_capacity(n);
    for _ in 0..n {
        if u32_at(z, at) != Some(0x0201_4b50) {
            return Err(bad("directory"));
        }
        let field = |o: usize| u32_at(z, at + o).ok_or_else(|| bad("directory"));
        let flags = u16_at(z, at + 8).ok_or_else(|| bad("directory"))?;
        let method = u16_at(z, at + 10).ok_or_else(|| bad("directory"))?;
        let (comp_size, size, header) = (field(20)?, field(24)?, field(42)?);
        let nl = u16_at(z, at + 28).ok_or_else(|| bad("directory"))? as usize;
        let el = u16_at(z, at + 30).ok_or_else(|| bad("directory"))? as usize;
        let cl = u16_at(z, at + 32).ok_or_else(|| bad("directory"))? as usize;
        let name = z.get(at + 46..at + 46 + nl).ok_or_else(|| bad("name"))?;
        if flags & 1 != 0 || comp_size == u32::MAX || size == u32::MAX || header == u32::MAX {
            return Err(bad("encrypted or zip64 entry"));
        }
        if method != 0 && method != 8 {
            return Err(bad("compression method"));
        }
        let name = String::from_utf8(name.to_vec()).map_err(|_| bad("name"))?;
        out.push(Entry { name, method, comp_size: comp_size as u64, size: size as u64, header: header as u64 });
        at += 46 + nl + el + cl;
    }
    Ok(out)
}

/// The bytes of one entry.
pub fn read(z: &[u8], e: &Entry) -> Result<Vec<u8>, String> {
    let h = e.header as usize;
    if u32_at(z, h) != Some(0x0403_4b50) {
        return Err(bad("local header"));
    }
    let nl = u16_at(z, h + 26).ok_or_else(|| bad("local header"))? as usize;
    let el = u16_at(z, h + 28).ok_or_else(|| bad("local header"))? as usize;
    let start = h + 30 + nl + el;
    let raw = z.get(start..start + e.comp_size as usize).ok_or_else(|| bad("entry data"))?;
    let data = match e.method {
        0 => raw.to_vec(),
        _ => miniz_oxide::inflate::decompress_to_vec_with_limit(raw, e.size as usize).map_err(|_| bad(&e.name))?,
    };
    if data.len() as u64 != e.size {
        return Err(bad(&e.name));
    }
    Ok(data)
}

/// A zip of `files` (deflate), for the tests' fake releases.
#[cfg(test)]
pub fn write(files: &[(&str, &[u8])]) -> Vec<u8> {
    fn crc32(d: &[u8]) -> u32 {
        let mut c = !0u32;
        for &b in d {
            c ^= b as u32;
            for _ in 0..8 {
                c = if c & 1 != 0 { 0xEDB8_8320 ^ (c >> 1) } else { c >> 1 };
            }
        }
        !c
    }
    let (mut out, mut dir) = (vec![], vec![]);
    for (name, data) in files {
        let comp = miniz_oxide::deflate::compress_to_vec(data, 6);
        let (off, crc) = (out.len() as u32, crc32(data));
        let hdr = |sig: u32, central: bool| {
            let mut h = sig.to_le_bytes().to_vec();
            if central {
                h.extend(20u16.to_le_bytes());
            }
            h.extend(20u16.to_le_bytes());
            h.extend(0u16.to_le_bytes());
            h.extend(8u16.to_le_bytes());
            h.extend(0u32.to_le_bytes());
            h.extend(crc.to_le_bytes());
            h.extend((comp.len() as u32).to_le_bytes());
            h.extend((data.len() as u32).to_le_bytes());
            h.extend((name.len() as u16).to_le_bytes());
            h.extend(0u16.to_le_bytes());
            if central {
                h.extend([0u8; 6]); // comment length, disk, internal attributes
                h.extend(0u32.to_le_bytes()); // external attributes
                h.extend(off.to_le_bytes());
            }
            h.extend(name.as_bytes());
            h
        };
        let local = hdr(0x0403_4b50, false);
        dir.extend(hdr(0x0201_4b50, true));
        out.extend(local);
        out.extend(&comp);
    }
    let cd = out.len() as u32;
    out.extend(&dir);
    out.extend(0x0605_4b50u32.to_le_bytes());
    out.extend([0u8; 4]);
    out.extend((files.len() as u16).to_le_bytes());
    out.extend((files.len() as u16).to_le_bytes());
    out.extend((dir.len() as u32).to_le_bytes());
    out.extend(cd.to_le_bytes());
    out.extend(0u16.to_le_bytes());
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_written_zip_reads_back() {
        let big = vec![7u8; 100_000];
        let z = write(&[
            ("MHGU Definitive Edition/exefs/subsdk1", b"module"),
            ("MHGU Definitive Edition/romfs/a.arc", &big),
        ]);
        let e = entries(&z).unwrap();
        assert_eq!(
            e.iter().map(|e| e.name.as_str()).collect::<Vec<_>>(),
            ["MHGU Definitive Edition/exefs/subsdk1", "MHGU Definitive Edition/romfs/a.arc"]
        );
        assert_eq!(read(&z, &e[0]).unwrap(), b"module");
        assert_eq!(read(&z, &e[1]).unwrap(), big);
        assert!(entries(&z[..z.len() - 5]).is_err());
    }
}
