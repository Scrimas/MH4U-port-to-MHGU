"""build.py : build subsdk1 (core + every registered monster's code) + the main IPS patch.

  build.py            build into module/out/
  build.py install    also install into the Ryujinx mod folder: exefs/, every monster's data file
                      (romfs/nativeNX/mh4uport/<name>.bin, always) and the monsters' assets (romfs/...); PORT_ASSETS =
                      comma-separated packages whose assets to install (default: all, "none" = none)

Hooks: (name, main offset of the hooked instruction). The two instructions at the site
are moved into the trampoline, so they must not be pc-relative or branches (checked).
"""
import glob, os, re, shutil, struct, subprocess, sys, tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import alloc, nso, paths, ui_icons

MONSTERS = alloc.monsters()        # registry order (allocations.toml): registry indexes, append order
QUESTS_PER_ENTRY = alloc.QUESTS_PER_ENTRY   # port.h PORT_QUESTS


def package(m):
    """monsters/<package>/package.toml: version, code = C prefix (<code>_register_class, g_<code>_dti), gu_class =
    name of the GU class that runs the monster instead (its donor's: a GU variant, e.g. uEm067_00 for em067_01); a
    package of several entries names each entry's class in [classes] (entry name = code; entries may share one)"""
    with open(os.path.join(paths.monster(m['name']), 'package.toml'), 'rb') as f:
        p = tomllib.load(f)
    if m['name'] in p.get('classes', {}): p['code'] = p['classes'][m['name']]
    return p


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
# Only the GAP between main and subsdk1 is fixed: the bases themselves move with the loader (yuzu / Eden put an
# argument area after rtld, so their main is not at 0x704000; Ryujinx's is). Nothing in the module or the IPS uses
# an absolute address: main addresses are relocated by rtld from the module's own base (crt0.S g_main_base,
# main_ref()), hook entries are pc-relative jumps into the entry window (hookwin_asm()), hook returns go through
# rtld-relocated words. MODULE_BASE / MAIN_BASE stay for the gap and for the logs' symbols.txt.
MAIN_GAP = MODULE_BASE - MAIN_BASE
HOOKWIN_SPAN = 0x40000      # entry granularity: `add pc, pc, #X << 18` reaches tramp - site - 8 = X * 0x40000


