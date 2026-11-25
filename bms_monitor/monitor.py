import csv, io, json, os, re, time, logging, unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests, openpyxl, xlrd
from defusedxml import ElementTree as ET
from playwright.sync_api import sync_playwright, Error as PlaywrightError
URL='https://www.bms-fw.bayern.de/Navigation/Public/lastminute.aspx'
STATE=Path('/data/state.json')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
def norm(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD',str(s).lower().replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')).encode('ascii','ignore').decode())
def download():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, args=['--no-sandbox'])
        try:
            page=browser.new_page(accept_downloads=True)
            for attempt in range(1,4):
                try:
                    logging.info('BMS Seitenaufruf %d/3',attempt)
                    response=page.goto(URL,wait_until='domcontentloaded',timeout=60000)
                    if response is not None and response.status>=400:
                        raise RuntimeError('BMS HTTP '+str(response.status))
                    logging.info('BMS Seite geladen: %s',page.url)
                    break
                except PlaywrightError as exc:
                    logging.warning('Seitenaufruf %d/3 fehlgeschlagen: %s',attempt,exc)
                    if attempt==3:raise
                    time.sleep(5*attempt)
                    page.close()
                    page=browser.new_page(accept_downloads=True)
            button=page.get_by_text('Export',exact=True)
            if not button.count(): button=page.locator('input[value="Export"], [title="Export"], [aria-label="Export"]')
            with page.expect_download(timeout=90000) as event:
                button.first.click(timeout=30000)
            d=event.value
            return Path(d.path()).read_bytes(),d.suggested_filename
        finally: browser.close()
def rows(data,name):
    if data.startswith(b'PK'):
        book=openpyxl.load_workbook(io.BytesIO(data),read_only=True,data_only=True)
        return list(book.active.values)
    if data.startswith(bytes.fromhex('d0cf11e0')):
        sheet=xlrd.open_workbook(file_contents=data).sheet_by_index(0)
        return [sheet.row_values(i) for i in range(sheet.nrows)]
    if data.lstrip().startswith(b'<') or data.startswith((bytes.fromhex('fffe'),bytes.fromhex('feff'),bytes.fromhex('efbbbf'))):
        try: root=ET.fromstring(data)
        except ET.ParseError: root=None
        if root is not None:
            local=lambda e:e.tag.rsplit('}',1)[-1]
            if local(root).lower()=='html': raise ValueError('HTML statt Export erhalten')
            rr=[e for e in root.iter() if local(e).lower()=='row']
            if rr:
                return [[''.join(c.itertext()).strip() for c in r if local(c).lower()=='cell'] for r in rr]
            groups={}
            for e in root.iter():
                children=list(e)
                if len(children)>=4 and all(not list(c) for c in children):
                    key=tuple(local(c) for c in children)
                    groups.setdefault(key,[]).append([c.text or '' for c in children])
            if groups:
                k=max(groups,key=lambda k:len(groups[k])); return [list(k)]+groups[k]
            raise ValueError('Unbekannte XML-Struktur')
    for enc in ('utf-8-sig','utf-16','cp1252'):
        try:
            s=data.decode(enc); dialect=csv.Sniffer().sniff(s[:8192],delimiters=';,\t'); return list(csv.reader(io.StringIO(s),dialect))
        except (UnicodeError,csv.Error): pass
    raise ValueError('Unbekanntes Exportformat: '+name)
ALIASES={'title':['lehrgang','lehrgangsbezeichnung','bezeichnung','lehrgangsname','lehrgangsart'], 'key':['terminschlussel','terminschluessel','terminnummer','lehrgangsnummer','termin'], 'start':['beginn','von','lehrgangsbeginn','startdatum','datumvon'], 'end':['ende','bis','lehrgangsende','enddatum','datumbis'], 'place':['schulungsort','ort','feuerwehrschule','schule','veranstaltungsort','ausbildungsort'], 'free':['freieplatze','freieplaetze','restplatze','restplaetze','frei','anzahlfreierplatze','anzahlfreierplaetze']}
def parse_date(v):
    if isinstance(v,datetime): return v.date()
    s=str(v).strip()
    for f in ('%d.%m.%Y','%d.%m.%Y %H:%M','%Y-%m-%d','%Y-%m-%dT%H:%M:%S','%Y-%m-%d %H:%M:%S'):
        try:return datetime.strptime(s,f).date()
        except ValueError:pass
    raise ValueError('Unbekanntes Datum: '+s)
