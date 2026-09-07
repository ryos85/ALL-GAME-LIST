"""Apply individually researched release dates without changing personal records."""
import argparse
import collections
import copy
import datetime
import json
from pathlib import Path

import game_library as storage
from catalog_review import render_report

ROOT = Path(__file__).resolve().parent
STAMP = '2026-09-07-individual-review'


def build(current, previous_report, evidence):
    if current.get('catalogAuditSummary', {}).get('followup', {}).get('id') == STAMP:
        raise ValueError('個別調査は反映済みです。')
    result, report = copy.deepcopy(current), copy.deepcopy(previous_report)
    lookup = {g['id']: g for g in result['games']}
    expected = {r['id'] for r in report['issues'] if r['status'] == '資料間不一致'} | {'ngp-079'}
    if len(evidence) != len({e[0] for e in evidence}) or {e[0] for e in evidence} != expected:
        raise ValueError('調査対象と出典の対応が一致しません。')
    counts = collections.Counter()
    for ident, day, note, grade, urls in evidence:
        if grade not in {'official', 'press', 'publication', 'multiple', 'unresolved', 'scope'}:
            raise ValueError(grade)
        if bool(day) != (grade not in {'unresolved', 'scope'}) or not urls:
            raise ValueError(ident)
        if day:
            datetime.date.fromisoformat(day)
        g = lookup[ident]
        old = g['releaseDate']
        state = ('ゲーム対象外' if grade == 'scope' else '日付未確定') if day is None else ('訂正済み' if day != old else '登録日を採用')
        counts[state] += 1
        g['releaseDateVerification'] = dict(grade=grade, checkedAt='2026-09-07', note=note, sources=urls)
        if day:
            if day != old:
                g.setdefault('originalCatalog', dict(title=g['title'], releaseDate=old))
                g['releaseDate'] = day
            g['releaseDateSources'] = urls
        if grade == 'scope':
            g['releaseOrderExcluded'] = True
        own = next((r for r in report['issues'] if r['id'] == ident and r['kind'] == '発売日'), None)
        if own is None:
            own = dict(id=ident, family=g.get('family', 'NGP'), title=g['title'], kind='発売日', before=old)
            report['issues'].append(own)
        own.update(status=state, after=day or '実発売日は未確定', note=note,
                   sources=list(dict.fromkeys(urls + own.get('sources', []))))
        for row in report['rows']:
            if row['id'] == ident:
                row.update(status=state, date=g['releaseDate'], verification=copy.deepcopy(g['releaseDateVerification']))
    lookup['gb-1055']['releaseVariants'] = [
        dict(kind='プリライト版', releaseDate='2000-07-31'),
        dict(kind='書き換え開始', releaseDate='2000-08-01'),
    ]
    # These imported rows describe system/expansion cards, not released games.
    for ident in ['pce-022', 'pce-155', 'pce-156', 'pce-302', 'pce-552', 'pce-553']:
        if ident in lookup:
            lookup[ident]['releaseOrderExcluded'] = True
    for g in result['games']:
        own = [r for r in report['issues'] if r['id'] == g['id']]
        if own:
            g['catalogReview'] = copy.deepcopy(own)
    report['followup'] = dict(id=STAMP, checkedAt='2026-09-07', reviewed=len(evidence), counts=dict(counts))
    report['summary'] = dict(collections.Counter(r['status'] for r in report['rows']))
    report['limitations'] = [
        '発売日が食い違った65件と、表記の違いで同定できていなかったDH2の1件を個別調査しました。訂正・採用の理由と資料を各作品に記録しています。',
        '公式資料、報道、書籍、販売店等の複数資料を区別しています。複数資料からの採用日は公式確定日を意味せず、反対の記載がある資料も残しています。',
        '日付未確定の6作品は、調べた資料が食い違い確定できませんでした。並び順には元の登録日を仮に使用しています。SYSTEM Ver2.0はバージョンの混同があり、ゲームの通番から除外しています。',
        '全件の一覧照合には元Excelと同じ系統の資料も含みます。一致した全作品を一次資料で個別に確認したものではありません。',
        '発売順は現登録内の機種区分ごとの番号です。同日はタイトル順。未確定日・追加・訂正により番号が変わるため、全発売作品の確定通番ではありません。',
    ]
    result['catalogAuditSummary'] = {k: v for k, v in report.items() if k != 'rows'}
    return result, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'library.json'
    raw = path.read_bytes()
    current = json.loads(raw)
    previous = storage.read_json(ROOT / 'catalog_audit.json')
    evidence = json.loads((ROOT / 'release_date_evidence.json').read_text(encoding='utf-8-sig'))
    result, report = build(current, previous, evidence)
    if args.apply:
        if path.read_bytes() != raw:
            raise RuntimeError('調査反映中に記録が更新されました。上書きを中止します。')
        result['revision'] = current['revision'] + 1
        result['updatedAt'] = storage.now()
        storage.write_atomic(path, result)
        storage.write_atomic(ROOT / 'catalog_audit.json', report)
        (ROOT / '発売情報の確認結果.html').write_text(render_report(report), encoding='utf-8')
    print(json.dumps(report['followup'], ensure_ascii=False))


if __name__ == '__main__':
    main()
