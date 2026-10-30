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
import aan, fskl, msact, sdt, msgrip, msmot, mshit, msfx, fmod2gu, mshud
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
ACTIONS = []             # every MHF action that plays a Magnet Spike motion (set by main: 19, 47, 134, 137 have no
                         # steps, 50 plays the shared motion 1 only)
RELEASE, GC_HIT = 208, 207   # MHF shared actions the module runs: charge released (35 charged / 36), guard hit
SHARED = (RELEASE, GC_HIT)
# GU common slot -> MHF motion (S: by duration, loop and root path; the first test's motion log checks them)
COMMON = {1: 1001, 4: 1004, 5: 1001, 6: 1001, 7: 1001, 12: 1006, 13: 1007,
          14: 1462, 15: 1010, 16: 1011, 20: 1020, 24: 1024, 32: 1010, 33: 1011, 80: 1002, 81: 1008}
# slots GU's common code plays that every class fills alike: GS's motion (slot -> GS slot). 2 / 3 = the draw /
# sheathe (GS's events: on the back until frame 14 / from frame 36), 9 / 11 = the sheathes while moving (common
# 1/3; test 1 played MHF 1021 there, an Impact-form evade: "sheathing while walking rolls"), GS's until MHF's are
# found (MHF's are not in w13's part 0: S, a shared motion bank). Impact plays 5020 / 5024 / 5032 / 5033 for 1 / 4 /
# 12 / 13 (ms_class.c ms_setmotion)
GU_COPY = {s: s for s in (2, 3, 9, 11, 51, 52, 61, 90, 91, 92, 95, 150, 152, 169, 170, 171, 172, 173, 180, 181, 182,
                          195, 196, 201, 221, 231, 232, 233, 234, 252, 253, 254, 255)}
GU_COPY.update({53: 51, 54: 52, 96: 95, 174: 169, 175: 170, 176: 171, 177: 172, 178: 173})
COMMON_USED = {1, 2, 3, 4, 6, 7, 9, 11, 12, 13, 18, 20, 24, 27, 28, 30, 32, 33, 36, 42, 51, 52, 53, 54, 60, 80, 81,
               90, 91, 92, 95, 96, 104, 151, 152, 154, 155, 163, 164, 165, 169, 172, 173, 174, 179, 181, 182, 195,
               196, 198, 201, 211, 212, 213, 252, 255}      # bank-5 slots GU's common code names (scan, S)

# class input ids (player +0x1424.. = 8 words, 0x285e54): one per (MHF input, MHF condition) pair in first-use order,
# + MS_ID_IMPACT in Impact; the module's translator (ms_act.c ms_input) sets an id when its input is pressed and its
# condition holds. Stick + circle / tri share the circle / tri ids under cmd_type 0xc (stick tilted + class id).
PAIRS = {}
MS_ID_IMPACT = 64
STICK_INPUTS = {6: 3, 22: 2}
# drawn idle (msact.IDLE) inputs: the conditions MHF's cancels give the same inputs (R1 moves cost a gauge bar,
# aiming needs a marker in range); 11 = R1 + SELECT Magnetise: condition 13 (this mode's charge ready, 0x10336810)
IDLE_COND = {7: 1, 8: 1, 9: 1, 10: 1, 17: 1, 24: 10, 23: 11, 11: 13}
NEVER = 998                           # a frame no motion reaches: "not in this step"


def pair_id(inp, cond):
    key = (STICK_INPUTS.get(inp, inp), cond)
    if key not in PAIRS:
        PAIRS[key] = len(PAIRS)
        assert len(PAIRS) <= MS_ID_IMPACT, 'class ids: more than %d input / condition pairs' % MS_ID_IMPACT
    return PAIRS[key]


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
    """bank-5 slots GU's common code does not name: first those no GU class list uses, then the other classes' own
    slots (class 5 has its own list; main clears GS's per-slot effect entries for them, the class-5 psl being GS's)"""
    used = set()
    for w in ('w00', 'w14', 'w08', 'w02'):
        d = gu_arc('player/quest/%s.arc' % w)['player\\mot\\%s\\%s' % (w, w)][1]
        used |= {i for i, o in enumerate(lmt.anims(d)) if o}
    reserved = COMMON_USED | set(COMMON) | set(GU_COPY) | {0}
    return ([s for s in range(1, 256) if s not in reserved | used] +
            [s for s in range(1, 256) if s in used and s not in reserved])


