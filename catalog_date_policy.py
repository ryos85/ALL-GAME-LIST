"""Apply the user's date choices while retaining the research evidence."""
import collections
import copy
import json

import game_library as storage
from catalog_review import render_report

EXCEL_IDS = {'gb-648', 'gb-696', 'gb-726', 'gb-799', 'gb-977', 'gb-1041'}
CATALOGUE_IDS = {'pce-unlicensed-13', 'pce-unlicensed-16'}
YEAR_ID = 'pce-unlicensed-10'
POLICY = '不一致が解消できない発売日はExcel記載日を採用。Excelにない作品は資料掲載日を採用。年しか分からない作品は整理用に1月1日を設定する。'


def build(current, previous_report):
    if current.get('releaseDatePolicy'):
        raise ValueError('日付の採用方針は反映済みです。')
    result, report = copy.deepcopy(current), copy.deepcopy(previous_report)
    targets = EXCEL_IDS | CATALOGUE_IDS | {YEAR_ID}
    unresolved = {g['id'] for g in result['games'] if g.get('releaseDateVerification', {}).get('grade') == 'unresolved'}
    if unresolved != targets:
        raise ValueError('対象の9作品が調査時と異なります。')
    decisions = []
    for game in result['games']:
        ident = game['id']
        if ident not in targets:
            continue
        old = copy.deepcopy(game['releaseDateVerification'])
        if ident in EXCEL_IDS:
            grade, note = 'excel', 'ユーザー指定によりExcel記載日を採用。'
        elif ident in CATALOGUE_IDS:
            grade, note = 'catalogue', 'Excelにない作品のため、現在登録している資料掲載日を採用。'
        else:
            if game['releaseDate'] != '1994':
                raise ValueError('J・サンダーの年が調査時と異なります。')
            game['releaseDate'] = '1994-01-01'
            game.pop('releaseOrderExcluded', None)
            game.pop('releaseOrderExclusionReason', None)
            grade, note = 'estimated', '年のみ判明しているため、ユーザー指定により整理用の日付を1994年1月1日に設定。実際の発売月日を示すものではありません。'
        if ident not in EXCEL_IDS:
            game['classificationNote'] = '国内で発売された非公認ゲーム。' + game['compatibilityLabel'] + '。'
        game['releaseDateVerification'] = dict(grade=grade, checkedAt='2026-09-07', note=note,
            sources=old.get('sources', []), previousResearch=old)
        status = {'excel': 'Excel記載日を採用', 'catalogue': '資料掲載日を採用', 'estimated': '月日を補完'}[grade]
        decisions.append(dict(id=ident, family=game['family'], title=game['title'], date=game['releaseDate'],
            status=status, note=note, sources=old.get('sources', [])))
        for row in report['rows']:
            if row['id'] == ident:
                row.update(date=game['releaseDate'], status=status, verification=copy.deepcopy(game['releaseDateVerification']))
        for entry in report['issues']:
            if entry['id'] == ident and entry['kind'] in {'発売日', '登録漏れ'}:
                entry.setdefault('previousResearchNote', entry['note'])
                entry.update(status=status, after=game['releaseDate'], note=note, workStatus='完了')
    for game in result['games']:
        if game['id'] in targets:
            game['catalogReview'] = copy.deepcopy([r for r in report['issues'] if r['id'] == game['id'] or r.get('mergedInto') == game['id']])
    report['dateDecisions'] = decisions
    report['completion']['uncertainDates'] = 0
    report['completion']['numberedGames'] = sum(not g.get('releaseOrderExcluded', False) for g in result['games'])
    active = {g['id'] for g in result['games']}
    report['summary'] = dict(collections.Counter(r['status'] for r in report['rows'] if r['id'] in active))
    report['limitations'][1] = POLICY
    report['limitations'][2] = '採用日と調査上の確認度は区別し、資料間の相違は調査記録として保持しています。1月1日で補完した作品は詳細に明示します。'
    report['limitations'][3] = '通番は現登録内の機種区分ごとの発売順です。同日はタイトル順。月日不明は1月1日として並べ、システムカード6件は対象外です。追加・訂正で番号は変わります。'
    result['releaseDatePolicy'] = dict(adoptedAt='2026-09-07', note=POLICY)
    result['catalogAuditSummary'] = {k: v for k, v in report.items() if k != 'rows'}
    return result, report


def main():
    path = storage.ROOT / 'library.json'
    original = path.read_bytes()
    current = json.loads(original)
    result, report = build(current, storage.read_json(storage.ROOT / 'catalog_audit.json'))
    personal = lambda d: {g['id']: {k: v for k, v in g.items() if k not in {'releaseDate', 'releaseDateVerification', 'releaseOrderExcluded', 'releaseOrderExclusionReason', 'catalogReview', 'classificationNote'}} for g in d['games']}
    assert personal(current) == personal(result)
    rendered = render_report(report)
    if path.read_bytes() != original:
        raise RuntimeError('処理中に記録が更新されました。')
    result.update(revision=current['revision'] + 1, updatedAt=storage.now())
    storage.write_atomic(path, result)
    storage.write_atomic(storage.ROOT / 'catalog_audit.json', report)
    (storage.ROOT / '発売情報の確認結果.html').write_text(rendered, encoding='utf-8')
    print(json.dumps(dict(revision=result['revision'], decisions=len(report['dateDecisions']), numbered=report['completion']['numberedGames']), ensure_ascii=False))


if __name__ == '__main__':
    main()
