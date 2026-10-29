"""msbuild.py : build the Magnet Spike's MHGU files (Phase 2 vertical slice, notes/phase2.md) from the MHF sources
(dump/mhf) and GU templates (paths.GU_ROMFS), into weapons/magnet_spike/romfs (RomFS mirror) and gen/ms_data.inc
(the module's action tables). Both outputs hold game data: gitignored.

  msbuild.py              everything
  msbuild.py report       print the slot plan, the cancel tables and the attack list only

What it writes (arc paths = the file-ID table's class-5 names, which GU already lists):
  arc/player/quest/w05.arc     player\\mot\\w05\\w05 (body motions), w05_sa (empty list), player\\param\\pl_w05 (GS's
                               values: Phase 2 stand-in), player\\hit\\pl_we05_hitdata / _hitsize
  arc/player/quest/w05_m.arc   player\\cam\\w05\\w05, w05_sa (GS's camera lists: stand-in)
  arc/player/quest/w05_mN.arc  N = 0..5 (every style gets the Guild set): player\\cmd\\w05\\plcmd_w05_<style> (the
                               cancel tables) + the commands they name (ours, and GU's common ones)
  arc/weapon/w05/001.arc       weapon\\w05\\mbg001\\mbg001 (wk400 as GU MOD; MH3's class-5 model ids name mbgNNN)
  arc/weapon/w05/g00.arc       weapon\\w05\\mot\\wg05_00 (weapon motions, by body slot; index 0 = the sheathed
                               weapon), wg05_sa_00 (empty)
Motion slots: GU's common actions play fixed bank-5 slots (idle 1, walk 2-4, rolls 9 / 12 / 13, draw 80, ...;
mode 2 = slot 215 true: 20, 24, 32, 33, 81 ...); those get the MHF equivalents (COMMON), slots every GU class
shares get GU's own motion (GU_COPY, from GS's list), and the Magnet Spike's own action motions take slots no GU
class uses (free_slots)."""
import json, math, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WEAPON = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(WEAPON))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import paths, arcpack, xfs, lmt
import aan, fskl, msact, sdt, msgrip, msmot, mshit, fmod2gu
sys.path.append(paths.GU_PY)
from romfs import RomFS
from arc import arc_entries, arc_read

MHF = os.path.join(ROOT, 'dump', 'mhf')
OUT_ROMFS = os.path.join(WEAPON, 'romfs', 'nativeNX', 'arc')
OUT_GEN = os.path.join(WEAPON, 'gen')
WK = os.path.join(MHF, 'weapon', 'wk400')
# w05_m0..m5: GU's own style names (file IDs 27 + class * 6 + style, 0x29b514): Guild, Striker, Aerial, Adept,
# Alchemy, Valor (test 1: style 5 while the user played Valor)
STYLES = ['guild', 'old', 'airhike', 'bushi', 'kizuna', 'tatsujin']

T_LMT, T_PARAM, T_HDP, T_HTS = 0x76820d81, 0x496f8f22, 0x4e2ef008, 0x5653c1b0
T_CMD, T_TBL, T_CAM = 0x5139901d, 0x4b4c2bd3, 0x30991f46

# the slice (notes/phase2.md): MHF action numbers
CUTTING = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 13, 17, 122, 126, 152, 155, 14, 90, 78]
IMPACT = [18, 32, 33, 34, 35, 36, 26, 91, 79]
SLICE = CUTTING + IMPACT
RELEASE = 208            # MHF shared action "charge released": 35 (charged) or 36 (module code, ms_act.c)
# GU common slot -> MHF motion (S: by duration, loop and root path; the first test's motion log checks them)
COMMON = {1: 1001, 4: 1004, 5: 1001, 6: 1001, 7: 1001, 9: 1021, 11: 1021, 12: 1006, 13: 1007,
          14: 1462, 15: 1010, 16: 1011, 20: 1020, 24: 1024, 32: 1010, 33: 1011, 80: 1002, 81: 1008}
# slots GU's common code plays that every class fills alike: GS's motion (slot -> GS slot). 2 / 3 = the draw /
# sheathe (GS's events: on the back until frame 14 / from frame 36), GS's until MHF's are found (MHF's are not in
# w13's part 0: S, a shared motion bank)
GU_COPY = {s: s for s in (2, 3, 51, 52, 61, 90, 91, 92, 95, 150, 152, 169, 170, 171, 172, 173, 180, 181, 182, 195,
                          196, 201, 221, 231, 232, 233, 234, 252, 253, 254, 255)}