def mhf_motions(acts):
    """MHF body motions the actions play (bank 1 = w13), in first-use order"""
    out = []
    for a in ACTIONS:
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
    return msmot.lmt_bytes(body), msmot.lmt_bytes(wpn), report, holders, (w13w, wbones, weapon, w13, bbones)


def empty_list(n=1):
    return b'LMT\0' + struct.pack('<HH', 67, n) + bytes(4 * n) + bytes(-(8 + 4 * n) % 16)


# ------------------------------------------------------------------------------------------------ attacks

SPECIAL_EVENTS = (4, 42, 43, 44)     # MHF special attacks (mhfsdt kind 0x79: marker shot, Pin Finisher, extra hits)
# specials MHF's code spawns (no event; notes/mechanics.md): special -> (motion posing its shapes, frame). Guard
# Counter success 57 / 76 / 77 (1 / 2 / 3+ guarded hits): #5 / #6 / #7 at f32 of motion 1034 (0x103339d0);
# magnetised Finishing Slash (motion 1035, actions 152 / 154 / 155): #10 after f38 (Magnetic Shock's #12: not traced)
CODE_SPECIALS = {5: (1034, 32), 6: (1034, 32), 7: (1034, 32), 10: (1035, 38)}
# Magnetic Shock 5 x 3 (MHF task kind 0x0f, 0x1004d810; started by 0x1004d3e0 from the per-motion extras: 159 / 160
# at f8 of 1031 / 1032, 161 / 162 at the start of 1082): special #12 at task ticks 3 / 5 / 7 / 10 at these spots
# (x, z cm in the hunter's frame, 0x1004d650): one hit entry per spot, its root shapes moved there (ms_act.c timer)
SHOCK = [(-120.0, 170.0), (-90.0, 250.0), (-30.0, 400.0), (40.0, 550.0)]
MAGNETISE_PCT = 10                   # MS block prm61


def attack_instances(acts):
    """(action, event index, step, frame, MHF attack id, special) for every attack event (3 = kind 0x78, specials =
    kind 0x79)"""
    out = []
    for a in ACTIONS:
        for k, (step, kind, cond, frame, loop, eid, prm) in enumerate(acts[a]['events']):
            if eid == 3 or eid in SPECIAL_EVENTS:      # 42 spawns special #11, 43 / 44 #8 (param = extra arg)
                aid = {42: 11, 43: 8, 44: 8}.get(eid, prm)
                out.append((a, k, step, frame if kind not in (1, 2) else 0, aid, eid != 3))
    return out


