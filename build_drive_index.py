"""
build_drive_index.py - builds data/drive_index.json (lightweight, no files)
"""
import os, json
from collections import Counter

ROOT = r'C:\Users\danih\Documents\DriveFiles\מעליות תוכניות'
OUT  = r'C:\Users\danih\Documents\elevator-poc-recovered\data\drive_index.json'

EXT_TYPE = {
    '.pdf':'PDF','.docx':'Word','.doc':'Word',
    '.xlsx':'Excel','.xls':'Excel',
    '.jpg':'תמונה','.jpeg':'תמונה','.png':'תמונה','.JPG':'תמונה',
    '.pptx':'מצגת','.ppsx':'מצגת','.ppt':'מצגת',
    '.mp4':'וידאו','.avi':'וידאו','.mov':'וידאו',
}

MFR_KW = {
    'TKE':       ['tke','thyssenkrupp','cmc','tac','evolution','vacon','dea','tcm','טיסן'],
    'KONE':      ['kone','kce','lce','kdl','tms','קונה'],
    'Schindler': ['schindler','3300','5500','bio','שינדלר'],
    'Otis':      ['otis','gen2','gecb'],
    'ORONA':     ['orona','arca'],
    'פרוליפט':   ['פרוליפט','prolift','plac','plc100'],
    'קונסול':    ['קונסול','fw20','fw8','fw6','fw4','cnc','pcw'],
    'ליאב':      ['ליאב','uml'],
    'אומר':      ['אומר','ecs lift'],
}

def guess_mfr(path):
    t = path.lower().replace('\\', '/')
    for mfr, kws in MFR_KW.items():
        if any(k in t for k in kws):
            return mfr
    return ''

def size_label(b):
    if b >= 1048576: return f'{b/1048576:.1f} MB'
    if b >= 1024:    return f'{b/1024:.0f} KB'
    return f'{b} B'

items = []
folders = set()
errors = 0

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames.sort()
    rel_dir = os.path.relpath(dirpath, ROOT).replace('\\', '/')
    if rel_dir == '.':
        rel_dir = ''
    parts = [p for p in rel_dir.split('/') if p]
    cat = parts[0] if parts else 'כללי'
    if rel_dir:
        folders.add(rel_dir)

    for fname in sorted(filenames):
        full = os.path.join(dirpath, fname)
        try:
            sz = os.path.getsize(full)
        except Exception:
            errors += 1
            continue
        ext = os.path.splitext(fname)[1].lower()
        rel_path = (rel_dir + '/' + fname).lstrip('/')
        items.append({
            'n':  fname,
            'p':  rel_dir,
            'k':  EXT_TYPE.get(ext, ext.lstrip('.').upper() or 'קובץ'),
            's':  sz,
            'sl': size_label(sz),
            'c':  cat,
            'm':  guess_mfr(rel_path),
        })

index = {
    'v':       1,
    'total':   len(items),
    'folders': len(folders),
    'items':   items,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
raw = json.dumps(index, ensure_ascii=False, separators=(',', ':'))
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(raw)

sz_kb = round(len(raw.encode('utf-8')) / 1024)

print(f'קבצים:     {len(items)}')
print(f'תיקיות:    {len(folders)}')
print(f'גודל JSON: {sz_kb} KB')
print(f'שגיאות:    {errors}')
print(f'נשמר:      {OUT}')
print()
cats = Counter(i['c'] for i in items)
for c, n in cats.most_common():
    print(f'  {c}: {n} קבצים')