GU_COPY.update({53: 51, 54: 52, 96: 95, 174: 169, 175: 170, 176: 171, 177: 172, 178: 173})
COMMON_USED = {1, 2, 3, 4, 6, 7, 9, 11, 12, 13, 18, 20, 24, 27, 28, 30, 32, 33, 36, 42, 51, 52, 53, 54, 60, 80, 81,
               90, 91, 92, 95, 96, 104, 151, 152, 154, 155, 163, 164, 165, 169, 172, 173, 174, 179, 181, 182, 195,
               196, 198, 201, 211, 212, 213, 252, 255}      # bank-5 slots GU's common code names (scan, S)

# class input ids (player +0x1424 bits, set by the module's translator ms_input.c): MHF input -> id; Impact = +16
CLASS_ID = {2: 0, 3: 1, 4: 2, 5: 3, 13: 4, 14: 5, 15: 6, 21: 7}
ID_NAMES = ['TRI', 'CIRCLE', 'TRICIRCLE', 'SELECT', 'R2', 'CIRCLE_HELD', 'CIRCLE_REL', 'TRI_REL']
STICK_INPUTS = {6: 3, 22: 2}          # stick + circle / tri: cmd_type 0xc (stick tilted + class id)
NEVER = 998                           # a frame no slice motion reaches: "not in this step"


def rom():
    global _ROM
    try: return _ROM
    except NameError: _ROM = RomFS(paths.GU_ROMFS); return _ROM


def gu_arc(name):
    """{path: (type, data)} (a path held by two types keeps the last: use gu_entries for whole copies)"""
    d = rom().read('/nativeNX/arc/' + name)
    return {e[0]: (e[1], arc_read(d, e)) for e in arc_entries(d)}


def gu_entries(name):
    d = rom().read('/nativeNX/arc/' + name)
    return [(e[0], e[1], arc_read(d, e)) for e in arc_entries(d)]


# ------------------------------------------------------------------------------------------------ motions

def free_slots():
    """bank-5 slots no GU class list uses and GU's common code does not name"""
    used = set()
    for w in ('w00', 'w14', 'w08', 'w02'):
        d = gu_arc('player/quest/%s.arc' % w)['player\\mot\\%s\\%s' % (w, w)][1]
        used |= {i for i, o in enumerate(lmt.anims(d)) if o}
    reserved = used | COMMON_USED | set(COMMON) | set(GU_COPY) | {0}
    return [s for s in range(1, 256) if s not in reserved]


def mhf_motions(acts):
    """MHF body motions the slice actions play, in first-use order"""
    out = []
    for a in SLICE:
        for kind, mot, start, blend, frame, loops in acts[a]['steps']:
            if kind in (3, 4, 5) and mot not in out: out.append(mot)
    return out


def slot_plan(acts):
    free = free_slots()
    plan = {s: m for s, m in COMMON.items()}
    own = {}
    for m in mhf_motions(acts):
        own[m] = free.pop(0)
        plan[own[m]] = m
    return plan, own