def build_hits(acts, sdt_d, w00, w02, own, holders, wdata):
    es = sdt.entries(sdt_d)
    kinds = {}
    for kind in (0x78, 0x79):
        e = next(e for e in es if e['kind'] == kind)
        kinds[kind] = sdt.attacks(sdt_d, e), sdt.shape_sets(sdt_d, e)
    tmpl_cut = mshit.hdp_parse(w00)[1]
    tmpl_imp = mshit.hdp_parse(w02)[3]
    w13w, wbones, weapon = wdata[:3]
    entries, sets, index, report, swings = [[0] * 28], [], {}, [], []
    todo = [((a, k), acts[a]['steps'][step][1], frame, aid, special,
             'action %3d event %d (step %d f%d)' % (a, k, step, frame))
            for a, k, step, frame, aid, special in attack_instances(acts)]
    todo += [(('code', n), mot, f, n, True, 'code special (motion %d f%d)' % (mot, f))
             for n, (mot, f) in sorted(CODE_SPECIALS.items())]
    todo += [(('shock', k), 1031, 8, 12, True, 'Magnetic Shock 5 x 3 spot %d' % k) for k in range(len(SHOCK))]
    for key, mot, frame, aid, special, where in todo:
        atk, shapes = kinds[0x79 if special else 0x78]
        if aid >= len(atk): continue
        r = atk[aid]
        if special and not r['mv']:              # MV-0 specials: MHF's detection volumes (#1 marker shot, #3 pin
            report.append('hit   -: %s MHF special %2d MV 0: not armed (ms_act.c does its job)' % (where, aid))
            continue                             # grab 8 m, #11): GU would land 0-damage hits
        cut = bool(r['type'] & 0x200)            # attacks 0x20a cut / 0x10a impact, specials 0x200 / 0x100
        dur = r['raw'][1]
        mid_f = frame + dur // 2
        part, s = (mot - 1000) // 100, (mot - 1000) % 100
        mo = w13w[part].get(s)
        hs = holders.get(mot)
        hand = hs[min(mid_f, len(hs) - 1)] if hs else 14
        joint = 8 if hand == 14 else 12
        W = msgrip.pose(weapon.bones, msgrip.tracks_of(mo, weapon.bones), mid_f) if mo else {}
        shp, tip = [], None
        si = aid if special else r['shape']          # specials: the shape set of their own id (14 sets, r[8] = 0;
        variant = shapes[si][0] if si < len(shapes) else []    # #5-7 / 10 / 12 = 1 m x 4 m pillars, #8 7 m on the weapon)
        for kind_bone, typ, u0, flag, rad, x0, y0, z0, x1, y1, z1 in variant:
            pa, pb = np.array([x0, y0, z0, 1.0]), np.array([x1, y1, z1, 1.0])
            if flag & 8 and kind_bone in W:          # on a weapon bone: into the holding hand's frame
                M = W[kind_bone]
                shp.append(mshit.capsule(joint, rad, (M @ pa)[:3], (M @ pb)[:3]))
                for q in (pa, pb):                   # the blade tip (msfx arcs): the end farthest from the hand
                    d = np.linalg.norm((M @ q)[:3])
                    if not tip or d > tip[2]: tip = (kind_bone, q[:3], d)
            else:                                    # around the hunter: the root (a shock spot: moved there)
                off = np.array([SHOCK[key[1]][0], 0.0, SHOCK[key[1]][1]]) if key[0] == 'shock' else 0.0
                shp.append(mshit.capsule(255, rad, pa[:3] + off, pb[:3] + off))
        sets.append(shp)
        swings.append(dict(mot=mot, frame=frame, dur=dur, cut=cut, special=special, tip=tip and tip[:2]))
        e = mshit.hdp_entry(tmpl_cut if cut else tmpl_imp, r['mv'], dur, mshit.CUT if cut else mshit.IMPACT,
                            len(sets) - 1, None if cut else r['ko'])
        index[key] = len(entries)
        entries.append(e)
        report.append('hit %3d: %s MHF %s %2d MV %3d KO %5.1f %-6s live %2d f, joint %3d, %d shapes' % (
            len(entries) - 1, where, 'special' if special else 'attack', aid, r['mv'], r['ko'],
            'cut' if cut else 'impact', dur, joint, len(shp)))
    # Magnetise (MHF 0x1033c5d0: an attack or special spawned while this mode is magnetised deals MV x (100 + prm61)
    # / 100): entry k's magnetised copy is k + MS_MAG_BASE
    base = len(entries) - 1
    for e in entries[1:]:
        m = list(e)
        mv = e[26] * (100 + MAGNETISE_PCT) // 100
        m[4], m[26] = min(mv, 250), mv
        entries.append(m)
    index['mag_base'] = base
    return mshit.hdp_bytes(entries), mshit.hts_bytes(sets), index, report, swings


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
    """GU command paths for one MHF cancel of action a (empty = an action with no Magnet Spike data)"""
    nxt, inp, cond = c['next'], c['input'], c['cond']
    if inp == 0 or nxt in (202, 203):                    # roll (shared 202 / 203): GU's common evades
        return [C.com('plcmd_com_0x0001_013a'), C.com('plcmd_com_0x0001_014a')]
    if inp == 1:                                         # stick: GU's common drawn move
        return [C.com('plcmd_com_0x0001_006e')]
    if nxt not in ACTIONS and nxt not in SHARED: return []
    if inp == 20 and cond == 0: return [C.ours_cmd(nxt, 0, 0)]       # always
    k = pair_id(inp, cond) + MS_ID_IMPACT * mode
    return [C.ours_cmd(nxt, 0xc if inp in STICK_INPUTS else 8, k)]


def idle_commands(C, window):
    """the Magnet Spike's drawn-idle inputs (msact.IDLE), both modes (mode-specific ids), in one window: aiming
    first, then the R1 combos, then the plain inputs. The stick (input 1, GU's common move) is left to the table's
    own move command after ours (test 1 had it before the plain inputs: no attack while walking)"""
    out = []
    for inp, (ca, ia) in sorted(msact.IDLE.items(), key=lambda x: (x[0] not in (19, 23, 24), x[0] < 7, x[0])):
        if inp == 1: continue
        for mode, act in ((0, ca), (1, ia)):
            if act not in ACTIONS: continue
            fake = dict(next=act, input=inp, cond=IDLE_COND.get(inp, 0))
            out += [cmd_obj(p, *window) for p in cancel_commands(C, None, fake, mode)]
    return out


