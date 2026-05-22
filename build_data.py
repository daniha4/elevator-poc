r"""
Build fault_index.json from all available PDFs.
Run from: C:/Users/danih/Documents/elevator-poc-recovered/
"""
import fitz, re, json, sys, os, collections
sys.stdout.reconfigure(encoding='utf-8')

OUT_JSON = r"C:\Users\danih\Documents\elevator-poc-recovered\data\fault_index.json"
MRL = r"C:\Users\danih\Documents\elevator-poc\mrl_extracted\MRL"

records = []

def has_hebrew(t):
    return any('א' <= c <= 'ת' for c in t)

def clean(t, maxlen=130):
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) > maxlen:
        t = t[:maxlen].rsplit(' ', 1)[0].strip()
    return t

# ══════════════════════════════════════════════════════════════
# 1. TKE CMC4+  (CMC4plus_FaultCodes.pdf)
# ══════════════════════════════════════════════════════════════
def parse_cmc4plus(pdf_path):
    recs = []
    try:
        doc = fitz.open(pdf_path)
    except:
        print(f"  SKIP (not found): {pdf_path}")
        return recs
    CODE_RE = re.compile(r'^(\d{1,3})\s*$')
    NEMON_RE = re.compile(r'^[A-Z][A-Z0-9_]{2,}$')
    seen = set()
    for page in doc:
        lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
        i = 0
        while i < len(lines):
            m = CODE_RE.match(lines[i])
            if m:
                code_num = int(m.group(1))
                if code_num > 255 or code_num in seen:
                    i += 1; continue
                seen.add(code_num)
                nemon, desc, display = '', '', ''
                j = i + 1
                while j < min(i+8, len(lines)):
                    l = lines[j]
                    if NEMON_RE.match(l) and not nemon:
                        nemon = l
                    elif l.startswith('תצוגה') or l.startswith('Display'):
                        display = l
                    elif has_hebrew(l) and not desc:
                        desc = l
                    elif len(l) > 10 and not has_hebrew(l) and not nemon and re.match(r'[A-Z]', l):
                        nemon = l
                    j += 1
                parts = ['Code {:03d}'.format(code_num)]
                if nemon: parts.append(nemon)
                if display: parts.append('תצוגה: ' + display.replace('תצוגה:','').replace('Display:','').strip())
                if desc: parts.append(clean(desc))
                recs.append({
                    'file': 'CMC4plus_FaultCodes.pdf',
                    'page': str(5000 + code_num),
                    'snippet': ' | '.join(parts),
                    'keyword': 'fault',
                    'has_code': 'true',
                    'normalized_manufacturer': 'TKE',
                    'normalized_controller': 'CMC4+',
                })
            i += 1
    print(f"  CMC4+: {len(recs)} קודים")
    return recs

# ══════════════════════════════════════════════════════════════
# 2. TKE CMC4+20.50  (coordinate-based)
# ══════════════════════════════════════════════════════════════
def parse_cmc4_20_50(pdf_path):
    recs = []
    try:
        doc = fitz.open(pdf_path)
    except:
        print(f"  SKIP: {pdf_path}"); return recs
    X_DISPLAY_START=80; X_OUTAV_START=115; X_NEMON_START=150
    X_MEANING_START=230; X_MEANING_END=530; Y_TOL=4
    seen = set()
    for page in doc:
        words = page.get_text('words')
        code_col    = [(w[1],w[4]) for w in words if w[0]<X_DISPLAY_START and re.match(r'^\d{1,3}$',w[4]) and int(w[4])<=255]
        display_col = [(w[1],w[4]) for w in words if X_DISPLAY_START<=w[0]<X_OUTAV_START]
        outav_col   = [(w[1],w[4]) for w in words if X_OUTAV_START<=w[0]<X_NEMON_START]
        nemon_col   = [(w[1],w[4]) for w in words if X_NEMON_START<=w[0]<X_MEANING_START]
        meaning_col = [(w[1],w[4]) for w in words if X_MEANING_START<=w[0]<X_MEANING_END]
        for cy,code_text in sorted(code_col):
            code_num = int(code_text)
            if code_num in seen: continue
            seen.add(code_num)
            def at_row(col):
                return [t for wy,t in col if abs(wy-cy)<=Y_TOL]
            display = ' '.join(at_row(display_col)).strip()
            outav   = ' '.join(at_row(outav_col)).strip()
            nemon   = re.sub(r'_+','_',' '.join(at_row(nemon_col)).replace('#','').strip()).strip('_')
            meaning = re.sub(r'\s+',' ',' '.join(at_row(meaning_col)).replace('#',' ')).strip()
            if not nemon and not meaning: continue
            if nemon=='---' and not meaning: continue
            parts = ['Code {:03d}'.format(code_num)]
            if nemon and nemon not in ('---',): parts.append(nemon)
            if display and display not in ('NO','SI','NO NO','DISPLAY','--'): parts.append('תצוגה: '+display)
            if outav=='YES': parts.append('FAULT')
            if meaning and meaning not in ('MEANING CMC4+20.50','MEANING','--','*****'): parts.append(meaning)
            recs.append({
                'file': 'TKE_CMC4_20.50_FaultStack.pdf',
                'page': str(5000+code_num),
                'snippet': ' | '.join(parts),
                'keyword': 'fault', 'has_code': 'true',
                'normalized_manufacturer': 'TKE',
                'normalized_controller': 'CMC4+20.50',
            })
    recs.sort(key=lambda r: int(re.search(r'Code (\d+)',r['snippet']).group(1)))
    print(f"  CMC4+20.50: {len(recs)} קודים")
    return recs

