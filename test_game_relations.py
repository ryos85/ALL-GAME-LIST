import copy
import unittest
import game_library as app
from import_game_relations import apply_relations
from build_game_relations import build, title_key


class RelationshipTests(unittest.TestCase):
    def setUp(self):
        self.data=app.library()
        self.relations=app.read_json(app.ROOT/'作品の関連情報.json')

    def test_preserves_records_and_reapply_is_unchanged(self):
        before=copy.deepcopy(self.data)
        after=apply_relations(self.data,self.relations)
        self.assertEqual(self.data,before)
        self.assertEqual(after['games'],before['games'])
        self.assertEqual(apply_relations(after,self.relations),after)
        self.assertEqual(after['relationships'],self.relations)

    def game(self,platform,title):
        return next(g for g in self.data['games'] if g['platform']==platform and title_key(g['title'])==title_key(title))

    def relation(self,a,b):
        return next((link for link in self.relations['links'] if {link['a'],link['b']}=={a['id'],b['id']}),None)

    def test_same_title_does_not_link_different_games(self):
        for title,left,right in [('ソニックザヘッジホッグ','MD','PS3'),('ソニックザヘッジホッグ','MD','GG'),('カービィのきらきらきっず','GB','SFC'),('悪魔城ドラキュラ','3DS-VC','SFC')]:
            self.assertIsNone(self.relation(self.game(left,title),self.game(right,title)))

    def test_remake_direction_uses_edition_not_vc_release_date(self):
        original=self.game('New3DS-VC','ファイナルファンタジーIV')
        remake=self.game('NDS','ファイナルファンタジーIV')
        self.assertGreater(original['releaseDate'],remake['releaseDate'])
        link=self.relation(original,remake)
        self.assertEqual((link['a'],link['b'],link['kind']),(original['id'],remake['id'],'remake'))

    def test_similar_words_do_not_create_false_series(self):
        byid={g['id']:g for g in self.data['games']}
        excluded={'sonic':['ブラストマン','ウィングス','ダックテイルズ'],'saga':['ぷりサガ','ZOIDS'],'ys':['イースター'],'tales':['ダックテイルズ']}
        for sid,words in excluded.items():
            series=next(s for s in self.relations['series'] if s['id']==sid)
            for member in series['games']:
                self.assertFalse(any(word in byid[member]['title'] for word in words))
        self.assertNotEqual(title_key('ぷよぷよ!'),title_key('ぷよぷよ!!'))

    def test_two_remakes_are_not_presented_as_each_others_original(self):
        original=self.game('SFC','ドラゴンクエストV 天空の花嫁')
        ps2=self.game('PS2','ドラゴンクエストV 天空の花嫁')
        ds=self.game('NDS','ドラゴンクエストV 天空の花嫁')
        self.assertEqual(self.relation(original,ps2)['kind'],'remake')
        self.assertEqual(self.relation(original,ds)['kind'],'remake')
        self.assertEqual(self.relation(ps2,ds)['kind'],'edition')

    def test_builder_is_idempotent_and_preserves_manual_links(self):
        self.assertEqual(build(self.data,self.relations),self.relations)
        manual={'a':self.game('PS','クロノ・クロス')['id'],'b':self.game('SFC','クロノ・トリガー')['id'],'kind':'edition','sources':['https://example.com/manual']}
        extra=copy.deepcopy(self.relations);extra['links'].append(manual)
        self.assertIn(manual,build(self.data,extra)['links'])

    def test_dangling_and_self_links_are_rejected(self):
        for target in ('nonexistent',self.relations['links'][0]['a']):
            invalid=copy.deepcopy(self.relations)
            invalid['links'][0]['b']=target
            with self.assertRaises(AssertionError):apply_relations(self.data,invalid)

    def test_duplicate_pair_is_rejected(self):
        invalid=copy.deepcopy(self.relations)
        link=invalid['links'][0]
        invalid['links'].append({**link,'a':link['b'],'b':link['a']})
        with self.assertRaises(AssertionError):apply_relations(self.data,invalid)


if __name__=='__main__':unittest.main()
