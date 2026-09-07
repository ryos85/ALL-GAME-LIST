"""Import a reviewed, public catalogue without replacing personal records.

--build-cache reads locally cached Japanese publisher/catalogue sources and writes
追加ハードの発売一覧.json. Normal execution applies that snapshot, offline.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / '追加ハードの発売一覧.json'
CHECKED = '2026-09-07'
FAMILIES = {'N64':'ニンテンドウ64','GC':'ゲームキューブ','NDS':'ニンテンドーDS',
            '3DS':'ニンテンドー3DS','PS':'プレイステーション','PS2':'プレイステーション2',
            'PS3':'プレイステーション3','PSP':'プレイステーション・ポータブル',
            'PSV':'PlayStation Vita','GG':'ゲームギア','PC-FX':'PC-FX'}
FAMITSU_CODES = dict(zip(['n64','cube','ds','3ds','ps','ps2','ps3','psp','psv','gg','pcfx'], FAMILIES))
EDITION = re.compile(r'限定|同梱|パック|セット|BOX|ボックス|コレクター|プレミアム|LIMITED|PACK|SET|パッケージ|特典|Best|ベスト|べすと|定番|殿堂|カプコレ|PS\s*one\s*Books|廉価|価格|プライス|PRICE|VALUE|バリュ|割引|キャンペーン|マル得|お買い得|お得|再発売|Super\s*Lite|スーパーライト|Major\s*Wave|Mejor\s*Wave|マル安|ポップ.?コレクション|円|TAITO2000|Magical\s*1500|Choice|復刻|テクコレ|サンコレ|ヒッツ|HITS|セレクト|セレクション|ミレニアム.?コレクション|なつコレ|夏キャン|IFコレクション|ぽっきり|EPV|ライブラリー|サマーチャンス|シスコン.?ゲームギャラリー|エビコレ|アニバーサリー|三昧シリーズ|アスキー.?カジュアルコレクション|ビクターホラーコレクション|エンターブレイン.?コレクション|キーボード|コントローラ|ガンコン|ジョグコン|マイク|携帯電話接続|ポケットステーションもいっしょ|サンリオ流通',re.I)
EXCLUDE_TITLE = re.compile(r'追加コンテンツ|ダウンロードコンテンツ|\bDLC\b|追加楽曲|シーズンパス|体験版|更新データ|デジコロ|どこぽんちょいす|データ移行アプリ|予告編|ハンドル for|^アニメ 蒼き雷霆|^LEGO.*ムービー 3D$',re.I)
EXTRA_EDITION = re.compile(r'D-Collection|EA[:：]SY|プラチナ.?リミテッド|\d+コレクション|電撃SP|でらっくすぱっく|初回(?:プレス|生産)|特装|特別版|Platinum Collection|ぐっどぷらいす|SELECTION|感謝祭|神子手箱|クリーナー|ポーチ付き|ドラマCD付|SIMPLE\s*2000|アタリホット|BUNDLE|ベルベット.?モデル|NEW(?:リンコ|マナカ|ネネ)デラックス|SPECIAL\s+EDITION|バンダイナムコスペシャル|優待DL',re.I)
HARDWARE_TITLE = re.compile(r'^(?:PlayStation\s*(?:3\b|Vita\b)|プレイステーション[３3]|プレイステーション[・･]?ポータブル|ニンテンドー3DS(?:\s*[（(]|\s+LL)|ニンテンドーDS\s*(?:Lite|i\b)|ワイヤレスコントローラー|PSP-\d)',re.I)
PLATFORMS = {code:{'name':name,'badge':code,'family':code} for code,name in FAMILIES.items()}
PLATFORMS.update({
    'N64-DD': {'name':'ニンテンドウ64・64DD専用','badge':'64DD','family':'N64'},
    'DSi': {'name':'ニンテンドーDSi専用・DSiウェア','badge':'DSi専用','family':'NDS'},
    'New3DS': {'name':'Newニンテンドー3DS専用','badge':'New 3DS専用','family':'3DS'},
    '3DS-VC': {'name':'3DS バーチャルコンソール','badge':'3DS VC','family':'3DS'},
    'New3DS-VC': {'name':'New 3DS専用 バーチャルコンソール','badge':'New 3DS VC','family':'3DS'},
})

def text(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()

def title_key(value):
    value=unicodedata.normalize('NFKC',value).casefold()
    return ''.join(c for c in value if c.isalnum())

def clean_title(value):
    # Remove distribution/packaging labels only. Subtitles and remake names stay.
    value=text(value)
    labels=r'通常版|ソフト単体版|ソフト単品版|単体版|PS Store ダウンロード版|ニンテンドーeショップ ダウンロード版|DSiウェア ダウンロード版|3DSダウンロード(?:ソフト|版)|New3DS専用・3DSダウンロードソフト|(?:New3DS専用・|3DS |ゲームボーイアドバンス )?バーチャルコンソール版'
    value=re.sub(r'\s*[（(](?:'+labels+r')[）)]','',value)
    value=re.sub(r'\s*[（(][^（）()]*ダウンロード(?:版|ソフト)[^（）()]*[）)]','',value)
    value=re.sub(r'\s*[（(](?:New3DS専用|ソフト単体)[）)]','',value)
    value=re.sub(r'\s*(?:PlayStation\s*[23]?|PS[23P]?)\s+the\s+Best\s*',' ',value,flags=re.I)
    value=re.sub(r'^Newニンテンドー3DS専用\s*','',value)
    value=re.sub(r'【配信終了】','',value)
    value=re.sub(r'\s*[（(]\s*[）)]','',value)
    return value.strip()

def edition_title(value):
    value=clean_title(value)
    return re.sub(r'\s*[（(]([^（）()]+)[）)]',lambda m:'' if EDITION.search(m[1]) or EXTRA_EDITION.search(m[1]) else m[0],value).strip()

def split_versions(versions):
    chosen=min([v for v in versions if v['isMain']] or versions,key=lambda v:(v['releaseDateOrder'],v['id']))
    canonical={title_key(edition_title(chosen['nameJa'])):chosen}
    for v in sorted(versions,key=lambda v:(v['releaseDateOrder'],v['id'])):
        name=edition_title(v['nameJa']);key=title_key(name)
        if not key or key in canonical:continue
        if EDITION.search(v['nameJa']) or EXTRA_EDITION.search(v['nameJa']):continue
        if re.search(r'Edition|エディション',name,re.I) and title_key(clean_title(chosen['nameJa'])) in key:continue
        # A label-free different title is a content variant (e.g. Pokemon Y,
        # Medarot Kuwagata, an expansion disc), not a limited package.
        canonical[key]=v
    buckets={key:[] for key in canonical}
    for v in versions:
        key=title_key(edition_title(v['nameJa']))
        if key in buckets:target=key
        else:
            matches=[k for k in canonical if k in key]
            target=max(matches,key=len) if matches else next(iter(canonical))
        buckets[target].append(v)
    return [(canonical[key],items) for key,items in buckets.items()]

def date(value):
    nums=re.findall(r'\d+',str(value))
    if len(nums)==1 and len(nums[0])==8: nums=[nums[0][:4],nums[0][4:6],nums[0][6:]]
    if len(nums)<3: return ''
    try: return dt.date(*map(int,nums[:3])).isoformat()
    except ValueError: return ''

def row(platform,title,release,publisher='',genre='',source='',grade='catalogue',**extra):
    assert platform in PLATFORMS and date(release), (platform,title,release)
    return dict(platform=platform,title=text(title),releaseDate=date(release),
                publisher=text(publisher),genre=text(genre),sources=[source],grade=grade,**extra)

def famitsu_records(cache):
    groups=defaultdict(dict)
    for file in sorted(cache.glob('fm_*.json')):
        for item in json.loads(file.read_text(encoding='utf8')):
            if item['isGlobal'] or '【海外' in item['nameJa']: continue
            if EXCLUDE_TITLE.search(item['nameJa']): continue
            groups[(item['platform'],item['groupId'])][item['id']]=item
    originals=defaultdict(set)
    for (platform,_),versions in groups.items():
        for v in versions.values():
            if not v['isDownload']: originals[v['gameTitleId']].add(platform)
    result=[]
    expanded=[(platform,group_id,chosen,items) for (platform,group_id),versions in groups.items()
              for chosen,items in split_versions(list(versions.values()))]
    for platform,group_id,chosen,versions in expanded:
        # PS1/PS2/PSP compatibility downloads are not releases for the receiving
        # hardware; old PS Store dates can even precede Vita's launch.
        old=originals[chosen['gameTitleId']]
        if all(v['isDownload'] for v in versions):
            if platform in {'psp','ps3','psv'} and ('ps' in old or 'PCエンジン版' in chosen['nameJa']): continue
            if platform=='ps3' and 'ps2' in old: continue
            if platform=='psv' and 'psp' in old: continue
        code=FAMITSU_CODES[platform]
        name=chosen['nameJa']
        if platform=='ds' and 'DSi' in name: code='DSi'
        if platform=='3ds':
            if 'バーチャルコンソール' in name: code='New3DS-VC' if 'New3DS' in name else '3DS-VC'
            elif 'New3DS専用' in name: code='New3DS'
        release=date(chosen['releaseDateOrder'])
        if not release:
            # Keep partial dates transparent, never turn a date ending 32 into
            # an invented day. The explicit date can be supplied by another source.
            continue
        r=row(code,edition_title(name),release,source=f'https://www.famitsu.com/game/title/{group_id}/page/1',
              grade='press',famitsuGroup=group_id,gameTitleId=chosen['gameTitleId'],
              famitsuItem=chosen['id'],
              distribution='download' if all(v['isDownload'] for v in versions) else 'package',
              variants=[{'title':v['nameJa'],'releaseDate':date(v['releaseDateOrder']),
                         'source':f'https://www.famitsu.com/game/title/{group_id}/page/1'}
                        for v in sorted(versions,key=lambda v:(v['releaseDateOrder'],v['id'])) if v['id']!=chosen['id']])
        result.append(r)
    return result

def html_rows(cache,name,encoding=None):
    from lxml import html
    raw=(cache/(name+'.html')).read_bytes()
    doc=html.fromstring(raw.decode(encoding) if encoding else raw)
    for tr in doc.xpath('//tr'):
        cells=tr.xpath('./td|./th')
        if len(cells)>=3 and len(tr.text_content())<1800:
            yield [text(c.text_content()) for c in cells]

def supplements(cache):
    result=[]
    for name in ['n64']+[f'n64_{y}' for y in range(1996,2000)]:
        url='https://www.nintendo.co.jp/n01/n64/software/'+('allsoft.html' if name=='n64' else name[4:]+'.html')
        for c in html_rows(cache,name,'cp932'):
            if date(c[0]): result.append(row('N64',c[1],c[0],c[2],c[3],url,'official'))
    for name,code in [('n64list','N64'),('gc','GC'),('ds','NDS')]+[(f'ps{i}','PS') for i in range(4)]:
        file='n64.html' if name=='n64list' else f'ps_0{name[-1]}.html' if name.startswith('ps') else name+'.html'
        url='https://www.super-famicom.jp/etc00/gamelist/'+file
        for c in html_rows(cache,name):
            if name=='ds':
                if date(c[0]):result.append(row(code,c[1],c[0],c[2],c[3],url))
            elif len(c)>3 and date(c[2]):
                platform='N64-DD' if code=='N64' and '64DD' in ' '.join(c) else code
                result.append(row(platform,c[0],c[2],c[1],c[3 if code=='PS' else 4],url))
    for c in html_rows(cache,'pcfx'):
        if date(c[0]):result.append(row('PC-FX',c[1],c[0],c[2],source='https://www.gavas.jp/user_data/pcfx_game_title.php'))
    for name,licensee in [('gg_official',False),('gg_license',True)]:
        raw=(cache/(name+'.txt')).read_text(encoding='utf8')
        raw=re.sub(r'cite.*?','',raw)
        raw=re.sub(r'L\d+:\s*','\n',raw)
        raw=raw[raw.index('発売日  | タイトル'):]
        year=0
        entries=re.split(r'(?m)(?=^\s*(?:19\d{2}年|\d{1,2}月\s*\d{1,2}日\s*\|))',raw)
        for entry in entries:
            entry=entry.strip()
            y=re.match(r'(19\d{2})年',entry)
            if y:year=int(y[1]);continue
            m=re.match(r'(\d{1,2})月\s*(\d{1,2})日\s*\|',entry)
            if not m:continue
            c=[text(x) for x in entry.split('|')]
            if len(c)<5: raise ValueError('Invalid SEGA table row')
            title=re.sub(r'\(ゲームギア本体に.*?同梱\)','',c[1])
            url='https://www.sega.jp/history/hard/gamegear/software'+('_l' if licensee else '')+'.html'
            result.append(row('GG',title,f'{year}/{m[1]}/{m[2]}',c[2] if licensee else 'セガ',c[3] if licensee else c[2],url,'official'))
    for file in sorted(cache.glob('ctr_*.json')):
        for item in json.loads(file.read_text(encoding='utf8')):
            if EXCLUDE_TITLE.search(item['title']):continue
            form=item['sform'];code='New3DS' if form.startswith('KTR') else '3DS'
            if '/' in form or form in {'CTR_GB','CTR_GBC','CTR_GAMEGEAR'}:
                code='New3DS-VC' if form.startswith('KTR') else '3DS-VC'
            release=date(item['sdate'])
            if not release: continue
            result.append(row(code,item['title'],release,item['maker'],' / '.join(item['genre'] or []),
                'https://www.nintendo.co.jp/software/3ds/index_all.html','official',nintendoId=item['id'],
                distribution='package' if form in {'CTR','CTR_DOWNLOADABLE','KTR_DOWNLOADABLE'} else 'download'))
    return result

def gdr_supplements(cache):
    from lxml import html
    genres={'ACT':'アクション','RPG':'ロールプレイング','AADV':'アクションアドベンチャー',
            'ADV':'アドベンチャー','SLT':'シミュレーション','SPT':'スポーツ','RCG':'レース',
            'STG':'シューティング','PZL':'パズル','TBL':'テーブル','FTG':'対戦格闘','Etc':'その他'}
    result=[]
    for file in cache.glob('gdrmeta_*.html'):
        code=file.name.split('_')[1]
        doc=html.fromstring(file.read_bytes())
        for tr in doc.xpath('//tr'):
            cells=tr.xpath('./td')
            if len(cells)<6 or len(tr.text_content())>1600 or not date(cells[0].text_content()):continue
            for span in tr.xpath('.//span[@class="EN"]'):span.drop_tree()
            c=[text(x.text_content()) for x in cells]
            result.append(row(code,c[1],c[0],c[2].split('/')[0],genres.get(c[3],c[3]),
                              'https://tk-nz.game.coocan.jp/gamedatabase/software/'+file.name.split('_',2)[2]))
    return result

def attach_details(base,cache):
    details={}
    for file in cache.glob('md_*.json'):
        details[int(file.stem[3:])]=json.loads(file.read_text(encoding='utf8'))
    result=[]
    for r in base:
        detail=details.get(r.get('famitsuGroup'),{})
        genre=detail.get('genre') or ''
        # A group can include a console bundle and a real game. Drop hardware
        # only if its entire genre is hardware, not combined game genres.
        if genre=='本体・周辺商品' or HARDWARE_TITLE.search(r['title']):continue
        if not r.get('publisher'):r['publisher']=detail.get('manufacturer') or ''
        if not r.get('genre'):r['genre']=genre.replace('本体・周辺商品 / ','').replace(' / 本体・周辺商品','')
        result.append(r)
    return result

def consolidate_exact(base):
    lookup={}
    for r in sorted(base,key=lambda r:r['releaseDate']):
        key=(r['platform'],title_key(edition_title(r['title'])))
        if key not in lookup:lookup[key]=r;continue
        target=lookup[key]
        for u in r['sources']:
            if u not in target['sources']:target['sources'].append(u)
        target.setdefault('variants',[]).extend(r.get('variants',[]))
        target['variants'].append({'title':r['title'],'releaseDate':r['releaseDate'],'source':r['sources'][0]})
    for r in lookup.values():
        unique={ (v['title'],v['releaseDate']):v for v in r.get('variants',[]) }
        r['variants']=list(unique.values())
    return list(lookup.values())

def merge_sources(base,extra):
    """Match exact normalized titles only; ambiguous/fuzzy matches need review."""
    lookup=defaultdict(list)
    for r in base:lookup[(r['platform'],title_key(r['title']))].append(r)
    unmatched=[]
    for r in extra:
        key=(r['platform'],title_key(clean_title(r['title'])))
        candidates=lookup[key]
        # Several press records omit the New 3DS restriction in the title.
        # The official software form is the authority for this hardware split.
        if not candidates and r.get('nintendoId') and r['platform']=='New3DS':
            candidates=lookup[('3DS',key[1])]
            if len(candidates)==1:candidates[0]['platform']='New3DS'
        match=candidates[0] if len(candidates)==1 else next((x for x in candidates if x['releaseDate']==r['releaseDate']),None)
        if match is None:
            unmatched.append(r)
            continue
        for source in r['sources']:
            if source not in match['sources']:match['sources'].append(source)
        for field in ['publisher','genre']:
            if r.get(field) and (not match.get(field) or r['grade']=='official'):match[field]=r[field]
        if r['grade']=='official':
            # An eShop rerelease can be later than the original cartridge.
            if not r.get('nintendoId') or r['releaseDate']<=match['releaseDate']:
                match['releaseDate']=r['releaseDate'];match['grade']='official'
            if r.get('nintendoId'):match['nintendoId']=r['nintendoId']
    return base,unmatched

def make_game(r):
    code=r['platform']
    # Source-based stable identity keeps notes attached if title spelling changes.
    identity='famitsu:'+str(r.get('famitsuItem',r['famitsuGroup'])) if r.get('famitsuGroup') else 'nintendo:'+r['nintendoId'] if r.get('nintendoId') else title_key(r['title'])
    gid='catalog-'+code.lower()+'-'+hashlib.sha256(identity.encode()).hexdigest()[:16]
    return {'id':gid,'title':r['title'],'family':PLATFORMS[code]['family'],'platform':code,
            'releaseDate':r['releaseDate'],'publisher':r.get('publisher') or '未確認',
            'genre':r.get('genre') or '未分類','originalGenre':r.get('genre') or '',
            'interest':'unknown','owned':'unknown','wanted':False,'memo':'','legacy':{},'sourceRecords':[],
            'compatibilityLabel':PLATFORMS[code]['name'],
            'classificationNote':'国内の発売記録から追加。通常版・廉価版・限定パッケージは同一機種内で統合。',
            'classificationSources':r['sources'],'releaseDateSources':r['sources'],
            'releaseDateVerification':{'grade':r['grade'],'checkedAt':CHECKED,'note':'参照資料の発売日を採用。','sources':r['sources']},
            'catalogVariants':r.get('variants',[]),'catalogImport':'additional-hardware-2026-09',
            'aliases':list(dict.fromkeys([v['title'] for v in r.get('variants',[])])),
            'distribution':r.get('distribution','package')}

def apply_snapshot(data,snapshot):
    result=copy.deepcopy(data)
    existing={g['id'] for g in result['games']}
    added=[]
    for r in snapshot['games']:
        game=make_game(r)
        if game['id'] not in existing:
            existing.add(game['id']);result['games'].append(game);added.append(game)
    if added:
        result['platforms'].update({k:v for k,v in PLATFORMS.items() if any(g['platform']==k for g in added)})
        result['families'].update(FAMILIES)
        result['revision']+=1
        result['updatedAt']=dt.datetime.now(dt.timezone.utc).isoformat()
        result['additionalHardwareImport']={'checkedAt':CHECKED,'counts':dict(Counter(g['family'] for g in added)),
                                           'scope':snapshot['scope']}
    return result,len(added)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build-cache',type=Path)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if args.build_cache:
        base=famitsu_records(args.build_cache)
        extra=supplements(args.build_cache)
        # These two full hardware lists have stronger coverage/metadata than the
        # press database. Use their titles as the base, retaining official dates.
        base=[r for r in base if r['platform'] not in {'GG','N64'}]
        base += [r for r in extra if r['platform']=='GG' or
                 (r['platform'] in {'N64','N64-DD'} and 'super-famicom.jp' in r['sources'][0])]
        base,unmatched=merge_sources(base,extra)
        base,_=merge_sources(base,gdr_supplements(args.build_cache))
        # Six official-only New 3DS releases absent from the press snapshot.
        for r in unmatched:
            if r['platform']=='New3DS-VC' or (r['platform']=='New3DS' and r['title'].startswith('密着対戦')):
                base.append(r)
        base=consolidate_exact(attach_details(base,args.build_cache))
        (args.build_cache/'unmatched.json').write_text(json.dumps(unmatched,ensure_ascii=False,indent=2),encoding='utf8')
        SNAPSHOT.write_text(json.dumps({'checkedAt':CHECKED,'scope':'国内発売作品。通常版・再販・限定パッケージを統合。DSi専用・New 3DS専用・3DS VCは別区分。海外版、追加コンテンツ、PS系の旧機種互換配信は除外。','games':base},ensure_ascii=False,indent=2),encoding='utf8')
        print('Base:',dict(Counter(r['platform'] for r in base)),'Unmatched supplements:',dict(Counter(r['platform'] for r in unmatched)))
    if args.apply:
        import game_library
        data,count=apply_snapshot(game_library.library(),json.loads(SNAPSHOT.read_text(encoding='utf8')))
        if count:game_library.write_atomic(ROOT/'library.json',data)
        print('Added:',count,'Total:',len(data['games']))

if __name__=='__main__':main()