def main_ref(off):
    """assembler expression for main + off, relocated by rtld (R_ARM_RELATIVE against the module's own base)"""
    return '(__module_start - 0x%x)' % (MAIN_GAP - off) if off <= MAIN_GAP else '(__module_start + 0x%x)' % (off - MAIN_GAP)
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
    ('stats_hunted', 0x3A3930),  # reads the same array (lost in a comment by 0815499, restored 2026-10-26)
    ('size_data', 0x6880C),    # em_size_scale_data cached (r0): the save slots' size records = the monsters' (main.c)
    ('save_hunts', 0x523104),    # save hunts + captures by ID (bound 136): 0x59 -> its save slot 0x1064
    ('set_action', 0x76154),   # enemy setAction(this, cat, num, mode): diagnostic log of em089 action changes
    ('set_target', 0xC6E14),   # enemy setTarget(this, kind, sub, param, slot): em089 arena points -> emd stage-19 table
    ('stage_path', 0x15339C),  # stage arc path builder: alias stage -> its folder while the quest runs (stage_alias.c)
    ('stage_maprec', 0x61C394),  # cUIOEnlargeMap setup: per-area map record -> 4U m19 scale / offset (stage.c)
    ('stage_wholerec', 0x61B608),  # cUIOEnlargeMap setup: whole-map record -> scale 60000 / 40000 (4U m19) (stage.c)
    ('stage_name_list', 0x614840), ('stage_name_quest', 0x6149C8),  # stage-name index stores: the alias's name
    ('stage_name_board', 0x613410),                                 # for its quests (stage_alias.c)
    ('quest_group_fix', 0x3B7DE8),  # quest list loader step: placeholder 1011009 -> quest 11491 in memory
    ('quest_unlocked', 0x3B2174),   # (_, id) -> 1 for quest 11491
    ('quest_clear_fix', 0x388D40),  # results-scene clear write: rename the freshly loaded quest list first
    ('quest_group_append', 0x39BB6C),  # quest_group parser exit (r4 = the list): append the quest_append quests
    ('notes_unlock_check', 0x554DA4),  # Hunter's Notes unlock condition (talk action 6 / condition 44): log entry 123
    ('utf8_null_guard', 0x7CA340),  # (out, s, n) UTF-8 helper: s = NULL -> "" (abandon crash safety net, stage.c)
    ('stage_gimmicks', 0x50249C),   # stage gimmick shell spawner (Fortress st003/004/006/007/008): log only (stage.c)
    ('dmg_sub', 0x98AF4),      # diagnostic: enemy HP -= pending damage (main.c)
    ('dmg_special', 0x98AC4),  # diagnostic: damage diverted (0x8187c true), no HP subtraction
    ('set_hp', 0x9A764),       # diagnostic: enemy setHP(this, value)
    ('add_hp', 0x9A7B8),       # diagnostic: enemy addHP(this, delta)
    ('dmg_recv', 0x9D6F8),     # diagnostic: monster damage receiver (monster, part, damage, kind)
    ('name_index', 0x55BDA4),  # (mgr, id) -> monsterName GMD entry (= 0x50b64(id)); 137 -> EM089_NAME_ENTRY
    ('bgm_select', 0x4E60D4),  # (ctl, boss entry, u8 *has, u32 *id): battle theme id -> a registered monster's (bgm.c)
    ('bgm_stqr', 0xB6D72C),    # (stqr, id) -> sequence: its bgm_ids looked up in its own STQR (bgm.c)
    ('bgm_play', 0x4E34A4),    # sSoundControl play stream request: log only while its quests run (bgm.c)
    ('stage_spear_count', 0x502694), ('stage_siege_phase', 0x3A5EC4), ('stage_dragonator_fire', 0x503BB0),  # stage_gimmick.c
    ('stage_cart_request', 0x497040), ('stage_cart_avail', 0x495B40), ('stage_cart_tick', 0x495D0C),  # stage_cart.c
    ('stage_cart_place', 0x495D6C),  # stage_cart.c: riders carried with the pose the collision was just placed with
    ('stage_cart_ground', 0x2E85A4), ('stage_cart_air', 0x2E86FC),  # stage_cart.c: deck backstop for riders, log
    ('stage_frame', 0x503C7C),  # stage_doors.c (+ stage_cannon.c tick)
    ('stage_kobj_bcast', 0x500D18),  # quest-start KowareObj command 0: held in the alias's areas (stage_alias.c)
    ('stage_cannon_ready', 0x503B88), ('stage_dragonator_post', 0x503A5C), ('stage_cannon_shot', 0x46365C),
    ('stage_shell_dtor', 0x4A18B4), ('stage_kobj_extra', 0x4FDF7C), ('stage_cleanup', 0x4FF074),  # stage_cannon.c
    ('stage_demolisher_pose', 0x466618), ('stage_demolisher_efx', 0x466B9C),  # stage_demolisher.c (uShellPlcom_011)
    ('em089_tar_dmg', 0x2F1C60), ('em089_tar_struggle', 0x2BBA74), ('em089_tar_mash', 0x2BBB00),
    ('em089_tar_webpost', 0x2826F4),  # em089_tarhunter.c: Gogmazios' tar on hunters on GU's web status
    ('item_data_loaded', 0x19237C),  # rItemData load exit (r4 = this): Gogmazios materials in DUMMY items (items.c)
    ('item_text_loaded', 0xB83C48),  # rGUIMessage load exit (r4 = this): their names in itemData_<lang> (items.c)
    ('bui_record', 0x3A3874),  # (quest, em id) -> break reward record: em089's own for 0x59 (items.c)
    ('gear_armor_series', 0x129994), ('gear_armor_create', 0x4BFEE0), ('gear_armor_process', 0x4C0360),  # gear.c:
    ('gear_skill_type', 0x4CEE64), ('gear_skill', 0x4CE98C),   # table load exits (r4 = res): Gogma records appended
    ('gear_deco', 0x191A20), ('gear_deco_create', 0x4C0CB0),   # rDecoData / rDecoCreateData: the Arcane jewels
    ('gear_has_skill', 0xE0DA0),   # (skills, id) -> has skill: Enlightened Blade counts as Element / Status Atk Up
    ('em067_01_act', 0xF78F98),    # uEm067_00 slot 125 action dispatcher: Tigerstripe (variant 1) action / motion
                                   # log (monsters/tigerstripe_zamtrios/module/em067_01_diag.c)
    ('em067_01_post', 0x48C4F0),   # shell request post: no 2/7 tremor for Tigerstripe, as 4U (em067_01_gaps.c);
                                   # restores the variant byte at the three ball posts
    ('em067_01_ball', 0xF72700),   # Tigerstripe's paralysis balls: GU's variant-0 post path (em067_01_shells.c)
    ('em067_01_ball43', 0xF735C0),
    ('em067_01_ball42', 0xF73870),
    ('em067_01_end', 0xCA118),     # base "no case" thunks -> slot 247: Tigerstripe's actions GU lacks run instead
    ('em067_01_end7', 0xCA10C),    # (em067_01_moves.c)
    ('em067_01_amove', 0x8F004),   # area move setup / transfer: Tigerstripe log lines (em067_01_diag.c)
    ('em067_01_atransfer', 0xB5D6C),
    ('em057_01_act', 0xF03620),    # uEm057_00 slot 125 action dispatcher: Stygian Zinogre (variant 1) action / motion
                                   # log and its own actions (monsters/stygian_zinogre/module/em057_01_diag.c, _moves.c)
    ('em057_01_remap', 0xEEF31C),  # uEm057_00 slot 127 action remap: 4U's remap for variant 1 (em057_01_moves.c)
    ('em057_01_atk', 0x7DC2C),     # GU attackEx: Stygian's attack indices in the GU handlers it keeps (em057_01_fix.c)
    ('em057_01_start', 0xEEFED0),  # uEm057_00 slot 129 action start: 4U's start work for variant 1 (em057_01_start.c)
    ('em057_01_glow', 0xEF3214),   # uEm057_00 slot 132 material charge glow (GU only): skipped for variant 1 (_fix.c)
    ('em057_01_efx', 0xF060C4),    # uEm057_00 slot 116 effect gateway: 4U Stygian's records for variant 1 (_efx.c)
    ('em057_01_pstance', 0xEF4484),  # mid hooks (return 0) at GU's pillar frame loops, whose posts GU removed: the 4U
    ('em057_01_pwalk1', 0xEF6450),   # posts for variant 1: charge stance 1/6.. (ef4280 step 1), charge walk 2/40 steps
    ('em057_01_pwalk2', 0xEF6338),   # 1 / 2 (ef62e4) (em057_01_posts.c)
    ('em057_01_vparams', 0xEFA930),  # orb family efa930 (= 4U 0x84c280) entry: keeps its 4U parameters, then mid hooks
    ('em057_01_volley1', 0xEFAA6C),  # at its frame-88 / frame-58 posts (GU posts no orb for variant 1): Stygian's orbs
    ('em057_01_volley2', 0xEFAAB4),  # (em057_01_posts.c, em057_01_shell046.c)
    ('dala_dmg_end', 0x98E44),     # enemy damage update 0x97ddc, after the rage add, before the reaction dispatcher
                                   # (r0 = this): Dalamadur tail rage -> head, shared reactions (dala_react.c)
    ('dala_heat_zone', 0x6A160),   # (mgr, area, pos) heat-aura zone test (Teostra only): 1 inside the Dalamadur
                                   # head's zone (dala_head25.c)
    ('dala_map_pos', 0xC09C8),     # (out, obj) object position getter: the map icon loop's call (lr 0x61a110) gets
                                   # the Dalamadur halves' 4U icon joints (dala_head25.c)
    ('dala_ground_pre', 0x2E8590), # hunter ground function 0x2e846c before its ray query (r4 hunter): Dalamadur's
                                   # walk ground off for the ray, back on at dala_ground (dala_walk.c)
    ('dala_ground', 0x2E85AC),     # hunter ground function 0x2e846c after its ray query (r0 hit, r1 ground y, r4
                                   # hunter, r5 &[sp+0x1c]; after stage_cart_ground): 4U's ground windows on
                                   # Dalamadur's body for local and remote hunters (dala_walk.c)
    ('dala_cam_begin', 0x26934),   # quest camera collision step entry / its only exit: Dalamadur's walk ground off
    ('dala_cam_end', 0x26E34),     # during the camera's stage sweep, as 4U's camera never sees it (dala_walk.c)
    ('dala_camtilt_begin', 0x238E0),  # quest camera terrain tilt (ground ray under the hunter) entry / its only
    ('dala_camtilt_end', 0x23938),    # exit (r4 camera): the walk ground off for its ray (dala_walk.c)
    ('icon_set', 0x56EF58),    # icon setter 0x56ef50 after its push: UI indexes 196.. = our atlas (icons.c)
    ('board_icon', 0x3A3178),  # (_, quest board byte) -> UI index + 1: bytes 200.. = our atlas (icons.c)
    ('board_byte', 0x6132E0),  # board loop before that call: no hyper badge for our bytes (icons.c)
    ('tex_bind', 0xA4FAF0),    # sprite texture bind (sprite, ID): our icon sprites keep our atlas (icons.c)
    ('tex_entry', 0xB80FD0),   # .gui texture entry by ID: our IDs -> their entry copies (icons.c)
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
# Chameleos / Teostra / Fatalis, notes/api-map.md); ui_icon = UI icon index: atlas = i / 98 (HD_cmn_micon00/01,
# then ours from 196: icons.c, tools/ui_icons.py), cell = i % 98 in 7 columns (0x56ef50, 0x560918 kind 3)
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