# GU's jumps (common 1/4, 1/5, 1/137, 1/140: tables 18 / 19) take GS's jump attack: tri = MHF's falling attacks,
# 59 Cutting / 73 Impact (the attraction flight's tri, 58 -> 59 / 68 -> 73), which run airborne until they land
FALLING = (59, 73)
JUMP_TABLES = (18, 19)


def weapon_commands(C, k, window):
    """the Magnet Spike's commands for a GU common-action table k that had GS's weapon commands (in their place, with
    their window): 18 / 19 jumps = the falling attacks, else the drawn-idle inputs (0 drawn idle, 10, 11 drawn move,
    12 / 13 rolls)"""
    if k in JUMP_TABLES:
        return [cmd_obj(p, *window) for mode, act in enumerate(FALLING) if act in ACTIONS
                for p in cancel_commands(C, None, dict(next=act, input=2, cond=0), mode)]
    return idle_commands(C, window)


def build_commands(acts, gs_m0):
    """-> (command files {path: bytes}, table list bytes, {(action, step): table index}, report)"""
    C = Commands(gs_m0)
    gst = gs_tables(gs_m0)
    tables, report = [], []
    # 0 = drawn idle, 10-46 = GS's common-action tables (the table pickers ms_class.c keep GS's indexes), GS's weapon
    # commands replaced by ours at their place: before GU's move / Hunter Arts commands (GU takes the first ready
    # command: test 1's idle table had them after, so attacks never started while the stick was tilted); 1-9 = GS's
    # attack tables have no Magnet Spike counterpart (empty)
    def common_table(k):
        out, done = [], False
        for c in gst[k]:
            name = c['CmdBase'][1].split('\\')[-1]
            window = [struct.unpack('<f', struct.pack('<I', c[f]))[0] for f in ('PreFrame', 'StartFrame', 'EndFrame')]
            if name.startswith('plcmd_w00'):
                if not done: out += weapon_commands(C, k, window)
                done = True
                continue
            out.append(cmd_obj(C.com(name), *window))
        if done:
            report.append('table %3d: GU common: %s' % (k, ', '.join(
                o['CmdBase'][1].split('\\')[-1].replace('plcmd_', '') for o in out)))
        return out
    tables.append(common_table(0))
    tables += [[] for _ in range(9)]
    tables += [common_table(k) for k in range(10, len(gst))]
    # one table per (action, step), the cancels in priority order (GU takes the first ready command; GU's move last
    # among equals: test 1's X + A after the Guard Counter lost to a tilted stick)
    index = {}
    for a in ACTIONS:
        cs = sorted(acts[a]['cancels'], key=lambda c: (-c['pri'], c['input'] == 1))
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

