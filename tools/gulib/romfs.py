"""romfs.py : read the MHGU RomFS, either the folder Ryujinx extracts (right-click the game > Extract Data > RomFS: the
v1.4 files when the update is installed) or a RomFS image. Vendored from MHGU_Editor (scratch/py/romfs.py,
GPL-3.0-or-later); folder support added.

  r = RomFS(path)      r.files = {'/nativeNX/...': (image offset or None, size)}, r.read('/nativeNX/...') -> bytes
                       (a missing file raises KeyError in both forms)
  romfs.py PATH REGEX OUTDIR      extract every file whose path matches REGEX (paths kept)
"""
import os, re, struct, sys


class RomFS:
    def __init__(s, path):
        s.files = {}
        if os.path.isdir(path):
            if not os.path.isdir(os.path.join(path, 'nativeNX')):      # the extraction may sit one folder down
                sub = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d, 'nativeNX'))]
                if len(sub) == 1: path = os.path.join(path, sub[0])
            s.dir = path
            for d, _, fs in os.walk(path):
                rel = os.path.relpath(d, path).replace(os.sep, '/')
                pre = '' if rel == '.' else '/' + rel
                for fn in fs:
                    s.files[pre + '/' + fn] = (None, os.path.getsize(os.path.join(d, fn)))
            return
        s.dir = None
        s.f = open(path, 'rb')
        h = struct.unpack('<10Q', s._rd(0, 80))
        s.dm = s._rd(h[3], h[4]); s.fm = s._rd(h[7], h[8]); s.data = h[9]
        s._walk(0, '')

    def _rd(s, o, n):
        s.f.seek(o); return s.f.read(n)

    def _walk(s, doff, path):
        _, _, child, fil, _, nl = struct.unpack_from('<6I', s.dm, doff)
        p = path + '/' + s.dm[doff + 24:doff + 24 + nl].decode() if doff else ''
        f = fil
        while f != 0xFFFFFFFF:
            _, fs, off, sz, _, nl2 = struct.unpack_from('<IIQQII', s.fm, f)
            s.files[p + '/' + s.fm[f + 32:f + 32 + nl2].decode()] = (s.data + off, sz)
            f = fs
        c = child
        while c != 0xFFFFFFFF:
            s._walk(c, p)
            c = struct.unpack_from('<I', s.dm, c + 4)[0]

    def read(s, name):
        off, sz = s.files[name]
        if s.dir:
            with open(s.dir + name, 'rb') as f: return f.read()
        return s._rd(off, sz)


if __name__ == '__main__':
    r = RomFS(sys.argv[1]); pat = re.compile(sys.argv[2]); out = sys.argv[3]
    n = 0
    for k in r.files:
        if pat.search(k):
            dst = out + k; os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(r.read(k)); n += 1
    print(n, 'files')
