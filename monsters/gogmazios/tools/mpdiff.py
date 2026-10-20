#!/usr/bin/env python3
"""mpdiff.py : compare the Ryujinx logs of two machines that hunted Gogmazios together (multiplayer check).

usage: python3 tools/mpdiff.py LOG_A LOG_B

Each machine logs every em089 action start (em089_act.c log_action):
  action C/N (how) ... pos X,Z ... slot0 K/S/P tgt T local L ctl 0|1 serial S yaw Y
The controller (ctl 1, normally the room host) runs the AI and sends each action with its serial; the other machine
replays it with the same serial (setAction modes 3 / 4 keep it). Action ends (slot 247 -> category 0) are local on
every machine and get a local serial, so only non-idle actions are matched, by serial.

Reports: who controlled the monster, net send / receive counts, the matched actions with differing (cat, num),
target hunter (tgt) or slot 0, the position / yaw gap at action start, actions seen by one machine only, and the
gimmick events (cannon fire, cart legs, doors, Dragonator) on each side.
"""
import math, re, sys

ACT = re.compile(r'em089 \w+ action (\d+)/(\d+) \((\w+)\).* pos (-?\d+),(-?\d+) .*slot0 (\d+)/(\d+)/(\d+) tgt (\d+) '
                 r'local (-?\d+) ctl (\d) serial (\d+) yaw ([0-9a-f]+)')
GIMMICK = re.compile(r'stage cannon \d: FIRE|stage cart: lever|stage cart: arrived|stage doors: boss HP|'
                     r'Dragonator fired|stage cannon \d: switch pressed')


def load(path):
    acts, sends, recvs, gim, hunters = [], 0, 0, [], None
    for l in open(path, errors='replace'):
        if 'gogport: ' not in l:
            continue
        ts, m = l[:12], l.split('gogport: ', 1)[1].strip()
        a = ACT.search(m)
        if a:
            c, n, how, x, z, k, s, p, tgt, loc, ctl, ser, yaw = a.groups()
            acts.append(dict(ts=ts, cat=int(c), num=int(n), how=how, x=int(x), z=int(z), slot0=(int(k), int(s), int(p)),
                             tgt=int(tgt), local=int(loc), ctl=int(ctl), serial=int(ser), yaw=int(yaw, 16)))
        elif 'em089 net send' in m:
            sends += 1
        elif 'em089 net receive' in m:
            recvs += 1
        elif m.startswith('em089 hunters'):
            hunters = m
        elif GIMMICK.search(m):
            gim.append((ts, m))
    return dict(path=path, acts=acts, sends=sends, recvs=recvs, gim=gim, hunters=hunters)


def yaw_gap(a, b):
    d = abs(a - b) & 0xffff
    return min(d, 0x10000 - d) * 360.0 / 65536.0


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    A, B = load(sys.argv[1]), load(sys.argv[2])
    for tag, L in (('A', A), ('B', B)):
        ctl = sorted({a['ctl'] for a in L['acts']})
        loc = sorted({a['local'] for a in L['acts']})
        print('%s %s\n   %d actions, controller flag %s, local hunter index %s, net send %d / receive %d%s'
              % (tag, L['path'], len(L['acts']), ctl, loc, L['sends'], L['recvs'],
                 '\n   ' + L['hunters'] if L['hunters'] else ''))
    key = lambda L: {a['serial']: a for a in L['acts'] if a['cat'] != 0}
    ka, kb = key(A), key(B)
    both = sorted(set(ka) & set(kb), key=lambda s: ka[s]['ts'])
    print('\nmatched by serial: %d (A only %d, B only %d)' % (len(both), len(set(ka) - set(kb)), len(set(kb) - set(ka))))
    bad, gaps = 0, []
    for s in both:
        a, b = ka[s], kb[s]
        d = math.hypot(a['x'] - b['x'], a['z'] - b['z'])
        gaps.append(d)
        diffs = [f for f in ('cat', 'num', 'tgt', 'slot0') if a[f] != b[f]]
        if diffs or d > 300 or yaw_gap(a['yaw'], b['yaw']) > 20:
            bad += 1
            if bad <= 40:
                print('  serial %5d  A %s %d/%d tgt %d slot0 %s  B %s %d/%d tgt %d slot0 %s  pos gap %.0f yaw gap %.0f'
                      % (s, a['ts'], a['cat'], a['num'], a['tgt'], a['slot0'], b['ts'], b['cat'], b['num'], b['tgt'],
                         b['slot0'], d, yaw_gap(a['yaw'], b['yaw'])))
    if gaps:
        gaps.sort()
        print('position gap at action start: median %.0f, 90th %.0f, max %.0f (units; the hunter is ~170 tall)'
              % (gaps[len(gaps) // 2], gaps[int(len(gaps) * 0.9)], gaps[-1]))
    print('mismatched / far apart: %d of %d' % (bad, len(both)))
    for tag, L, K, O in (('A', A, ka, kb), ('B', B, kb, ka)):
        only = [K[s] for s in sorted(set(K) - set(O), key=lambda s: K[s]['ts'])]
        if only:
            print('%s only (first 10): %s' % (tag, ', '.join('%s %d/%d #%d' % (a['ts'], a['cat'], a['num'], a['serial'])
                                                         for a in only[:10])))
    for tag, L in (('A', A), ('B', B)):
        print('\n%s gimmick events:' % tag)
        for ts, m in L['gim'][:30]:
            print('  %s %s' % (ts, m[:110]))


if __name__ == '__main__':
    main()