# ══════════════════════════════════════════════════════════════
# 3. KONE KCE (Hebrew, 95 pages)
# ══════════════════════════════════════════════════════════════
def parse_kone_kce(pdf_path):
    recs = []
    try:
        doc = fitz.open(pdf_path)
    except:
        print(f"  SKIP: {pdf_path}"); return recs
    full = ''
    for p in doc:
        full += p.get_text() + '\n'
    lines = [l.strip() for l in full.splitlines() if l.strip()]
    CODE_RE  = re.compile(r'^\d{4}$')
    PRIO_RE  = re.compile(r'^\d$')
    REASON_START = re.compile(r'^[אבגד]\)|^\)[אבגד]|^נתונים\d|^\d\)')
    code_positions = [(i,int(lines[i])) for i in range(len(lines)) if CODE_RE.match(lines[i])]
    seen = set()
    for idx,(pos,code_num) in enumerate(code_positions):
        code_str = '{:04d}'.format(code_num)
        if code_str in seen: continue
        seen.add(code_str)
        block_start = pos+1
        priority = ''
        if block_start < len(lines) and PRIO_RE.match(lines[block_start]):
            priority = lines[block_start]; block_start += 1
        block_end = code_positions[idx+1][0] if idx+1<len(code_positions) else block_start+30
        name_parts = []
        for j in range(block_start, min(block_end, block_start+15, len(lines))):
            line = lines[j]
            if REASON_START.match(line): break
            if re.match(r'קודי תקלה|© זכויות|KONE Corporation|דף\d', line): continue
            if len(line)<=2 and not has_hebrew(line): continue
            name_parts.append(line)
        fault_name = re.sub(r'\s+',' ',' '.join(name_parts)).strip()
        if len(fault_name)>150: fault_name = fault_name[:150].rsplit(' ',1)[0]
        if not fault_name: continue
        parts = ['Code '+code_str, fault_name]
        if priority: parts.append('עדיפות '+priority)
        recs.append({
            'file': 'KONE_KCE_fault_codes.pdf',
            'page': str(7000+code_num),
            'snippet': ' | '.join(parts),
            'keyword': 'fault', 'has_code': 'true',
            'normalized_manufacturer': 'KONE',
            'normalized_controller': 'KCE',
        })
    recs.sort(key=lambda r: int(r['page']))
    print(f"  KCE: {len(recs)} קודים")
    return recs

