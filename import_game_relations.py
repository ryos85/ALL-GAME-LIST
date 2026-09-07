"""Apply reviewed game relationships without modifying any personal records."""
import copy
from urllib.parse import urlparse
import game_library as app


def apply_relations(data, relationships):
    assert relationships['schemaVersion']==1
    ids={game['id'] for game in data['games']}
    series_ids=set()
    for series in relationships['series']:
        assert series['id'] not in series_ids
        series_ids.add(series['id'])
        assert len(series['games'])==len(set(series['games']))
        assert set(series['games'])<=ids
        assert series['sources'] and all(urlparse(s).scheme=='https' for s in series['sources'])
    pairs=set()
    for link in relationships['links']:
        pair=frozenset((link['a'],link['b']))
        assert len(pair)==2 and pair<=ids and pair not in pairs
        assert link['kind'] in {'port','remake','collection'}
        assert link['sources'] and all(urlparse(s).scheme=='https' for s in link['sources'])
        pairs.add(pair)
    result=copy.deepcopy(data)
    if result.get('relationships')!=relationships:
        result['relationships']=copy.deepcopy(relationships)
        result['revision']+=1
        result['updatedAt']=app.now()
    return result


if __name__=='__main__':
    before=app.library()
    result=apply_relations(before,app.read_json(app.ROOT/'作品の関連情報.json'))
    assert result['games']==before['games']
    if result!=before:
        assert app.library()==before, 'Records changed while preparing relationships; retry.'
        app.write_atomic(app.ROOT/'library.json',result)
    app.export_viewer()
    print('Relationship metadata applied; personal records preserved.')
