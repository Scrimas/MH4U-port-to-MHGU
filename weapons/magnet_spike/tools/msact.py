"""MHF Magnet Spike moveset from the decoded mhfdat.bin (+ attack values from the decoded mhfsdt.bin, tools/sdt.py).
Read by the shared action engine of mhfo-hd.dll (2019-09-02 ZZ): header u32 0x614 -> 14 x {i32 count, u32 records} per
weapon type (Magnet Spike = 13); action record 24 B {u32 nSteps, steps*, u32 nCancels, cancels*, u32 nEvents, events*}.

time spec (8 B, used by cancels and events; checks 0x10a68090 / 0x10a68510): u16 step, u8 kind (1 = when the step
  starts, 2 = never, else at a frame), i8 cond (>= 1: compared with player +0x208 instead of the frame), u16 frame,
  u16 loop (the step's loop counter, player +0xf98)
step (12 B, 0x10a67790): u16 kind, u16 motion, u16 start frame, u16 blend, u16 frame, u16 loops. kind 3 = play the
  motion and wait for `loops` loops; 4 = play it until `frame` of loop `loops`; 5 = hold; 0 / 1 = go to another action
  (0x10a81af0 / 0x10a81c20 with (blend, action) as seen); 2 = weapon callback. After the last step the action ends
  (back to idle) unless an event set player +0x410 = 2. Motion = bank * 1000 + part * 100 + slot (bank 1 = w13.mot).
cancel (40 B, 0x10a68110): u16 priority, u16 condition (0..13 -> MS table 0x11926c5c), u16 input (0..24 -> MS table
  0x11926bf8), time spec "buffer open", time spec "buffer close", u16 next action, time spec "go open", time spec "go
  close". An input pressed while the buffer window is open (and the condition holds) is kept; the action changes while
  the go window is open. A higher priority beats a lower one already kept.
event (12 B): time spec + u16 event id (-> MS handler table 0x11926b40) + u16 param.
usage: python3 -I msact.py MHFDAT.dec.bin MHFSDT.dec.bin [ACTION ...]"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdt

# input checks (0x11926bf8), button names from MHF's key config (categories 13-14 "Magnet Spike 1/2"; R-stick and
# "special analog" alternatives left out); "aim:" = only while aiming (L2 held, MS flags bit 0), when they also mask
# every other input
INPUTS = ['roll (x)', 'stick', 'tri', 'circle', 'tri+circle', 'transform (SELECT)', 'stick+circle', 'R1+tri',
          'R1+circle', 'R1+tri+circle', 'R1+special(A)', 'R1+SELECT', 'never', 'guard counter (R2)', 'circle held',
          'circle released', 'R1', 'R1+evade(x)', 'never', 'aim: circle', 'always', 'tri released', 'stick+tri',
          'aim: special(A)', 'aim: tri']
# cancel conditions (0x11926c5c); "gauge N" = at least N bars of the magnet gauge (1 bar = param 19 = 2000)
CONDS = ['always', 'gauge 1', 'gauge 2', 'gauge 3', 'gauge 4', 'gauge 5', 'MS flag 0x8', 'not 0x101bc9d0',
         '0x1032b4f0', 'fall height', 'gauge 1 + attract ok', 'gauge 1 + repel ok', 'MS flag 0x20000', 'mode check']
# frame events (0x11926b40)
EVENTS = {1: 'guard/flags', 2: 'set +0x12', 3: 'ATTACK', 4: 'SPECIAL ATTACK', 5: '+0x4f0 max', 6: 'ext+0x280=1',
          7: '+0x4ee max', 8: '+0x4ee max(fn)', 9: 'ext+0x284=1', 10: '+0x4ee=', 11: 'evade (stamina)', 12: 'shake',
          13: 'speed %', 14: 'turn to stick', 15: 'effect 0x43c', 16: 'local 0x10337fe0', 17: 'task 0x3c',
          18: 'magnet 0x1033c080 / idle', 19: 'magnet 0x1033c080', 20: 'magnet 0x1033bec0', 21: 'armor flag',
          22: 'MS flag 0x2', 23: 'MS flag 0x4', 24: 'MS +0x6a', 25: 'MS +0x67', 26: 'MS flag 0x20', 27: 'MS +0x6b',
          28: 'MS +0x6c', 29: 'MS +0x6d lo', 30: 'MS +0x6d hi', 31: 'MS flag 0x80 + f', 32: 'MS flag 0x80 off',
          33: 'MS +0x78', 34: 'MS flag 0x400', 35: 'MS flag 0x800', 36: 'MS vec reset', 37: 'MS lo reset',
          38: 'MS hi reset', 39: 'turn to target', 40: 'mode flag 0x8000', 41: 'local 0x109a9fa0',
          42: 'SPECIAL ATTACK 42', 43: 'SPECIAL ATTACK 43', 44: 'SPECIAL ATTACK 44', 45: 'gauge/stamina cost'}
# drawn idle (0x1032d2d0): input -> (Cutting action, Impact action); input 0 is the shared roll (group 0 action 28)
IDLE = {19: (82, 84), 24: (58, 68), 23: (66, 67), 7: (11, 39), 8: (108, 117), 9: (12, 38), 10: (106, 158),
        11: (163, 164), 17: (107, 116), 13: (14, 112), 1: (40, 44), 6: (6, 23), 4: (2, 26), 2: (0, 18), 3: (6, 32),
        5: (90, 91)}
# sheathed (0x1032d110, 0x1032d210): input -> action (group 1); tri from standing = group 0 action 4
SHEATHED = {2: 'tri: group 0 action 4 (standing) / 78 (moving)', 4: 'tri+circle: 79', 9: 'R1+tri+circle: 112',
            22: 'stick+tri: 78'}


def tspec(t):
    step, kind, cond, frame, loop = t
    if kind == 1: return 's%d start' % step
    if kind == 2: return 'never'
    if cond >= 1: return 's%d lvl>=%d' % (step, cond)
    return 's%d f%d%s' % (step, frame, ' L%d' % loop if loop else '')


def actions(d, weapon=13):
    t = struct.unpack_from('<I', d, 0x614)[0]
    n, p = struct.unpack_from('<iI', d, t + 8 * weapon)
    out = []
    for a in range(n):
        ns, ps, nc, pc, ne, pe = struct.unpack_from('<6I', d, p + 24 * a)
        steps = [struct.unpack_from('<6H', d, ps + 12 * k) for k in range(ns)]
        cancels = []
        for k in range(nc):
            o = pc + 40 * k
            pri, cond, inp = struct.unpack_from('<3H', d, o)
            ts = [struct.unpack_from('<HBbHH', d, o + x) for x in (6, 14, 24, 32)]
            nxt = struct.unpack_from('<H', d, o + 22)[0]
            cancels.append(dict(pri=pri, cond=cond, input=inp, buf=ts[:2], go=ts[2:], next=nxt))
        events = [struct.unpack_from('<HBbHHHH', d, pe + 12 * k) for k in range(ne)]
        out.append(dict(steps=steps, cancels=cancels, events=events))
    return out


def modes(d):
    """MS block (mhfdat header u32 0xb90): action -> 'C' / 'I' / 'C+I'"""
    b = struct.unpack_from('<I', d, 0xb90)[0]; m = {}
    for cnt, ptr, tag in ((2, 0x18, 'C'), (4, 0x1c, 'I'), (6, 0x20, 'C+I')):
        n = struct.unpack_from('<h', d, b + cnt)[0]; p = struct.unpack_from('<I', d, b + ptr)[0]
        for a in struct.unpack_from('<%dH' % n, d, p): m[a] = tag
    return m


def show(a, i, mode, atk, spc):
    lines = ['action %3d  [%s]' % (i, mode.get(i, '-'))]
    for s in a['steps']:
        lines.append('  step kind %d motion %4d  start f%d blend %d frame %d loops %d' % s)
    for e in a['events']:
        step, kind, cond, frame, loop, eid, prm = e
        x = ''
        if eid == 3 and prm < len(atk): x = '  = MV %d KO %g %s' % (atk[prm]['mv'], atk[prm]['ko'], {0x20a: 'cut', 0x10a: 'impact'}.get(atk[prm]['type'], ''))
        if eid in (4, 42, 43, 44) and prm < len(spc): x = '  = special MV %d' % spc[prm]['mv']
        lines.append('  event %-13s %-20s param %d%s' % (tspec((step, kind, cond, frame, loop)), EVENTS.get(eid, eid), prm, x))
    for c in a['cancels']:
        lines.append('  cancel %-22s if %-20s buffer %s..%s  go %s..%s -> %d  (pri %d)' % (
            INPUTS[c['input']] if c['input'] < 25 else c['input'], CONDS[c['cond']] if c['cond'] < 14 else c['cond'],
            tspec(c['buf'][0]), tspec(c['buf'][1]), tspec(c['go'][0]), tspec(c['go'][1]), c['next'], c['pri']))
    return '\n'.join(lines)


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read(); s = open(sys.argv[2], 'rb').read()
    es = sdt.entries(s)
    atk = sdt.attacks(s, next(e for e in es if e['kind'] == 0x78))
    spc = sdt.attacks(s, next(e for e in es if e['kind'] == 0x79))
    acts = actions(d); mode = modes(d)
    sel = [int(x) for x in sys.argv[3:]] or range(len(acts))
    for i in sel: print(show(acts[i], i, mode, atk, spc))
