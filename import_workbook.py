"""Append the populated workbook sheets without replacing personal records."""
import argparse
import collections
from contextlib import closing
import copy
import datetime
import hashlib
import json
from pathlib import Path

import openpyxl
from openpyxl.utils.datetime import from_excel

import game_library as storage
from import_neogeo import GENRES

SOURCE = Path(r'D:\EmuGame\ROMリスト.xlsx')
SHEETS = {
    'ワンダースワン': 'WS', 'PCエンジン': 'PCE', 'メガドライブ': 'MD',
    'ゲームボーイ': 'GB', 'ゲームボーイアドバンス': 'GBA',
    'セガサターン': 'SS', 'スーパーファミコン': 'SFC', 'ドリームキャスト': 'DC',
}
FAMILIES = {'NGP': 'ネオジオポケット', **{v: k for k, v in SHEETS.items()}}
# code: (display name, compact badge, parent hardware)
PLATFORM_ROWS = {
    'NGP': ('ネオジオポケット（モノクロ）', 'NGP', 'NGP'),
    'NGPC': ('ネオジオポケットカラー', 'NGPC', 'NGP'),
    'WS': ('ワンダースワン（モノクロ）', 'WS', 'WS'),
    'WSC': ('ワンダースワンカラー', 'WSC', 'WS'),
    'PCE': ('PCエンジン HuCard', 'PCE', 'PCE'),
    'PCE-CD': ('PCエンジン CD-ROM²', 'PCE CD', 'PCE'),
    'PCE-SCD': ('PCエンジン SUPER CD-ROM²', 'PCE SCD', 'PCE'),
    'PCE-ACD': ('PCエンジン アーケードカード専用', 'PCE ACD', 'PCE'),
    'SGX': ('PCエンジン スーパーグラフィックス専用', 'SGX', 'PCE'),
    'MD': ('メガドライブ', 'MD', 'MD'),
    'MCD': ('メガCD', 'MCD', 'MD'),
    '32X': ('スーパー32X', '32X', 'MD'),
    'GB': ('ゲームボーイ（モノクロ）', 'GB', 'GB'),
    'GB-GBC': ('ゲームボーイ＆カラー共通', 'GB/GBC', 'GB'),
    'GBC': ('ゲームボーイカラー専用', 'GBC', 'GB'),
    'GBA': ('ゲームボーイアドバンス', 'GBA', 'GBA'),
    'SS': ('セガサターン', 'SS', 'SS'),
    'SFC': ('スーパーファミコン', 'SFC', 'SFC'),
    'DC': ('ドリームキャスト', 'DC', 'DC'),
}
PLATFORMS = {k: dict(name=v[0], badge=v[1], family=v[2]) for k, v in PLATFORM_ROWS.items()}
NP_SOURCE = 'https://blog.gameboymania.com/2014/03/np.html'
NINTENDO_SOURCE = 'https://www.nintendo.co.jp/n02/dmg/index.html'
NP_COLOR = {979, 1089, 1200, 1201, 1210}
NP_DUAL = {1036, 1054, 1055, 1209, 1226, 1232, 1239, 1243, 1249, 1261}
GENRE_NAMES = {**GENRES, 'RCE': 'レース', '対戦格闘': '格闘'}


def classify(family, note, number):
    sources = []
    if family == 'WS':
        mapping = {'': ('WS', 'モノクロ版'), '両対応': ('WSC', 'カラー版・モノクロ本体にも対応'),
                   'カラー専用': ('WSC', 'カラー専用')}
    elif family == 'PCE':
        mapping = {
            '': ('PCE', 'HuCard'),
            'スーパーグラフィックス対応': ('PCE', 'HuCard・スーパーグラフィックスにも対応'),
            'スーパーグラフィックス専用': ('SGX', 'スーパーグラフィックス専用 HuCard'),
            'CD-ROM2専用': ('PCE-CD', 'CD-ROM²専用'),
            'SUPER CD-ROM2専用': ('PCE-SCD', 'SUPER CD-ROM²専用'),
            'SUPER CD-ROM2専用\n/アーケードカード対応': ('PCE-SCD', 'SUPER CD-ROM²専用・アーケードカード対応'),
            'アーケードカード専用': ('PCE-ACD', 'アーケードカード専用 CD-ROM²'),
        }
    elif family == 'MD':
        mapping = {'': ('MD', 'メガドライブ用カートリッジ'), 'メガCD専用': ('MCD', 'メガCD専用'),
                   'スーパー32X専用': ('32X', 'スーパー32X専用')}
    elif family == 'GB':
        mapping = {'': ('GB', 'ゲームボーイ（モノクロ版）'),
                   'ゲームボーイカラー対応': ('GB-GBC', 'ゲームボーイ＆カラー共通'),
                   'ゲームボーイカラー専用': ('GBC', 'ゲームボーイカラー専用')}
        if note == 'ニンテンドウパワー専用':
            if number not in NP_COLOR | NP_DUAL:
                raise ValueError(f'未照合のニンテンドウパワー作品: {number}')
            platform = 'GBC' if number in NP_COLOR else 'GB-GBC'
            label = 'カラー専用' if number in NP_COLOR else 'ゲームボーイ＆カラー共通'
            sources = [NP_SOURCE]
            if number in (979, 1055):
                sources.insert(0, NINTENDO_SOURCE)
            return platform, label + '・ニンテンドウパワー専用', sources
    else:
        mapping = {'': (family, FAMILIES[family])}
    if note not in mapping:
        raise ValueError(f'分類できないExcel備考: {family} / {note!r}')
    platform, label = mapping[note]
    return platform, label, sources


