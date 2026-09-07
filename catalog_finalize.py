"""Apply reviewed omissions/edition consolidations without losing source records."""
import argparse
import collections
import copy
import datetime
import json
from pathlib import Path

import catalog_completion_evidence as evidence
from catalog_review import render_report
import game_library as storage

ROOT = Path(__file__).resolve().parent
STAMP = '2026-09-07-catalog-completion'
PERSONAL = ('interest', 'owned', 'wanted', 'memo')


def merge_edition(target, edition, note, sources):
    if target['platform'] != edition['platform']:
        raise ValueError('別機種版は統合できません。')
    # Preserve each full record even where the combined state differs.
    target.setdefault('preConsolidationPersonal', {k:copy.deepcopy(target[k]) for k in PERSONAL})
    target.setdefault('mergedEditions', []).append(copy.deepcopy(edition))
    target['aliases'] = list(dict.fromkeys(target.get('aliases', []) + [edition['title']]))
    target.setdefault('releaseVariants', []).append(dict(
        kind=edition['title'], releaseDate=edition['releaseDate'][:7] if edition['id'] in
        {'gb-1264','gb-1265','gb-1266','gb-1267','gb-1268'} else edition['releaseDate'],
        note=note, sources=sources))
    for source in edition.get('sourceRecords', []):
        if source not in target.setdefault('sourceRecords', []):
            target['sourceRecords'].append(copy.deepcopy(source))
    # Positive ownership/wanted marks apply to the work. Interest conflicts are
    # retained separately instead of silently choosing a different preference.
    if edition['owned'] == 'yes' or target['owned'] == 'unknown':
        target['owned'] = edition['owned']
    target['wanted'] = target['wanted'] or edition['wanted']
    if target['interest'] == 'unknown':
        target['interest'] = edition['interest']
    if edition['memo'] and edition['memo'] != target['memo']:
        target['memo'] = '\n\n'.join(s for s in [target['memo'], f"【{edition['title']}】\n{edition['memo']}"] if s)


def issue(game, kind, status, before, after, note, sources):
    return dict(id=game['id'], title=game['title'], family=game.get('family','NGP'),
                kind=kind,status=status,before=before,after=after,note=note,sources=sources)


