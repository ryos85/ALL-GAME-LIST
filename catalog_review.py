"""Build a dated audit report and apply only explicitly reviewed catalogue fixes."""
import argparse
import collections
import copy
import html
import json
from pathlib import Path
import audit_catalog as audit
import game_library as storage

ROOT = Path(__file__).resolve().parent
ALIASES = {
 'ngp-045':'パーティメール', 'ngp-049':'機甲世紀ユニトロン',
 'ngp-053':'神機世界エヴァリューション はてしないダンジョン',
 'ngp-055':'クルーボーダーズ ポケット',
 'ngp-058':'幕末浪漫 特別編 月華の剣士 月に咲く花、散りゆく華',
 'ngp-063':'メモリーズオフ・ピュア', 'ngp-066':'がんばれねおぽけくん（仮）',
 'ngp-076':'インフィニティ・キュア',
 'md-045':'ESWAT：サイバーポリス イースワット', 'md-060':'ＦＺ戦記ＡＸＩＳ',
 'md-231':'ひょっこりひょうたん島', 'md-269':'ロードブラスターＦＸ',
 'md-306':'三國志Ⅲ＜MEGA-CD版＞', 'md-308':'スイッチ',
 'md-360':'蒼き狼と白き牝鹿・元朝秘史 ＜MEGA-CD版＞',
 'md-367':'パーティークイズ ＭＥＧＡ Ｑ', 'md-431':'信長の野望・覇王伝',
 'md-445':'FORMULA ONE WORLD CHAMPIONSHIP 1993 HEAVENLY SYMPHONY',
 'md-473':'シャドー・オブ・ザ・ビーストⅡ 獣神の呪縛', 'md-505':'ＮＢＡ ＪＡＭ',
 'md-518':'GOLF MAGAZINE PRESENTS 36 GREAT HOLES STARRING FRED COUPLES',
}
# The listed source title was reviewed as the same release; automatic fuzzy matches
# are never used to change a record or declare an omission.
TITLE_FIXES = {
 'gba-007':'F-ZERO FOR GAMEBOY ADVANCE',
 'gba-027':'全日本GT選手権',
 'gba-069':'ロボットポンコッツ２ リングバージョン／クロスバージョン',
 'gba-070':'ロボットポンコッツ２ リングバージョン／クロスバージョン',
 'gba-091':'Adventure of TOKYO Disney SEA',
 'gba-138':'GUILTY GEAR X ADVANCE EDITION',
 'gba-155':'沈黙の遺跡〜エストポリス外伝〜',
 'gba-158':'GROOVE ADVENTURE RAVE 〜光と闇の大決戦〜',
 'gba-196':'モトクロスマニアックスADVANCE',
 'gba-207':'かまいたちの夜 〜ADVANCE〜',
 'gba-256':'伝説のスタフィー',
 'gba-261':'GROOVE ADVENTURE RAVE 光と闇の大決戦２',
 'gba-265':'ちょびっツ for Gameboy Advance アタシだけのヒト',
 'gba-428':'スーパーロボット大戦Ｄ',
 'gba-478':'ゲゲゲの鬼太郎 危機一髪！妖怪列島',
 'gba-518':'ダブルドラゴン 双載龍 Advance',
 'gba-588':'ＦＩＮＡＬ ＦＡＮＴＡＳＹ Ｉ・ＩＩ ＡＤＶＡＮＣＥ',
 'gba-596':'シャイニング・フォース〜黒き竜の復活〜',
 'md-269':'ロードブラスターＦＸ',
 'md-473':'シャドー・オブ・ザ・ビーストⅡ 獣神の呪縛',
}
DATE_IDS = {'md-488','md-530','md-533','md-534','md-535','md-537','md-542','md-546',
            'gba-176','gba-431','gba-536'}
ADDITIONS = [
 ('gba-gbw12','ゲームボーイウォーズアドバンス1+2','2004-11-25','任天堂','シミュレーション',
  'https://www.nintendo.co.jp/n08/before/n2005_b01.html'),
 ('gba-twin01','めざせデビュー！ファッションデザイナー物語＋かわいいペットゲームギャラリー２','2004-08-12','カルチャーブレーン','アドベンチャー',
  'https://www.nintendo.co.jp/n08/before/04_0810.html'),
]