def c_tables(acts, modes, own, tbl_index, hit_index, mvs):
    """gen/ms_data.inc: every action's steps and events (MHF event ids; attacks / specials = their hit-data index,
    the MHF param in prm), the class-id pairs and each hit entry's motion value (the gauge gain on hit) for ms_act.c"""
    L = ['/* ms_data.inc: generated by weapons/magnet_spike/tools/msbuild.py from MHF\'s mhfdat / mhfsdt (game data,',
         ' * gitignored) -- do not edit. MHF action numbers; motion = bank-5 slot of player\\\\mot\\\\w05\\\\w05. */',
         '#define MS_ID_IMPACT %d' % MS_ID_IMPACT, '#define MS_RELEASE %d' % RELEASE, '#define MS_GC_HIT %d' % GC_HIT,
         '#define MS_NPAIRS %d' % len(PAIRS), 'static const struct ms_pair ms_pairs[] = {']
    L += ['    {%d, %d},  /* id %d: %s if %s */' % (i, c, k, msact.INPUTS[i], msact.CONDS[c] if c < 14 else c)
          for (i, c), k in sorted(PAIRS.items(), key=lambda x: x[1])] + ['};']
    L.append('#define MS_MAG_BASE %d  /* hit k magnetised = k + MS_MAG_BASE */' % hit_index['mag_base'])
    L += ['#define MS_HIT_SPECIAL_%d %d' % (n, hit_index[('code', n)]) for n in sorted(CODE_SPECIALS)
          if ('code', n) in hit_index]
    L += ['#define MS_NSHOCK %d' % len(SHOCK),
          '#define MS_HIT_SHOCK %d  /* + k: Magnetic Shock 5 x 3 spot k (SHOCK) */' % hit_index[('shock', 0)],
          '#define MS_EFX_SHOCK %d  /* + k: its effect (msfx.SHOCK_TEMPLATE moved to spot k) */' % msfx.SHOCK_EFX,
          '#define MS_EFX_MARKER %d  /* msfx.MARKER_EFX */' % msfx.MARKER_EFX[0],
          '#define MS_EFX_AURA %d  /* msfx.AURA_EFX */' % msfx.AURA_EFX[0]]
    L += ['#define MS_NHITS %d' % len(mvs), 'static const uint16_t ms_hit_mv[] = {'] + [
        '    %s,' % ', '.join(str(v) for v in mvs[i:i + 20]) for i in range(0, len(mvs), 20)] + ['};']
    steps, events, rows = [], [], []
    for a in ACTIONS:
        s0, e0 = len(steps), len(events)
        for k, (kind, mot, start, blend, frame, loops) in enumerate(acts[a]['steps']):
            slot = own.get(mot, 0xffff) if kind in (3, 4, 5) else mot
            steps.append('    {%d, %d, %d, %d, %d, %d, %d},  /* %d: MHF motion %d */' % (
                kind, slot, start, blend, frame, loops, 2000 + tbl_index[(a, k)], a, mot))
        for k, (step, kind, cond, frame, loop, eid, prm) in enumerate(acts[a]['events']):
            when = 0 if kind == 1 else 2 if kind == 2 else 3 if cond >= 1 else 1
            hit = hit_index.get((a, k), 0)
            events.append('    {%d, %d, %d, %d, %d, %d, %d, %d},  /* %d: %s */' % (
                step, when, frame, loop, max(cond, 0), eid, prm, hit, a, msact.EVENTS.get(eid, eid)))
        rows.append('    {%d, %d, %d, %d, %d, %d},' % (a, mode_of(a), len(steps) - s0, s0, len(events) - e0, e0))
    L += ['static const struct ms_step ms_steps[] = {'] + steps + ['};']
    L += ['static const struct ms_event ms_events[] = {'] + events + ['};']
    L += ['static const struct ms_action ms_actions[] = {'] + rows + ['};']
    L.append('#define MS_IDLE_TABLE 2000')
    return '\n'.join(L) + '\n'


# ------------------------------------------------------------------------------------------------ arcs

# class-5 model number -> MHF weapon model: GU's file table names weapon\w05\mbg001..mbg007 (ids 21815-21821, MH3's
# class-5 files; C: their path hashes). 1 = the Phase 2 test weapon, 2-7 = the smithy's (msweapons.py)
MODELS = {1: 'wk400', 2: 'wk595', 3: 'wk606', 4: 'wk414', 5: 'wk415', 6: 'wk404', 7: 'wk407'}