def build(current, previous_report):
    if current.get('catalogAuditSummary', {}).get('completion', {}).get('id') == STAMP:
        raise ValueError('補完・統合は反映済みです。')
    result, report = copy.deepcopy(current), copy.deepcopy(previous_report)
    lookup = {g['id']: g for g in result['games']}
    removed = set()
    for source_id, target_id, note, urls in evidence.MERGES:
        src, dst = lookup[source_id], lookup[target_id]
        if src['releaseDate'] < dst['releaseDate']:
            raise ValueError(f'初版より前の再販: {source_id}')
        merge_edition(dst, src, note, urls)
        entry = issue(src,'再販・別版','統合済み',src['releaseDate'],dst['title']+'／'+dst['releaseDate'],note,urls)
        prior = next((r for r in report['issues'] if r['id']==source_id and r['kind']=='再販・別版'),None)
        if prior is None: report['issues'].append(entry)
        else: prior.update(entry)
        # The issue belongs to the retained work as well as the archived edition.
        entry['mergedInto'] = target_id
        if prior is not None: prior['mergedInto'] = target_id
        removed.add(source_id)
        for row in report['rows']:
            if row['id']==source_id: row.update(status='統合済み',mergedInto=target_id)
    result['games'] = [g for g in result['games'] if g['id'] not in removed]
    for ident, note, urls in evidence.KEEP:
        g=lookup[ident]
        entry=issue(g,'再販・別版','別作品として維持',g['title'],g['title'],note,urls)
        prior=next((r for r in report['issues'] if r['id']==ident and r['kind']=='再販・別版'),None)
        if prior is None: report['issues'].append(entry)
        else: prior.update(entry)
    result['platforms']['PCE-GE']=dict(name='PCエンジン GAMES EXPRESS CD CARD専用',badge='PCE GE-CD',family='PCE')
    for ident,title,day,platform,publisher,genre,urls,note in evidence.ADDITIONS:
        if ident in lookup or any(g['title']==title and g['platform']==platform for g in result['games']):
            raise ValueError(f'追加作品が重複: {ident}')
        if len(day)==10: datetime.date.fromisoformat(day)
        elif not (len(day)==4 and day.isdigit()): raise ValueError(day)
        compatibility={'PCE':'HuCard（非公認）','PCE-CD':'CD-ROM²',
                       'PCE-SCD':'SUPER CD-ROM²（非公認）',
                       'PCE-GE':'GAMES EXPRESS CD CARD必須／SUPER CD-ROM²・DUO系（非公認）'}[platform]
        g=dict(id=ident,title=title,displayNo='',family='PCE',platform=platform,
            releaseDate=day,publisher=publisher,genre=genre,originalGenre=genre,
            interest='unknown',owned='unknown',wanted=False,memo='',legacy={},sourceRecords=[],
            compatibilityLabel=compatibility,classificationNote=note,classificationSources=urls,
            releaseDateSources=urls,releaseDateVerification=dict(grade='catalogue' if len(day)==10 else 'unresolved',
                checkedAt='2026-09-07',note=note,sources=urls))
        if ident.startswith('pce-unlicensed'): g['licenseStatus']='unlicensed'
        if ident in {'pce-unlicensed-13','pce-unlicensed-16'}:
            g['releaseDateVerification']['grade']='unresolved'
        if len(day)!=10:
            g['releaseOrderExcluded']=True
            g['releaseOrderExclusionReason']='発売月日が不明のため通番は未付与。'
        result['games'].append(g)
        date_note=('発売日未確定・並び順用 '+day) if g['releaseDateVerification']['grade']=='unresolved' else day
        report['issues'].append(issue(g,'登録漏れ','追加済み','未登録',date_note+'／'+compatibility,note,urls))
        report['rows'].append(dict(id=ident,title=title,family='PCE',platform=platform,date=day,
            status='日付未確定' if g['releaseDateVerification']['grade']=='unresolved' else '補完済み',
            references=[],verification=g['releaseDateVerification']))
    for title,note,urls in evidence.EXCLUSIONS:
        own=next(r for r in report['issues'] if r['kind']=='収録範囲' and r['title']==title)
        own.update(status='対象外として確定',after='ゲーム一覧には追加しない',note=note,sources=urls)
    for own in report['issues']:
        if own['kind']=='収録範囲' and own['status']=='追加候補':
            own.update(status='追加済み', after='各作品を追加済み。登録漏れの欄に掲載。',
                       note='ビックリマン1本、ULTRABOX全6号、国内非公認23本を補完。')
        if own['status'] in {'統合候補','追加候補','資料間不一致','照合保留'}:
            raise ValueError(f'未処理の項目: {own["title"]}')
        own['workStatus']='完了'
    active={g['id'] for g in result['games']}
    recorded={r['id'] for r in report['rows']}
    for g in result['games']:
        if g['id'] not in recorded:
            report['rows'].append(dict(id=g['id'],title=g['title'],family=g.get('family','NGP'),
                platform=g['platform'],date=g['releaseDate'],status='補完済み',references=[]))
    for row in report['rows']:
        if row['status']=='日付相違':
            resolved=next((r for r in report['issues'] if r['id']==row['id'] and r['kind']=='発売日'),None)
            if not resolved or resolved['status']!='訂正済み': raise ValueError(row['id'])
            row.update(status='訂正済み',date=lookup[row['id']]['releaseDate'])
    for g in result['games']:
        own=[r for r in report['issues'] if r['id']==g['id'] or r.get('mergedInto')==g['id']]
        if own: g['catalogReview']=copy.deepcopy(own)
    report['afterCount']=len(result['games'])
    report['summary']=dict(collections.Counter(r['status'] for r in report['rows'] if r['id'] in active))
    report['completion']=dict(id=STAMP,checkedAt='2026-09-07',added=len(evidence.ADDITIONS),
        merged=len(removed),kept=len(evidence.KEEP),excluded=len(evidence.EXCLUSIONS),
        completedItems=len(report['issues']),pendingItems=0,
        uncertainDates=sum(g.get('releaseDateVerification',{}).get('grade')=='unresolved' for g in result['games']),
        numberedGames=sum(not g.get('releaseOrderExcluded',False) for g in result['games']))
    report['limitations']=[
        '登録済み機種の一覧照合、相違点の調査、登録漏れの追加、再販の統合を反映済みです。確認結果の各項目に処理内容と根拠を残しました。',
        '発売日未確定は既存6作品と追加3作品です。既存6作品とCDパチスロ・CD美少女パチンコは資料が食い違うため仮の日付で並べます。J・サンダーは1994年までの記録とし、通番を付けません。',
        '日付の調査完了と、発売日の確定は別です。資料掲載日の採用を公式確認済みとは表示しません。追加した非公認作品でも資料間の相違と採用理由を保存しています。',
        '通番は現登録内の機種区分ごとの発売順です。同日はタイトル順。システムカード6件と発売月日不明1件は対象外です。追加・訂正で番号は変わります。',
        '通常版へ統合した23件の元のExcel行・以前の評価・個人記録・再販日は詳細に保存しています。続編・内容変更版・別機種版は別登録です。',
        '全件を一覧照合していますが、全作品の一次資料を一件ずつ確認したものではありません。今回参照した国内発売一覧を対象とする照合であり、今後も未掲載作品が判明する可能性があります。',
    ]
    result['catalogAuditSummary']={k:v for k,v in report.items() if k!='rows'}
    return result,report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    path=ROOT/'library.json'
    original=path.read_bytes()
    current=json.loads(original)
    result,report=build(current,storage.read_json(ROOT/'catalog_audit.json'))
    if args.apply:
        if path.read_bytes()!=original: raise RuntimeError('処理中に記録が更新されました。上書きを中止します。')
        result['revision']=current['revision']+1
        result['updatedAt']=storage.now()
        storage.write_atomic(path,result)
        storage.write_atomic(ROOT/'catalog_audit.json',report)
        (ROOT/'発売情報の確認結果.html').write_text(render_report(report),encoding='utf-8')
    print(json.dumps(report['completion'],ensure_ascii=False))


if __name__=='__main__': main()