def text(value):
    return '' if value is None else str(value)


def read_candidates(path=SOURCE):
    candidates, sheet_counts = [], {}
    with closing(openpyxl.load_workbook(path, read_only=True, data_only=True)) as wb:
        for sheet, family in SHEETS.items():
            ws = wb[sheet]
            expected = ['No.', '所有', '評価', '遊びたい', 'ジャンル', '発売日', 'タイトル', '発売元', '備考']
            if list(next(ws.values))[:9] != expected:
                raise ValueError(f'列構成が変わっています: {sheet}')
            used_numbers, ordinal = set(), 0
            for row_index, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                if not row[6]:
                    continue
                ordinal += 1
                number = int(row[0]) if row[0] is not None else ordinal
                if number in used_numbers:
                    raise ValueError(f'Noが重複しています: {sheet} / {number}')
                used_numbers.add(number)
                note = text(row[8])
                platform, label, links = classify(family, note, number)
                raw_date = row[5]
                date = from_excel(raw_date, wb.epoch) if isinstance(raw_date, (int, float)) else raw_date
                if not isinstance(date, (datetime.datetime, datetime.date)):
                    raise ValueError(f'発売日を読み取れません: {sheet} / {row_index}')
                source = {'sheet': sheet, 'row': row_index, 'no': row[0], 'genre': text(row[4]),
                          'owned': text(row[1]), 'rating': text(row[2]), 'want': text(row[3]), 'note': note}
                candidates.append({
                    'id': f'{family.lower()}-{number:03d}', 'displayNo': f'{number:03d}',
                    'title': row[6], 'platform': platform, 'family': family,
                    'compatibilityLabel': label, 'releaseDate': date.strftime('%Y-%m-%d'),
                    'publisher': text(row[7]), 'genre': GENRE_NAMES.get(row[4], row[4] or '未分類'),
                    'originalGenre': text(row[4]), 'interest': 'unknown',
                    'owned': 'yes' if row[1] in ('○', '〇') else 'unknown', 'wanted': False, 'memo': '',
                    'legacy': {k: source[k] for k in ('owned', 'rating', 'want')},
                    'sourceSheet': sheet, 'sourceRow': row_index, 'sourceRecords': [source],
                    'classificationSources': links,
                    'classificationNote': ('Excel備考の「ニンテンドウパワー専用」では色区分が不明のため、対応表で補足。'
                                           if links else f'Excel「{sheet}」の備考欄に基づく分類。備考: {note or "区分の記載なし"}。'),
                })
            sheet_counts[sheet] = ordinal
    return candidates, sheet_counts


def consolidate(candidates):
    """Only consolidate exact title/date/publisher/platform matches; retain all source rows."""
    result, index = [], {}
    for record in candidates:
        record = copy.deepcopy(record)
        key = tuple(record[k] for k in ('platform', 'title', 'releaseDate', 'publisher'))
        if key not in index:
            result.append(record)
            index[key] = record
            continue
        kept = index[key]
        kept['sourceRecords'].extend(record['sourceRecords'])
        if record['owned'] == 'yes':
            kept['owned'] = 'yes'
        if kept['genre'] != record['genre']:
            kept['classificationNote'] += f' 同じ作品の重複行あり。ジャンル表記差: {kept["genre"]} / {record["genre"]}（元の行を保存）。'
    return result


def merge_library(current, candidates, sheet_counts):
    result = copy.deepcopy(current)
    existing = {g['id']: g for g in current['games']}
    editions = {e['id']: e for g in current['games'] for e in g.get('mergedEditions', [])}
    appended = []
    for record in consolidate(candidates):
        if record['id'] in editions:
            old = editions[record['id']]
            if old['title'] != record['title'] or old.get('sourceRow') != record['sourceRow']:
                raise ValueError(f'統合済みIDと別の作品が衝突: {record["id"]}')
            continue
        if record['id'] in existing:
            old = existing[record['id']]
            original_title = old.get('originalCatalog', {}).get('title', old['title'])
            if record['title'] not in {old['title'], original_title} or old.get('sourceRow') != record['sourceRow']:
                raise ValueError(f'既存IDと別の作品が衝突: {record["id"]}')
            continue
        result['games'].append(record)
        appended.append(record)
    result['platforms'] = {**PLATFORMS, **result.get('platforms', {})}
    result['families'] = FAMILIES
    result['sourceName'] = 'ROMリスト.xlsx'
    result['importSummary'] = {'sheetRows': sheet_counts, 'emptySheets': [s for s, n in sheet_counts.items() if not n],
                               'consolidatedRows': len(candidates) - len(consolidate(candidates))}
    if result != current:
        result['revision'] += 1
        result['updatedAt'] = storage.now()
    return result, appended


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    path = storage.ROOT / 'library.json'
    original = path.read_bytes()
    current = json.loads(original)
    candidates, sheet_counts = read_candidates()
    result, appended = merge_library(current, candidates, sheet_counts)
    if args.apply and result != current:
        if path.read_bytes() != original:
            raise RuntimeError('取り込み中に記録が更新されました。もう一度実行してください。')
        storage.write_atomic(path, result)
    print(json.dumps({'applied': args.apply, 'added': len(appended), 'total': len(result['games']),
                      'sheets': sheet_counts, 'platforms': dict(collections.Counter(g['platform'] for g in result['games'])),
                      'duplicateRowsMerged': len(candidates) - len(consolidate(candidates)),
                      'sourceSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
