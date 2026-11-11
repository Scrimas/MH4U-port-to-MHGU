"""make_icon.py : draw the installer's icon, a quest scroll with a red wax seal and blue ribbon tails (own art, pixel art on
MHGU_Editor's 32 x 32 grid and in its icon's colours, with the editor's three claw slashes in gold on the seal), into
installer/gui/assets/: icon-256.png (the window, the Linux menu, the AppImage), icon.svg (the Linux menu, any size) and
icon.ico (the .exe: 16 px from the hand-drawn 16 x 16 map; 24 px the 32 x 32 one smoothed down, 48 px it at 1.5x, crisp:
the 16 x 16 one at 3x loses the claws; 32, 64, 128 and 256 px whole multiples).
Run again only after changing a map or the palette.

  python3 installer/packaging/make_icon.py
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'gui', 'assets')

# one letter per pixel, "." transparent
PALETTE = {
    'G': '#1c1424',  # outline
    'I': '#f4ebd1',  # paper, light
    'J': '#d3bf9d',  # paper
    'S': '#9a806e',  # paper shade, text lines
    'L': '#3e2126',  # ink
    'M': '#c98543',  # knob, light
    'N': '#9b5631',  # knob
    'Q': '#6a372a',  # knob, dark
    'K': '#f3834a',  # wax glint
    'C': '#d6452f',  # wax, light
    'B': '#a2262e',  # wax
    'D': '#651729',  # wax, dark
    'A': '#33101e',  # wax edge
    'F': '#ffe189',  # gold, light
    'E': '#db9d2f',  # gold
    'H': '#a0601f',  # gold, dark
    'U': '#6f9de6',  # ribbon, light
    'V': '#2f62c0',  # ribbon
    'W': '#1d3a7a',  # ribbon, dark
}

SCROLL_32 = [
    '................................',
    '.G.GGGGGGGGGGGGGGGGGGGGGGGGGG.G.',
    'GMGGJIIIIIIIIIIIIIIIIIIIIIIJGGMG',
    'GNGGSJJJJJJJJJJJJJJJJJJJJJJSGGNG',
    'GQGGQSSSSSSSSSSSSSSSSSSSSSSQGGQG',
    '.G.GGGGGGGGGGGGGGGGGGGGGGGGGG.G.',
    '.....GSSSSSSSSSSSSSSSSSSSSG.....',
    '.....GJJJJJJJJJJJJJJJJJJJSG.....',
    '.....GJIIIIIIIIIIIIIIIIIJSG.....',
    '.....GJIILLLLLLLLLLLLLIIJSG.....',
    '.....GJIIQQQQQQQQIIIIIIIJSG.....',
    '.....GJIIIIIIIIIIIIIIIIIJSG.....',
    '.....GJIIIIIIIIIIIIIIIIIJSG.....',
    '.....GJISSSSSSSSSSSSSSSIJSG.....',
    '.....GJIIIIIIIIIIIAAAAAAJSG.....',
    '.....GJISSSSSSIIIKCCCCCBASG.....',
    '.....GJIIIIIIIIIKCCCDDBBBAG.....',
    '.....GJISSSSSSSACCDDBBFBBBA.....',
    '.....GJIIIIIIIIACCDBFBFBFDA.....',
    '.....GJISSSSSIIACDBFBEBFBDA.....',
    '.....GJIIIIIIIIACDBEBEBEBDA.....',
    '.....GJISSSSSSIACBEBEBHBDDA.....',
    '.....GJIIIIIIIIABBHBHBBBDDA.....',
    '.....GJIIIIIIIIIABBBBBDDDAG.....',
    '.....GJJJJJJJJJGGABDDDDDAJG.....',
    '.G.GGGGGGGGGGGGUVGAAAAAAWGGGG.G.',
    'GMGGJIIIIIIIIIGUVGIIIIGVWGIJGGMG',
    'GNGGSJJJJJJJJGUVGJJJJJJGVWGSGGNG',
    'GQGGQSSSSSSSSGUVGSSSSSSGVWGQGGQG',
    '.G.GGGGGGGGGGGVGVGGGGGGWGWGGG.G.',
    '.............GG.GG....GG.GG.....',
    '................................',
]

# drawn for 16 px: the 32 x 32 one shrunk smears the seal and the lines
SCROLL_16 = [
    '................',
    '.GGGGGGGGGGGGGG.',
    'GMJIIIIIIIIIIJMG',
    'GQSJJJJJJJJJJSQG',
    '.GGGGGGGGGGGGGG.',
    '..GSSSSSSSSSSG..',
    '..GJLLLLLLLISG..',
    '..GJIIIIIAAAAG..',
    '..GJSSSIACKBBA..',
    '..GJIIIIACBFBA..',
    '..GJSSSIABEBDA..',
    '.GGGGGGGABBDDAG.',
    'GMJIIIIIIAAAAJMG',
    'GQSJJJJJGVGGVGQG',
    '.GGGGGGGGVGGVGG.',
    '........G.GG.G..',
]


def bitmap(rows):
    n = len(rows)
    assert all(len(r) == n for r in rows), 'a map must be square'
    img = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c != '.':
                h = PALETTE[c]
                img.putpixel((x, y), (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255))
    return img


def scaled(rows, factor):
    img = bitmap(rows)
    return img.resize((img.width * factor, img.height * factor), Image.NEAREST)


def svg(rows):
    """One path per colour, a rectangle per run of pixels in a row, crisp at any size."""
    runs = {}
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            c, w = row[x], 1
            while x + w < len(row) and row[x + w] == c:
                w += 1
            if c != '.':
                runs.setdefault(c, []).append('M%d %dh%dv1h-%dz' % (x, y, w, w))
            x += w
    n = len(rows)
    paths = ''.join('<path fill="%s" d="%s"/>\n' % (PALETTE[c], ''.join(d)) for c, d in runs.items())
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="256" height="256" shape-rendering="crispEdges">\n'
            '<title>Quest scroll</title>\n%s</svg>\n' % (n, n, paths))


def main():
    os.makedirs(OUT, exist_ok=True)
    big = scaled(SCROLL_32, 8)
    big.save(os.path.join(OUT, 'icon-256.png'), optimize=True)
    with open(os.path.join(OUT, 'icon.svg'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(svg(SCROLL_32))
    frames = [
        bitmap(SCROLL_16),
        bitmap(SCROLL_32).resize((24, 24), Image.LANCZOS),
        bitmap(SCROLL_32),
        bitmap(SCROLL_32).resize((48, 48), Image.NEAREST),
        scaled(SCROLL_32, 2),
        scaled(SCROLL_32, 4),
    ]
    big.save(os.path.join(OUT, 'icon.ico'), sizes=[(f.width, f.height) for f in frames] + [(256, 256)],
             append_images=frames)
    print('wrote', os.path.relpath(OUT))


if __name__ == '__main__':
    main()
