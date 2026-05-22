"""
make_icons.py - generates all PWA icons for iOS + Android
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = r'C:\Users\danih\Documents\elevator-poc-recovered'

def make_icon(size):
    img = Image.new('RGB', (size, size), '#0B0F1A')
    d = ImageDraw.Draw(img)

    # Rounded background circle
    pad = int(size * 0.08)
    d.ellipse([pad, pad, size-pad, size-pad], fill='#1A2235')

    # Lightning bolt (⚡) as text
    font_size = int(size * 0.52)
    try:
        # Try system fonts
        for fname in ['seguiemj.ttf', 'segoeui.ttf', 'arial.ttf']:
            fpath = f'C:/Windows/Fonts/{fname}'
            if os.path.exists(fpath):
                font = ImageFont.truetype(fpath, font_size)
                break
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    text = '⚡'
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1] - int(size * 0.03)
    d.text((x, y), text, fill='#3B82F6', font=font)

    # Small "E" letter bottom right
    try:
        small_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', int(size*0.18))
    except Exception:
        small_font = ImageFont.load_default()
    d.text((size*0.62, size*0.68), 'E', fill='#7A91A8', font=small_font)

    return img

# Generate all needed sizes
sizes = {
    'icon-192.png': 192,
    'icon-512.png': 512,
    'apple-touch-icon.png': 180,      # iOS home screen
    'apple-touch-icon-120.png': 120,  # iPhone retina
    'apple-touch-icon-152.png': 152,  # iPad retina
    'apple-touch-icon-167.png': 167,  # iPad Pro
    'apple-touch-icon-180.png': 180,  # iPhone 6 Plus
    'favicon.png': 32,
}

for fname, size in sizes.items():
    img = make_icon(size)
    path = os.path.join(OUT, fname)
    img.save(path, 'PNG')
    print(f'  {fname} ({size}x{size})')

# Also create splash screens for iOS
# iPhone (375x812 @2x = 750x1624 actual)
splashes = [
    ('splash-750x1334.png',  750,  1334),  # iPhone 8
    ('splash-1125x2436.png', 1125, 2436),  # iPhone X/XS
    ('splash-828x1792.png',  828,  1792),  # iPhone XR
    ('splash-1242x2688.png', 1242, 2688),  # iPhone XS Max
    ('splash-1170x2532.png', 1170, 2532),  # iPhone 12/13
    ('splash-1179x2556.png', 1179, 2556),  # iPhone 14 Pro
]

for fname, w, h in splashes:
    img = Image.new('RGB', (w, h), '#0B0F1A')
    d = ImageDraw.Draw(img)
    # Center icon
    icon_size = min(w, h) // 4
    icon = make_icon(icon_size)
    x = (w - icon_size) // 2
    y = (h - icon_size) // 2 - h // 10
    img.paste(icon, (x, y))
    # App name
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', icon_size // 4)
    except:
        font = ImageFont.load_default()
    name = 'Elevator'
    bbox = d.textbbox((0,0), name, font=font)
    tw = bbox[2] - bbox[0]
    d.text(((w-tw)//2, y + icon_size + icon_size//6), name, fill='#E2E8F0', font=font)
    img.save(os.path.join(OUT, fname), 'PNG')
    print(f'  {fname} ({w}x{h})')

print('\nDone!')