def build(current, refs):
    original = current['games']
    result=copy.deepcopy(current)
    issues=[];rows=[]
    # Audit the pre-change snapshot, including preserved original Excel spellings.
    for g in original:
        family=g.get('family','NGP')
        keys={audit.norm(g['title'])}
        if g['id'] in ALIASES:keys.add(audit.norm(ALIASES[g['id']]))
        pool=[r for r in refs if r['family']==family and audit.norm(r['title']) in keys
              and (not r['platform'] or r['platform']==g['platform'])]
        by_url=collections.defaultdict(list)
        for r in pool:by_url[r['url']].append(r)
        pool=[r for rs in by_url.values() for r in ([x for x in rs if x['date']==g['releaseDate']] or rs)]
        independent=[r for r in pool if 'super-famicom.jp' not in r['url']]
        different=[r for r in independent if r['date']!=g['releaseDate']]
        # A monochrome release is not a conflicting date for its colour remake.
        if g['id'] in {'gb-834','gb-846'}:different=[]
        if g['id']=='gb-708':different=[] # reference's Unix epoch placeholder is not a release date
        rows.append(dict(id=g['id'],title=g['title'],family=family,platform=g['platform'],date=g['releaseDate'],
                         status='日付相違' if different else '公式一覧一致' if any(r['primary'] for r in pool) else '別一覧一致' if independent else '元表系一覧のみ' if pool else '照合保留',references=pool))
        if different:
            issues.append(dict(kind='発売日',status='訂正済み' if g['id'] in DATE_IDS else '資料間不一致',id=g['id'],family=family,title=g['title'],before=g['releaseDate'],after=' / '.join(sorted({r['date'] for r in different})),sources=list(dict.fromkeys(r['url'] for r in different))))
        if any(k in g['title'] for k in ['廉価','ハッピープライス','再版','[復刻版]','HUDSON THE BEST','スペシャルエディション']):
            issues.append(dict(kind='再販・別版',status='統合候補',id=g['id'],family=family,title=g['title'],before=g['releaseDate'],after='通常版との内容・個人記録の対応を確認してから統合',sources=[]))
    lookup={g['id']:g for g in result['games']}
    for ident in DATE_IDS:
        g=lookup[ident]
        found=[r for r in refs if r['primary'] and r['family']==g.get('family') and audit.norm(r['title'])==audit.norm(g['title']) and (not r['platform'] or r['platform']==g['platform'])]
        dates={r['date'] for r in found}
        if len(dates)!=1:raise ValueError(f'Ambiguous reviewed date: {ident}')
        g.setdefault('originalCatalog',dict(title=g['title'],releaseDate=g['releaseDate']))
        g['releaseDate']=dates.pop()
        g['releaseDateSources']=list(dict.fromkeys(r['url'] for r in found))
    for ident,title in TITLE_FIXES.items():
        g=lookup[ident]
        found=[r for r in refs if r['primary'] and r['family']==g.get('family') and audit.norm(r['title'])==audit.norm(title) and r['date']==g['releaseDate']]
        if not found:raise ValueError(f'Missing primary source for title: {ident}')
        updated=found[0]['title']
        if ident in {'gba-069','gba-070'}:
            updated=g['title'].replace('ポンコッツ３','ポンコッツ２')
        g.setdefault('originalCatalog',dict(title=g['title'],releaseDate=g['releaseDate']))
        issues.append(dict(kind='タイトル',status='訂正済み',id=ident,family=g.get('family'),title=g['title'],before=g['title'],after=updated,sources=[found[0]['url']]))
        g['title']=updated
        g['titleSources']=[found[0]['url']]
    for ident,title,day,publisher,genre,url in ADDITIONS:
        if ident in lookup:continue
        if not any(r['url']==url and audit.norm(r['title'])==audit.norm(title) and r['date']==day for r in refs):raise ValueError('Missing addition source')
        result['games'].append(dict(id=ident,title=title,family='GBA',platform='GBA',releaseDate=day,publisher=publisher,genre=genre,
          compatibilityLabel='ゲームボーイアドバンス',interest='unknown',owned='unknown',wanted=False,memo='',legacy={},
          sourceRecords=[],classificationSources=[url],classificationNote='任天堂公式の発売一覧から補完。',releaseDateSources=[url],titleSources=[url]))
        issues.append(dict(kind='登録漏れ',status='追加済み',id=ident,family='GBA',title=title,before='未登録',after=day,sources=[url]))
    # Catalogue scope differences: these are candidates, not automatic omissions.
    candidates=[('WS','mama Mitte','体脂肪率計に付属する健康管理ソフト','https://blackstraycat.nobody.jp/wonderswan/'),
        ('PCE','ビックリマン大事界','データベース／マルチメディアソフト','https://pcefan.com/pcengine/entry15.html'),
        ('PCE','マジカルザウルスツアー','図鑑・マルチメディアソフト','https://pcefan.com/pcengine/entry15.html'),
        ('PCE','ULTRABOX 創刊号〜6号','CD-ROMマガジン6本','https://pcefan.com/pcengine/entry15.html'),
        ('PCE','アイドル花札ファンクラブ／究極麻雀 アイドルグラフィック／レディソード／PCパチスロアイドルギャンブラー／AVポーカー ワールドギャンブラー／ボディコンクエストII／究極麻雀2 スーパーアイドルグラフィック／クイズ投稿写真','非公認ソフト等。収録範囲の確認が必要','https://pcefan.com/pcengine/entry15.html')]
    for fam,title,note,url in candidates:issues.append(dict(kind='収録範囲',status='追加候補',id='',family=fam,title=title,before='未登録',after=note,sources=[url]))
    for g in result['games']:
        own=[x for x in issues if x['id']==g['id']]
        if own:g['catalogReview']=own
    report=dict(checkedAt='2026-09-07',beforeCount=len(original),afterCount=len(result['games']),
        summary=dict(collections.Counter(r['status'] for r in rows)),issues=issues,rows=rows,
        limitations=['全件を発売一覧と機械照合した結果です。元Excelと同じ系統と思われる一覧も含み、一致は正確性の保証ではありません。',
        '同日・同名の別媒体、通常版とカラー版、再販は区別しています。資料間で不一致の発売日は未確定のままです。',
        'ネオジオポケットの補足一覧には重複したタイトル表記があり、ディーエイチ2の同定は保留です。',
        '発売順は現登録内の機種区分ごとの番号です。全発売作品の確定通番ではなく、追加・訂正で番号が変わります。',
        '同日はタイトル順。同日内に実際の発売の前後があったことを意味しません。'])
    result['catalogAuditSummary']={k:v for k,v in report.items() if k not in {'rows'}}
    return result,report

