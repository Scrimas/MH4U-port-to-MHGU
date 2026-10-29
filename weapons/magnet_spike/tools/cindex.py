"""Index of a Decomp.java output file: one line per function with size, callers, the functions it calls and the
data it touches, so a large decompiled region can be surveyed before reading it.
usage: python3 -I cindex.py FILE.c [REGEX]     (REGEX: only functions whose body matches)
       python3 -I cindex.py FILE.c --show ADDR...  (print those functions' bodies)"""
import re, sys

HEAD = re.compile(r'^// ==== \S+\s+entry (\w+)\s+size (\d+)\s+callers \[(.*)\]')


def functions(path):
    """-> [(entry, size, callers, body text)]"""
    out = []; cur = None; body = []
    for line in open(path, errors='replace'):
        m = HEAD.match(line)
        if m:
            if cur: out.append(cur + ('\n'.join(body),))
            cur = (m.group(1), int(m.group(2)), [c for c in m.group(3).split(', ') if c]); body = []
        elif cur:
            body.append(line.rstrip('\n'))
    if cur: out.append(cur + ('\n'.join(body),))
    return out


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--show':
        want = {'%08x' % int(a, 16) for a in sys.argv[3:]}
        for e, size, callers, body in functions(sys.argv[1]):
            if e in want: print('// %s  %d B  callers %s\n%s' % (e, size, ','.join(callers), body.strip()))
        sys.exit()
    pat = re.compile(sys.argv[2]) if len(sys.argv) > 2 else None
    for e, size, callers, body in functions(sys.argv[1]):
        if pat and not pat.search(body): continue
        calls = sorted(set(re.findall(r'FUN_([0-9a-f]{8})', body)) - {e})
        data = sorted(set(re.findall(r'DAT_([0-9a-f]{8})', body)))
        tables = sorted(set(re.findall(r'PTR_\w*?_([0-9a-f]{8})', body)))
        ms = '  MS' if re.search(r"\+ 3\) == '\\r'|\+ 3\) != '\\r'", body) else ''
        print('%s %5d B  callers %-28s calls %s%s%s%s' % (
            e, size, ','.join(callers[:3]) + ('+%d' % (len(callers) - 3) if len(callers) > 3 else ''),
            ' '.join(calls[:12]) + (' +%d' % (len(calls) - 12) if len(calls) > 12 else ''),
            '  tbl ' + ' '.join(tables) if tables else '', '  dat ' + ' '.join(data[:6]) if data else '', ms))