def build_motions(plan, gs_list):
    w13 = aan.parse(open(os.path.join(MHF, 'motion', 'w13.aan'), 'rb').read())
    w13w = aan.parse(open(os.path.join(MHF, 'motion', 'w13w.aan'), 'rb').read())
    _, bbones = fskl.parse(open(os.path.join(MHF, 'player', 'm_editpl.fskl'), 'rb').read())
    _, wbones = fskl.parse(open(os.path.join(WK, '1.fskl'), 'rb').read())
    weapon = msgrip.Weapon(open(os.path.join(WK, '0.fmod'), 'rb').read(), open(os.path.join(WK, '1.fskl'), 'rb').read())
    fist = msgrip.fists(open(os.path.join(MHF, 'player', 'm_editpl.0.bin'), 'rb').read(),
                        open(os.path.join(MHF, 'player', 'm_editpl.fskl'), 'rb').read())
    gs_off = lmt.anims(gs_list)
    body, wpn, report, holders = {}, {}, [], {}
    for slot, mid in sorted(plan.items()):
        ev = None
        if slot in COMMON and gs_off[slot]:          # GU's motion events of that common slot, rescaled
            ev = msmot.gu_events(gs_list, gs_off[slot])
        a = msmot.body(w13, mid, None)
        if ev: a['events'] = msmot.rescale_events(ev, a['frames'])
        body[slot] = a
        part, s = (mid - 1000) // 100, (mid - 1000) % 100
        mo = w13w[part].get(s)
        hs = None
        if mo:
            hs = msgrip.holders(weapon, msgrip.tracks_of(mo, weapon.bones), mo['frames'], fist)
            holders[mid] = hs
        wpn[slot] = msmot.weapon(w13w, wbones, mid, hs, msmot.body_world(w13, bbones, mid), a['frames'])
        sw = [f for f in range(1, len(hs)) if hs[f] != hs[f - 1]] if hs else []
        report.append('slot %3d <- MHF %d  %3d frames loop %4d%s' % (slot, mid, a['frames'], a['loop'],
                      '  hand switch at %s' % sw if sw else ''))
    for slot, src in sorted(GU_COPY.items()):
        if gs_off[src]: body[slot] = ('gu', gs_list, src)
    # weapon index 0 = the sheathed weapon (GU's weapon sync 0x308b3c plays it for any sheathed motion; MHF keys no
    # sheathed weapon motion): the Cutting form, as the drawn idle's first frame (S), its root at rest on GU's carry
    wpn[0] = msmot.weapon_pose(w13w, wbones, COMMON[1], 0)
    report.append('weapon 0 <- MHF %d frame 0 (sheathed: Cutting form, root at rest)' % COMMON[1])
    return msmot.lmt_bytes(body), msmot.lmt_bytes(wpn), report, holders, (w13w, wbones, weapon)


def empty_list(n=1):
    return b'LMT\0' + struct.pack('<HH', 67, n) + bytes(4 * n) + bytes(-(8 + 4 * n) % 16)


# ------------------------------------------------------------------------------------------------ attacks

def attack_instances(acts):
    """(action, event index, step, frame, MHF attack id) for every ATTACK event of the slice"""
    out = []
    for a in SLICE:
        for k, (step, kind, cond, frame, loop, eid, prm) in enumerate(acts[a]['events']):
            if eid == 3: out.append((a, k, step, frame if kind not in (1, 2) else 0, prm))
    return out


def build_hits(acts, sdt_d, w00, w02, own, holders, wdata):
    es = sdt.entries(sdt_d)
    e78 = next(e for e in es if e['kind'] == 0x78)
    atk = sdt.attacks(sdt_d, e78)
    shapes = sdt.shape_sets(sdt_d, e78)
    tmpl_cut = mshit.hdp_parse(w00)[1]
    tmpl_imp = mshit.hdp_parse(w02)[3]
    w13w, wbones, weapon = wdata
    entries, sets, index, report = [[0] * 28], [], {}, []
    entries[0][10] = 254 if False else 0
    for a, k, step, frame, aid in attack_instances(acts):
        r = atk[aid]
        cut = r['type'] == 0x20a
        dur = r['raw'][1]
        mot = acts[a]['steps'][step][1]
        mid_f = frame + dur // 2
        part, s = (mot - 1000) // 100, (mot - 1000) % 100
        mo = w13w[part].get(s)
        hs = holders.get(mot)
        hand = hs[min(mid_f, len(hs) - 1)] if hs else 14
        joint = 8 if hand == 14 else 12
        W = msgrip.pose(weapon.bones, msgrip.tracks_of(mo, weapon.bones), mid_f) if mo else {}
        shp = []
        variant = shapes[r['shape']][0] if r['shape'] < len(shapes) else []
        for kind_bone, typ, u0, flag, rad, x0, y0, z0, x1, y1, z1 in variant:
            pa, pb = np.array([x0, y0, z0, 1.0]), np.array([x1, y1, z1, 1.0])
            if flag & 8 and kind_bone in W:          # on a weapon bone: into the holding hand's frame
                M = W[kind_bone]
                shp.append(mshit.capsule(joint, rad, (M @ pa)[:3], (M @ pb)[:3]))
            else:                                    # around the hunter: the root
                shp.append(mshit.capsule(255, rad, pa[:3], pb[:3]))
        sets.append(shp)
        e = mshit.hdp_entry(tmpl_cut if cut else tmpl_imp, r['mv'], dur, mshit.CUT if cut else mshit.IMPACT,
                            len(sets) - 1)
        index[(a, k)] = len(entries)
        entries.append(e)
        report.append('hit %2d: action %3d event %d (step %d f%d) MHF attack %2d MV %3d KO %5.1f %-6s live %2d f, '
                      'joint %3d, %d shapes' % (len(entries) - 1, a, k, step, frame, aid, r['mv'], r['ko'],
                                                'cut' if cut else 'impact', dur, joint, len(shp)))
    return mshit.hdp_bytes(entries), mshit.hts_bytes(sets), index, report