# Items appended past GU's 2991 (allocations.toml [monster.append] items; notes/items-append.md): the code that bounds
# item IDs by the count is raised by the appended count, the per-item buffers grow with it, and the items-obtained
# set / clear / test are replaced (items.c: IDs from 3008 use a reserved save block). Nothing changes without them.
ITEMS_APPENDED = alloc.item_count() - alloc.GU_ITEMS
ITEM_BOUND_SITES = [            # movw rX, #0xbad / #0xbae / #0xbaf: `id - 1 <= 2989` checks and one loop over all IDs
    0x6F3DF8, 0x6F90F4, 0x6FA504, 0x6FA7EC, 0x6FBA28, 0x6FCEBC, 0x6FCF98, 0x6FCFB0, 0x6FD020, 0x6FD0E0, 0x6FD19C,
    0x7054E8, 0x709438, 0x7094EC, 0x7094F4, 0x72F2B0, 0x72F890, 0x72FA24, 0x72FBF4, 0x744394, 0x78D9E4,
    0x199C08,                   # item box sort / merge 0x199ae4: loop over its u32[2991] stack array
    0x383F14, 0x383F38, 0x383F78, 0x383F88, 0x383F9C, 0x383FD8]    # 0x3839bc: per-item byte buffer (size, count)
ITEM_ARRAY_SIZE = 0x199B78      # movw r1, #0x2ebc: memset of that stack array (4 x 2991)
ITEM_SORT_FRAME = (0x199AE8, 0x199D4C)    # sub / add sp, sp, #708 (+ #11264): the array is sp+8 .. the frame top
if ITEMS_APPENDED:
    HOOKS += [('obtained_set', 0x1943D4), ('obtained_clear', 0x194408), ('obtained_test', 0x19443C)]
    REPLACE_HOOKS |= {'obtained_set', 'obtained_clear', 'obtained_test'}
if 'TEST_QUEST_RANK' in os.environ.get('GOG_DEFINES', ''):   # test: Stygian's quests at that rank (em057_01_ai.c)
    HOOKS += [('em057_01_rank', 0x3A8D68)]                   # GU quest rank getter (4U 0x69ae70)

