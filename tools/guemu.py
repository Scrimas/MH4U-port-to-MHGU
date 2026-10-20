"""guemu.py : run one of MHGU's resource loaders (vtable slot "load(stream)") on a real file under unicorn and
log where every byte of the file lands in the object.  Run with /home/scrimas/Projects/MHGU_Editor/scratch/venv.

  guemu.py LOADER VTABLE FILE [OBJSIZE]      -> prints "file_off obj_off size" per read, plus heap blocks

Image: MHGU 1.4 main (mem.bin, flat) mapped at 0, so unrelocated pointers (R_ARM_RELATIVE addends in place) are
already valid. Stubs: stream init 0x8260d4 (no-op), stream read 0x82710c(ctx, dst, n) (copies the next n file
bytes and logs them). Any other call into a function listed in ALLOC is served from a bump heap.
"""
import struct, sys
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UcError
from unicorn.arm_const import *

MEM = open('/home/scrimas/Projects/MHGU_Editor/scratch/mem.bin', 'rb').read()
IMG_END = 0x2147000
STREAM_INIT, STREAM_READ = 0x8260D4, 0x82710C
OBJ, HEAP, STACK, CTX = 0x30000000, 0x34000000, 0x3F000000, 0x3E000000
RET = 0x3D000000          # return address sentinel
FAKE_HEAP, HEAP_ALLOC = 0x3D000100, 0x3D000800   # object returned by the heap getter; its vtable -> HEAP_ALLOC
HEAP_GETTER = 0x7AA47C    # returns a heap object; loaders then call heap->vt[0x1c/4](heap, size, align)
ALLOC = {}                # filled from the command line: addr -> name (functions treated as malloc(size))
import json, os
PLT = {int(k, 16): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                             '..', 'dump', 'gu_plt.json'))).items()}