# ══════════════════════════════════════════════════════════════
# 4. KONE LCE (KONE_MRL_FaultCodes.pdf)
# ══════════════════════════════════════════════════════════════
def parse_kone_lce(pdf_path):
    recs = []
    try:
        doc = fitz.open(pdf_path)
    except:
        print(f"  SKIP: {pdf_path}"); return recs
    all_lines = []
    for i,page in enumerate(doc):
        for line in page.get_text().splitlines():
            s = line.strip()
            if s: all_lines.append((i+1, s))
    CODE_ALONE = re.compile(r'^(\d{4})$')
    CODE_WITH  = re.compile(r'^(\d{4})(.+)')
    faults = {}
    section_header = ''
    i = 0
    while i < len(all_lines):
        pg, line = all_lines[i]
        m_alone = CODE_ALONE.match(line)
        m_with  = CODE_WITH.match(line)
        if not m_alone and not m_with and has_hebrew(line) and not re.match(r'^\d',line):
            if len(line)<30 and not re.search(r'[/\\]',line):
                section_header = line
        elif m_with:
            code_str = m_with.group(1); rest = m_with.group(2).strip()
            if has_hebrew(rest) or len(rest)>3:
                desc = clean(rest)
                if code_str not in faults and desc:
                    faults[code_str] = desc
                if int(code_str)<1000: section_header=''
        elif m_alone:
            code_str = m_alone.group(1); code_num = int(code_str)
            if code_str in faults: i+=1; continue
            collected = []
            j = i+1
            while j<len(all_lines) and len(collected)<4:
                _,nxt = all_lines[j]
                if CODE_ALONE.match(nxt): break
                mw = CODE_WITH.match(nxt)
                if mw and has_hebrew(mw.group(2)):
                    collected.append(mw.group(2).strip()); break
                if has_hebrew(nxt) and not re.match(r'^\d{4}',nxt):
                    collected.append(nxt)
                j+=1
            parts = []
            if code_num>=1000 and section_header and has_hebrew(section_header):
                parts.append(section_header)
            if collected: parts.append(' '.join(collected))
            desc = clean(' - '.join(parts)) if parts else ''
            if not desc and code_num>=1000 and section_header: desc=clean(section_header)
            if desc: faults[code_str]=desc
            if code_num<1000: section_header=''
        i+=1
    for code_str,desc in sorted(faults.items()):
        code_num = int(code_str)
        snippet = 'Code {} | {}'.format(code_str, desc)
        recs.append({
            'file': 'KONE_MRL_FaultCodes.pdf',
            'page': str(9000+code_num),
            'snippet': snippet,
            'keyword': code_str, 'has_code': 'true',
            'normalized_manufacturer': 'KONE',
            'normalized_controller': 'LCE',
        })
    print(f"  LCE: {len(recs)} קודים")
    return recs

# ══════════════════════════════════════════════════════════════
# 5. KONE KDL16  (Main code + Sub code format)
# ══════════════════════════════════════════════════════════════
def parse_kdl16(pdf_path):
    recs = []
    try:
        doc = fitz.open(pdf_path)
    except:
        print(f"  SKIP: {pdf_path}"); return recs
    full = ''
    for p in doc: full += p.get_text() + '\n'
    lines = [l.strip() for l in full.splitlines() if l.strip()]
    MAIN_RE = re.compile(r'^(\d{3})\s+(.+)$')
    SUB_RE  = re.compile(r'^(\d{4})\s+(.+)$')
    BARE_MAIN = re.compile(r'^(\d{3})$')
    seen = set()
    cur_main = ''
    cur_main_name = ''
    i = 0
    while i < len(lines):
        l = lines[i]
        mm = MAIN_RE.match(l)
        bm = BARE_MAIN.match(l)
        ms = SUB_RE.match(l)
        if mm and not ms:
            cur_main = mm.group(1)
            cur_main_name = mm.group(2).strip()
        elif bm:
            cur_main = bm.group(1)
        elif ms:
            sub = ms.group(1); sub_name = ms.group(2).strip()
            key = '{}-{}'.format(cur_main, sub)
            if key not in seen and cur_main:
                seen.add(key)
                desc = ''
                if i+1 < len(lines) and len(lines[i+1]) > 5 and not SUB_RE.match(lines[i+1]) and not BARE_MAIN.match(lines[i+1]):
                    desc = clean(lines[i+1], 100)
                parts = ['Code {}-{}'.format(cur_main, sub), sub_name]
                if cur_main_name and cur_main_name not in sub_name: parts.insert(1, cur_main_name)
                if desc: parts.append(desc)
                recs.append({
                    'file': 'KONE_KDL16_FaultCodes.pdf',
                    'page': str(8000 + len(recs)),
                    'snippet': ' | '.join(parts),
                    'keyword': 'fault', 'has_code': 'true',
                    'normalized_manufacturer': 'KONE',
                    'normalized_controller': 'KDL16',
                })
        i += 1
    print(f"  KDL16: {len(recs)} קודים")
    return recs


