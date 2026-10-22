"""extdata4u.py : MH4U event (DLC) quests from a 4U extdata backup (the user's Checkpoint dump, gitignored under
dump/extdata_4u/: files quest1..quest5, ~40 quests each, the ROM quests' 'v005' format read by tools/quest4u.py).

  extdata4u.py list [DIR]        every quest: file, number, star, stage, bosses, English title
  extdata4u.py show NUM [DIR]    one quest's header bytes

Library: quest(num, dir=EXTDATA) -> the 4U quest bytes (from its 'v005' start), quests(dir) -> [(file, num, bytes)].

Cipher (C on the user's files: every checksum holds; scheme of the 4U save files, documented in svanheulen's mhef,
SavedataCipher MH4G_SD_QUEST): drop the last 0x100 bytes, Blowfish-ECB over byte-swapped u32 words, the first u32 >>
16 seeds an XOR stream over the u16 words after it (k = k * 0xb0 % 0xff53, k 0 -> 1), whose first u32 is the byte
sum of the rest. The Blowfish key is the game's own NUL-terminated string in the 4U v1.1 exe (KEY_4U, read from
dump/exefs_v11/mem.bin): never copied into the repo or printed.
"""
import glob, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from items4u import EXE, EXE_BASE          # noqa: E402
import quest4u                             # noqa: E402

EXTDATA = os.path.join(os.path.dirname(HERE), 'dump', 'extdata_4u')
KEY_4U = 0xe05e04                          # savedata / extdata Blowfish key (56 B + NUL) in the 4U v1.1 exe
_DEC = {}


def _key():
    d = open(EXE, 'rb').read()
    return d[KEY_4U - EXE_BASE:d.index(b'\0', KEY_4U - EXE_BASE)]


def _swap32(b):
    return b''.join(b[i:i + 4][::-1] for i in range(0, len(b), 4))


def decrypt(buf):
    """an encrypted extdata quest file -> its plain body (ValueError on a bad checksum)"""
    from cryptography.hazmat.primitives.ciphers import Cipher, modes
    from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
    dec = Cipher(Blowfish(_key()), modes.ECB()).decryptor()
    buf = buf[:-0x100]
    buf = _swap32(dec.update(_swap32(buf)) + dec.finalize())
    k = struct.unpack_from('<I', buf, 0)[0] >> 16
    h = list(struct.unpack('<%dH' % ((len(buf) - 4) // 2), buf[4:]))
    for i in range(len(h)):
        k = (k or 1) * 0xb0 % 0xff53
        h[i] ^= k
    out = struct.pack('<%dH' % len(h), *h)
    csum, body = struct.unpack_from('<I', out, 0)[0], out[4:]
    if csum != sum(body) & 0xffffffff: raise ValueError('extdata checksum mismatch')
    return body


def quests(dir=EXTDATA):
    """[(file, 4U quest number, quest bytes)] of every quest1..quest5 under dir (recursive)"""
    out = []
    for f in sorted(glob.glob(os.path.join(dir, '**', 'quest[1-5]'), recursive=True)):
        if f not in _DEC: _DEC[f] = decrypt(open(f, 'rb').read())
        d, i = _DEC[f], _DEC[f].find(b'v005')
        while i >= 4:
            out.append((f, struct.unpack_from('<H', d, i - 4 + 0xC0)[0], d[i - 4:]))
            i = d.find(b'v005', i + 4)
    return out


def quest(num, dir=EXTDATA):
    """4U quest m<num> from the extdata (KeyError if absent)"""
    for f, n, q in quests(dir):
        if n == num: return q
    raise KeyError('4U quest m%05d not in %s' % (num, dir))


def bosses(q):
    """4U boss em numbers of a quest (spawn records 0x28 B from [+0x28], closed by 0xffffffff)"""
    out, rec = [], struct.unpack_from('<I', q, struct.unpack_from('<I', q, 0x28)[0])[0]
    while struct.unpack_from('<I', q, rec)[0] != 0xFFFFFFFF and len(out) < 8:
        out.append(struct.unpack_from('<I', q, rec)[0])
        rec += 0x28
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['list']:
        for f, n, q in quests(*a[1:2]):
            print('%s m%05d star %d stage %d bosses %s | %s' % (os.path.basename(f), n, q[0xC2], q[0xC4], bosses(q),
                                                              quest4u.text4u(q)['eng'][0]))
    elif a[:1] == ['show']:
        q = quest(int(a[1]), *a[2:3])
        print(q[:0x100].hex(' ', 4))
    else:
        sys.exit(__doc__)
