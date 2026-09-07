import copy
import json
import unittest
from urllib.parse import urlparse

import import_hardware_catalog as catalog


def item(identifier,title,main=True,release=20131012):
    return {'id':identifier,'nameJa':title,'isMain':main,'releaseDateOrder':release}


class HardwareCatalogTests(unittest.TestCase):
    def test_content_versions_stay_separate_and_packages_join_correct_version(self):
        versions=[item(1,'ポケットモンスター X'),item(2,'ポケットモンスター Y',False),
                  item(3,'ポケットモンスター Y （ニンテンドーeショップ ダウンロード版）',False),
                  item(4,'ポケットモンスター X パック プレミアムゴールド',False)]
        split=catalog.split_versions(versions)
        self.assertEqual(len(split),2)
        self.assertEqual({v['id'] for v in split[0][1]},{1,4})
        self.assertEqual({v['id'] for v in split[1][1]},{2,3})

    def test_expanded_game_is_not_a_budget_package(self):
        split=catalog.split_versions([item(1,'三國志IV'),item(2,'三國志IV with パワーアップキット',False),
                                     item(3,'三國志IV （コーエー定番シリーズ）',False)])
        self.assertEqual(len(split),2)
        self.assertEqual(len(split[0][1]),2)

    def test_apply_preserves_existing_and_repeated_import_preserves_edits(self):
        old={'id':'original','title':'既存作品','interest':'play','memo':'保存済み','owned':'yes'}
        before={'games':[old],'platforms':{},'families':{},'revision':16,'updatedAt':'old'}
        snapshot={'scope':'test','games':[catalog.row('PS','新規作品','1994-12-03',source='https://www.famitsu.com/') ]}
        original=copy.deepcopy(before)
        applied,count=catalog.apply_snapshot(before,snapshot)
        self.assertEqual(before,original)
        self.assertEqual(applied['games'][0],old)
        self.assertEqual(count,1)
        applied['games'][1].update(interest='curious',wanted=True,memo='追加後のメモ',owned='yes')
        again,count=catalog.apply_snapshot(applied,snapshot)
        self.assertEqual(again,applied)
        self.assertEqual(count,0)

    def test_different_platforms_have_different_ids(self):
        a=catalog.row('PS','同名作品','1996-01-01',source='https://www.famitsu.com/')
        b={**a,'platform':'PS2'}
        self.assertNotEqual(catalog.make_game(a)['id'],catalog.make_game(b)['id'])

    def test_later_eshop_release_does_not_replace_cartridge_release(self):
        base=catalog.row('3DS','カートリッジ作品','2014-01-23',source='https://www.famitsu.com/',grade='press')
        extra=catalog.row('3DS','カートリッジ作品','2019-02-06',source='https://www.nintendo.co.jp/',grade='official',nintendoId='123')
        merged,_=catalog.merge_sources([base],[extra])
        self.assertEqual(merged[0]['releaseDate'],'2014-01-23')
        self.assertEqual(merged[0]['grade'],'press')

    def test_dataset_is_valid_and_contains_only_approved_sources(self):
        rows=json.loads(catalog.SNAPSHOT.read_text(encoding='utf8'))['games']
        self.assertEqual({catalog.PLATFORMS[r['platform']]['family'] for r in rows},set(catalog.FAMILIES))
        ids=[catalog.make_game(r)['id'] for r in rows]
        self.assertEqual(len(ids),len(set(ids)))
        allowed={'www.famitsu.com','www.nintendo.co.jp','www.sega.jp','www.super-famicom.jp',
                 'www.gavas.jp','tk-nz.game.coocan.jp','super-famicom.jp'}
        for r in rows:
            self.assertEqual(catalog.date(r['releaseDate']),r['releaseDate'])
            self.assertTrue(r['title'].strip())
            self.assertNotIn('【海外',r['title'])
            # This is a separately sold Saturn title, despite "preview" in its name.
            if r['title']=='だいな あいらん 予告編':
                self.assertEqual(r['platform'],'SS')
                self.assertEqual(r['grade'],'official')
            else:
                self.assertFalse(catalog.EXCLUDE_TITLE.search(r['title']),r['title'])
            self.assertNotEqual(r['genre'],'本体・周辺商品')
            for source in r['sources']:self.assertIn(urlparse(source).hostname,allowed)
        self.assertEqual(sum(r['platform']=='GG' for r in rows),196)
        self.assertEqual(sum(r['platform']=='PC-FX' for r in rows),62)


if __name__=='__main__':unittest.main()