# ------------------------------------------------------------------------------------------------ commands

def tspec_step(t, k, end_value):
    """MHF time spec -> this step's frame: (state, frame) with state 'before' / 'in' / 'after' / 'never'"""
    step, kind, cond, frame, loop = t
    if kind == 2: return 'never', None
    if step < k: return 'before', 0
    if step > k: return 'after', None
    return 'in', 0 if kind == 1 else frame


def command_window(c, k):
    """one MHF cancel in step k -> (Pre, Start, End) as GU floats; None = never usable in this step"""
    b0, _b1 = c['buf']; g0, g1 = c['go']
    sb, fb = tspec_step(b0, k, 0)
    s0, f0 = tspec_step(g0, k, 0)
    s1, f1 = tspec_step(g1, k, 0)
    if sb == 'never' or s0 == 'never': return None
    if s1 == 'before': return None                        # the go window closed in an earlier step
    pre = 999 if sb == 'after' else fb
    if s0 == 'after':                                     # buffering only: the transition comes in a later step
        return (pre, NEVER, NEVER) if pre != 999 else None
    start = f0
    end = 0 if s1 in ('after', 'never') else max(f1, 1)
    return (pre, start, end)


class Commands:
    """command files (path -> rPlBaseCmd fields) and the table list"""
    def __init__(self, gs_m0):
        self.tmpl_cmd = next(b for p, (t, b) in gs_m0.items() if t == T_CMD)
        self.tmpl_tbl = next(b for p, (t, b) in gs_m0.items() if t == T_TBL)
        self.gs = gs_m0
        self.files = {}                                   # path -> bytes
        self.ours = {}                                    # (act_no, cmd_type, param0) -> path

    def com(self, name):
        """a GU common command, copied from GS's style arc"""
        p = 'player\\cmd\\com\\' + name
        self.files[p] = self.gs[p][1]
        return p

    def ours_cmd(self, act, cmd_type, p0):
        key = (act, cmd_type, p0)
        if key not in self.ours:
            n = sum(1 for k in self.ours if k[0] == act)
            p = 'player\\cmd\\w05\\plcmd_w05_0x0010_%03d%s' % (act, 'abcdefghijklmnop'[n])
            o = xfs.parse(self.tmpl_cmd)
            o.update(mQuality=2, act_st=0x10, act_no=act, act_param=0, cmd_type=cmd_type, cmd_param0=p0,
                     cmd_param1=0, cmd_param2=0, cmd_param3=0)
            self.files[p] = xfs.build(self.tmpl_cmd, o)
            self.ours[key] = p
        return self.ours[key]


def fbits(v):
    return struct.unpack('<I', struct.pack('<f', float(v)))[0]


def cmd_obj(path, pre, start, end):
    return {'_class': 0x61ee27ea, 'Active': 1, 'CmdBase': ('rPlBaseCmd', path, 2), 'PreFrame': fbits(pre),
            'StartFrame': fbits(start), 'EndFrame': fbits(end)}


def gs_tables(gs_m0):
    root = xfs.parse(next(b for p, (t, b) in gs_m0.items() if t == T_TBL))
    arr = root['TblList']['mpArray']
    out = []
    for t in arr:
        cs = t['Command']['mpArray']
        out.append(cs if isinstance(cs, list) else [cs])
    return out


MODES = {}                            # MHF action -> 'C' / 'I' / 'C+I' (msact.modes; set by main)


def mode_of(a):
    """the mode an action runs in (MHF sets the mode from the action it starts, 0x1032c480): 90 'to Impact' is I"""
    return 1 if MODES.get(a) == 'I' else 0


