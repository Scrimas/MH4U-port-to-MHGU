#!/usr/bin/env python3
"""gogreport.py : summarize a Ryujinx log of a Gogmazios test session, so the tester only has to play and close.

usage: python3 monsters/gogmazios/tools/gogreport.py [LOG]      (default: newest log in ~/.config/Ryujinx/Logs)

Reports: crash / errors, quest + spawn, action coverage against the handler table of module/em089_act.c
(s_ported), state / mode / HP timeline, tar timeline (part modes, visibility words), stubs and unmapped conditions.
"""
import collections, glob, os, re, sys

MON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # monsters/gogmazios
LOGS = os.path.expanduser('~/.config/Ryujinx/Logs/*.log')
TAR_PARTS = {0: 'head', 7: 'chest', 2: 'left arm', 3: 'right arm', 6: 'tail'}   # 4U part numbers in the log
MODES = {0: 'Solid', 1: 'Liquid', 2: 'Gas'}
NOISE = ('TamperMachine', 'FFmpeg', 'AudioRenderer', 'NvdecProcessor')


def handler_table():
    src = open(os.path.join(MON, 'module', 'em089_act.c')).read()
    body = src[src.index('s_ported[] = {'):]
    body = body[:body.index('};')]
    return sorted({(int(c), int(n)) for c, n in re.findall(r'\{\s*(\d+),\s*(\d+),\s*\d+,\s*act_\w+\}', body)})


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(LOGS), key=os.path.getmtime)
    lines = open(path, errors='replace').read().splitlines()
    gog = [(l[:12], re.split(r'(?:gog|mh4u)port: ', l, maxsplit=1)[1]) for l in lines
           if re.search(r'(?:gog|mh4u)port: ', l)]
    print('log:', path)
    end = lines[-1][:12] if lines else '?'

    crash = [l for l in lines if 'Unhandled exception' in l or 'InvalidAccessHandler' in l]
    errors = collections.Counter(re.sub(r'0x[0-9a-f]+', 'X', l[13:].strip())[:120]
                                 for l in lines if '|E|' in l and not any(n in l for n in NOISE))
    print('session end %s | crash: %s' % (end, 'YES ' + crash[0][:120] if crash else 'no'))
    for e, n in errors.most_common(5):
        print('  error x%d: %s' % (n, e))

    t = lambda pat: [(ts, m) for ts, m in gog if re.search(pat, m)]
    prep = t(r'quest_prep quest')
    spawn = t(r'uEm089_00 new_instance')
    print('quest: %s | spawned: %d' % (prep[0][1] if prep else 'no quest_prep line', len(spawn)))

    acts = [re.search(r'action (\d+)/(\d+) \((\w+)', m) for ts, m in gog]
    seen = collections.Counter((int(a.group(1)), int(a.group(2))) for a in acts if a)
    table = handler_table()
    print('\nactions: %d starts, %d distinct of %d handlers (%.0f %%)' % (
        sum(seen.values()), len([k for k in seen if k in table]), len(table),
        100.0 * len([k for k in seen if k in table]) / max(1, len(table))))
    print('  most frequent:', ', '.join('%d/%d x%d' % (c, n, k) for (c, n), k in seen.most_common(12)))
    missing = collections.defaultdict(list)
    for c, n in table:
        if (c, n) not in seen:
            missing[c].append(n)
    for c in sorted(missing):
        print('  never seen, cat %d: %s' % (c, ' '.join(map(str, missing[c]))))
    other = [k for k in seen if k not in table]
    if other:
        print('  outside the table (engine / reactions):', ', '.join('%d/%d x%d' % (c, n, seen[(c, n)]) for c, n in other))

    print('\nstate / mode / HP:')
    for ts, m in t(r'em089 (state \d+ mode|hp \d+%|test HP|data set)'):
        print('  %s %s' % (ts, m.replace('em089 ', '')))

    print('\nrage / phase 2 / wing / lights:')
    for ts, m in t(r'em089 (phase|rage|test rage|wing|light|remap)')[:40]:
        print('  %s %s' % (ts, m.replace('em089 ', '')))
    for name, pat in (('camera shakes', r'em089 camera shake'), ('attack windows shortened', r'em089 attack slot \d+ shortened'),
                      ('2/15 think lists', r'em089 2/15 end')):
        print('  %s: %d' % (name, len(t(pat))))

    print('\ndamage (attack arms, first 120):')
    atk = [re.search(r'active (\d+) power (\d+) rate (-?\d+)/100', m) for ts, m in t(r'em089 attack slot \d+ index \d+ active')]
    atk = [a for a in atk if a]
    print('  %d arms, %d inactive, rate x100: %s' % (len(atk), sum(a.group(1) == '0' for a in atk),
                                                     ' '.join(sorted({a.group(3) for a in atk})) or '-'))
    print('  power:', ', '.join('%s x%d' % kv for kv in collections.Counter(a.group(2) for a in atk).most_common(10)) or 'none')
    print('  not enabled: %d' % len(t(r'em089 attack slot \d+ index \d+ param')))

    print('\nheight / arena:')
    for ts, m in t(r'em089 (height (up|down)|arena point|cond 8 |quake: monster too high|efx ground impact|'
                   r'7/47 wall turn|1/24 start)')[:40]:
        print('  %s %s' % (ts, m.replace('em089 ', '')))

    print('\nshell ends (reason, digits cut):')
    for name, pat in (('ground', r'em089 ground shell \d+ \(sub (\d+)\) end: (.*)'),
                      ('attack', r'em089 attack shell \d+ \(sub (\d+)\) end: (.*)'),
                      ('quake', r'em089 quake shell \d+ end: ()(.*)')):
        ends = [re.search(pat, m) for ts, m in gog]
        c = collections.Counter('%s %s' % (e.group(1), re.sub(r'\s*-?\d.*', '', e.group(2))) for e in ends if e)
        print('  %s: %s' % (name, ', '.join('sub %s x%d' % kv for kv in sorted(c.items())) or 'none'))

    print('\nmisc:')
    for ts, m in t(r'(em089 tail break|area map record|whole map record|em089 efx shell016|em089 attack shell \d+ spawn|'
                   r'em089 efx beam|effect scale x1000|em089 react|em089 shell posts|stage gimmicks|'
                   r'stage dragonator: (fire|camera))')[:40]:
        print('  %s %s' % (ts, m.replace('em089 ', '')))

    print('\ntar:')
    for ts, m in t(r'em089 tar (part|word|spawn)'):
        mm = re.search(r'tar part (\d+) -> mode (\d+) \(amount (-?\d+)', m)
        if mm:
            k, md = int(mm.group(1)), int(mm.group(2))
            print('  %s %s -> %s (amount %s)' % (ts, TAR_PARTS.get(k, k), MODES.get(md, md), mm.group(3)))
        else:
            print('  %s %s' % (ts, m.replace('em089 ', '')))

    print('\nbreaks:')
    for ts, m in t(r'em089 (break records|break state|part \d+ \(.*(flinch|sever)|tail severed)'):
        print('  %s %s' % (ts, m.replace('em089 ', '')))

    print('\nshells:')
    shells = t(r'em089 shell')
    kinds = collections.Counter(re.search(r'spawn kind (\d+)', m).group(1) for ts, m in shells if 'spawn kind' in m)
    print('  spawns by kind:', ', '.join('%s x%d' % kv for kv in sorted(kinds.items())) or 'none')
    print('  impacts %d, timeouts %d' % (sum('impact' in m for ts, m in shells), sum('timed out' in m for ts, m in shells)))
    for m, n in collections.Counter(m for ts, m in shells if re.search(r'dropped|failed|no hit data', m)).most_common(5):
        print('  x%d %s' % (n, m.replace('em089 ', '')))

    print('\naim:')
    aim = t(r'em089 aim')
    print('  %d lines;' % len(aim), ', '.join('%s x%d' % kv for kv in collections.Counter(
        m.split()[2] for ts, m in aim).items()) or 'none')
    for ts, m in aim[:6]:
        print('  %s %s' % (ts, m.replace('em089 ', '')))

    print('\nsound / BGM:')
    for ts, m in t(r'em089 bgm (theme|stqr)')[:8]:
        print('  %s %s' % (ts, m.replace('em089 ', '')))
    plays = t(r'bgm play ')
    print('  play requests: %d;' % len(plays), ', '.join('slot %s id %s x%d' % (k[0], k[1], n) for k, n in collections.Counter(
        re.search(r'slot (\d+) id (\w+)', m).groups() for ts, m in plays).most_common(10)) or 'none')
    print('  code SE:', ', '.join('%s x%d' % kv for kv in collections.Counter(
        re.sub(r' \(.*', '', m.split('snd ', 1)[1]) for ts, m in t(r'em089 snd ')).most_common(8)) or 'none')

    print('\nstubs / unmapped:')
    for m, n in collections.Counter(re.sub(r'\(.*', '', m) for ts, m in t(r'em089 (stub|cond \d+ \(|run .* safety)')).most_common(15):
        print('  x%d %s' % (n, m.replace('em089 ', '')))


if __name__ == '__main__':
    main()
