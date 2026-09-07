"""Read-only catalogue comparison; never changes personal game records."""
import collections
import datetime
import difflib
import functools
import json
import os
from pathlib import Path
import re
import unicodedata
from lxml import html

CACHE = Path(os.environ['TEMP']) / 'all-game-list-audit-20260907'
ROOT = Path(__file__).resolve().parent

@functools.lru_cache(maxsize=20000)
def norm(s):
    s = unicodedata.normalize('NFKC', s).lower()
    s = re.sub(r'\(vol\.\s*\d+\)', '', s)
    roman={'i':'1','ii':'2','iii':'3','iv':'4','v':'5','vi':'6','vii':'7','viii':'8','ix':'9'}
    s = re.sub(r'(?<![a-z])(?:viii|vii|iii|vi|iv|ii|ix|v|i)(?![a-z])',lambda m:roman[m[0]],s)
    return ''.join(c for c in s if c.isalnum())

def date(s):
    m = re.search(r'(19\d\d|20\d\d)[年./-]\s*(\d{1,2})[月./-]\s*(\d{1,2})', s)
    if not m: return None
    try: return datetime.date(*map(int,m.groups())).isoformat()
    except ValueError: return None

def rows(name):
    doc = html.fromstring((CACHE/name).read_bytes())
    return doc, [[c.text_content().strip() for c in tr.xpath('./th|./td')] for tr in doc.xpath('//tr')]

def sources():
    out=[]
    def add(family,title,day,url,primary=False,platform=None):
        if day and title: out.append(dict(family=family,title=title,date=day,url=url,primary=primary,platform=platform))
    for name,fam,url,ti,di in [
        ('ws','WS','https://www.super-famicom.jp/etc00/gamelist/ws.html',0,2),
        ('ws2','WS','https://blackstraycat.nobody.jp/wonderswan/',4,3),
        ('gba2','GBA','https://www.super-famicom.jp/etc00/gamelist/gba.html',0,2),
        ('gb2','GB','https://www.super-famicom.jp/etc00/gamelist/gb.html',0,2),
        ('pce2','PCE','https://www.super-famicom.jp/etc00/gamelist/pce.html',0,2),
        ('pce','PCE','https://pcefan.com/pcengine/entry15.html',2,1),
        ('gb','GB','https://retrogamebm.com/console/gb/',0,1),
        ('nintendo_gb','GB','https://www.nintendo.co.jp/n02/dmg/index.html',0,1)]:
        for r in rows(name+'.html')[1]:
            if len(r)>max(ti,di): add(fam,r[ti],date(r[di]),url,name.startswith('nintendo'))
    for r in json.loads((CACHE/'ngp.json').read_text(encoding='utf-8')):
        add('NGP',r['title'],r['release_date'],'https://github.com/game-soft/neogeo-pocket')
    manifests=json.loads((CACHE/'gba_sources.json').read_text(encoding='utf-8'))
    manifests.append(dict(file='nintendo_gba.html',url='https://www.nintendo.co.jp/n08/index.html'))
    for source in manifests:
        doc,table=rows(source['file'])
        for r in table:
            if len(r)==4 and date(r[0]): add('GBA',r[1],date(r[0]),source['url'],True,'GBA')
        for cell in doc.xpath('//td[not(.//td)]'):
            t=cell.text_content().strip()
            if t.count('発売日')==1 and '発売日' in t and len(t)<400:
                title,rest=t.split('発売日',1)
                if '(再販)' not in rest: add('GBA',title.strip(),date(rest),source['url'],True,'GBA')
    for names,platform,url in [
        (['md_first','md_last'],'MD','https://www.sega.jp/history/hard/megadrive/software.html'),
        (['mdl_first','mdl_last','mdl_end','mdl_middle'],'MD','https://www.sega.jp/history/hard/megadrive/software_l.html'),
        (['mcd'],'MCD','https://www.sega.jp/history/hard/mega-cd/software.html'),
        (['mcdl'],'MCD','https://www.sega.jp/history/hard/mega-cd/software_l.html'),
        (['32x'],'32X','https://www.sega.jp/history/hard/super32x/software.html'),
        (['32xl'],'32X','https://www.sega.jp/history/hard/super32x/software_l.html')]:
        lines={}
        for name in names:
            path=CACHE/(name+'.txt')
            if not path.exists(): continue
            raw=path.read_text(encoding='utf-8')
            for n,s in re.findall(r'L(\d+):\s*(.*?)(?=L\d+:|\Z)',raw,re.S): lines[int(n)]=re.sub(r'cite.*?','',s).strip()
        year=None; pending=''
        for n,s in sorted(lines.items()):
            if re.fullmatch(r'19\d\d年',s): year=int(s[:4])
            if re.match(r'\d{1,2}月\s*\d{1,2}日\s*\|',s):
                pending=s
            elif pending: pending+=' '+s
            if pending.count('|')>=3 and year:
                parts=pending.split('|');m=re.search(r'(\d+)月\s*(\d+)日',parts[0])
                add('MD',parts[1].strip(),datetime.date(year,*map(int,m.groups())).isoformat(),url,True,platform)
                pending=''
    return list({tuple(r.values()):r for r in out}.values())

def compare(games,refs):
    matches=[];unmatched=[];used=set()
    keys=[norm(r['title']) for r in refs]
    for g in games:
        fam=g.get('family','NGP');key=norm(g['title'])
        pool=[(i,r) for i,r in enumerate(refs) if r['family']==fam and (not r['platform'] or r['platform']==g['platform'])]
        exact=[(i,r) for i,r in pool if keys[i]==key]
        by_url=collections.defaultdict(list)
        for i,r in exact: by_url[r['url']].append((i,r))
        exact=[pair for group in by_url.values() for pair in ([x for x in group if x[1]['date']==g['releaseDate']] or group)]
        if exact:
            used.update(i for i,r in exact)
            matches.append({'id':g['id'],'title':g['title'],'family':fam,'currentDate':g['releaseDate'],'references':[r for i,r in exact]})
        else:
            suggestions=sorted(((difflib.SequenceMatcher(None,key,keys[i]).ratio(),r) for i,r in pool),key=lambda x:x[0],reverse=True)[:3]
            unmatched.append({'id':g['id'],'title':g['title'],'family':fam,'date':g['releaseDate'],'suggestions':[{'score':round(s,3),**r} for s,r in suggestions]})
    missing=[r for i,r in enumerate(refs) if i not in used]
    return dict(matches=matches,unmatched=unmatched,referenceOnly=missing)

if __name__=='__main__':
    games=json.loads((ROOT/'library.json').read_text(encoding='utf-8'))['games']
    refs=sources();result=compare(games,refs)
    (CACHE/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REFERENCES',dict(collections.Counter(r['family'] for r in refs)))
    print('MATCHES',dict(collections.Counter(r['family'] for r in result['matches'])))
    print('UNMATCHED',dict(collections.Counter(r['family'] for r in result['unmatched'])))
    for r in result['matches']:
        dates=sorted(set(s['date'] for s in r['references']))
        if dates!=[r['currentDate']]:print('DATE',r['id'],r['title'],r['currentDate'],dates)