def render_report(report):
    esc=lambda v:html.escape(str(v))
    def table(items,columns):
        head=''.join('<th>'+esc(label)+'</th>' for key,label in columns)
        body=''
        for r in items:
            body+='<tr>'+''.join('<td>'+esc(r.get(k,''))+'</td>' for k,l in columns)
            body+='<td>'+''.join('<a target="_blank" rel="noopener noreferrer" href="'+esc(u)+'">資料'+str(i+1)+'</a> ' for i,u in enumerate(r.get('sources',[])))+'</td></tr>'
        return '<div class="scroll"><table><thead><tr>'+head+'<th>出典</th></tr></thead><tbody>'+body+'</tbody></table></div>'
    groups=''
    for kind in ['登録漏れ','発売日','タイトル','再販・別版','収録範囲']:
        selected=[r for r in report['issues'] if r['kind']==kind]
        columns=([('workStatus','対応')] if report.get('completion') else [])+[('status','判定'),('family','機種'),('title','作品'),('before','登録内容'),('after','採用内容'),('note','理由')]
        groups+='<section><h2>'+esc(kind)+' — '+str(len(selected))+'件</h2>'+table(selected,columns)+'</section>'
    status=collections.Counter(r['status'] for r in report['rows'])
    completion=report.get('completion')
    completion_heading=''
    if completion:
        status=report['summary']
        completion_heading='<p><strong>対応完了 '+str(completion['completedItems'])+'件 ／ 未対応 '+str(completion['pendingItems'])+'件</strong>　追加 '+str(completion['added'])+'本・統合 '+str(completion['merged'])+'件・通番更新 '+str(completion['numberedGames'])+'本</p>'
        if report.get('dateDecisions'):
            completion_heading+='<p><a href="#unresolved-dates">発売日の採用内容 '+str(len(report['dateDecisions']))+'作品</a>：指定された日付の扱いを反映済みです。</p>'
        elif completion['uncertainDates']:
            completion_heading+='<p><a href="#unresolved-dates">発売日未確定 '+str(completion['uncertainDates'])+'作品の一覧</a>。「完了」は処理の完了を示し、日付の確定を意味しません。</p>'
    unresolved=[]
    for row in report['rows']:
        verification=row.get('verification',{})
        if verification.get('grade')=='unresolved' and not row.get('mergedInto'):
            unresolved.append(dict(family=row['family'],title=row['title'],date=row['date'],
                                   note=verification['note'],sources=verification.get('sources',[])))
    if unresolved:
        if completion and len(unresolved)!=completion['uncertainDates']:
            raise ValueError('発売日未確定の件数と一覧が一致しません。')
        groups='<section id="unresolved-dates"><h2>発売日未確定 — '+str(len(unresolved))+'作品</h2><p>資料の相違や情報不足が残る作品です。下の日付は確定した発売日ではありません。</p>'+table(unresolved,[('family','機種'),('title','作品'),('date','並び順用の記録'),('note','未確定の理由')])+'</section>'+groups
    elif report.get('dateDecisions'):
        decisions=report['dateDecisions']
        groups='<section id="unresolved-dates"><h2>発売日の採用内容 — '+str(len(decisions))+'作品</h2><p>Excel記載日を優先し、年しか分からない作品は1月1日として登録しました。</p>'+table(decisions,[('family','機種'),('title','作品'),('date','採用日'),('note','採用理由')])+'</section>'+groups
    return '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>発売情報の確認結果</title><style>body{font:14px/1.6 system-ui,sans-serif;color:#172b42;margin:20px}h1{font-size:22px}h2{font-size:17px;margin:24px 0 6px}p{margin:8px 0}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:6px 8px;text-align:left;border:1px solid #d6dee8;vertical-align:top}th{background:#edf2f8}td:nth-child(-n+3),th:nth-child(-n+3){white-space:nowrap}td:nth-child(4){min-width:180px}td:nth-child(5){min-width:75px}td:nth-child(6){min-width:130px}td:nth-child(7){min-width:250px}tr:nth-child(even){background:#f8fafc}a{color:#24558b;white-space:nowrap}.scroll{overflow:auto}ul{padding-left:20px}</style><h1>発売情報の確認結果</h1>'+completion_heading+'<p>2026年9月7日／'+str(report['beforeCount'])+'本を一覧照合。補完後 '+str(report['afterCount'])+'本。</p><p>'+esc(' ／ '.join(k+': '+str(v)+'本' for k,v in status.items()))+'</p><details><summary>照合範囲と発売日の扱い</summary><ul>'+''.join('<li>'+esc(s)+'</li>' for s in report['limitations'])+'</ul></details>'+groups+'</html>'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    path=ROOT/'library.json';raw=path.read_bytes();current=json.loads(raw)
    if current.get('catalogAuditSummary',{}).get('checkedAt')=='2026-09-07':
        raise RuntimeError('この確認結果は反映済みです。再実行による重複適用を中止しました。')
    result,report=build(current,audit.sources())
    (ROOT/'発売情報の確認結果.html').write_text(render_report(report),encoding='utf-8')
    (ROOT/'catalog_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if args.apply:
        if path.read_bytes()!=raw:raise RuntimeError('Library changed while auditing')
        result['revision']=current['revision']+1;result['updatedAt']=storage.now()
        storage.write_atomic(path,result)
    print(json.dumps({'applied':args.apply,'summary':report['summary'],'issues':dict(collections.Counter(r['kind'] for r in report['issues'])),'total':report['afterCount']},ensure_ascii=False))

if __name__=='__main__':main()
