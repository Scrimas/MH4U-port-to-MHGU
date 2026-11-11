"""plugin_sigs.py : the MHGU 1.4 code a Forge plugin checks before it hooks, read from the plugin's .nro.

  plugin_sigs.py PLUGIN.nro [WIDTH]    print each checked main offset and how many bytes of v1.4 code follow it

Forge plugins (Key Quest Markers, Damage Numbers) carry a table of (u32 main offset, v1.4 bytes from there) and
install nothing when one check fails (issues #10, #13). This scans every 4-aligned word of the .nro: a word that is a
main offset and is followed by at least 16 bytes equal to GU main at that offset is a table entry. The printed list
goes into module/build.py PLUGIN_CHECKED; WIDTH (default: the longest match, which is the plugin's own width when
its entries are back to back) is what to write there. Small accidental matches of the plugin's own ARM code to GU
code are not entries: those are not preceded by their address.

Then module/build.py refuses any hook or IPS record inside those bytes. Reads the plugin file only, writes nothing.
"""
import os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

MIN_MATCH = 16


def entries(main, nro):
    """[(main offset, matching byte count, .nro offset)]"""
    out = []
    for p in range(0, len(nro) - 4 - MIN_MATCH, 4):
        a = struct.unpack_from('<I', nro, p)[0]
        if not 0x1000 <= a < len(main) - MIN_MATCH or nro[p + 4:p + 4 + MIN_MATCH] != main[a:a + MIN_MATCH]:
            continue
        n = MIN_MATCH
        while p + 4 + n < len(nro) and a + n < len(main) and nro[p + 4 + n] == main[a + n]: n += 1
        out.append((a, n, p))
    return out


def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    with open(paths.GU_MAIN, 'rb') as f: img = f.read()
    with open(sys.argv[1], 'rb') as f: nro = f.read()
    found = entries(img, nro)
    if not found: sys.exit('no signature table found in %s' % sys.argv[1])
    for a, n, p in sorted(found):
        print('0x%07X  0x%02x bytes  (.nro 0x%x)' % (a, n, p))
    width = int(sys.argv[2], 0) if len(sys.argv) > 2 else max(n for _, n, _ in found)
    print('%d entries; PLUGIN_CHECKED width 0x%x' % (len(found), width))


if __name__ == '__main__':
    main()
