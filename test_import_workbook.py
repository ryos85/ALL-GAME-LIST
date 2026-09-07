import copy
import unittest

import import_workbook as importer


def record(identifier='gba-001', **overrides):
    result = {'id': identifier, 'title': '検証用ゲーム', 'platform': 'GBA', 'releaseDate': '2001-03-21',
              'publisher': '検証用メーカー', 'sourceRow': 2, 'sourceRecords': [{'row': 2}],
              'genre': 'RPG', 'owned': 'unknown', 'interest': 'unknown', 'wanted': False,
              'memo': '', 'legacy': {'rating': '○'}, 'classificationNote': ''}
    result.update(overrides)
    return result


class WorkbookImportTests(unittest.TestCase):
    def test_hardware_and_compatibility_are_distinct(self):
        cases = [('WS', '', 'WS'), ('WS', '両対応', 'WSC'), ('WS', 'カラー専用', 'WSC'),
                 ('PCE', '', 'PCE'), ('PCE', 'CD-ROM2専用', 'PCE-CD'),
                 ('PCE', 'SUPER CD-ROM2専用\n/アーケードカード対応', 'PCE-SCD'),
                 ('PCE', 'アーケードカード専用', 'PCE-ACD'),
                 ('PCE', 'スーパーグラフィックス専用', 'SGX'),
                 ('PCE', 'スーパーグラフィックス対応', 'PCE'),
                 ('MD', 'メガCD専用', 'MCD'), ('MD', 'スーパー32X専用', '32X'),
                 ('GB', 'ゲームボーイカラー対応', 'GB-GBC'), ('GB', 'ゲームボーイカラー専用', 'GBC')]
        for family, note, expected in cases:
            with self.subTest(family=family, note=note):
                self.assertEqual(importer.classify(family, note, 1)[0], expected)
        self.assertEqual(importer.classify('GB', 'ニンテンドウパワー専用', 979)[0], 'GBC')
        self.assertEqual(importer.classify('GB', 'ニンテンドウパワー専用', 1055)[0], 'GB-GBC')
        with self.assertRaises(ValueError):
            importer.classify('MD', '新しい未確認の区分', 1)

    def test_deduplicate_exact_work_keeping_source_rows(self):
        a = record()
        b = record('gba-002', sourceRow=3, sourceRecords=[{'row': 3}], genre='アクション', owned='yes')
        merged = importer.consolidate([a, b])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['sourceRecords'], [{'row': 2}, {'row': 3}])
        self.assertEqual(merged[0]['owned'], 'yes')
        self.assertIn('ジャンル表記差', merged[0]['classificationNote'])
        self.assertEqual(a['sourceRecords'], [{'row': 2}])

    def test_different_platform_or_release_remains_separate(self):
        candidates = [record(), record('mcd-001', platform='MCD'),
                      record('gba-002', releaseDate='2002-03-21')]
        self.assertEqual(len(importer.consolidate(candidates)), 3)

    def test_merge_preserves_personal_records_and_is_idempotent(self):
        previous = record('ngp-001', platform='NGP', interest='play', wanted=True, memo='残すメモ')
        current = {'schemaVersion': 1, 'revision': 10, 'updatedAt': 'before', 'games': [previous]}
        original = copy.deepcopy(current)
        result, added = importer.merge_library(current, [record()], {'ゲームボーイアドバンス': 1})
        self.assertEqual(current, original)
        self.assertEqual(result['games'][0], previous)
        self.assertEqual(len(added), 1)
        result['games'][1].update(interest='curious', wanted=True, memo='取り込み後の編集')
        again, added_again = importer.merge_library(result, [record()], {'ゲームボーイアドバンス': 1})
        self.assertEqual(again, result)
        self.assertEqual(added_again, [])

    def test_id_collision_fails_instead_of_replacing_a_game(self):
        current = {'revision': 1, 'games': [record()]}
        with self.assertRaises(ValueError):
            importer.merge_library(current, [record(title='別の作品')], {'GBA': 1})


if __name__ == '__main__':
    unittest.main()