# Magnet Spike (MHF) as class 5 / box type 12: Phase 2 vertical slice, test builds only (GOG_DEFINES="MS_SLICE";
# weapons/magnet_spike/notes/phase2.md). Saves keep type-12 entries and class 5 raw: vanilla GU cannot load them.
MS_SLICE = 'MS_SLICE' in os.environ.get('GOG_DEFINES', '')
MS_DIR = os.path.join(ROOT, 'weapons', 'magnet_spike')
if MS_SLICE:
    HOOKS += [
        ('ms_factory', 0x275BC8),     # factory after a class constructor (r8 info, r10 object): class 5's vtable
        ('ms_base', 0x13C208),        # (sEquip, type, id) -> base record: type 12 = ours (ms_class.c)
        ('ms_level', 0x13ED08),       # (sEquip, type, row) -> level row: type 12 = ours
        ('ms_pwl_gmk', 0x13F554), ('ms_pwl_disp', 0x13F594), ('ms_pwl_carry', 0x13F5D4), ('ms_pwl_sub', 0x13F614),
        ('ms_box_ptr', 0x14B0B0),     # item box loader entry (r0 = the box)
        ('ms_box_loaded', 0x3E7804),  # after the box load: one Magnet Spike in the box (test build)
        ('ms_motion', 0x281998),      # set-motion (p, motion): class-5 motion log (diagnostic)
        ('ms_attach', 0x3078B8),      # weapon attach (weapon, hunter, part type): class 5 in hand on joint 8
        ('ms_setmotion', 0x53A164),   # unit set-motion (unit, motion, mode): class 5's Impact idle / walk slots
        ('ms_forge_create', 0x6F9658),    # smithy create getter (this, type, row): type 12 = ours
        ('ms_forge_process', 0x70153C),   # smithy process getter (this, type, row): type 12 = ours
        ('ms_hud', 0x646560),         # CB phial widget update after its hunter reads (r4 widget, r5 hunter)
        ('ms_snd_file', 0x4EA0DC),    # weapon sound-request file ID (?, class, equipment, k): class 5 asks as GS
        ('ms_wsync', 0x308DDC), ('ms_wsync2', 0x308E68),  # weapon sync's class reads: class 5 picks by mode as SA
    ]
# the forge's category menu (ms_class.c "the forge's category menu"): order, labels, top-panel icon lists
MS_TABLES = {'ms_forge_order': 0x1650022, 'ms_forge_label': 0x1650058, 'ms_shop_icons': 0x176F3E4}
MS_LIT_PATCHES = [(0x6F2DA8, 0x6F2CEC, 'ms_forge_order'), (0x6F2B1C, 0x6F2A94, 'ms_forge_label'),
                  (0x6F29AC, 0x6F1D2C, 'ms_forge_label'), (0x5933F8, 0x5930B8, 'ms_shop_icons')] if MS_SLICE else []
MS_GUNNER_SITES = [0x144968, 0x144A0C, 0x144B24, 0x6ECEFC, 0x6ED884, 0x6FCB2C, 0x7037A8, 0x70B738]