def cancel_commands(C, a, c, mode):
    """GU command paths for one MHF cancel of action a (empty = not in the slice)"""
    nxt, inp = c['next'], c['input']
    if c['cond'] not in (0,): return []                  # gauge / marker / flag conditions: Phase 3 moves
    if nxt in (202, 203):                                # roll: GU's common evades out of an attack
        return [C.com('plcmd_com_0x0001_013a'), C.com('plcmd_com_0x0001_014a')]
    if inp == 1:                                         # stick: GU's common drawn move
        return [C.com('plcmd_com_0x0001_006e')]
    target = nxt if nxt in SLICE or nxt == RELEASE else None
    if target is None: return []
    if inp == 20: return [C.ours_cmd(target, 0, 0)]       # always
    if inp in STICK_INPUTS:
        return [C.ours_cmd(target, 0xc, STICK_INPUTS[inp] + 16 * mode)]
    if inp in CLASS_ID:
        return [C.ours_cmd(target, 8, CLASS_ID[inp] + 16 * mode)]
    return []


def build_commands(acts, gs_m0):
    """-> (command files {path: bytes}, table list bytes, {(action, step): table index}, report)"""
    C = Commands(gs_m0)
    gst = gs_tables(gs_m0)
    tables, report = [], []
    # 0: drawn idle = GS's idle commons + the Magnet Spike's idle inputs, both modes (mode-specific ids)
    idle = []
    for c in gst[0]:
        name = c['CmdBase'][1].split('\\')[-1]
        if name.startswith('plcmd_w00'): continue
        idle.append(cmd_obj(C.com(name), 0, 0, 0))
    for inp, (ca, ia) in sorted(msact.IDLE.items()):
        for mode, act in ((0, ca), (1, ia)):
            if act not in SLICE: continue
            fake = dict(next=act, input=inp, cond=0)
            for p in cancel_commands(C, None, fake, mode):
                idle.append(cmd_obj(p, 0, 0, 0))
    tables.append(idle)
    report.append('table   0: drawn idle: %s' % ', '.join(o['CmdBase'][1].split('\\')[-1].replace('plcmd_', '')
                                                         for o in idle))
    # 1-9: GS's attack tables have no Magnet Spike counterpart (empty); 10-46: GS's common-action tables, without
    # GS's weapon commands (the table pickers ms_class.c keep GS's indexes)
    tables += [[] for _ in range(9)]
    for t in gst[10:]:
        keep = []
        for c in t:
            name = c['CmdBase'][1].split('\\')[-1]
            if name.startswith('plcmd_w00'): continue
            keep.append(cmd_obj(C.com(name), *[struct.unpack('<f', struct.pack('<I', c[f]))[0]
                                              for f in ('PreFrame', 'StartFrame', 'EndFrame')]))
        tables.append(keep)
    # the slice: one table per (action, step), the cancels in priority order (GU takes the first ready command)
    index = {}
    for a in SLICE:
        cs = sorted(acts[a]['cancels'], key=lambda c: -c['pri'])
        for k in range(len(acts[a]['steps'])):
            t = []
            for c in cs:
                w = command_window(c, k)
                if w is None: continue
                for p in cancel_commands(C, a, c, mode_of(a)):
                    t.append(cmd_obj(p, *w))
            index[(a, k)] = len(tables)
            tables.append(t)
            report.append('table %3d: action %3d step %d: %s' % (
                len(tables) - 1, a, k, ', '.join('%s %g/%g/%g' % (
                    o['CmdBase'][1].split('\\')[-1].replace('plcmd_', ''),
                    *[struct.unpack('<f', struct.pack('<I', o[f]))[0] for f in ('PreFrame', 'StartFrame', 'EndFrame')])
                    for o in t)))
    root = xfs.parse(C.tmpl_tbl)
    tl = root['TblList']
    proto = tl['mpArray'][0]
    arr = []
    for t in tables:
        o = {'_class': proto['_class'], 'Command': {'_class': proto['Command']['_class'], 'mAutoDelete': 0,
                                                    'mpArray': t}}
        arr.append(o)
    tl['mpArray'] = arr
    return C.files, xfs.build(C.tmpl_tbl, root), index, report


# ------------------------------------------------------------------------------------------------ module tables