# ══════════════════════════════════════════════════════════════
# 5b. TKE TAC50K / Evolution 2 (English)
# ══════════════════════════════════════════════════════════════
def parse_tac50k(pdf_paths):
    recs = []
    seen = set()
    SKIP = re.compile(r'^(©|TAC|ThyssenKrupp|Car Error|Codes|CODE|DEFINITION|THYSSENKRUPP|Page \d|y$)', re.IGNORECASE)
    CODE_RE = re.compile(r'^(\d{1,4})$')
    for pdf_path in pdf_paths:
        try:
            doc = fitz.open(pdf_path)
        except:
            print(f"  SKIP: {pdf_path}"); continue
        full = ''
        for p in doc: full += p.get_text() + '\n'
        lines = [l.strip() for l in full.splitlines() if l.strip()]
        i = 0
        while i < len(lines):
            m = CODE_RE.match(lines[i])
            if m and not SKIP.match(lines[i]):
                code = m.group(1)
                key = 'TAC50K-' + code
                if key not in seen:
                    seen.add(key)
                    desc = ''
                    j = i + 1
                    while j < min(i+3, len(lines)):
                        nl = lines[j]
                        if CODE_RE.match(nl) or SKIP.match(nl): break
                        if len(nl) > 8 and not desc:
                            desc = clean(nl, 120)
                        j += 1
                    if desc:
                        recs.append({
                            'file': 'TKE_TAC50K_Codes2.pdf',
                            'page': str(2000 + int(code)),
                            'snippet': 'Code {} | {}'.format(code, desc),
                            'keyword': 'fault', 'has_code': 'true',
                            'normalized_manufacturer': 'TKE',
                            'normalized_controller': 'TAC50K',
                        })
            i += 1
    recs.sort(key=lambda r: int(r['page']))
    print(f"  TAC50K: {len(recs)} קודים")
    return recs

# ══════════════════════════════════════════════════════════════
# 6. Schindler 3300
# ══════════════════════════════════════════════════════════════
def parse_schindler_3300(pdf_path):
    recs = []
    try:
        doc = fitz.open(pdf_path)
    except:
        print(f"  SKIP: {pdf_path}"); return recs
    seen = set()
    CODE_RE = re.compile(r'^(\d{4})$')
    for page in doc:
        lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
        i=0
        while i<len(lines):
            m=CODE_RE.match(lines[i])
            if m:
                code_str=m.group(1)
                if code_str in seen: i+=1; continue
                seen.add(code_str)
                nemon,desc='',''
                j=i+1
                while j<min(i+6,len(lines)):
                    l=lines[j]
                    if re.match(r'^E_[A-Z_]+$',l) and not nemon: nemon=l
                    elif has_hebrew(l) and not desc: desc=clean(l)
                    elif not has_hebrew(l) and len(l)>8 and not nemon: nemon=l
                    j+=1
                parts=['Code '+code_str]
                if nemon: parts.append(nemon)
                if desc: parts.append(desc)
                recs.append({
                    'file': 'Schindler_3300_Training.pdf',
                    'page': str(3000+int(code_str)),
                    'snippet': ' | '.join(parts),
                    'keyword': 'fault', 'has_code': 'true',
                    'normalized_manufacturer': 'Schindler',
                    'normalized_controller': '3300',
                })
            i+=1
    print(f"  Schindler 3300: {len(recs)} קודים")
    return recs

# ══════════════════════════════════════════════════════════════
# 7. Schindler 5500 (יומן שגיאות S5500.pdf)
# ══════════════════════════════════════════════════════════════
def parse_schindler_5500(pdf_path):
    recs = []
    try:
        doc = fitz.open(pdf_path)
    except:
        print(f"  SKIP: {pdf_path}"); return recs
    full=''
    for p in doc: full += p.get_text()+'\n'
    if len(full.strip())<200:
        print(f"  5500: PDF סרוק, לא ניתן לחלץ")
        return recs
    lines = [l.strip() for l in full.splitlines() if l.strip()]
    CODE_RE = re.compile(r'^(\d{4})$')
    seen = set()
    i=0
    while i<len(lines):
        m=CODE_RE.match(lines[i])
        if m:
            code_str=m.group(1)
            if code_str in seen: i+=1; continue
            seen.add(code_str)
            desc=''
            j=i+1
            while j<min(i+5,len(lines)):
                l=lines[j]
                if CODE_RE.match(l): break
                if has_hebrew(l) and not desc: desc=clean(l)
                elif len(l)>10 and not desc: desc=clean(l)
                j+=1
            if desc:
                recs.append({
                    'file': 'Schindler_5500_יומן_שגיאות.pdf',
                    'page': str(4000+int(code_str)),
                    'snippet': 'Code {} | {}'.format(code_str,desc),
                    'keyword': 'fault', 'has_code': 'true',
                    'normalized_manufacturer': 'Schindler',
                    'normalized_controller': '5500',
                })
        i+=1
    print(f"  Schindler 5500: {len(recs)} קודים")
    return recs

