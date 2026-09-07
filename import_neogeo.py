"""Read the source workbook once. Never overwrite an edited library."""
import collections
import datetime
import json
from pathlib import Path

import openpyxl
from openpyxl.utils.datetime import from_excel

ROOT = Path(__file__).resolve().parent
SOURCE = Path(r'D:\EmuGame\ROMリスト.xlsx')
SOURCE_A = 'https://en.wikipedia.org/wiki/List_of_Neo_Geo_Pocket_games'
SOURCE_B = 'https://www.super-famicom.jp/etc00/gamelist/ngp.html'
# Source-row identifiers are explicitly mapped, not inferred from release dates.
MONO_TITLES = {
    'キング・オブ・ファイターズR-1', "ネオジオカップ'98", 'ベースボールスターズ',
    'ポケットテニス', 'めろんちゃんの成長日記', '連結パズル つなげてポンッ!',
    '将棋の達人', 'サムライスピリッツ!', 'ネオ・チェリーマスター',
}
DUAL_ROWS = {10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,
             32,33,34,35,36,37,38,39,40,42,43,44,45,47,61,67,69}
COLOR_ONLY_ROWS = {46,51,56,57,58,59,60,62,63,65,66,68,70,71,72,73,74,77,78,79,80,81,82}
# The Japanese source gives '?' here. Keep compatibility unresolved rather than
# convert a single unsupported assertion to a confirmed compatibility claim.
UNRESOLVED_ROWS = {41,48,49,50,52,53,54,55,64,75,76}
GENRES = {'FTG':'格闘','SPG':'スポーツ','SPT':'スポーツ','SLG':'シミュレーション',
          'PZL':'パズル','TBL':'テーブル','ACT':'アクション','RPG':'RPG',
          'ETC':'その他','SRPG':'シミュレーションRPG','TCG':'カード','STG':'シューティング',
          'ADV':'アドベンチャー','音楽':'音楽'}

def import_library():
    if (ROOT / 'library.json').exists():
        raise SystemExit('library.json already exists; existing edits were preserved.')
    wb = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    games = []
    assert not (DUAL_ROWS & COLOR_ONLY_ROWS or DUAL_ROWS & UNRESOLVED_ROWS or COLOR_ONLY_ROWS & UNRESOLVED_ROWS)
    assert DUAL_ROWS | COLOR_ONLY_ROWS | UNRESOLVED_ROWS == set(range(10,83))
    for row_number, row in enumerate(wb['ネオジオポケット'].iter_rows(min_row=2, values_only=True), 2):
        if not row[6]:
            continue
        n = int(row[0])
        is_mono = row[6] in MONO_TITLES
        assert is_mono == (n <= 9)
        compatibility = 'mono' if is_mono else 'dual' if n in DUAL_ROWS else 'color' if n in COLOR_ONLY_ROWS else 'unknown'
        date = from_excel(row[5], wb.epoch).date().isoformat() if isinstance(row[5], (float,int)) else str(row[5])[:10]
        games.append({
            'id': f'ngp-{n:03d}', 'title': row[6], 'platform': 'NGP' if is_mono else 'NGPC',
            'compatibility': compatibility, 'releaseDate': date, 'publisher': row[7] or '',
            'genre': GENRES.get(row[4], row[4] or '未分類'), 'originalGenre': row[4],
            'interest':'unknown', 'owned':'yes' if row[1] == '○' else 'unknown',
            'wanted':False, 'memo':'', 'legacy':{'owned':row[1] or '', 'rating':row[2] or '', 'want':row[3] or ''},
            'sourceRow':row_number, 'classificationSources':[SOURCE_A,SOURCE_B],
            'classificationNote': 'モノクロ版9作品の一覧と照合。カラー本体でもプレイ可能。' if is_mono else
                'カラー版。モノクロ本体での互換性は資料に未記載・不明があるため確認保留。' if compatibility == 'unknown' else
                'カラー版。2つの対応表の互換性記載を照合。' + ('本編はカラー専用。モノクロ本体では別のおまけゲームが動作する例外あり。' if n == 70 else ''),
        })
    wb.close()
    assert len(games) == 82 and len({g['id'] for g in games}) == 82
    library = {'schemaVersion':1,'revision':0,'updatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'sourceName':'ROMリスト.xlsx / ネオジオポケット', 'games':games}
    (ROOT / 'library.json').write_text(json.dumps(library,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'imported':len(games), 'platforms':dict(collections.Counter(g['platform'] for g in games)),
                      'compatibility':dict(collections.Counter(g['compatibility'] for g in games)),
                      'owned':dict(collections.Counter(g['owned'] for g in games))},ensure_ascii=False))

if __name__ == '__main__':
    import_library()
