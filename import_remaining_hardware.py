"""Import SFC, Saturn and Dreamcast from cached Japanese catalogue sources."""
import argparse
import copy
import json
import re
import unicodedata
from urllib.parse import urljoin
from collections import Counter
from pathlib import Path

from lxml import html
import import_hardware_catalog as catalog

TARGETS = {'SFC','SFC-NP','SFC-TURBO','SS','DC','DC-VM'}
SEGA_PAGES = {'ss_sega':('SS','segasaturn',False),'ss_license':('SS','segasaturn',True),
              'dc_sega':('DC','dreamcast',False),'dc_license':('DC','dreamcast',True)}


def sfc_records(cache):
    url='https://super-famicom.jp/d_03.html'
    doc=html.fromstring((cache/'sfc_index.html').read_bytes())
    result=[]
    for tr in doc.xpath('//tr')[1:]:
        c=[catalog.text(x.text_content()) for x in tr.xpath('./td|./th')]
        if len(c)!=6 or not catalog.date(c[2]):
            raise ValueError(f'Unexpected SFC catalogue row: {c}')
        title,publisher,release,genre,_,note=c
        code='SFC-TURBO' if title.startswith('スーファミターボ専用') else 'SFC-NP' if 'ニンテンドーパワー専用' in note else 'SFC'
        title=re.sub(r'^スーファミターボ専用\s*','',title)
        links=[url]+[urljoin(url,a) for a in tr.xpath('./td[1]//a/@href')]
        r=catalog.row(code,title,release,publisher,genre,url,sourceNote=note if note!='－' else '')
        r['sources']=links
        r['variants']=[]
        for label,d in re.findall(r'(廉価版|復刻版)：(\d{4}/\d{1,2}/\d{1,2})',note):
            r['variants'].append({'title':title+'（'+label+'）','releaseDate':catalog.date(d),'source':url})
        result.append(r)
    return result


def sega_records(cache,name):
    platform,hardware,licensee=SEGA_PAGES[name]
    url=f'https://www.sega.jp/history/hard/{hardware}/software'+('_l' if licensee else '')+'.html'
    raw=(cache/(name+'.txt')).read_text('utf-8')
    raw=re.sub(r'cite.*?','',raw)
    raw=re.sub(r'L\d+:\s*','\n',raw)
    raw=raw[raw.index('発売日  | タイトル'):]
    # Split at date/year/section boundaries, retaining wrapped title lines.
    parts=re.split(r'(?m)(?=^\s*(?:(?:19|20)\d{2}年?\s*$|\d{1,2}月\s*\d{1,2}日\s*\||##### |## よく))',raw)
    result=[];year=None;code=platform
    for part in parts:
        part=part.strip()
        if part.startswith('## よく'):break
        if '##### ソフト内蔵ビジュアルメモリ' in part:code='DC-VM';continue
        y=re.match(r'^((?:19|20)\d{2})年?(?:\s|$)',part)
        if y:year=int(y[1]);continue
        m=re.match(r'^(\d{1,2})月\s*(\d{1,2})日\s*\|',part)
        if not m:continue
        c=[catalog.text(x) for x in part.split('|')]
        if not year or len(c)<5:raise ValueError(f'Incomplete SEGA row: {c}')
        title=c[1]
        publisher=c[2] if licensee else 'セガ'
        genre=c[3] if licensee else c[2]
        product=c[5 if licensee else 4] if code!='DC-VM' else ''
        r=catalog.row(code,title,f'{year}/{m[1]}/{m[2]}',publisher,genre,url,'official',productCode=product)
        if code=='SS' and product=='T-32103G':
            # The official table repeats Vol.3; the product/date identify Vol.2.
            r['title']=title.replace('Vol.3','Vol.2')
            sources=['https://www.famitsu.com/game/title/15242/page/1',
                     'https://www.gavas.jp/products/detail.php?product_id=1820']
            r['sources'].extend(sources)
            r['catalogReview']=[{'kind':'タイトル','status':'訂正済み','before':title,'after':r['title'],
                                 'note':'型番T-32103G・1998年1月15日発売はVol.2。国内2資料で照合。','sources':sources}]
        result.append(r)
    if not result:raise ValueError('Empty SEGA catalogue: '+name)
    return result


def package_title(title):
    """Remove explicit packaging labels, never content/version subtitles."""
    title=re.sub(r'\s*[（(][^()（）]*?(?:限定|通常版|同梱|@barai|ドリコレ|サタコレ|お買い得|廉価)[^()（）]*[）)]','',title,flags=re.I)
    title=re.sub(r'\s*(?:メモリアルパック|ドリコレ|サタコレ)\s*$','',title)
    return catalog.text(title)