EVENT_IDS = {3: 'MS_EV_ATTACK', 1: 'MS_EV_GUARD', 21: 'MS_EV_ARMOR', 13: 'MS_EV_SPEED', 14: 'MS_EV_TURN',
             39: 'MS_EV_TURN_TARGET', 12: 'MS_EV_SHAKE', 26: 'MS_EV_CHARGED'}


def c_tables(acts, modes, own, tbl_index, hit_index):
    """gen/ms_data.inc: the slice's actions, steps and events for ms_act.c"""
    L = ['/* ms_data.inc: generated by weapons/magnet_spike/tools/msbuild.py from MHF\'s mhfdat / mhfsdt (game data,',
         ' * gitignored) -- do not edit. MHF action numbers; motion = bank-5 slot of player\\\\mot\\\\w05\\\\w05. */']
    for i, n in enumerate(ID_NAMES):
        L.append('#define MS_ID_%s %d' % (n, i))
    L.append('#define MS_ID_IMPACT 16')
    L.append('#define MS_RELEASE %d' % RELEASE)
    steps, events, rows = [], [], []
    for a in SLICE:
        s0, e0 = len(steps), len(events)
        for k, (kind, mot, start, blend, frame, loops) in enumerate(acts[a]['steps']):
            slot = own.get(mot, 0xffff) if kind in (3, 4, 5) else mot
            steps.append('    {%d, %d, %d, %d, %d, %d, %d},  /* %d: MHF motion %d */' % (
                kind, slot, start, blend, frame, loops, 2000 + tbl_index[(a, k)], a, mot))
        for k, (step, kind, cond, frame, loop, eid, prm) in enumerate(acts[a]['events']):
            if eid not in EVENT_IDS: continue
            when = 0 if kind == 1 else 2 if kind == 2 else 1
            arg = hit_index.get((a, k), 0) if eid == 3 else prm
            events.append('    {%d, %d, %d, %s, %d},  /* %d: %s param %d */' % (
                step, when, frame, EVENT_IDS[eid], arg, a, msact.EVENTS.get(eid, eid), prm))
        rows.append('    {%d, %d, %d, %d, %d, %d},' % (a, mode_of(a), len(steps) - s0, s0, len(events) - e0, e0))
    L += ['static const struct ms_step ms_steps[] = {'] + steps + ['};']
    L += ['static const struct ms_event ms_events[] = {'] + events + ['};']
    L += ['static const struct ms_action ms_actions[] = {'] + rows + ['};']
    L.append('#define MS_IDLE_TABLE 2000')
    return '\n'.join(L) + '\n'


# ------------------------------------------------------------------------------------------------ arcs

def model_arc():
    """wk400 as weapon\\w05\\mbg001\\mbg001 in a copy of GS 001's arc (its MRL with the texture paths renamed)"""
    old, new = 'weapon\\w00\\two001\\two001', 'weapon\\w05\\mbg001\\mbg001'
    assert len(old) == len(new)
    ver, ents = arcpack.read(rom().read('/nativeNX/arc/weapon/w00/001.arc'))
    tmp = os.path.join(OUT_GEN, 'w00_001.arc')
    open(tmp, 'wb').write(arcpack.build(ents))
    fixed = os.path.join(OUT_GEN, 'w05_001_tmp.arc')
    fmod2gu.build_arc(WK, tmp, fixed)
    ver, ents = arcpack.read(open(fixed, 'rb').read())
    out = []
    for path, th, data in ents:
        if th == fmod2gu.T_MRL: data = data.replace(old.encode(), new.encode())
        out.append((path.replace(old, new), th, data))
    os.remove(tmp); os.remove(fixed)
    return arcpack.build(out)


def write(rel, data):
    p = os.path.join(OUT_ROMFS, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data)
    return p


