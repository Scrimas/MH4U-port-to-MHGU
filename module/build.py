"""build.py : build subsdk1 (core + every registered monster's code) + the main IPS patch.

  build.py            build into module/out/
  build.py install    also install into the Ryujinx mod folder: exefs/, every monster's data file
                      (romfs/nativeNX/mh4uport/<name>.bin, always) and the monsters' assets (romfs/...); PORT_ASSETS =
                      comma-separated monster names whose assets to install (default: all, "none" = none)

Hooks: (name, main offset of the hooked instruction). The two instructions at the site
are moved into the trampoline, so they must not be pc-relative or branches (checked).
"""
import glob, os, re, shutil, struct, subprocess, sys, tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import alloc, nso, paths

MONSTERS = alloc.monsters()        # registry order (allocations.toml): registry indexes, append order


def package(m):
    """monsters/<name>/package.toml: version, code = C prefix (<code>_register_class, g_<code>_dti), gu_class = name
    of the GU class that runs the monster instead (its donor's: a GU variant, e.g. uEm067_00 for em067_01)"""
    with open(os.path.join(paths.monster(m['name']), 'package.toml'), 'rb') as f:
        return tomllib.load(f)


def gu_class_dti(m, raw):
    """the donor's class DTI (main address) for a gu_class monster, checked against the name in package.toml"""
    want = package(m)['gu_class']
    dti = raw[m['donor_index']]
    pkl = os.path.join(paths.GU_SCRATCH, 'dti.pkl')            # MHGU_Editor: DTI address -> {(name, ...)}
    if os.path.exists(pkl):
        import pickle
        names = {n for n, _ in pickle.load(open(pkl, 'rb')).get(dti, ())}
        if want not in names: sys.exit('%s: donor %d runs %s, not gu_class %s' % (m['name'], m['donor_index'],
                                                                               names or '?', want))
    return dti


MAIN_IMG = paths.GU_MAIN   # MHGU 1.4 main, flat
MAIN_BUILD_ID = 'FB08F1D20FD1204FE7070672777F869B'
MODULE_BASE = 0x2E19000   # subsdk1 lands where sdk was (Ryujinx log: image 3)
MAIN_BASE = 0x704000      # main (image 1)
MAIN_IMAGE_END = 0x2147000  # text + ro + data + bss
# install target: the test data dir by default (tools/ryutest.sh); GOG_MOD_ROOT=~/.config/Ryujinx/mods for the real one
MOD_ROOT = os.path.expanduser(os.environ.get('GOG_MOD_ROOT', os.path.join(ROOT, 'ryuroot', 'mods')))
MOD_NAME = 'MH4U Port'
MOD_DIR = os.path.join(MOD_ROOT, 'contents', '0100770008dd8000', MOD_NAME)

