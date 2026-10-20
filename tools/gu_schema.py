"""gu_schema.py : field maps of MHGU's enemy data files, from emulating the game's own loaders (tools/guemu.py).
Run with the MHGU_Editor scratch venv (unicorn).

  gu_schema.py FILE KIND        print "file_off size dest" with dest = obj+X or <pointer path>[i]+X

Kinds and their loader (vtable slot 11) / vtable / vfunc to skip (slot 15, reset):
"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guemu

KINDS = {   # kind: (loader, vtable, reset vfunc)
    'bodydata':   (0x50EF4, 0x1732D3C, 0x50EAC),
    'dtbase':     (0x538BC, 0x1732FEC, 0x53EA0),
    'dtbparts':   (0x5575C, 0x1733048, 0x56180),
    'dttune':     (0x57740, 0x17330A4, 0x564BC),
    'attackdata': (0x5954C, 0x17331BC, 0x59504),
    'partsvis':   (0x599A8, 0x1733218, 0x59A88),
    'hitsize':    (0x16A0A8, 0x173EBB8, 0x16A400),
}
ALLOC = {0x7AF3A0, 0x7AF37C}       # operator new(size) variants used by the streamed loaders


def schema(data, kind):
    loader, vtable, reset = KINDS[kind]
    state, err, obj, uc = guemu.run(loader, vtable, data, alloc=ALLOC, skip={reset})
    blocks = state['blocks']
    # which pointer field holds each heap block (object first, then other blocks)
    owner = {}
    mem = {('obj', 0): bytes(uc.mem_read(guemu.OBJ, 0x10000))}
    for i, (p, n) in enumerate(blocks):
        mem[('heap', i)] = bytes(uc.mem_read(p, max(n, 4)))
    for i, (p, n) in enumerate(blocks):
        for key, b in mem.items():
            for o in range(0, len(b) - 3, 4):
                if struct.unpack_from('<I', b, o)[0] == p and key != ('heap', i):
                    owner[i] = (key, o)
    def path(addr):
        if guemu.OBJ <= addr < guemu.OBJ + 0x1000000:
            return ('obj', addr - guemu.OBJ)
        for i, (p, n) in enumerate(blocks):
            if p <= addr < p + max(n, 16) + 64:
                return ('heap%d' % i, addr - p)
        return ('?', addr)
    fields = [(fo, n, path(dst)) for fo, dst, n in state['log']]
    return dict(fields=fields, blocks=blocks, owner=owner, read=state['pos'], size=len(data), error=err, mem=mem)


def describe(s):
    out = []
    for i, (p, n) in enumerate(s['blocks']):
        own = s['owner'].get(i)
        out.append('heap%d: %d bytes, pointer at %s' % (i, n, '%s%s+%#x' % (own[0][0], '' if own[0][0] == 'obj' else own[0][1], own[1]) if own else '?'))
    return out


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    s = schema(data, sys.argv[2])
    print('read %d / %d bytes, error after read: %s' % (s['read'], s['size'], s['error']))
    for line in describe(s): print(' ', line)
    for fo, n, (reg, off) in s['fields']:
        print('%5x %2d %s+%#x' % (fo, n, reg, off))
