import copy
import json
import unittest
from pathlib import Path

import catalog_finalize as finish
import catalog_completion_evidence as evidence
import import_workbook as importer


def record(ident, **kwargs):
    g=dict(id=ident,title=ident,platform='GB',family='GB',releaseDate='1990-01-01',
        interest='unknown',owned='unknown',wanted=False,memo='',sourceRow=1,
        sourceRecords=[{'row':ident}],legacy={'rating':'○'},genre='RPG',publisher='検証用',classificationNote='')
    g.update(kwargs)
    return g


class CompletionTests(unittest.TestCase):
    def test_merge_preserves_both_personal_records(self):
        a=record('a',interest='none',owned='no',memo='初版のメモ')
        b=record('b',interest='play',owned='yes',wanted=True,memo='再販のメモ')
        original=copy.deepcopy(b)
        finish.merge_edition(a,b,'再販',['https://example.com/edition'])
        self.assertEqual(a['mergedEditions'],[original])
        self.assertEqual(a['preConsolidationPersonal']['owned'],'no')
        self.assertEqual(a['interest'],'none')
        self.assertEqual(a['owned'],'yes')
        self.assertTrue(a['wanted'])
        self.assertIn('初版のメモ',a['memo'])
        self.assertIn('再販のメモ',a['memo'])
        self.assertEqual(a['sourceRecords'],[{'row':'a'},{'row':'b'}])
        self.assertEqual(b,original)

    def test_different_platform_rejected(self):
        with self.assertRaises(ValueError):
            finish.merge_edition(record('a'),record('b',platform='GBC'),'再販',[])

    def test_reimport_does_not_resurrect_editions_or_remove_platforms(self):
        a,b=record('a'),record('b',releaseDate='1995-01-01')
        finish.merge_edition(a,b,'再販',[])
        state=dict(games=[a],revision=1,platforms={'PCE-GE':{'name':'専用カード'}})
        result,added=importer.merge_library(state,[b],{'GB':1})
        self.assertEqual(added,[])
        self.assertEqual(result['games'],[a])
        self.assertIn('PCE-GE',result['platforms'])
        b['title']='IDが同じ別作品'
        with self.assertRaises(ValueError): importer.merge_library(state,[b],{})

    def test_applied_state_has_no_pending_candidate_and_retains_unknown_dates(self):
        # Exercise the real reviewed mapping against a minimal non-personal fixture.
        games={}
        for old,new,_,_ in evidence.MERGES:
            games.setdefault(new,record(new))
            games[old]=record(old,releaseDate='2002-03-01')
        for ident,_,_ in evidence.KEEP: games.setdefault(ident,record(ident))
        report=dict(rows=[],issues=[dict(kind='収録範囲',title=t,status='追加候補',id='') for t,_,_ in evidence.EXCLUSIONS])
        state=dict(games=list(games.values()),platforms={})
        before=copy.deepcopy(state)
        result,report=finish.build(state,report)
        self.assertEqual(state,before)
        self.assertEqual(len(result['games']),len(state['games'])+30-23)
        self.assertTrue(all(i['workStatus']=='完了' for i in report['issues']))
        lookup={g['id']:g for g in result['games']}
        self.assertEqual(lookup['pce-unlicensed-10']['releaseDate'],'1994')
        self.assertTrue(lookup['pce-unlicensed-10']['releaseOrderExcluded'])
        self.assertEqual(lookup['pce-unlicensed-13']['releaseDateVerification']['grade'],'unresolved')
        self.assertEqual(sum(g['platform']=='PCE-GE' for g in result['games']),7)
        self.assertEqual(len([g for g in result['games'] if g['id'].startswith('pce-ultrabox')]),6)
        with self.assertRaises(ValueError): finish.build(result,report)


if __name__=='__main__': unittest.main()