def model_arc(n):
    """MODELS[n] as weapon\\w05\\mbgNNN\\mbgNNN in a copy of GS 001's arc (its MRL with the texture paths renamed)"""
    old, new = 'weapon\\w00\\two001\\two001', 'weapon\\w05\\mbg%03d\\mbg%03d' % (n, n)
    assert len(old) == len(new)
    ver, ents = arcpack.read(rom().read('/nativeNX/arc/weapon/w00/001.arc'))
    tmp = os.path.join(OUT_GEN, 'w00_001.arc')
    open(tmp, 'wb').write(arcpack.build(ents))
    fixed = os.path.join(OUT_GEN, 'w05_%03d_tmp.arc' % n)
    fmod2gu.build_arc(os.path.join(MHF, 'weapon', MODELS[n]), tmp, fixed)
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
    ACTIONS[:] = [a for a, r in enumerate(acts) if r['steps'] and all(
        k in (0, 1, 2) or m // 1000 == 1 for k, m, *_ in r['steps'])]
    w00 = gu_arc('player/quest/w00.arc')
    w02 = gu_arc('player/quest/w02.arc')
    gs_m0 = gu_arc('player/quest/w00_m0.arc')
    gs_m = gu_arc('player/quest/w00_m.arc')
    plan, own = slot_plan(acts)
    body, wlist, mreport, holders, wdata = build_motions(plan, w00['player\\mot\\w00\\w00'][1])
    msmot.check(body); msmot.check(wlist)
    hdp, hts, hit_index, hreport, swings = build_hits(acts, sdt_d, w00['player\\hit\\pl_we00_hitdata'][1],
                                                      w02['player\\hit\\pl_we02_hitdata'][1], own, holders, wdata)
    cmds, tbl, tbl_index, creport = build_commands(acts, gs_m0)
    freport = []
    arcs, posts, snd_drop, sounds = msfx.build(swings, wdata, holders, own, GU_COPY, COMMON, freport)
    arcs += [(msfx.SHOCK_EFX + k, (x, 0.0, z), (0.0, 0.0, 0.0), 1.0, msfx.SHOCK_TEMPLATE)
             for k, (x, z) in enumerate(SHOCK)] + [msfx.MARKER_EFX, msfx.AURA_EFX]
    rep = mreport + hreport + creport + freport
    open(os.path.join(OUT_GEN, 'report.txt'), 'w').write('\n'.join(rep) + '\n')
    if report_only:
        print('\n'.join(rep)); return
    mvs = [e[26] for e in mshit.hdp_parse(hdp)]
    open(os.path.join(OUT_GEN, 'ms_data.inc'), 'w').write(c_tables(acts, modes, own, tbl_index, hit_index, mvs))
    # GS's effect and sound lists (per-motion effects / sounds, the class's effect files and sound banks) under the
    # class-5 names GU's file-ID table holds: GS's entries on GS's motion slots (our common slots), our action slots
    # get msfx's swing arcs and swing sounds
    rename = {'effect\\psl\\player\\mot\\w00\\w00': 'effect\\psl\\player\\mot\\w05\\w05',
              'effect\\psl\\player\\mot\\w00\\w00_sa': 'effect\\psl\\player\\mot\\w05\\w05_sa',
              'effect\\pel\\pl\\w00_000': 'effect\\pel\\pl\\w05_000', 'effect\\pel\\pl\\w00_800': 'effect\\pel\\pl\\w05_800',
              'sound\\pts\\pl\\w00_000': 'sound\\pts\\pl\\w05_000', 'sound\\pts\\pl\\w00_800': 'sound\\pts\\pl\\w05_800',
              'sound\\call\\pl\\pl_wp00': 'sound\\call\\pl\\pl_wp05'}
    fx = [(rename.get(p, p), t, b) for p, t, b in gu_entries('player/quest/w00.arc')
          if t not in (T_LMT, T_PARAM, T_HDP, T_HTS)]
    # the psl ('PSL', u16 version, u16 count, count x u32 offset per motion slot): no GS effect on the slots our
    # actions took from GS's own range (free_slots), our arcs instead
    for i, (p, t, b) in enumerate(fx):
        if p == 'effect\\psl\\player\\mot\\w05\\w05':
            b = bytearray(b)
            for s in own.values(): struct.pack_into('<I', b, 8 + 4 * s, 0)
            fx[i] = (p, t, msfx.psl_add(bytes(b), posts))
        elif p == 'effect\\pel\\pl\\w05_000':
            fx[i] = (p, t, msfx.pel_add(b, arcs))
        elif p == 'sound\\call\\pl\\pl_wp05':
            fx[i] = (p, t, msfx.mss_rebuild(b, snd_drop, sounds))
    # GS's weapon sound requests and banks (ms_snd_file answers GS's file IDs for class 5: two001, two_bcom), loaded
    # with the class; its Hunter Arts bank (two_arts) left out
    fx += [(p, t, b) for n in ('001', 'mat_b') for p, t, b in gu_entries('weapon/w00/snd/%s.arc' % n)
           if '_arts' not in p]
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
    for n in sorted(MODELS):
        write('weapon/w05/%03d.arc' % n, model_arc(n))
    for name in ('001', 'mat_b', 'mat_i'):                # GS's weapon sound arcs (sounds phase: MHF's)
        write('weapon/w05/snd/%s.arc' % name, rom().read('/nativeNX/arc/weapon/w00/snd/%s.arc' % name))
    write('weapon/w05/g00.arc', arcpack.build([('weapon\\w05\\mot\\wg05_00', T_LMT, wlist),
                                               ('weapon\\w05\\mot\\wg05_sa_00', T_LMT, empty_list())]))
    print('HUD: ' + mshud.build())                      # the gauge's look (ms_class.c hud_look)
    print('motions: %d body slots (%d KB), weapon list %d KB; %d hits; %d tables, %d command files' % (
        len(plan), len(body) // 1024, len(wlist) // 1024, len(hit_index), len(tbl_index) + 47, len(cmds)))
    print('report: %s' % os.path.join(OUT_GEN, 'report.txt'))


if __name__ == '__main__':
    main(sys.argv[1:] == ['report'])
