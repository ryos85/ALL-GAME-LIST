import copy
import unittest
import game_library as app
from import_game_relations import apply_relations


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
        self.assertEqual(len({g for s in self.relations['series'] for g in s['games']}),14)

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
