"""make_icon.py : draw the installer's icon, the "4U" monogram (own art: a rounded square in the Fluent accent with
"4U" in DejaVu Sans Bold), into installer/gui/assets/icon-256.png and icon.ico (16..256). Run again only to change it.

  python3 installer/packaging/make_icon.py [FONT.ttf]     default: fontconfig's "DejaVu Sans:bold"
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'gui', 'assets')


def draw(font_path, size=1024):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((32, 32, size - 32, size - 32), radius=size // 5, fill=(0, 103, 192, 255))
    f = ImageFont.truetype(font_path, int(size * 0.46))
    x0, y0, x1, y1 = d.textbbox((0, 0), '4U', font=f)
    d.text(((size - (x1 - x0)) / 2 - x0, (size - (y1 - y0)) / 2 - y0), '4U', font=f, fill=(255, 255, 255, 255))
    return img


def main():
    font = sys.argv[1] if len(sys.argv) > 1 else subprocess.run(
        ['fc-match', '-f', '%{file}', 'DejaVu Sans:bold'], capture_output=True, text=True, check=True).stdout
    big = draw(font)
    os.makedirs(OUT, exist_ok=True)
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, 'icon-256.png'), optimize=True)
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, 'icon.ico'),
                                               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print('wrote', os.path.relpath(OUT))


if __name__ == '__main__':
    main()