def ms_patches(img):
    """(site, old, new) words for class 5 (MS_SLICE only). GU still treats class 5 as the leftover MH3 bowgun slot:
    gunner tests `class - 4 < 3`, masks 0x47 over classes 4..10 (GU's own 0x172314 already uses 0x45), bowgun cases
    in two class switches and two per-class tables, the bowgun weapon part; gu-weapon-class.md "Class 5 in GU"."""
    if not MS_SLICE: return []
    word = lambda a: struct.unpack_from('<I', img, a)[0]
    out = [
        (0x275B2C, 0x29C, 0x40),               # factory class jump table entry 5: return 0 -> the Great Sword case
        (0x16283D0, 6, 0),                     # weapon part type per class (0x277830): bowgun 6 -> GS's single part
        (0x27C860, 0xE3A01047, 0xE3A01045),    # gunner helper kind 1: classes {4,5,6,10} -> {4,6,10}
        (0x28AC94, 0xE3A01047, 0xE3A01045),    # the same mask at 0x28ac80
        (0x180DA8, 0xA0, 0x40),                # switch(class) 0x180d78: class 5 -> class 0's case (was 4 / 6 / 10)
        (0x665B34, 0x58, 0x264),               # switch(class) 0x665b04 (HUD gauges): class 5 -> the Charge Blade's
                                               # case (sharpness + phials; ms_hud drives the phials: magnet gauge)
        (0x1630594, 6, 5), (0x16309C4, 6, 5),  # per-class values for classes 4..10 (0x58a1d4 / 0x58eff4): 6 -> 5
        (0x1628064, 2, 1),                     # gunner table by type - 7 (0x26ee8c strips blademaster armor)
        (0x145B94, 0xE3072FDF, 0xE3072FFF),    # item box blademaster / gunner mask 0x7fdf -> 0x7fff
        # gunner helper kind 0 (0x27c804): r0 = (5 >> (class - 4)) & 1, classes 4 and 6 only
        (0x27C814, 0xE3A00001, 0xE3A00005), (0x27C818, 0xE3510003, 0xE1A00130),
        (0x27C81C, 0x3A000012, 0xE2000001), (0x27C820, 0xEA000012, 0xE12FFF1E)]
    # the weapon setup's file-ID bases (0x288d10; one-time .bss tables of 0x286ac0 / 0x286c2c / 0x286e28 / 0x287024)
    # skip class 5: its entries get "no file" (0, read-only 0x15a0cd8), so no model, weapon motions or pwl. GU's file
    # table still names MH3's class-5 files at the gaps: model base = class * 2 + part -> weapon\w05\mbg001 - 1 (part 1
    # keeps the .bss 0); weapon motions wg05_00 / wg05_sa_00; pwl = the Great Sword's pl_w00_gNN (stand-in, as the
    # pwl getters ms_class.c answers)
    mv = word(0x286B5C)                        # movw r2, #0x591e (LBG's base, entry 12)
    out += [(0x286B5C, mv, movw_imm(mv, 0x5536)), (0x286B64, 0xE5801028, 0xE5802028), (0x286B68, 0xE580102C, mv),
            (0x286CC4, 0xE5911000, 0xE30014B0),     # ldr r1, [r1] (the "no file" value) -> movw r1, #0x4b0
            (0x286EC0, 0xE5911000, 0xE3001653),     # -> movw r1, #0x653
            (0x2870B4, 0xE5911000, 0xE300175B)]     # -> movw r1, #0x75b
    for s in MS_GUNNER_SITES:                  # sub rA, rB, #4; cmp rA, #3; blo -> cmp rB, #4; cmpne rB, #6; beq
        sub, cmp, blo = word(s), word(s + 4), word(s + 8)
        ra, rb = (sub >> 12) & 15, (sub >> 16) & 15
        assert sub & 0xFFF00FFF == 0xE2400004 and cmp == 0xE3500003 | ra << 16 and blo >> 24 == 0x3A, hex(s)
        out += [(s, sub, 0xE3500004 | rb << 16), (s + 4, cmp, 0x13500006 | rb << 16), (s + 8, blo, blo & 0x0FFFFFFF)]
    # guard: class 5 joins the Great Sword's class masks (movw #imm, bit 5 added) in the can-guard check 0x2f2ba0, its
    # angle rule and the guard-level thresholds of 0x2f0670 (the Magnet Spike's Guard Counter / Impact guard windows)
    for site, old, new in ((0x2F2BC8, 0xC20B, 0xC22B), (0x2F2D8C, 0xC081, 0xC0A1), (0x2F07C0, 0xC001, 0xC021)):
        w = word(site)
        assert (w >> 4 & 0xF000 | w & 0xFFF) == old, hex(site)
        out.append((site, w, movw_imm(w, new)))
    # the forge: weapon categories 14 -> 15 (cursor config {kind 8, 7 per page, count, 0}, read only by 0x6f29c8);
    # the per-type list icon (u8 at 0x165000c + type): type 12 = LBG's 0x3f -> the Great Sword's 0x37 (stand-in)
    out += [(0x1650080, 0x0509000E, 0x0509000F), (0x1650018, 0x43383F3F, 0x43383F37)]
    # per-class value tables whose class-5 entry holds the bowgun values: class 0's (the generic melee values; phase2.md
    # lists them with the Great Sword stand-ins): (table, entry size) as read at 0x29ab40 / 0x2aca3c / 0x2ad1e8 /
    # 0x2cdbd4 / 0x2dfb84 / 0x2e21a4
    for base, size in MS_CLASS_TABLES:
        new = bytearray(img[base + 5 * size & ~3:base + 6 * size + 3 & ~3])
        lo = (base + 5 * size) - (base + 5 * size & ~3)
        new[lo:lo + size] = img[base:base + size]
        for k in range(0, len(new), 4):
            a = (base + 5 * size & ~3) + k
            old_w, new_w = word(a), struct.unpack_from('<I', new, k)[0]
            if old_w != new_w: out.append((a, old_w, new_w))
    return out


MS_CLASS_TABLES = [(0x162543C, 2), (0x162882C, 2), (0x16287AC, 4), (0x1628D90, 10), (0x1628F14, 4), (0x1629578, 4)]


def movw_imm(word, imm):
    """the same `movw rD, #imm16` with another immediate"""
    assert (word & 0x0FF00000) == 0x03000000 and imm < 0x10000, hex(word)
    return (word & 0xFFF0F000) | (imm & 0xF000) << 4 | (imm & 0xFFF)


def arm_imm(v):
    """ARM modified immediate (rot << 8 | imm8) for v, None when v has no encoding"""
    for rot in range(16):
        x = ((v << 2 * rot) | (v >> (32 - 2 * rot))) & 0xFFFFFFFF if rot else v
        if x < 256: return rot << 8 | x
    return None