HOOKS = [
    ('em_create', 0x4EBCC),    # monster factory (DTI table 0x1731e2c)
    ('quest_prep', 0x68A70),   # quest spawn prep: requests enemy\em%03d_%02d.arc for id r1
    ('em_arc_request', 0x15334C),  # (mgr, id): kind-48 arc request used by the quest loader (aQuest/sQuest)
    ('em_record', 0x69C258),   # (res, index): per-index record of the global resource [[g]+0x2590] -> enemy+0x7628
    ('file_id', 0x152960),     # (_, fileId) -> resource: serves the monsters' file IDs (port.c, data file FILE)
    ('gear_pwl', 0x272910),    # rPlayerWeaponList load exit: Gogma HBG / SA motion sets (gear.c)
    ('stats_add', 0x3A75FC),   # quest-end tally: index from 0x50b64 (obj+0x114/0x116+index*8, no bound)
    ('stats_exit', 0x3A7F00),  # the tally's exit: objectives after its loop (diagnostic)
    ('stats_hunted', 0x3A3930),  # reads the same array
    ('save_hunts', 0x523104),    # save hunts + captures by ID (bound 136): 0x59 -> its save slot 0x1064
    ('set_action', 0x76154),   # enemy setAction(this, cat, num, mode): diagnostic log of em089 action changes
    ('set_target', 0xC6E14),   # enemy setTarget(this, kind, sub, param, slot): em089 arena points -> emd stage-19 table
    ('stage_path', 0x15339C),  # stage arc path builder: stage 26 -> m28 files for the Gogmazios quest (stage.c)
    ('stage_maprec', 0x61C394),  # cUIOEnlargeMap setup: per-area map record -> 4U m19 scale / offset (stage.c)
    ('stage_wholerec', 0x61B608),  # cUIOEnlargeMap setup: whole-map record -> scale 60000 / 40000 (4U m19) (stage.c)
    ('quest_group_fix', 0x3B7DE8),  # quest list loader step: placeholder 1011009 -> quest 11491 in memory
    ('quest_unlocked', 0x3B2174),   # (_, id) -> 1 for quest 11491
    ('quest_clear_fix', 0x388D40),  # results-scene clear write: rename the freshly loaded quest list first
    ('notes_unlock_check', 0x554DA4),  # Hunter's Notes unlock condition (talk action 6 / condition 44): log entry 123
    ('utf8_null_guard', 0x7CA340),  # (out, s, n) UTF-8 helper: s = NULL -> "" (abandon crash safety net, stage.c)
    ('stage_gimmicks', 0x50249C),   # stage gimmick shell spawner (Fortress st003/004/006/007/008): log only (stage.c)
    ('dmg_sub', 0x98AF4),      # diagnostic: enemy HP -= pending damage (main.c)
    ('dmg_special', 0x98AC4),  # diagnostic: damage diverted (0x8187c true), no HP subtraction
    ('set_hp', 0x9A764),       # diagnostic: enemy setHP(this, value)
    ('add_hp', 0x9A7B8),       # diagnostic: enemy addHP(this, delta)
    ('dmg_recv', 0x9D6F8),     # diagnostic: monster damage receiver (monster, part, damage, kind)
    ('name_index', 0x55BDA4),  # (mgr, id) -> monsterName GMD entry (= 0x50b64(id)); 137 -> EM089_NAME_ENTRY
    ('bgm_select', 0x4E60D4),  # (ctl, boss entry, u8 *has, u32 *id): battle theme id -> em089's (em089_bgm.c)
    ('bgm_stqr', 0xB6D72C),    # (stqr, id) -> sequence: ids 0x900/0x901 looked up in em089's STQR (em089_bgm.c)
    ('bgm_play', 0x4E34A4),    # sSoundControl play stream request: log only in quest 11491 (em089_bgm.c)
    ('stage_spear_count', 0x502694), ('stage_siege_phase', 0x3A5EC4), ('stage_dragonator_fire', 0x503BB0),  # stage_gimmick.c
    ('stage_cart_request', 0x497040), ('stage_cart_avail', 0x495B40), ('stage_cart_tick', 0x495D0C),  # stage_cart.c
    ('stage_frame', 0x503C7C), ('stage_kobj_bcast', 0x500D18),  # stage_doors.c (+ stage_cannon.c tick)
    ('stage_cannon_ready', 0x503B88), ('stage_dragonator_post', 0x503A5C), ('stage_cannon_shot', 0x46365C),
    ('stage_shell_dtor', 0x4A18B4), ('stage_kobj_extra', 0x4FDF7C), ('stage_cleanup', 0x4FF074),  # stage_cannon.c
    ('item_data_loaded', 0x19237C),  # rItemData load exit (r4 = this): Gogmazios materials in DUMMY items (items.c)
    ('item_text_loaded', 0xB83C48),  # rGUIMessage load exit (r4 = this): their names in itemData_<lang> (items.c)
    ('bui_record', 0x3A3874),  # (quest, em id) -> break reward record: em089's own for 0x59 (items.c)
    ('gear_armor_series', 0x129994), ('gear_armor_create', 0x4BFEE0), ('gear_armor_process', 0x4C0360),  # gear.c:
    ('gear_skill_type', 0x4CEE64), ('gear_skill', 0x4CE98C),   # table load exits (r4 = res): Gogma records appended
    ('gear_deco', 0x191A20), ('gear_deco_create', 0x4C0CB0),   # rDecoData / rDecoCreateData: the Arcane jewels
    ('gear_has_skill', 0xE0DA0),   # (skills, id) -> has skill: Enlightened Blade counts as Element / Status Atk Up
    ('em067_01_act', 0xF78F98),    # uEm067_00 slot 125 action dispatcher: Tigerstripe (variant 1) action / motion
                                   # log (monsters/tigerstripe_zamtrios/module/em067_01_diag.c)
    ('em067_01_post', 0x48C4F0),   # shell request post: no 2/7 tremor for Tigerstripe, as 4U (em067_01_gaps.c)
]
# weapon / sharpness table load exits (gear.c GEAR_HOOK wrappers, out/gear_hooks.inc), "name 0xSITE", written by
# monsters/gogmazios/tools/gear_weapons_em089.py (gu_class finds and checks each class's site)
_GEAR_HOOKS = os.path.join(HERE, 'gear_hooks.txt')
if os.path.exists(_GEAR_HOOKS):
    HOOKS += [(l.split()[0], int(l.split()[1], 16)) for l in open(_GEAR_HOOKS) if l.strip()]
