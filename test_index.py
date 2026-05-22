import json, os

data = json.load(open('data/drive_index.json', encoding='utf-8'))
cats = ['MRL','בקרים','ישראליות','מעליות הידראוליות','חייגנים']
BASE = r'C:\Users\danih\Documents\DriveFiles\מעליות תוכניות'

print(f"Total items: {data['total']}, folders: {data['folders']}\n")
for cat in cats:
    items = [i for i in data['items'] if i['c']==cat]
    sample = items[0] if items else None
    if sample:
        path = os.path.join(BASE, sample['p'].replace('/',os.sep), sample['n'])
        exists = os.path.exists(path)
        url = 'file:///C:/Users/danih/Documents/DriveFiles/מעליות תוכניות/' + sample['p'] + '/' + sample['n']
        print(f"[{cat}]")
        print(f"  file: {sample['n']}")
        print(f"  size: {sample['sl']}")
        print(f"  path exists: {exists}")
        print(f"  file:/// URL: {url[:80]}...")
        print()
