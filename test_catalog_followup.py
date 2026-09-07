import copy
import unittest

from catalog_followup import build


class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.games = [dict(id=i, title=i, family='GB', platform='GB', releaseDate='2000-08-01',
                           interest='play', owned='yes', wanted=True, memo='箱付き',
                           legacy={'rating': '◎'}, sourceRecords=[{'row': 5}])
                      for i in ['ngp-079', 'gb-1055', 'uncertain', 'pce-155']]
        self.current = {'games': self.games}
        self.report = {'issues': [dict(id=i, kind='発売日', status='資料間不一致', before='2000-08-01')
                                  for i in ['gb-1055', 'uncertain', 'pce-155']],
                       'rows': [dict(id=g['id'], status='日付相違') for g in self.games]}
        self.evidence = [[i, d, '資料を照合', grade, ['https://example.com/source']]
                         for i, d, grade in [('ngp-079', '2001-01-25', 'multiple'),
                                              ('gb-1055', '2000-07-31', 'official'),
                                              ('uncertain', None, 'unresolved'),
                                              ('pce-155', None, 'scope')]]

    def test_personal_fields_and_input_are_preserved(self):
        before = copy.deepcopy(self.current)
        result, report = build(self.current, self.report, self.evidence)
        self.assertEqual(self.current, before)
        for old, new in zip(self.games, result['games']):
            for key in ['id', 'interest', 'owned', 'wanted', 'memo', 'legacy', 'sourceRecords']:
                self.assertEqual(old[key], new[key])
        self.assertEqual(report['followup']['counts']['訂正済み'], 2)

    def test_uncertain_dates_are_not_fabricated_and_hardware_is_excluded(self):
        result, _ = build(self.current, self.report, self.evidence)
        lookup = {g['id']: g for g in result['games']}
        self.assertEqual(lookup['uncertain']['releaseDate'], '2000-08-01')
        self.assertNotIn('releaseDateSources', lookup['uncertain'])
        self.assertTrue(lookup['pce-155']['releaseOrderExcluded'])
        self.assertEqual([v['releaseDate'] for v in lookup['gb-1055']['releaseVariants']],
                         ['2000-07-31', '2000-08-01'])

    def test_missing_duplicate_and_invalid_evidence_are_rejected(self):
        for invalid in [self.evidence[:-1], self.evidence + self.evidence[:1]]:
            with self.assertRaises(ValueError):
                build(self.current, self.report, invalid)
        invalid = copy.deepcopy(self.evidence)
        invalid[0][1] = '2001-02-30'
        with self.assertRaises(ValueError):
            build(self.current, self.report, invalid)

    def test_repeat_application_is_rejected(self):
        result, report = build(self.current, self.report, self.evidence)
        with self.assertRaises(ValueError):
            build(result, report, self.evidence)


if __name__ == '__main__':
    unittest.main()