# hooks whose C function always returns nonzero: the hooked function is replaced, its first two instructions
# are never replayed (0x55bda4 is `mov r0, r1; b 0x50b64`: the branch cannot be displaced)
REPLACE_HOOKS = {'name_index'}

# Registry relocation (notes/registry.md): module copies of the per-index tables with one entry per ported monster
# (indexes 137.., allocations.toml), and the code that addresses them repointed.
# (symbol, main address, entries, entry size, pointers?)
REG_TABLES = [
    ('reg_pairs', 0x1597EA4, 137, 8, False),   # (id, index) pairs, + one pair per monster + sentinel
    ('reg_dti', 0x1731E2C, 137, 4, True),      # class DTI per index
    ('reg_cro', 0x1732050, 137, 4, True),      # "roEmNNN.cro" names
    ('reg_files', 0x1732A68, 137, 4, True),    # 0xCC-byte file manifests (users go through GOT 0x1839618)
    ('reg_flags', 0x159F4DC, 137, 4, False),   # attribute bits
    ('reg_icon', 0x162E7F8, 137, 4, False),    # UI icon/name index
    ('reg_u16', 0x159FB3A, 138, 2, False),     # read at [index + 1]
    ('reg_mapicon', 0x1635354, 89, 4, False),  # map icon size class by EM NUMBER (0..88), via data word 0x183fff0
]
# per monster (allocations.toml): mapicon_class = map icon size class of a NEW em number (Gogmazios 18, as Kushala /
# Chameleos / Teostra / Fatalis, notes/api-map.md); ui_icon = UI icon index: atlas = i / 98 (HD_cmn_micon00/01),
# cell = i % 98 in 7 columns (0x56ef50, 0x560918 kind 3); the game uses 0..140, the HD UI v4 cheat 141 / 143-145
# (literal address, address of the pc-relative add/ldr using it, table symbol)
LIT_PATCHES = [
    (0x50BD0, 0x50B74, 'reg_pairs'), (0x50BD4, 0x50B78, 'reg_pairs'), (0x50BD8, 0x50BB8, 'reg_pairs'),
    (0x50C50, 0x50BE8, 'reg_pairs'), (0x50C54, 0x50BF0, 'reg_pairs'), (0x50C58, 0x50C34, 'reg_pairs'),
    (0x4ECE8, 0x4EBFC, 'reg_dti'),
    (0x4ED44, 0x4ED34, 'reg_cro'), (0x4ED94, 0x4ED6C, 'reg_cro'), (0x4EDE4, 0x4EDC0, 'reg_cro'),
    (0x4EE38, 0x4EE10, 'reg_cro'),
    (0x6B43C, 0x6B430, 'reg_flags'),
    (0x560CC0, 0x560CB4, 'reg_icon'),
    (0xACBA8, 0xACB38, 'reg_u16'),
    (0x55511C, 0x554DBC, 'notes_unlock'),     # Hunter's Notes unlock conditions (notes.c)
    (0x5B0CE4, 0x5B0B98, 'notes_order'),      # Hunter's Notes display order
]
# Hunter's Notes tables copied with entry 123 in notes_em089.inc (notes_em089.py): main address per symbol
NOTES_TABLES = {'notes_unlock': 0x162D1F8, 'notes_order': 0x1631EF4}
# entry counts after the ported monsters (allocations.toml: registry indexes from 137, Notes entries from 123)
REG_COUNT = 137 + len(alloc.monsters())
NOTES_COUNT = 123 + sum('notes_entry' in m for m in alloc.monsters())
# 0x55FF3C: entry 0, then pairs (i + 1, i + 2) until i == bound, so entries 0..bound and the bound must be even:
# GU 123 entries -> 122; an even count -> the count (entries 0..count: the last is the padding record notes.c keeps)
NOTES_PAIR_BOUND = NOTES_COUNT - NOTES_COUNT % 2


