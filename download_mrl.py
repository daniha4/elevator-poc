"""
download_mrl.py — מוריד את כל הקבצים מ-Google Drive (Shared with me)
"""
import os, sys, json, requests, webbrowser, threading, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

OAUTH_CLIENT = r'C:\Users\danih\Documents\elevator-poc-recovered\oauth_client.json'
OAUTH_TOKEN  = r'C:\Users\danih\Documents\elevator-poc-recovered\oauth_token.json'
OUT_DIR      = r'C:\Users\danih\Documents\DriveFiles'
FOLDER_MIME  = 'application/vnd.google-apps.folder'
SCOPE        = 'https://www.googleapis.com/auth/drive.readonly'
TOKEN_URI    = 'https://oauth2.googleapis.com/token'
AUTH_URI     = 'https://accounts.google.com/o/oauth2/auth'
API          = 'https://www.googleapis.com/drive/v3/files'

_auth_code = None

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _auth_code = qs.get('code', [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'<h2>OK! Close this window and return to the terminal.</h2>')
        threading.Thread(target=self.server.shutdown, daemon=True).start()
    def log_message(self, *a): pass

def get_token():
    if os.path.exists(OAUTH_TOKEN):
        tok = json.load(open(OAUTH_TOKEN))
        # Try refresh
        creds = json.load(open(OAUTH_CLIENT))['installed']
        r = requests.post(TOKEN_URI, data={
            'client_id':     creds['client_id'],
            'client_secret': creds['client_secret'],
            'refresh_token': tok['refresh_token'],
            'grant_type':    'refresh_token',
        })
        if r.ok:
            new = r.json()
            tok['access_token'] = new['access_token']
            json.dump(tok, open(OAUTH_TOKEN, 'w'))
            return tok['access_token']

    # First-time login
    global _auth_code
    creds = json.load(open(OAUTH_CLIENT))['installed']
    redirect = 'http://localhost:8765'
    url = (AUTH_URI +
           '?client_id=' + creds['client_id'] +
           '&redirect_uri=' + redirect +
           '&response_type=code' +
           '&scope=' + urllib.parse.quote(SCOPE) +
           '&access_type=offline&prompt=consent')
    print('\nOpening browser - sign in with danihanoch2@gmail.com and click Allow...')
    server = HTTPServer(('localhost', 8765), _Handler)
    webbrowser.open(url)
    server.serve_forever()

    r = requests.post(TOKEN_URI, data={
        'client_id':     creds['client_id'],
        'client_secret': creds['client_secret'],
        'code':          _auth_code,
        'redirect_uri':  redirect,
        'grant_type':    'authorization_code',
    })
    r.raise_for_status()
    tok = r.json()
    json.dump(tok, open(OAUTH_TOKEN, 'w'))
    print('Token saved. Starting download...\n')
    return tok['access_token']


def drive_list(token, query, path=''):
    items = []
    page_token = None
    headers = {'Authorization': 'Bearer ' + token}
    while True:
        params = {
            'q': query + ' and trashed=false',
            'fields': 'nextPageToken,files(id,name,mimeType,size)',
            'pageSize': 1000, 'orderBy': 'name',
        }
        if page_token: params['pageToken'] = page_token
        r = requests.get(API, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        for f in r.json().get('files', []):
            item_path = (path + '/' + f['name']).lstrip('/')
            if f['mimeType'] == FOLDER_MIME:
                items.extend(drive_list(token, f"'{f['id']}' in parents", item_path))
            else:
                items.append({'id': f['id'], 'name': f['name'],
                              'path': item_path, 'size': int(f.get('size', 0))})
        page_token = r.json().get('nextPageToken')
        if not page_token: break
    return items


def download(token, file_id, dest):
    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.get(f'{API}/{file_id}', headers=headers,
                     params={'alt': 'media'}, stream=True, timeout=120)
    r.raise_for_status()
    with open(dest, 'wb') as f:
        for chunk in r.iter_content(65536):
            f.write(chunk)


def main():
    token = get_token()

    print('Scanning Google Drive - Shared with me...')
    items = drive_list(token, 'sharedWithMe=true')
    print(f'Found {len(items)} files\n')

    ok = skip = err = 0
    total = len(items)
    for i, item in enumerate(items, 1):
        dest = os.path.join(OUT_DIR, item['path'].replace('/', os.sep))
        if os.path.exists(dest) and os.path.getsize(dest) == item['size']:
            skip += 1
            print(f'  [{i}/{total}] skip: {item["path"]}')
            continue
        try:
            print(f'  [{i}/{total}] download: {item["path"]} ({item["size"]//1024} KB)')
            download(token, item['id'], dest)
            ok += 1
        except Exception as e:
            print(f'  [{i}/{total}] ERROR: {item["path"]} - {e}')
            err += 1

    print(f'\n== DONE ==  downloaded:{ok}  skipped:{skip}  errors:{err}  total:{total}')
    print(f'Files saved to: {OUT_DIR}')


if __name__ == '__main__':
    main()