def item_patches(img):
    """(site, old, new) words for ITEMS_APPENDED items past 2991 (none without)"""
    if not ITEMS_APPENDED: return []
    n, out = ITEMS_APPENDED, []
    word = lambda a: struct.unpack_from('<I', img, a)[0]
    imm16 = lambda w: (w >> 4) & 0xF000 | w & 0xFFF
    for site in ITEM_BOUND_SITES:
        w = word(site)
        assert imm16(w) in (0xBAD, 0xBAE, 0xBAF), 'item bound %x: %x' % (site, w)
        out.append((site, w, movw_imm(w, imm16(w) + n)))
    w = word(ITEM_ARRAY_SIZE)
    assert imm16(w) == 0x2EBC, hex(w)
    out.append((ITEM_ARRAY_SIZE, w, movw_imm(w, 0x2EBC + 4 * n)))
    grow = next(d for d in range(4 * n, 4 * n + 1024, 8) if arm_imm(708 + d) is not None)   # keeps 8-byte alignment
    for site, op in zip(ITEM_SORT_FRAME, (0xE24DDF00, 0xE28DDF00)):       # sub / add sp, sp, #708 (0xb1 ror 30)
        w = word(site)
        assert w == op | 0xB1, 'item sort frame %x: %x' % (site, w)
        out.append((site, w, (w & ~0xFFF) | arm_imm(708 + grow)))
    return out


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
                vals = [main_ref(v) for v in raw]
            else:
                vals = ['0x%x' % v for v in raw]
            for k, m in enumerate(MONSTERS):
                donor = 0 if CLONE_RATHIAN else m['donor_index']
                if sym == 'reg_dti' and 'gu_class' in package(m) and not CLONE_RATHIAN:
                    vals.append(main_ref(gu_class_dti(m, raw)))
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
                    vals.append(str(m['ui_icon']))     # own icon cell (tools/ui_icons.py), else the donor's
                else:
                    vals.append(vals[donor])
                if sym == 'reg_icon' and 'companion_of' not in m:
                    # the save slot (an unused 'dummy' index, main.c stats_add) shows the monster's icon: the quest
                    # result's size records name the slot's ID (icon accessor 0x560ca4(mgr, id) = table[index of id]),
                    # GU's dummies have the filler cell 109 (user 2026-10-26: "the icons are all rocks")
                    vals[m['save_index']] = vals[-1]
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
    codes = []                                                       # entries sharing a class register it once
    for m in own:
        if package(m)['code'] not in codes: codes.append(package(m)['code'])
    out += ['void %s_register_class(void);' % c for c in codes]
    own = [next(m for m in own if package(m)['code'] == c) for c in codes]
    out.append('const struct port_monster port_monsters[] = {')
    port = {m['name']: k for k, m in enumerate(MONSTERS)}
    for m in MONSTERS:
        q, s = [(m.get(k, []) + [0] * QUESTS_PER_ENTRY)[:QUESTS_PER_ENTRY] for k in ('quests', 'quest_slots')]
        sa, st = m.get('stage_alias', [0, 0]), stage_alias(m)
        mr = st.get('maprec', []) + [[0, 0, 0]] * (4 - len(st.get('maprec', [])))
        sz = package(m).get('size', {}).get(m['name'], [])
        assert len(sz) in (0, 1, 4) and all(v > 0 for v in sz), (m['name'], sz)   # [base] or [base, mini, silver, gold]
        sz = sz + [0] * (4 - len(sz))
        alt = m.get('standin_alt', [0])         # [stand-in ID, quest IDs...] (port.h standin_alt)
        assert not alt[0] or (len(alt) > 1 and set(alt[1:]) <= set(m.get('quests', []))), (m['name'], alt)
        alt_mask = sum(1 << m['quests'].index(qid) for qid in alt[1:])
        sn = m.get('append', {}).get('stage_name', 0)   # the alias's board name (port.h stage_name)
        assert sn in (0, 1) and (not sn or 'stage_alias' in m), (m['name'], sn)
        sn = GU_QUEST_MESSAGE + alloc.offset(m['name'], 'stage_name') if sn else 0
        out.append('    {"%s", 0x%x, %d, %d, 0x%x, %d, 0x%x, %d, %d, {%s}, {%s}, %s, %d, '
                   '%d, %d, 0x%x, 0x%x, %d, {%s}, {%s}, {%s}, %sf, {%s}, %d, 0x%x, 0x%x, %d},' % (
            m['name'], m['em_id'], m['registry_index'], m['donor_index'], m.get('standin_id', 0), m['save_index'],
            0x1064 + m['save_index'] - 105, m['name_entry'], m.get('notes_entry', 0),
            ', '.join('%d' % v for v in q), ', '.join('%d' % v for v in s),
            '%s_register_class' % package(m)['code'] if m in own else '0', port.get(m.get('companion_of'), -1),
            sa[0], sa[1], sum(1 << a for a in st.get('hold_kobj_areas', [])),
            sum(1 << (k - 48) for k in st.get('kinds', [])), len(st.get('maprec', [])),
            ', '.join('%rf' % float(r[0]) for r in mr), ', '.join('%d' % r[1] for r in mr),
            ', '.join('%d' % r[2] for r in mr), repr(float(st.get('wholemap_k', 0))),
            ', '.join('%rf' % float(v) for v in sz), int(m.get('quest_append', False)), alt[0], alt_mask, sn))
    return '\n'.join(out + ['};']) + '\n'


GU_QUEST_MESSAGE = 120   # GU's questMessage strings (resident_eng.arc GUI\06_msg): stage names 4..28, 114..119