def cmp_imm(word, imm):
    """the same `cmp rN, #imm` with another 8-bit immediate"""
    assert (word & 0xFFF0FF00) == 0xE3500000 and imm < 256, hex(word)
    return (word & ~0xFF) | imm


WORD_PATCHES = [
    (0x50B94, 0xE3530089, cmp_imm(0xE3530089, REG_COUNT)),    # id -> index search: cmp r3, #137 -> #REG_COUNT
    (0x50C10, 0xE3510089, cmp_imm(0xE3510089, REG_COUNT)),    # index -> id search: cmp r1, #137 -> #REG_COUNT
    # Hunter's Notes list loops, 123 -> NOTES_COUNT entries (notes.c)
    (0x24588C, 0xE354007B, cmp_imm(0xE354007B, NOTES_COUNT)),  # talk condition 44: an entry is due
    (0x247B2C, 0xE354007B, cmp_imm(0xE354007B, NOTES_COUNT)),  # talk action 6: unlock every due entry
    (0x5246BC, 0xE352007B, cmp_imm(0xE352007B, NOTES_COUNT)),  # em ID -> unlocked? (unrolled by 2: an even count reads the padding)
    (0x524750, 0xE35C007B, cmp_imm(0xE35C007B, NOTES_COUNT)),  # em ID -> unlocked? (0x524728, same shape)
    (0x55FF3C, 0xE352007A, cmp_imm(0xE352007A, NOTES_PAIR_BOUND)),  # count by type (unrolled by two, see above)
    (0x55FF84, 0xE35E007B, cmp_imm(0xE35E007B, NOTES_COUNT)),  # n-th entry of a type
    (0x5B0CB8, 0xE355007B, cmp_imm(0xE355007B, NOTES_COUNT)),  # list screen: visible entries in display order
]
GOT_FILES = 0x1839618                          # data word -> reg_files, written by module_init
CLONE_RATHIAN = 'CLONE_RATHIAN' in os.environ.get('GOG_DEFINES', '')   # test: Rathian's class / files for every monster
# (NATIVE_DONOR, test: keep the donor's manifest = game file IDs, is handled by port.c)


def reg_tables_asm(img):
    """tables.S: copies of the registry tables + one entry per ported monster (registry order)."""
    out = ['    .section .data.reg, "aw"']
    for sym, addr, n, size, ptr in REG_TABLES:
        if sym == 'reg_pairs':
            vals = ['0x%x' % w for w in struct.unpack_from('<%dI' % (2 * n), img, addr)]
            for m in MONSTERS:
                vals += ['0x%x' % m['em_id'], str(m['registry_index'])]
            vals += ['0xffffffff', '0xffffffff']        # sentinel (the search reads one pair past the last)
        else:
            raw = [int.from_bytes(img[addr + i * size:addr + (i + 1) * size], 'little') for i in range(n)]
            if ptr:
                assert all(0 < v < MAIN_IMAGE_END for v in raw), sym   # DTIs live in bss
                vals = ['0x%x' % (MAIN_BASE + v) for v in raw]
            else:
                vals = ['0x%x' % v for v in raw]
            for k, m in enumerate(MONSTERS):
                donor = 0 if CLONE_RATHIAN else m['donor_index']
                if sym == 'reg_dti' and 'gu_class' in package(m) and not CLONE_RATHIAN:
                    vals.append('0x%x' % (MAIN_BASE + gu_class_dti(m, raw)))
                elif sym == 'reg_dti':
                    vals.append(vals[0] if CLONE_RATHIAN else 'g_%s_dti' % package(m)['code'])
                elif sym == 'reg_files':
                    vals.append('port_manifests + %d' % (51 * 4 * k))   # donor's, then the data file's (port.c)
                elif sym == 'reg_u16':
                    vals.append(vals[donor + 1])       # index 137 + k lives at [138 + k]
                elif sym == 'reg_mapicon':
                    em = m['em_id'] & 0xff
                    if em >= len(vals):                # a new em number: its own size class (a GU one keeps GU's)
                        vals += ['0'] * (em + 1 - len(vals))
                        vals[em] = str(m['mapicon_class'])
                elif sym == 'reg_icon' and not CLONE_RATHIAN and 'ui_icon' in m:
                    vals.append(str(m['ui_icon']))     # own icon cell (monsters/<name>/tools/ui_*.py), else the donor's
                else:
                    vals.append(vals[donor])
        directive = '.hword' if size == 2 else '.word'
        out += ['    .global %s' % sym, '    .hidden %s' % sym, '    .align 2', '%s:' % sym]
        for i in range(0, len(vals), 8):
            out.append('    %s %s' % (directive, ', '.join(vals[i:i + 8])))
    return '\n'.join(out) + '\n'