def main(report_only=False):
    os.makedirs(OUT_GEN, exist_ok=True)
    dat = open(os.path.join(MHF, 'zz', 'mhfdat.dec.bin'), 'rb').read()
    sdt_d = open(os.path.join(MHF, 'zz', 'mhfsdt.dec.bin'), 'rb').read()
    acts, modes = msact.actions(dat), msact.modes(dat)
    MODES.update(modes)
    w00 = gu_arc('player/quest/w00.arc')
    w02 = gu_arc('player/quest/w02.arc')
    gs_m0 = gu_arc('player/quest/w00_m0.arc')
    gs_m = gu_arc('player/quest/w00_m.arc')
    plan, own = slot_plan(acts)
    body, wlist, mreport, holders, wdata = build_motions(plan, w00['player\\mot\\w00\\w00'][1])
    msmot.check(body); msmot.check(wlist)
    hdp, hts, hit_index, hreport = build_hits(acts, sdt_d, w00['player\\hit\\pl_we00_hitdata'][1],
                                              w02['player\\hit\\pl_we02_hitdata'][1], own, holders, wdata)
    cmds, tbl, tbl_index, creport = build_commands(acts, gs_m0)
    rep = mreport + hreport + creport
    open(os.path.join(OUT_GEN, 'report.txt'), 'w').write('\n'.join(rep) + '\n')
    if report_only:
        print('\n'.join(rep)); return
    open(os.path.join(OUT_GEN, 'ms_data.inc'), 'w').write(c_tables(acts, modes, own, tbl_index, hit_index))
    # GS's effect and sound lists (per-motion effects / sounds, the class's effect files and sound banks) under the
    # class-5 names GU's file-ID table holds: placeholders until the sounds / effects phase (they key GS's motion slots,
    # i.e. our common slots; our action slots are empty in GS's list)
    rename = {'effect\\psl\\player\\mot\\w00\\w00': 'effect\\psl\\player\\mot\\w05\\w05',
              'effect\\psl\\player\\mot\\w00\\w00_sa': 'effect\\psl\\player\\mot\\w05\\w05_sa',
              'effect\\pel\\pl\\w00_000': 'effect\\pel\\pl\\w05_000', 'effect\\pel\\pl\\w00_800': 'effect\\pel\\pl\\w05_800',
              'sound\\pts\\pl\\w00_000': 'sound\\pts\\pl\\w05_000', 'sound\\pts\\pl\\w00_800': 'sound\\pts\\pl\\w05_800',
              'sound\\call\\pl\\pl_wp00': 'sound\\call\\pl\\pl_wp05'}
    fx = [(rename.get(p, p), t, b) for p, t, b in gu_entries('player/quest/w00.arc')
          if t not in (T_LMT, T_PARAM, T_HDP, T_HTS)]
    write('player/quest/w05.arc', arcpack.build([
        ('player\\mot\\w05\\w05', T_LMT, body),
        ('player\\mot\\w05\\w05_sa', T_LMT, empty_list()),
        ('player\\param\\pl_w05', T_PARAM, w00['player\\param\\pl_w00'][1]),
        ('player\\hit\\pl_we05_hitdata', T_HDP, hdp),
        ('player\\hit\\pl_we05_hitsize', T_HTS, hts)] + fx))
    write('player/quest/w05_m.arc', arcpack.build([
        ('player\\cam\\w05\\w05', T_CAM, gs_m['player\\cam\\w00\\w00'][1]),
        ('player\\cam\\w05\\w05_sa', T_CAM, gs_m['player\\cam\\w00\\w00_sa'][1])]))
    for k, style in enumerate(STYLES):
        # the list last, as in GU's own style arcs: it resolves its command references while it loads, so a
        # command not loaded yet stays a null CmdBase that the command step skips (test 1: no command fired)
        ents = [(p, T_CMD, b) for p, b in sorted(cmds.items())]
        ents.append(('player\\cmd\\w05\\plcmd_w05_%s' % style, T_TBL, tbl))
        write('player/quest/w05_m%d.arc' % k, arcpack.build(ents))
    write('weapon/w05/001.arc', model_arc())
    for name in ('001', 'mat_b', 'mat_i'):                # GS's weapon sound arcs (sounds phase: MHF's)
        write('weapon/w05/snd/%s.arc' % name, rom().read('/nativeNX/arc/weapon/w00/snd/%s.arc' % name))
    write('weapon/w05/g00.arc', arcpack.build([('weapon\\w05\\mot\\wg05_00', T_LMT, wlist),
                                               ('weapon\\w05\\mot\\wg05_sa_00', T_LMT, empty_list())]))
    print('motions: %d body slots (%d KB), weapon list %d KB; %d hits; %d tables, %d command files' % (
        len(plan), len(body) // 1024, len(wlist) // 1024, len(hit_index), len(tbl_index) + 47, len(cmds)))
    print('report: %s' % os.path.join(OUT_GEN, 'report.txt'))


if __name__ == '__main__':
    main(sys.argv[1:] == ['report'])