def run(loader, vtable, data, objsize=0x10000, alloc=(), skip=(), trace_calls=False):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0, IMG_END)
    uc.mem_write(0, MEM[:IMG_END].ljust(IMG_END, b'\0'))
    for base, size in ((OBJ, 0x1000000), (HEAP, 0x4000000), (STACK - 0x100000, 0x100000), (CTX, 0x100000), (RET, 0x1000)):
        uc.mem_map(base, size)
    uc.mem_write(OBJ, struct.pack('<I', vtable))
    uc.mem_write(FAKE_HEAP, struct.pack('<I', FAKE_HEAP + 0x10) + bytes(12) + struct.pack('<32I', *[HEAP_ALLOC] * 32))
    state = dict(pos=0, heap=HEAP, log=[], blocks=[], calls=[])

    def ret(r0):
        uc.reg_write(UC_ARM_REG_R0, r0)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def on_code(uc, addr, size, _):
        if addr == STREAM_INIT:
            ret(uc.reg_read(UC_ARM_REG_R0))
        elif addr == STREAM_READ:
            dst, n = uc.reg_read(UC_ARM_REG_R1), uc.reg_read(UC_ARM_REG_R2)
            chunk = data[state['pos']:state['pos'] + n]
            uc.mem_write(dst, chunk.ljust(n, b'\0'))
            state['log'].append((state['pos'], dst, n))
            state['pos'] += n
            ret(n)
        elif addr in PLT:                       # SDK imports: the few libc ones the loaders use
            name = PLT[addr]
            r0, r1, r2 = (uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            if name in ('memcpy', 'memmove') or name.startswith(('__aeabi_memcpy', '__aeabi_memmove')):
                uc.mem_write(r0, bytes(uc.mem_read(r1, r2)))
            elif name.startswith('__aeabi_memset'):          # (dest, n, c)
                uc.mem_write(r0, bytes([r2 & 0xFF]) * r1)
            elif name == 'memset':                           # (dest, c, n)
                uc.mem_write(r0, bytes([r1 & 0xFF]) * r2)
            elif name == 'strlen':
                b = bytes(uc.mem_read(r0, 4096)); r0 = b.index(0)
            else:
                state['calls'].append(('import', name, uc.reg_read(UC_ARM_REG_LR)))
            ret(r0)
        elif addr == HEAP_GETTER:
            ret(FAKE_HEAP)
        elif addr == HEAP_ALLOC:                # heap->alloc(size = r1, align = r2)
            n = uc.reg_read(UC_ARM_REG_R1)
            p = (state['heap'] + 15) & ~15
            state['heap'] = p + max(n, 16) + 64
            state['blocks'].append((p, n))
            ret(p)
        elif addr in skip:
            state['calls'].append(('skip', addr, uc.reg_read(UC_ARM_REG_LR)))
            ret(uc.reg_read(UC_ARM_REG_R0))
        elif addr in alloc:
            n = uc.reg_read(UC_ARM_REG_R0)          # operator new(size), e.g. 0x7af3a0
            p = (state['heap'] + 15) & ~15
            state['heap'] = p + max(n, 16) + 64
            state['blocks'].append((p, n))
            ret(p)
        elif trace_calls and addr < IMG_END and uc.reg_read(UC_ARM_REG_LR) != addr + 4:
            pass

    uc.hook_add(UC_HOOK_CODE, on_code)
    uc.reg_write(UC_ARM_REG_SP, STACK - 0x1000)
    uc.reg_write(UC_ARM_REG_R0, OBJ)
    uc.reg_write(UC_ARM_REG_R1, CTX)
    uc.reg_write(UC_ARM_REG_LR, RET)
    err = None
    try:
        uc.emu_start(loader, RET, count=20_000_000)
    except UcError as e:
        err = '%s at pc=%#x lr=%#x' % (e, uc.reg_read(UC_ARM_REG_PC), uc.reg_read(UC_ARM_REG_LR))
    obj = bytes(uc.mem_read(OBJ, objsize))
    return state, err, obj, uc


WRITE_INIT, STREAM_WRITE = 0x82772C, 0x827CD0


def load_modify_write(loader, writer, vtable, data, modify, alloc=(), skip=()):
    """run the loader on `data`, call modify(uc, state) to edit the object in place (it may call
    state['alloc'](n) for new blocks), then run the writer (vtable slot 12) and return the bytes it writes."""
    state, err, obj, uc = run(loader, vtable, data, alloc=alloc, skip=skip)
    if state['pos'] != len(data):
        raise RuntimeError('loader stopped at %d/%d: %s' % (state['pos'], len(data), err))

    def new_block(n):
        p = (state['heap'] + 15) & ~15
        state['heap'] = p + max(n, 16) + 64
        state['blocks'].append((p, n))
        return p
    state['alloc'] = new_block
    modify(uc, state)
    out = bytearray()
    # write stream context {vtable, ?, buffer, pos, capacity}: the real write function 0x827cd0 and the writers'
    # inlined byte stores both append to buffer[pos]; the vtable's flush slot (0x38) is trapped.
    OUTBUF, FLUSH, WVT = 0x38000000, 0x3D000900, 0x3D000A00
    uc.mem_map(OUTBUF, 0x1000000)
    uc.mem_write(WVT, struct.pack('<64I', *[FLUSH] * 64))
    ctx_box = []

    def on_code(uc_, addr, size, _):
        if addr == WRITE_INIT:
            ctx = uc_.reg_read(UC_ARM_REG_R0)
            ctx_box.append(ctx)
            uc_.mem_write(ctx, struct.pack('<5I', WVT, 0, OUTBUF, 0, 0x800000))
            uc_.reg_write(UC_ARM_REG_PC, uc_.reg_read(UC_ARM_REG_LR))
        elif addr == FLUSH:
            ctx = uc_.reg_read(UC_ARM_REG_R0)
            pos = struct.unpack('<I', bytes(uc_.mem_read(ctx + 12, 4)))[0]
            out.extend(bytes(uc_.mem_read(OUTBUF, pos)))
            uc_.mem_write(ctx + 12, b'\0\0\0\0')
            uc_.reg_write(UC_ARM_REG_PC, uc_.reg_read(UC_ARM_REG_LR))
    h = uc.hook_add(UC_HOOK_CODE, on_code)
    uc.reg_write(UC_ARM_REG_SP, STACK - 0x1000)
    uc.reg_write(UC_ARM_REG_R0, OBJ)
    uc.reg_write(UC_ARM_REG_R1, CTX)
    uc.reg_write(UC_ARM_REG_LR, RET)
    werr = None
    try:
        uc.emu_start(writer, RET, count=20_000_000)
    except UcError as e:
        werr = '%s at pc=%#x lr=%#x' % (e, uc.reg_read(UC_ARM_REG_PC), uc.reg_read(UC_ARM_REG_LR))
    uc.hook_del(h)
    if ctx_box:
        pos = struct.unpack('<I', bytes(uc.mem_read(ctx_box[0] + 12, 4)))[0]
        out.extend(bytes(uc.mem_read(OUTBUF, pos)))
    return bytes(out), werr


def where(addr, blocks):
    if OBJ <= addr < OBJ + 0x1000000:
        return 'obj+%#x' % (addr - OBJ)
    for i, (p, n) in enumerate(blocks):
        if p <= addr < p + max(n, 16) + 64:
            return 'heap%d+%#x' % (i, addr - p)
    return '%#x' % addr


if __name__ == '__main__':
    loader, vtable = int(sys.argv[1], 16), int(sys.argv[2], 16)
    data = open(sys.argv[3], 'rb').read()
    alloc = {int(a[2:], 16) for a in sys.argv[4:] if a.startswith('a:')}     # a:ADDR  malloc-like
    skip = {int(a[2:], 16) for a in sys.argv[4:] if a.startswith('s:')}      # s:ADDR  no-op
    state, err, obj, uc = run(loader, vtable, data, alloc=alloc, skip=skip)
    print('read %d of %d bytes; heap blocks %d; error: %s' % (state['pos'], len(data), len(state['blocks']), err))
    for fo, dst, n in state['log']:
        print('%5x %-14s %d' % (fo, where(dst, state['blocks']), n))