def monsters_c():
    """port_monsters.c: the registered monsters for the core (port.h)"""
    out = ['/* port_monsters.c: generated by module/build.py from allocations.toml + package.toml -- do not edit */',
           '#include "port.h"']
    own = [m for m in MONSTERS if 'gu_class' not in package(m)]      # gu_class monsters register no class
    out += ['void %s_register_class(void);' % package(m)['code'] for m in own]
    out.append('const struct port_monster port_monsters[] = {')
    for m in MONSTERS:
        q, s = (m.get('quests', []) + [0, 0])[:2], (m.get('quest_slots', []) + [0, 0])[:2]
        out.append('    {"%s", 0x%x, %d, %d, 0x%x, %d, 0x%x, %d, %d, {%d, %d}, {%d, %d}, %s},' % (
            m['name'], m['em_id'], m['registry_index'], m['donor_index'], m.get('standin_id', 0), m['save_index'],
            0x1064 + m['save_index'] - 105, m['name_entry'], m['notes_entry'], q[0], q[1], s[0], s[1],
            '%s_register_class' % package(m)['code'] if m in own else '0'))
    return '\n'.join(out + ['};']) + '\n'

OUT = os.path.join(HERE, 'out')
EXTRA_DEFINES = ['-D' + d for d in os.environ.get('GOG_DEFINES', '').split()]
CFLAGS = ['--target=armv7a-none-eabihf', '-mcpu=cortex-a57', '-marm', '-mfloat-abi=hard',
          '-fPIC', '-fvisibility=hidden', '-ffreestanding', '-fno-builtin', '-nostdlib', '-O2', '-Wall', '-Wextra',
          '-fno-exceptions', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables']


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.exit('FAILED: %s\n%s%s' % (' '.join(a), r.stdout, r.stderr))
    if r.stderr.strip():
        sys.stderr.write(r.stderr)   # warnings of a successful compile (were dropped before 2026-10-19)
    return r.stdout


def displaced_ok(w):
    """reject instructions that depend on their address or change control flow."""
    if (w >> 28) == 0xF: return False
    if (w & 0x0E000000) == 0x0A000000: return False              # b / bl
    if (w & 0x0FFFFFF0) == 0x012FFF10: return False              # bx
    if ((w >> 16) & 15) == 15 and (w & 0x0C000000) in (0x04000000, 0x00000000): return False  # Rn = pc
    if ((w >> 12) & 15) == 15: return False                      # Rd = pc
    if (w & 0x0F000000) == 0x0D000000 and ((w >> 16) & 15) == 15: return False  # vldr [pc]
    return True


def is_ldr_pc_lit(w):
    """ldr rd, [pc, #+-imm] (AL)"""
    return (w & 0xFF7F0000) == 0xE51F0000 and ((w >> 12) & 15) != 15


def branch_into(img, site):
    """any b/bl within +-16 KB that lands on site+4 (inside the patched pair)?"""
    for a in range(max(0, site - 0x4000), site + 0x4000, 4):
        w = struct.unpack_from('<I', img, a)[0]
        if (w >> 28) != 0xF and (w & 0x0E000000) == 0x0A000000:
            off = w & 0xFFFFFF
            if off & 0x800000: off -= 0x1000000
            if a + 8 + 4 * off == site + 4: return a
    return None


def trampoline(img, name, site):
    """asm for one entry hook: call name_c(regs); nonzero -> return to the caller with the saved r0/r1."""
    out = ['    .global %s_tramp' % name, '    .hidden %s_tramp' % name, '    .hidden %s_c' % name,
           '    .align 2', '%s_tramp:' % name,
           '    push    {r0-r5, r12, lr}', '    vpush   {d0-d7}', '    add     r0, sp, #64',
           '    bl      %s_c' % name, '    cmp     r0, #0', '    vpop    {d0-d7}',
           '    pop     {r0-r5, r12, lr}', '    bxne    lr']
    if name in REPLACE_HOOKS:
        return '\n'.join(out[:-1] + ['    bx      lr'])
    lits = []
    for k in range(2):
        a = site + 4 * k
        w = struct.unpack_from('<I', img, a)[0]
        if is_ldr_pc_lit(w):
            imm = w & 0xFFF
            val = struct.unpack_from('<I', img, a + 8 + (imm if w & (1 << 23) else -imm))[0]
            lab = '.L%s_lit%d' % (name, k)
            out.append('    ldr     r%d, %s' % ((w >> 12) & 15, lab))
            lits.append('%s: .word 0x%08x' % (lab, val))
        elif displaced_ok(w):
            out.append('    .word   0x%08x' % w)
        else:
            sys.exit('hook %s: instruction %08x at %x cannot be displaced' % (name, w, a))
    out += ['    ldr     pc, [pc, #-4]', '    .word   0x%x' % (MAIN_BASE + site + 8)] + lits
    return '\n'.join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    img = open(MAIN_IMG, 'rb').read()
    inc = []
    for name, site in HOOKS:
        hit = branch_into(img, site)
        if hit is not None: sys.exit('hook %s: branch at %x targets %x (inside the patch)' % (name, hit, site + 4))
        inc.append(trampoline(img, name, site))
    open(os.path.join(OUT, 'hooks.inc'), 'w').write('\n'.join(inc) + '\n')
    open(os.path.join(OUT, 'tables.S'), 'w').write(reg_tables_asm(img))
    errs = alloc.check()
    if errs: sys.exit('allocations.toml:\n  ' + '\n  '.join(errs))
    open(os.path.join(OUT, 'alloc.h'), 'w').write(alloc.header())
    open(os.path.join(OUT, 'port_monsters.c'), 'w').write(monsters_c())
    open(os.path.join(OUT, 'gear_hooks.inc'), 'w').write(           # gear.c: one wrapper per table class hook
        ''.join('GEAR_HOOK(%s)\n' % l.split()[0] for l in open(_GEAR_HOOKS) if l.strip()))

    objs = []
    mods = [os.path.join(paths.monster(m['name']), 'module') for m in MONSTERS]
    incs = ['-I', OUT, '-I', HERE] + [a for d in mods for a in ('-I', d)]
    srcs = [os.path.join(HERE, f) for f in ('crt0.S', 'main.c', 'util.c', 'port.c', 'quest.c', 'items.c', 'gear.c',
                                            'notes.c')]
    for d in mods:                                     # every registered monster's code, registry order
        srcs += sorted(glob.glob(os.path.join(d, '*.c')))
    srcs += [os.path.join(OUT, 'port_monsters.c'), os.path.join(OUT, 'tables.S')]
    for path in srcs:
        o = os.path.join(OUT, os.path.basename(path) + '.o')
        run('clang', *CFLAGS, *EXTRA_DEFINES, *incs, '-c', path, '-o', o)
        objs.append(o)
    elf = os.path.join(OUT, 'subsdk1.elf')
    run('ld.lld', '-shared', '-T', os.path.join(HERE, 'link.ld'), '--hash-style=sysv', '-z', 'norelro',
        '-z', 'max-page-size=0x1000', '-init=module_init', '--no-undefined', '-o', elf, *objs)
    data = nso.elf2nso(open(elf, 'rb').read())
    open(os.path.join(OUT, 'subsdk1'), 'wb').write(data)

    syms = {}
    for line in run('llvm-nm', elf).splitlines():
        p = line.split()
        if len(p) == 3: syms[p[2]] = int(p[0], 16)

    # IPS32: offsets are NSO image offsets + 0x100 (header), as in Atmosphere/Ryujinx
    recs = b''
    for name, site in HOOKS:
        tramp = MODULE_BASE + syms[name + '_tramp']
        patch = struct.pack('<II', 0xE51FF004, tramp)       # ldr pc, [pc, #-4]; .word tramp
        recs += struct.pack('>IH', site + 0x100, len(patch)) + patch
    tables = dict({t[0]: t[1] for t in REG_TABLES}, **NOTES_TABLES)
    for lit, use, sym in LIT_PATCHES:
        old = struct.unpack_from('<I', img, lit)[0]
        delta = (use + 8 + old - tables[sym]) & 0xFFFFFFFF   # the code may address table + delta
        if delta > 0x10: sys.exit('literal %x: expected %s (+small), got target %x' % (lit, sym, use + 8 + old))
        new = (MODULE_BASE + syms[sym] - MAIN_BASE + delta - (use + 8)) & 0xFFFFFFFF
        recs += struct.pack('>IH', lit + 0x100, 4) + struct.pack('<I', new)
    for site, old, new in WORD_PATCHES:
        if struct.unpack_from('<I', img, site)[0] != old: sys.exit('word patch %x: unexpected original' % site)
        recs += struct.pack('>IH', site + 0x100, 4) + struct.pack('<I', new)
    open(os.path.join(OUT, MAIN_BUILD_ID + '.ips'), 'wb').write(b'IPS32' + recs + b'EEOF')

    with open(os.path.join(OUT, 'symbols.txt'), 'w') as f:
        for k, v in sorted(syms.items(), key=lambda kv: kv[1]):
            f.write('%08x %08x %s\n' % (MODULE_BASE + v, v, k))
    print('built', len(data), 'bytes; hooks', ', '.join('%s@%x' % h for h in HOOKS))
    for k in ('g_init_magic', 'g_hook_count'):
        if k in syms: print('  %s = 0x%x' % (k, MODULE_BASE + syms[k]))

    if sys.argv[1:] == ['install']:
        install()


def install():
    """exefs + every monster's data file (always: gear IDs depend on all of them) + the selected monsters' assets"""
    ex = os.path.join(MOD_DIR, 'exefs')
    os.makedirs(ex, exist_ok=True)
    for f in ('subsdk1', MAIN_BUILD_ID + '.ips'):
        shutil.copy(os.path.join(OUT, f), os.path.join(ex, f))
    dst = os.path.join(MOD_DIR, 'romfs')
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(os.path.join(dst, 'nativeNX', 'mh4uport'))
    for m in MONSTERS:
        src = os.path.join(paths.gen(m['name']), m['name'] + '.bin')
        if not os.path.exists(src): sys.exit('no data file %s: run monsters/%s/build.sh' % (src, m['name']))
        shutil.copy(src, os.path.join(dst, 'nativeNX', 'mh4uport'))
    sel = os.environ.get('PORT_ASSETS', 'all')
    names = [m['name'] for m in MONSTERS] if sel == 'all' else [] if sel == 'none' else sel.split(',')
    owner = {}
    for name in names:                                 # monsters never ship the same RomFS path
        src = paths.romfs(name)
        for d, _, files in os.walk(src):
            for f in files:
                rel = os.path.relpath(os.path.join(d, f), src)
                if rel in owner: sys.exit('RomFS path %s shipped by both %s and %s' % (rel, owner[rel], name))
                owner[rel] = name
                os.makedirs(os.path.join(dst, os.path.dirname(rel)), exist_ok=True)
                shutil.copy(os.path.join(d, f), os.path.join(dst, rel))
    print('installed into %s: data of %s, assets of %s' % (MOD_DIR, ', '.join(m['name'] for m in MONSTERS),
                                                           ', '.join(names) or 'none'))


if __name__ == '__main__':
    main()
