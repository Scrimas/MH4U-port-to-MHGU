"""emc.py : EMC (rEnemyCmd, enemy AI bytecode) reader.  Same format/version in MH4U and MHGU ("EMC\\0", 0x20120804).

Layout (from em089_cmd): header 16 bytes (magic, version, ngroups, 0), then ngroups x {u32 count, u32 offset, 0, 0}.
Each group points at `count` script entries {u32 length, u32 offset, 0, 0}; a script is a byte string (padded to 16).
Group 0 = top-level AI selectors (em089: 33), group 1 = action scripts (em089: 146), groups 2.. = small extra lists.

Bytecode (partly inferred, NOT from the interpreter): `00 cat num` starts native action (category, number) handled by
the monster class (em089: vtable slot 44 dispatch on work bytes +0x1ca/+0x1cb); `14 nn` runs action script nn of
group 1; `02 00 / 02 01 w ... / 02 ff` = weighted random choice; ops like 6f/77/78/1d/0b/0c/2e/57 are condition
blocks with sub-codes 00 (if) / 01 v (case) / 02 (else) / ff (end).

  emc.py FILE              summary + every script as hex
  emc.py FILE refs         native-action (cat,num) and script references per script (heuristic tokenizer)
"""
import struct, sys, collections


def parse(d):
    assert d[:4] == b'EMC\0', 'not EMC'
    ver, ngroups = struct.unpack_from('<II', d, 4)
    groups = []
    for g in range(ngroups):
        cnt, off = struct.unpack_from('<II', d, 0x10 + 16 * g)
        scripts = []
        for i in range(cnt):
            ln, so = struct.unpack_from('<II', d, off + 16 * i)
            scripts.append(d[so:so + ln])
        groups.append(scripts)
    return ver, groups


def to_gu(b):
    """4U EMC has 23 groups, GU 21; 4U's last two are empty. Keep every offset: rows 21-22 become padding."""
    magic, ver, ng, _ = struct.unpack_from('<4sIII', b, 0)
    assert magic == b'EMC\0' and ver == 0x20120804 and ng == 23
    for g in (21, 22):
        assert struct.unpack_from('<I', b, 16 + 16 * g)[0] == 0, 'group %d not empty' % g
    b = bytearray(b)
    struct.pack_into('<I', b, 8, 21)
    b[16 + 16 * 21:16 + 16 * 23] = bytes(32)
    return bytes(b)


def refs(code):
    """heuristic: `00 cat num` with cat < 14 at a token start, and `14 nn`."""
    nat, calls = [], []
    i = 0
    while i < len(code):
        b = code[i]
        if b == 0x00 and i + 2 < len(code) and code[i + 1] < 14:
            nat.append((code[i + 1], code[i + 2])); i += 3; continue
        if b == 0x14 and i + 1 < len(code):
            calls.append(code[i + 1]); i += 2; continue
        if b == 0x02 and i + 1 < len(code):
            i += 3 if code[i + 1] == 0x01 else 2; continue
        if i + 1 < len(code) and code[i + 1] in (0x00, 0x01):
            # generic block op: op sub arg [arg]
            i += 3; continue
        i += 2 if i + 1 < len(code) and code[i + 1] in (0x02, 0xff) else 1
    return nat, calls


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    ver, groups = parse(d)
    print('EMC version %08x, %d groups: %s' % (ver, len(groups), [len(g) for g in groups]))
    if sys.argv[2:] == ['refs']:
        allnat = collections.Counter()
        for gi, g in enumerate(groups):
            for si, s in enumerate(g):
                nat, calls = refs(s)
                allnat.update(nat)
                if nat or calls:
                    print('g%d s%-3d native %s  scripts %s' % (gi, si, ' '.join('%d:%d' % x for x in nat),
                                                               ' '.join(map(str, calls))))
        print('native actions referenced:', ' '.join('%d:%d' % k for k in sorted(allnat)))
    else:
        for gi, g in enumerate(groups):
            for si, s in enumerate(g):
                print('g%d s%-3d len %4d  %s' % (gi, si, len(s), s.hex(' ')))
