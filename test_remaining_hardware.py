import json
import unittest
from pathlib import Path
from unittest.mock import patch

import import_hardware_catalog as catalog
import import_remaining_hardware as remaining


class RemainingHardwareTests(unittest.TestCase):
    def test_wrapped_titles_and_visual_memory_year_boundary(self):
        with patch.object(Path,'read_text',return_value='''L0: 発売日  | タイトル | ジャンル | 価格 | 型番
L1: 2004年
L2: 2月24日 | 本編
L3: 続き | パズル | 4980円 | HDR-001 |
L4: ##### ソフト内蔵ビジュアルメモリ
L5: 1998
L6: 7月11日 | 内蔵ゲーム | シミュレーション | 2500円 | － | －
L7: ## よく見られるタグ
'''):
            rows=remaining.sega_records(Path('fixture'),'dc_sega')
            self.assertEqual([(r['platform'],r['title'],r['releaseDate']) for r in rows],
                             [('DC','本編 続き','2004-02-24'),('DC-VM','内蔵ゲーム','1998-07-11')])

    def test_content_plus_stays_distinct_and_reissue_merges(self):
        rows=[catalog.row('SS',name,date,source='https://www.sega.jp/') for name,date in
              [('ボクサーズ','1997-01-10'),('ボクサーズ＋','1997-05-02'),('ボクサーズ（限定版）','1997-06-01')]]
        merged=remaining.merge_packages(rows)
        self.assertEqual(len(merged),2)
        self.assertEqual(len({catalog.make_game(r)['id'] for r in merged}),2)
        self.assertEqual(merged[0]['releaseDate'],'1997-01-10')
        self.assertEqual(merged[0]['variants'][0]['title'],'ボクサーズ（限定版）')

    def test_catalog_counts_categories_and_confirmed_title_correction(self):
        rows=json.loads(catalog.SNAPSHOT.read_text('utf-8'))['games']
        new=[r for r in rows if r['platform'] in remaining.TARGETS]
        self.assertEqual(len(new),2998)
        self.assertEqual(sum(r['platform']=='SFC-NP' for r in new),25)
        self.assertEqual(sum(r['platform']=='SFC-TURBO' for r in new),13)
        self.assertEqual(sum(r['platform']=='DC-VM' for r in new),5)
        vol2=next(r for r in new if r.get('productCode')=='T-32103G')
        self.assertIn('Vol.2',vol2['title'])
        self.assertEqual(vol2['releaseDate'],'1998-01-15')
        self.assertTrue(vol2['catalogReview'])
        for r in new:
            self.assertTrue(r['publisher'])
            self.assertTrue(r['genre'])
            self.assertTrue(r['sources'])
        self.assertFalse(any(r['title']=='サクラ大戦 COMPLETE BOX' for r in new))
        sakura=next(r for r in new if r['platform']=='DC' and r['title']=='サクラ大戦')
        self.assertIn('サクラ大戦 COMPLETE BOX',[v['title'] for v in sakura['variants']])


if __name__=='__main__':unittest.main()
