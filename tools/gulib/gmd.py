"""gmd.py : GMD text strings (vendored from MHGU_Editor scratch/py, GPL-3.0-or-later)"""
import struct
def gmd_strings(d):
    assert d[:4] == b'GMD\0'
    lc, _, sc, _, ss, nl = struct.unpack('<6I', d[0x10:0x28])
    body = d[len(d) - ss:]
    return [x.decode('utf-8', 'replace') for x in body.split(b'\0')[:sc]]