def stage_alias(m):
    """package.toml [stage] of an entry with allocations.toml stage_alias (module/stage_alias.c): kinds = arc path kinds
    redirected to the folder (49 mapUI, 54 map_com, 55 language map_com, 56 stage, 58 area), hold_kobj_areas = areas
    whose KowareObjs keep GU's quest-start command 0 from playing, maprec = the area map records [k, x, y] per area
    (with kind 49), wholemap_k = the whole-map record scale (with kind 55)"""
    if 'stage_alias' not in m: return {}
    st = package(m).get('stage')
    if not st or not st.get('kinds'): sys.exit('%s: stage_alias needs package.toml [stage] kinds' % m['name'])
    assert all(48 <= k < 80 for k in st['kinds']) and all(0 <= a < 8 for a in st.get('hold_kobj_areas', [])), st
    assert (49 in st['kinds']) == bool(st.get('maprec')) and len(st.get('maprec', [])) <= 4, st
    assert (55 in st['kinds']) == bool(st.get('wholemap_k')), st
    return st

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
    if (w & 0x0F8003F0) == 0x06800070:                           # sxt*/uxt*: Rn = 15 means no accumulate
        return ((w >> 12) & 15) != 15 and (w & 15) != 15
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
    # back to main at site + 8 through an rtld-relocated data word (no absolute address in text, which rtld
    # cannot relocate); every register, the flags and lr are preserved
    out += ['    sub     sp, sp, #4', '    push    {r0}', '    ldr     r0, .L%s_retoff' % name,
            '.L%s_retpc:' % name, '    add     r0, pc, r0', '    ldr     r0, [r0]', '    str     r0, [sp, #4]',
            '    pop     {r0, pc}',
            '.L%s_retoff: .word %s_ret - (.L%s_retpc + 8)' % (name, name, name)] + lits
    out += ['    .pushsection .data.hookret, "aw"', '    .align 2', '%s_ret: .word %s' % (name, main_ref(site + 8)),
            '    .popsection']
    return '\n'.join(out)


def hookwin_asm(entries, windows):
    """the hook entry window: `b name_tramp` at each entry's offset, the rest zero (never executed)"""
    out = ['    .section .hookwin, "ax"', '    .arm', '    .global __hookwin', '    .hidden __hookwin',
           '    .balign 4', '__hookwin:']
    for off, name in sorted(entries):
        out += ['    .org __hookwin + 0x%x' % off, '    b       %s_tramp' % name]
    out.append('    .org __hookwin + 0x%x' % (windows * HOOKWIN_SPAN))
    return '\n'.join(out) + '\n'


