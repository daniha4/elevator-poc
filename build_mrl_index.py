"""
build_mrl_index.py — builds data/mrl_index.json

Modes (in order of preference):
  1. OAuth browser login (works for private/shared folders):
       python build_mrl_index.py --oauth
       → opens browser, sign in as danihanoch2@gmail.com

  2. Free API key (works if folder is "Anyone with the link"):
       python build_mrl_index.py --key AIza...
       Or: set GOOGLE_API_KEY=AIza... then python build_mrl_index.py

  3. Local folder scan (no internet needed — uses G: drive):
       python build_mrl_index.py --local
       python build_mrl_index.py --local --root "G:\\other\\path"

Get free API key (5 min):
  https://console.cloud.google.com/apis/credentials
  → Create project → Enable "Google Drive API" → Create API key → restrict to Drive API

For OAuth (10 min, private folders):
  https://console.cloud.google.com/apis/credentials
  → Create OAuth client ID → Desktop app → Download JSON → save as oauth_client.json
"""

import os, json, sys, argparse
from datetime import datetime, timezone

DRIVE_FOLDER_ID = '15RR-PsCux4QJcW4IzCLIyeKqGjplqo6G'
LOCAL_ROOT      = r'G:\dani\תוכניות דני\שטוף דני ואלעד\MRL'
OUT_PATH        = r'C:\Users\danih\Documents\elevator-poc-recovered\data\mrl_index.json'
OAUTH_CLIENT    = r'C:\Users\danih\Documents\elevator-poc-recovered\oauth_client.json'
OAUTH_TOKEN     = r'C:\Users\danih\Documents\elevator-poc-recovered\oauth_token.json'
API_BASE        = 'https://www.googleapis.com/drive/v3/files'
FOLDER_MIME     = 'application/vnd.google-apps.folder'
SCOPES          = ['https://www.googleapis.com/auth/drive.readonly']

MFR_KEYWORDS = {
    'TKE':       ['tke', 'thyssenkrupp', 'cmc', 'tac', 'evolution', 'vacon', 'dea', 'tcm', 'טיסן'],
    'KONE':      ['kone', 'kce', 'lce', 'kdl', 'tms', 'קונה'],
    'Schindler': ['schindler', '3300', '5500', 'שינדלר', 'bio'],
    'Otis':      ['otis', 'gen2', 'gen246'],
    'ORONA':     ['orona', 'arca'],
}

def guess_mfr(text):
    t = text.lower().replace('\\', '/').replace('/', ' ')
    for mfr, kws in MFR_KEYWORDS.items():
        if any(k in t for k in kws):
            return mfr
    return ''

def guess_kind(name):
    ext = os.path.splitext(name)[1].lower()
    return {'.pdf':'PDF','.docx':'Word','.doc':'Word','.xlsx':'Excel','.xls':'Excel',
            '.png':'תמונה','.jpg':'תמונה','.jpeg':'תמונה',
            '.ppsx':'מצגת','.pptx':'מצגת','.ppt':'מצגת'}.get(ext, ext.lstrip('.').upper() or 'קובץ')

def size_label(b):
    if not b: return ''
    b = int(b)
    if b >= 1_048_576: return f'{b/1_048_576:.1f} MB'
    if b >= 1024:      return f'{b/1024:.0f} KB'
    return f'{b} B'


# ── LOCAL SCAN ────────────────────────────────────────────────────────────────

def scan_local(root):
    items = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir = '' if rel_dir == '.' else rel_dir.replace('\\', '/')
        for fname in sorted(filenames):
            full = os.path.join(dirpath, fname)
            try: sz = os.path.getsize(full)
            except OSError: sz = 0
            rel_path = (rel_dir + '/' + fname).lstrip('/')
            items.append({
                'id':          rel_path,
                'name':        fname,
                'path':        rel_dir,
                'type':        'file',
                'mimeType':    'application/pdf' if fname.lower().endswith('.pdf') else '',
                'size':        sz,
                'sizeLabel':   size_label(sz),
                'viewUrl':     'file:///' + full.replace('\\', '/'),
                'localPath':   full,
                'manufacturer': guess_mfr(rel_path),
                'kind':        guess_kind(fname),
            })
    return items


# ── DRIVE API KEY (public folder) ─────────────────────────────────────────────