def matches(table, courses, mode):
    for i,row in enumerate(table):
        h=[norm(x) for x in row]; idx={k:next((j for j,x in enumerate(h) if x in a),None) for k,a in ALIASES.items()}
        if all(v is not None for v in idx.values()):break
    else: raise ValueError('Spalten nicht erkannt: '+repr(table[:3])[:700])
    found={}; total=0
    for row in table[i+1:]:
        if not any(str(x or '').strip() for x in row):continue
        if len(row)<=max(idx.values()):raise ValueError('Unvollständige Exportzeile')
        r={k:row[j] for k,j in idx.items()}; total+=1
        t=norm(r['title'])
        if not any((t == q if mode == 'exact' else q in t) for q in courses):continue
        if parse_date(r['start'])<datetime.now(ZoneInfo('Europe/Berlin')).date():continue
        if int(float(str(r['free']).replace(',','.')))>0:
            found[str(r['key'])]={k:str(v) for k,v in r.items()}
    logging.info('Export: %d Zeilen, %d passende Termine',total,len(found)); return found
def notify(service,title,message):
    domain,action=service.split('.',1)
    if domain!='notify':raise ValueError('notify_service muss notify.* sein')
    if action.startswith('mobile_app_'):
        payload={'title':title,'message':message,'data':{'url':URL,'clickAction':URL}}
    else:
        payload={'entity_id':service,'title':title,'message':message}
        action='send_message'
    res=requests.post('http://supervisor/core/api/services/'+domain+'/'+action,headers={'Authorization':'Bearer '+os.environ['SUPERVISOR_TOKEN']},json=payload,timeout=30)
    res.raise_for_status()
def save(state):
    tmp=STATE.with_suffix('.tmp');tmp.write_text(json.dumps(state));tmp.replace(STATE)
def main():
    cfg=json.loads(Path('/data/options.json').read_text()); service=cfg['notify_service']; interval=cfg['interval_minutes']*60
    if 'CHANGE_ME' in service:raise ValueError('Bitte notify_service konfigurieren')
    courses=[norm(x) for x in cfg.get('courses',['Gruppenführer']) if norm(x)]
    mode=cfg.get('match_mode','exact')
    if not courses or mode not in ('exact','contains'):raise ValueError('Bitte gültige Lehrgangsfilter konfigurieren')
    logging.info('Lehrgangsfilter: %s (%s)',cfg.get('courses',['Gruppenführer']),mode)
    state=json.loads(STATE.read_text()) if STATE.exists() else {'seen':{},'failures':0,'error_sent':False}
    while True:
        try:
            data,name=download(); logging.info('Export %s: %d Bytes',name,len(data)); found=matches(rows(data,name),courses,mode)
            for key,r in found.items():
                if key not in state['seen']:
                    notify(service,'🚒 FWS – freier Lehrgangsplatz!',f"{r['title']}\n{r['place']}\n{r['start']} – {r['end']}\nTerminschlüssel: {key}\nFreie Plätze: {r['free']}\n{URL}")
                    state['seen'][key]=r;save(state)
            state={'seen':found,'failures':0,'error_sent':False};save(state)
        except Exception:
            logging.exception('Prüfung fehlgeschlagen');state['failures']+=1
            if state['failures']>=3 and not state['error_sent']:
                try:notify(service,'BMS Monitor – Störung','Export konnte nicht zuverlässig geprüft werden. Bitte Restplatzbörse und Add-on-Protokoll prüfen.');state['error_sent']=True
                except Exception:logging.exception('Störungsmeldung fehlgeschlagen')
            save(state)
        time.sleep(interval)
if __name__=='__main__':main()