def main():
    os.makedirs(OUT, exist_ok=True)
    img = open(MAIN_IMG, 'rb').read()
    inc = []
    for name, site in HOOKS:
        hit = branch_into(img, site)
        if hit is not None: sys.exit('hook %s: branch at %x targets %x (inside the patch)' % (name, hit, site + 4))
        inc.append(trampoline(img, name, site))
    open(os.path.join(OUT, 'hooks.inc'), 'w').write('\n'.join(inc) + '\n')
    open(os.path.join(OUT, 'layout.inc'), 'w').write('    .equ MAIN_GAP, 0x%x\n' % MAIN_GAP)
    open(os.path.join(OUT, 'tables.S'), 'w').write(reg_tables_asm(img))
    errs = alloc.check()
    if errs: sys.exit('allocations.toml:\n  ' + '\n  '.join(errs))
    open(os.path.join(OUT, 'alloc.h'), 'w').write(alloc.header())
    open(os.path.join(OUT, 'port_monsters.c'), 'w').write(monsters_c())
    open(os.path.join(OUT, 'gear_hooks.inc'), 'w').write(           # gear.c: one wrapper per table class hook
        ''.join('GEAR_HOOK(%s)\n' % l.split()[0] for l in open(_GEAR_HOOKS) if l.strip()))

    objs = []
    mods = [os.path.join(paths.monster(p), 'module') for p in alloc.packages()]   # once per package
    incs = ['-I', OUT, '-I', HERE] + [a for d in mods for a in ('-I', d)]
    srcs = [os.path.join(HERE, f) for f in ('crt0.S', 'main.c', 'util.c', 'port.c', 'quest.c', 'items.c', 'gear.c',
                                            'notes.c', 'stage_alias.c', 'bgm.c', 'icons.c')]
    for d in mods:                                     # every registered monster's code, registry order
        srcs += sorted(glob.glob(os.path.join(d, '*.c')))
    if MS_SLICE:                                       # the Magnet Spike's code and its generated action tables
        gen = os.path.join(MS_DIR, 'gen', 'ms_data.inc')
        if not os.path.exists(gen): sys.exit('no %s: run weapons/magnet_spike/tools/msbuild.py' % gen)
        incs += ['-I', os.path.join(MS_DIR, 'module'), '-I', os.path.dirname(gen)]
        srcs += sorted(glob.glob(os.path.join(MS_DIR, 'module', '*.c')))
    srcs += [os.path.join(OUT, 'port_monsters.c'), os.path.join(OUT, 'tables.S')]
    for path in srcs:
        o = os.path.join(OUT, os.path.basename(path) + '.o')
        run('clang', *CFLAGS, *EXTRA_DEFINES, *incs, '-c', path, '-o', o)
        objs.append(o)
    elf = os.path.join(OUT, 'subsdk1.elf')
    win_src, win_obj = os.path.join(OUT, 'hookwin.S'), os.path.join(OUT, 'hookwin.S.o')

    def link(entries):
        """write the entry window (entries: [(window offset, hook name)]) and link; returns the symbols"""
        open(win_src, 'w').write(hookwin_asm(entries, windows))
        run('clang', *CFLAGS, *incs, '-c', win_src, '-o', win_obj)
        run('ld.lld', '-shared', '-T', os.path.join(HERE, 'link.ld'), '--hash-style=sysv', '-z', 'norelro',
            '-z', 'max-page-size=0x1000', '-init=module_init', '--no-undefined', '-o', elf, *objs, win_obj)
        syms = {}
        for line in run('llvm-nm', elf).splitlines():
            p = line.split()
            if len(p) == 3: syms[p[2]] = int(p[0], 16)
        return syms

    # Hook entries: the patched site is one `add pc, pc, #X << 18` into a window of HOOKWIN_SPAN-spaced stubs
    # (`b name_tramp`), so the jump depends only on MAIN_GAP. Pass 1 places the window, pass 2 fills it.
    windows = 1
    while True:
        syms = link([])
        win = syms['__hookwin']
        entries, used = [], set()
        for name, site in HOOKS:
            off = (site + 8 - MAIN_GAP - win) % HOOKWIN_SPAN
            k = 0
            while (off + k * HOOKWIN_SPAN) in used: k += 1          # two sites with the same residue: next window
            off += k * HOOKWIN_SPAN
            used.add(off)
            entries.append((off, name, site))
        if max(e[0] for e in entries) < windows * HOOKWIN_SPAN: break
        windows += 1
    syms2 = link([(off, name) for off, name, _ in entries])
    for k in [n + '_tramp' for n, _ in HOOKS] + ['__hookwin']:
        if syms2[k] != syms[k]: sys.exit('hook entry window: %s moved between the two links' % k)
    syms = syms2
    data = nso.elf2nso(open(elf, 'rb').read())
    open(os.path.join(OUT, 'subsdk1'), 'wb').write(data)

    # IPS32: offsets are NSO image offsets + 0x100 (header), as in Atmosphere/Ryujinx
    recs = b''
    for off, name, site in entries:
        delta = MAIN_GAP + win + off - (site + 8)
        x = delta // HOOKWIN_SPAN
        if delta % HOOKWIN_SPAN or not 0 < x < 256: sys.exit('hook %s: entry delta %#x not encodable' % (name, delta))
        patch = struct.pack('<I', 0xE28FF700 | x)           # add pc, pc, #(x ror 14) = x << 18
        recs += struct.pack('>IH', site + 0x100, len(patch)) + patch
    tables = dict({t[0]: t[1] for t in REG_TABLES}, **NOTES_TABLES, **MS_TABLES)
    for lit, use, sym in LIT_PATCHES + MS_LIT_PATCHES:
        old = struct.unpack_from('<I', img, lit)[0]
        delta = (use + 8 + old - tables[sym]) & 0xFFFFFFFF   # the code may address table + delta
        if delta > 0x10: sys.exit('literal %x: expected %s (+small), got target %x' % (lit, sym, use + 8 + old))
        new = (MODULE_BASE + syms[sym] - MAIN_BASE + delta - (use + 8)) & 0xFFFFFFFF
        recs += struct.pack('>IH', lit + 0x100, 4) + struct.pack('<I', new)
    for site, old, new in WORD_PATCHES + item_patches(img) + ms_patches(img):
        if struct.unpack_from('<I', img, site)[0] != old: sys.exit('word patch %x: unexpected original' % site)
        recs += struct.pack('>IH', site + 0x100, 4) + struct.pack('<I', new)
    open(os.path.join(OUT, MAIN_BUILD_ID + '.ips'), 'wb').write(b'IPS32' + recs + b'EEOF')

    with open(os.path.join(OUT, 'symbols.txt'), 'w') as f:
        for k, v in sorted(syms.items(), key=lambda kv: kv[1]):
            f.write('%08x %08x %s\n' % (MODULE_BASE + v, v, k))
    open(os.path.join(OUT, 'defines.txt'), 'w').write(' '.join(EXTRA_DEFINES) + '\n')   # tools/release.py: none
    ui_icons.build(OUT)                                # the icon atlases (romfs nativeNX/mh4uport, icons.c)
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
        if not os.path.exists(src): sys.exit('no data file %s: run monsters/%s/build.sh' % (src, alloc.package(m)))
        shutil.copy(src, os.path.join(dst, 'nativeNX', 'mh4uport'))
    for name, _, _ in ui_icons.ATLASES:
        shutil.copy(os.path.join(OUT, name), os.path.join(dst, 'nativeNX', 'mh4uport'))
    sel =os.environ.get('PORT_ASSETS', 'all')           # package names (an entry name selects its package)
    names = alloc.packages() if sel == 'all' else [] if sel == 'none' else \
        list(dict.fromkeys(paths.package(n) for n in sel.split(',')))
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
    # the Magnet Spike's files (weapons/magnet_spike/tools/msbuild.py), when the BUILT module has it: the switch comes
    # from the last build's defines.txt (install.sh runs the install step without GOG_DEFINES)
    built = open(os.path.join(OUT, 'defines.txt')).read().split() if os.path.exists(os.path.join(OUT, 'defines.txt')) else []
    if MS_SLICE or '-DMS_SLICE' in built:
        src = os.path.join(MS_DIR, 'romfs')
        if not os.path.isdir(src): sys.exit('no %s: run weapons/magnet_spike/tools/msbuild.py' % src)
        for d, _, files in os.walk(src):
            for f in files:
                rel = os.path.relpath(os.path.join(d, f), src)
                if rel in owner: sys.exit('RomFS path %s shipped by both %s and the Magnet Spike' % (rel, owner[rel]))
                os.makedirs(os.path.join(dst, os.path.dirname(rel)), exist_ok=True)
                shutil.copy(os.path.join(d, f), os.path.join(dst, rel))
        names = names + ['magnet_spike']
    print('installed into %s: data of %s, assets of %s' % (MOD_DIR, ', '.join(m['name'] for m in MONSTERS),
                                                           ', '.join(names) or 'none'))


if __name__ == '__main__':
    main()