def list_drive_apikey(folder_id, api_key, path=''):
    import requests
    items = []
    page_token = None
    while True:
        params = {
            'q': f"'{folder_id}' in parents and trashed=false",
            'key': api_key,
            'fields': 'nextPageToken,files(id,name,mimeType,size)',
            'pageSize': 1000, 'orderBy': 'name',
        }
        if page_token: params['pageToken'] = page_token
        r = requests.get(API_BASE, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        for f in data.get('files', []):
            item_path = (path + '/' + f['name']).lstrip('/')
            if f['mimeType'] == FOLDER_MIME:
                items.extend(list_drive_apikey(f['id'], api_key, item_path))
            else:
                sz = int(f.get('size', 0))
                items.append(make_drive_item(f, path, item_path, sz))
        page_token = data.get('nextPageToken')
        if not page_token: break
    return items


# ── DRIVE OAUTH ────────────────────────────────────────────────────────────────

def get_oauth_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(OAUTH_TOKEN):
        creds = Credentials.from_authorized_user_file(OAUTH_TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(OAUTH_CLIENT):
                print(f'\nERROR: oauth_client.json not found at: {OAUTH_CLIENT}')
                print('Steps to create it (free, 10 min):')
                print('  1. https://console.cloud.google.com/apis/credentials')
                print('  2. Create project → Enable Google Drive API')
                print('  3. Create OAuth client ID → Desktop app')
                print('  4. Download JSON → save as oauth_client.json next to this script')
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CLIENT, SCOPES)
            print('\nפותח דפדפן לאישור Google — היכנס עם danihanoch2@gmail.com\n')
            creds = flow.run_local_server(port=0)
        with open(OAUTH_TOKEN, 'w') as tok:
            tok.write(creds.to_json())
        print('OAuth token saved.')

    return build('drive', 'v3', credentials=creds)


def list_drive_oauth(service, folder_id, path=''):
    items = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields='nextPageToken,files(id,name,mimeType,size)',
            pageSize=1000, orderBy='name',
            pageToken=page_token
        ).execute()
        for f in resp.get('files', []):
            item_path = (path + '/' + f['name']).lstrip('/')
            if f['mimeType'] == FOLDER_MIME:
                items.extend(list_drive_oauth(service, f['id'], item_path))
            else:
                sz = int(f.get('size', 0))
                items.append(make_drive_item(f, path, item_path, sz))
        page_token = resp.get('nextPageToken')
        if not page_token: break
    return items


def make_drive_item(f, folder_path, rel_path, sz):
    return {
        'id':          rel_path,
        'name':        f['name'],
        'path':        folder_path,
        'type':        'file',
        'mimeType':    f.get('mimeType', ''),
        'size':        sz,
        'sizeLabel':   size_label(sz),
        'viewUrl':     f"https://drive.google.com/file/d/{f['id']}/view",
        'driveId':     f['id'],
        'manufacturer': guess_mfr(rel_path),
        'kind':        guess_kind(f['name']),
    }


# ── REPORT ────────────────────────────────────────────────────────────────────

def print_report(items, source):
    from collections import Counter
    files = [i for i in items if i['type'] == 'file']
    total_bytes = sum(i['size'] for i in files)
    mfrs   = Counter(i.get('manufacturer') or 'כללי' for i in files)
    kinds  = Counter(i.get('kind', 'קובץ')           for i in files)
    folders = set(i['path'] for i in files if i['path'])

    print(f'\n══ דוח MRL ({source}) ══')
    print(f'  קבצים:     {len(files)}')
    print(f'  תיקיות:    {len(folders)}')
    print(f'  גודל כולל: {size_label(total_bytes)}')
    print(f'\nלפי יצרן:')
    for m, n in mfrs.most_common():
        print(f'  {m}: {n}')
    print(f'\nלפי סוג:')
    for k, n in kinds.most_common():
        print(f'  {k}: {n}')
    print(f'\nתיקיות:')
    for fld in sorted(folders):
        cnt = sum(1 for i in files if i['path'] == fld)
        print(f'  {fld}/ ({cnt})')


# ── MAIN ──────────────────────────────────────────────────────────────────────

def save(items, source):
    files = [i for i in items if i['type'] == 'file']
    index = {
        'generated':  datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source':     source,
        'folderId':   DRIVE_FOLDER_ID,
        'total':      len(files),
        'items':      items,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Saved: {OUT_PATH}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--oauth',  action='store_true', help='OAuth browser login (private/shared folders)')
    parser.add_argument('--key',    default=os.environ.get('GOOGLE_API_KEY', ''), help='Free API key (public folders)')
    parser.add_argument('--local',  action='store_true', help='Scan local folder (no internet)')
    parser.add_argument('--root',   default=LOCAL_ROOT,  help='Local root for --local mode')
    args = parser.parse_args()

    # Auto-detect mode
    if not args.oauth and not args.key and not args.local:
        print('הכנס את מפתח ה-API של Google (מ-console.cloud.google.com):')
        args.key = input('API Key: ').strip()

    if args.oauth:
        try:
            print('Connecting to Google Drive via OAuth...')
            service = get_oauth_service()
            print(f'Fetching Drive folder: {DRIVE_FOLDER_ID}')
            items = list_drive_oauth(service, DRIVE_FOLDER_ID)
            source = 'drive-oauth'
        except ImportError:
            print('Missing packages. Run:')
            print('  pip install google-auth-oauthlib google-api-python-client')
            sys.exit(1)

    elif args.key:
        try:
            import requests
        except ImportError:
            print('Missing: pip install requests')
            sys.exit(1)
        print(f'Fetching Drive folder: {DRIVE_FOLDER_ID} (API key mode)')
        items = list_drive_apikey(DRIVE_FOLDER_ID, args.key)
        source = 'drive-apikey'

    else:  # --local
        root = args.root
        if not os.path.isdir(root):
            print(f'ERROR: folder not found: {root}')
            sys.exit(1)
        print(f'Scanning local: {root}')
        items = scan_local(root)
        source = 'local'

    save(items, source)
    print_report(items, source)


if __name__ == '__main__':
    main()