# ══════════════════════════════════════════════════════════════
# 8. TKE CMC3 (from MRL zip)
# ══════════════════════════════════════════════════════════════
def parse_cmc3(pdf_path):
    recs = []
    try:
        doc = fitz.open(pdf_path)
    except:
        print(f"  SKIP: {pdf_path}"); return recs
    full=''
    for p in doc: full += p.get_text()+'\n'
    if len(full.strip())<200:
        print(f"  CMC3: PDF סרוק")
        return recs
    CODE_RE = re.compile(r'^(\d{2})$')
    NEMON_RE = re.compile(r'^[A-Z][A-Z0-9_]{3,}$')
    lines=[l.strip() for l in full.splitlines() if l.strip()]
    seen=set()
    i=0
    while i<len(lines):
        m=CODE_RE.match(lines[i])
        if m:
            code_str=m.group(1)
            if code_str in seen: i+=1; continue
            seen.add(code_str)
            nemon,desc='',''
            j=i+1
            while j<min(i+8,len(lines)):
                l=lines[j]
                if NEMON_RE.match(l) and not nemon: nemon=l
                elif len(l)>15 and not re.match(r'^\d',l) and not desc:
                    desc=clean(l,100)
                j+=1
            if not nemon and not desc: i+=1; continue
            parts=['Code '+code_str]
            if nemon: parts.append(nemon)
            if desc: parts.append(desc)
            recs.append({
                'file': 'CMC3_FaultCodes_IRC34.pdf',
                'page': str(6000+int(code_str)),
                'snippet': ' | '.join(parts),
                'keyword': 'fault', 'has_code': 'true',
                'normalized_manufacturer': 'TKE',
                'normalized_controller': 'CMC3',
            })
        i+=1
    print(f"  CMC3: {len(recs)} קודים")
    return recs

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
pdfs_base = r"C:\Users\danih\Documents\elevator-poc-recovered\pdfs"

PDF_PATHS = {
    'CMC4+':       os.path.join(pdfs_base, 'CMC4plus_FaultCodes.pdf'),
    'CMC4+20.50':  os.path.join(pdfs_base, 'TKE_CMC4_20.50_FaultStack.pdf'),
    'CMC3':        os.path.join(pdfs_base, 'CMC3_FaultCodes_IRC34.pdf'),
    'KCE':         os.path.join(pdfs_base, 'KONE_KCE_fault_codes.pdf'),
    'LCE':         os.path.join(pdfs_base, 'KONE_MRL_FaultCodes.pdf'),
    'KDL16':       os.path.join(pdfs_base, 'KONE_KDL16_FaultCodes.pdf'),
    '3300':        os.path.join(pdfs_base, 'Schindler_3300_Training.pdf'),
    '5500':        os.path.join(pdfs_base, 'Schindler_5500_יומן_שגיאות.pdf'),
    'TAC50K_1':    os.path.join(pdfs_base, 'TKE_Evolution2_Codes1.pdf'),
    'TAC50K_2':    os.path.join(pdfs_base, 'TKE_TAC50K_Codes2.pdf'),
}

print("=== בונה fault_index.json ===\n")
records += parse_cmc4plus(PDF_PATHS['CMC4+'])
records += parse_cmc4_20_50(PDF_PATHS['CMC4+20.50'])
records += parse_cmc3(PDF_PATHS['CMC3'])
records += parse_kone_kce(PDF_PATHS['KCE'])
records += parse_kone_lce(PDF_PATHS['LCE'])
records += parse_kdl16(PDF_PATHS['KDL16'])
records += parse_schindler_3300(PDF_PATHS['3300'])
records += parse_schindler_5500(PDF_PATHS['5500'])
records += parse_tac50k([PDF_PATHS['TAC50K_1'], PDF_PATHS['TAC50K_2']])

print(f"\nסה\"כ לפני ניקוי: {len(records)}")

# Deduplicate
seen_keys = set()
unique = []
for r in records:
    k = (r['normalized_controller'], r['page'])
    if k not in seen_keys:
        seen_keys.add(k)
        unique.append(r)

print(f"אחרי dedup: {len(unique)}")

by_ctrl = collections.Counter(r['normalized_controller'] for r in unique)
for ctrl, n in sorted(by_ctrl.items(), key=lambda x: -x[1]):
    print(f"  {ctrl}: {n}")

os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(unique, f, ensure_ascii=False, separators=(',', ':'))
print(f"\nנשמר: {OUT_JSON}")