def merge_packages(records):
    result={}
    for r in sorted(records,key=lambda r:r['releaseDate']):
        original=r['title'];r=copy.deepcopy(r);r['title']=package_title(original)
        identity=catalog.title_key(r['title'])+'+'*unicodedata.normalize('NFKC',r['title']).count('+')
        key=(r['platform'],identity)
        r['catalogId']='japan:'+r['platform']+':'+identity
        variant={'title':original,'releaseDate':r['releaseDate'],'source':r['sources'][0]}
        if key in result:
            result[key].setdefault('variants',[]).append(variant)
            result[key]['variants'].extend(r.get('variants',[]))
            for source in r['sources']:
                if source not in result[key]['sources']:result[key]['sources'].append(source)
        else:
            result[key]=r
            if original!=r['title']:r.setdefault('variants',[]).append(variant)
    return list(result.values())


def three_hardware_records(cache):
    raw=sfc_records(cache)
    for name in SEGA_PAGES:raw.extend(sega_records(cache,name))
    return merge_bundles(merge_packages(raw))


def merge_bundles(records):
    # Existing discs sold together are recorded on each constituent game.
    # New compilations such as Suchie-Pai Mecha Genteiban retain their own entry.
    bundles={
        ('SS','大戦略パック'):['ワールドアドバンスド大戦略 ～鋼鉄の戦風～','ワールドアドバンスド大戦略 作戦ファイル'],
        ('SS','ＥＭＩＴ バリューセット'):['ＥＭＩＴ Vol.1 ～時の迷子～','ＥＭＩＴ Vol.2 ～命がけの旅～','ＥＭＩＴ Vol.3 ～私にさよならを～'],
        ('SS','三國志 バリューセット'):['三國志Ⅴ','三國志リターンズ'],
        ('SS','信長の野望 バリューセット'):['信長の野望・天翔記','信長の野望リターンズ'],
        ('SS','ＳＳアドベンチャーパック 七つの秘館＆ＭＹＳＴ'):['七つの秘館','ＭＹＳＴ'],
        ('SS','バーチャコップ スペシャルパック'):['バーチャコップ','バーチャコップ２'],
        ('SS','イブ・バーストエラー＆DESIRE バリューパック'):['イヴ・バーストエラー','ＤＥＳＩＲＥ'],
        ('SS','イブ・ザ・ロストワン＆DESIRE バリューパック'):['イブ・ザ・ロストワン','ＤＥＳＩＲＥ'],
        ('SS','イブ・バーストエラー＆イブ・ザ・ロストワン バリューパック'):['イヴ・バーストエラー','イブ・ザ・ロストワン'],
        ('SS','ルームメイト 井上涼子 ～COMPLETE BOX～'):['ルームメイト ～井上涼子～','ルームメイト ～涼子 in Summer Vacation～','ルームメイト３ ～涼子 風の輝く朝に～','涼子のおしゃべりルーム'],
        ('DC','サクラ大戦 COMPLETE BOX'):['サクラ大戦','サクラ大戦２ ～君、死にたもうことなかれ～','サクラ大戦３ ～巴里は燃えているか～','サクラ大戦４ ～恋せよ乙女～'],
    }
    lookup={(r['platform'],catalog.title_key(r['title'])):r for r in records}
    removed=set()
    for (code,title),contents in bundles.items():
        key=(code,catalog.title_key(title));bundle=lookup.get(key)
        if not bundle:continue
        for member in contents:
            target=lookup[(code,catalog.title_key(member))]
            target.setdefault('variants',[]).append({'title':bundle['title'],'releaseDate':bundle['releaseDate'],'source':bundle['sources'][0]})
        removed.add(bundle['catalogId'])
    return [r for r in records if r['catalogId'] not in removed]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build-cache',type=Path,required=True)
    args=parser.parse_args()
    added=three_hardware_records(args.build_cache)
    snapshot=json.loads(catalog.SNAPSHOT.read_text('utf-8'))
    snapshot['games']=[r for r in snapshot['games'] if r['platform'] not in TARGETS]+added
    snapshot['scope']='国内発売作品。通常版・再販・限定パッケージを統合。専用媒体・追加機能はカテゴリ別。海外版・追加コンテンツ・旧機種互換配信を除外。'
    catalog.SNAPSHOT.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
    print('New catalogue:',dict(Counter(r['platform'] for r in added)))


if __name__=='__main__':main()
