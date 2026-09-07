"""Build reviewed relationships from existing records; never merge or edit games.

Series rules only identify membership. Version links use explicit work/edition
groups: a similar title alone never creates a version link.
"""
import copy
import itertools
import re
import unicodedata
import game_library as app
from import_game_relations import apply_relations


def title_key(title):
    # Keep numbers, !, &, and subtitle words: e.g. Puyo ! and !! are different.
    return re.sub(r'[\s・･〜～~‐‑–—\-：:．.]', '', unicodedata.normalize('NFKC', title)).casefold()


SERIES = [
    ('sakura', 'サクラ大戦', r'サクラ大戦', r'実戦パチンコ', 'https://sakura-taisen.com/archives/game/nenpyou/index.html'),
    ('ff', 'ファイナルファンタジー', r'ファイナルファンタジー|finalfantasy|チョコボ', '', 'https://jp.finalfantasy.com/histories'),
    ('dq', 'ドラゴンクエスト', r'ドラゴンクエスト|トルネコの大冒険', r'newニンテンドー2dsll', 'https://www.dragonquest.jp/products/'),
    ('zelda', 'ゼルダの伝説', r'ゼルダ|リンクの冒険', '', 'https://www.nintendo.com/jp/character/zelda/history/index.html'),
    ('kirby', '星のカービィ', r'カービィ|デデデでデン', '', 'https://www.kirby.jp/history/'),
    ('metroid', 'メトロイド', r'メトロイド', '', 'https://www.nintendo.co.jp/3ds/a9aj/history/index.html'),
    ('rockman', 'ロックマン', r'ロックマン', '', 'https://www.capcom.co.jp/ir/data/pdf/annual/2018/annual_2018_05.pdf'),
    ('sonic', 'ソニック', r'ソニック|テイルス|カオティクス|シャドウザヘッジホッグ', r'ウィングス|ウイングス|ビートソニック|ブラストマン|ダックテイルズ|ダークテイルズ|超音速', 'https://sonic.sega.jp/SonicChannel/history/'),
    ('bio', 'バイオハザード', r'バイオハザード|biohazard', '', 'https://game.capcom.com/residentevil/ja/lineup.html'),
    ('tales', 'テイルズ オブ', r'^テイルズオブ', '', 'https://tales-ch.jp/titles/'),
    ('ys', 'イース', r'^イース|^ワンダラーズフロムイース', '', 'https://www.falcom.co.jp/ys'),
    ('castlevania', '悪魔城ドラキュラ', r'悪魔城|^ドラキュラ伝説|^ドラキュラii呪い|^キャッスルヴァニア|^バンパイアキラー', '', 'https://www.konami.com/games/castlevania/jp/ja/history'),
    ('persona', 'ペルソナ', r'ペルソナ', '', 'https://p-ch.jp/p30th/'),
    ('saga', 'サガ', r'^(魔界塔士)?(saga|サガ)|^(ロマンシング|romancing)(saga|サガ)|^アンリミテッドサガ', '', 'https://www.jp.square-enix.com/saga_portal/chronicle/index.html'),
    ('mana', '聖剣伝説', r'聖剣伝説', '', 'https://www.jp.square-enix.com/column/detail/134/'),
    ('ace', '逆転裁判', r'逆転裁判|逆転検事', '', 'https://store.captown.capcom.com/collections/ace-attorney'),
    ('puyo', 'ぷよぷよ', r'ぷよぷよ|なぞぷよ', r'機動劇団', 'https://puyo.sega.jp/portal/series/'),
    ('pokemon', 'ポケットモンスター', r'ポケットモンスター|ポケモン|ピカチュウ', '', 'https://www.pokemon.co.jp/game/'),
]

# Each entry specifies known releases of ONE work. No fuzzy matching is used.
# Sources support the work identity, not merely similarity of names.
WORKS = []


def work(source, *releases):
    WORKS.append((source, releases))


# Format: platform(s), exact title, edition generation. Across generations the
# later group is explicitly a remake; within a group it is another release.
def e(platform, title, generation=0):
    return (platform, title, generation)


FF = 'https://jp.finalfantasy.com/titles'
DQ = 'https://www.dragonquest.jp/guideline/'
KIRBY = 'https://www.kirby.jp/history/'
METROID = 'https://www.nintendo.com/jp/switch/ayl8a/report/vol3/index.html'
CASTLE = 'https://www.konami.com/games/castlevania/jp/ja/history'
SAGA = 'https://www.jp.square-enix.com/saga_portal/chronicle/index.html'
POKEMON = 'https://www.pokemon.co.jp/game/'

# Nintendo Virtual Console preserves the original game; same-name games on
# different original hardware (Kirby's Star Stacker, Castlevania) stay separate.
for title, original, vc in [
    ('星のカービィ','GB','3DS-VC'), ('星のカービィ2','GB','3DS-VC'),
    ('カービィのブロックボール','GB','3DS-VC'), ('カービィのピンボール','GB','3DS-VC'),
    ('カービィのきらきらきっず','GB','3DS-VC'), ('カービィのきらきらきっず','SFC','New3DS-VC'),
    ('カービィボウル','SFC','New3DS-VC'), ('星のカービィ 鏡の大迷宮','GBA','3DS-VC'),
]: work(KIRBY,e(original,title),e(vc,title))
for title, original, vc in [('メトロイドフュージョン','GBA','3DS-VC'),('スーパーメトロイド','SFC','New3DS-VC')]:
    work(METROID,e(original,title),e(vc,title))
work(METROID,e('GB','メトロイド2 リターン オブ サムス'),e('3DS-VC','メトロイドII RETURN OF SAMUS'),e('3DS','メトロイド サムスリターンズ',1))
work(METROID,e('GBA','ファミコンミニ 23 メトロイド'),e('3DS-VC','メトロイド'),e('GBA','メトロイド ゼロミッション',1))
work('https://www.nintendo.co.jp/ds/ykwj/subgame/index.html',e('SFC','星のカービィ スーパーデラックス'),e('NDS','星のカービィ ウルトラスーパーデラックス',1))

for title, original, vc in [('悪魔城ドラキュラ','SFC','New3DS-VC'),('悪魔城ドラキュラXX','SFC','New3DS-VC'),('ドラキュラ伝説','GB','3DS-VC')]:
    work(CASTLE,e(original,title),e(vc,title))
work(CASTLE,e('GBA','ファミコンミニ 29 悪魔城ドラキュラ'),e('3DS-VC','悪魔城ドラキュラ'))
work(CASTLE,e('PS|SS','悪魔城ドラキュラX 月下の夜想曲'))

for title in ['赤','緑','青','ピカチュウ','金','銀','クリスタルバージョン']:
    work(POKEMON,e('GB|GB-GBC|GBC|3DS-VC','ポケットモンスター '+title))
work(POKEMON,e('GB-GBC|3DS-VC','ポケモンカードGB'))
for old,new,old_platform,new_platform in [('赤','ファイアレッド','GB|3DS-VC','GBA'),('緑','リーフグリーン','GB|3DS-VC','GBA'),('金','ハートゴールド','GB-GBC|3DS-VC','NDS'),('銀','ソウルシルバー','GB-GBC|3DS-VC','NDS'),('ルビー','オメガルビー','GBA','3DS'),('サファイア','アルファサファイア','GBA','3DS')]:
    work(POKEMON,e(old_platform,'ポケットモンスター '+old),e(new_platform,'ポケットモンスター '+new,1))

for numeral,subtitle in [('IV','導かれし者たち'),('V','天空の花嫁'),('VI','幻の大地'),('VII','エデンの戦士たち'),('VIII','空と海と大地と呪われし姫君')]:
    if numeral=='IV': releases=[e('PS','ドラゴンクエストIV '+subtitle),e('NDS','ドラゴンクエストIV '+subtitle,1)]
    elif numeral=='V': releases=[e('SFC','ドラゴンクエストV '+subtitle),e('PS2','ドラゴンクエストV '+subtitle,1),e('NDS','ドラゴンクエストV '+subtitle,1)]
    elif numeral=='VI': releases=[e('SFC','ドラゴンクエストVI '+subtitle),e('NDS','ドラゴンクエストVI '+subtitle,1)]
    elif numeral=='VII': releases=[e('PS','ドラゴンクエストVII '+subtitle),e('3DS','ドラゴンクエストVII '+subtitle,1)]
    else: releases=[e('PS2|3DS','ドラゴンクエストVIII '+subtitle)]
    work(DQ,*releases)
for title in ['ドラゴンクエストビルダーズ アレフガルドを復活せよ','ドラゴンクエストヒーローズII 双子の王と予言の終わり']:
    work(DQ,e('PS3|PSV',title))

for num in ['IV','V','VI']:
    work(FF,e('SFC|PS|New3DS-VC','ファイナルファンタジー'+num),e('GBA','FINAL FANTASY '+num+' ADVANCE'),*([e('WSC','ファイナルファンタジーIV')] if num=='IV' else []))
work('https://www.jp.square-enix.com/ff3/',e('NDS|PSP','ファイナルファンタジーIII'))
work('https://www.jp.square-enix.com/game/detail/ff4/',e('SFC|PS|WSC|New3DS-VC','ファイナルファンタジーIV'),e('GBA','FINAL FANTASY IV ADVANCE'),e('NDS','ファイナルファンタジーIV',1))

for num in ['', '2', '3']:
    work(SAGA,e('SFC|New3DS-VC','ロマンシング サ・ガ'+num),*([e('PSV','ロマンシング サガ'+num)] if num else [e('WSC','Romancing Sa・Ga')]))
work(SAGA,e('GB','魔界塔士SaGa'),e('WSC','魔界塔士 サ・ガ',1))
work(SAGA,e('GB','SaGa2 秘宝伝説'),e('NDS','サガ2秘宝伝説 ゴッデス オブ デスティニー',1))
work(SAGA,e('GB','SaGa3 時空の覇者[完結編]'),e('NDS','サガ3時空の覇者 Shadow or Light',1))
work(SAGA,e('SFC|New3DS-VC','ロマンシング サ・ガ'),e('WSC','Romancing Sa・Ga'),e('PS2','ロマンシング サガ ミンストレルソング',1))
work('https://www.jp.square-enix.com/game/detail/s_seiken/',e('GB','聖剣伝説 ファイナルファンタジー外伝'),e('GBA','新約 聖剣伝説',1))
work('https://www.jp.square-enix.com/seiken/sp/',e('GB','聖剣伝説 ファイナルファンタジー外伝'),e('PSV','聖剣伝説 ファイナルファンタジー外伝',1))
work('https://www.jp.square-enix.com/seiken2_som/',e('SFC','聖剣伝説2'),e('PSV','聖剣伝説2 SECRET of MANA',1))

ZELDA='https://www.nintendo.com/jp/character/zelda/history/index.html'
for name in ['時のオカリナ','ムジュラの仮面']:
    work('https://www.nintendo.com/jp/interview/bdgea/index.html',e('N64','ゼルダの伝説 '+name),e('3DS','ゼルダの伝説 '+name+' 3D',1))
work(ZELDA,e('GB','ゼルダの伝説 夢をみる島'),e('GB-GBC|3DS-VC','ゼルダの伝説 夢をみる島DX'))
for title in ['ゼルダの伝説 ふしぎの木の実 大地の章','ゼルダの伝説 ふしぎの木の実 時空の章']:
    work(ZELDA,e('GBC|3DS-VC',title))
work(ZELDA,e('GBA|3DS-VC','ゼルダの伝説 ふしぎのぼうし'))
work(ZELDA,e('GBA','ファミコンミニ 05 ゼルダの伝説1'),e('3DS-VC','ゼルダの伝説1'))
work(ZELDA,e('GBA','ファミコンミニ 25 リンクの冒険'),e('3DS-VC','リンクの冒険'))
work(ZELDA,e('SFC|New3DS-VC','ゼルダの伝説 神々のトライフォース'),e('GBA','ゼルダの伝説 神々のトライフォース&4つの剣'))

ROCK='https://www.capcom.co.jp/ir/data/pdf/annual/2018/annual_2018_05.pdf'
for title,platforms in [
    ('ロックマンワールド','GB|3DS-VC'),('ロックマンワールド2','GB|3DS-VC'),
    ('ロックマンワールド3','GB|3DS-VC'),('ロックマンワールド4','GB|3DS-VC'),('ロックマンワールド5','GB|3DS-VC'),
    ('ロックマンX サイバーミッション','GB-GBC|3DS-VC'),('ロックマンX2 ソウルイレイザー','GBC|3DS-VC'),
    ('ロックマン&フォルテ','SFC|GBA'),('ロックマンX','SFC|New3DS-VC'),('ロックマンX2','SFC|New3DS-VC'),
    ('ロックマンX4','PS|SS'),('ロックマン8 メタルヒーローズ','PS|SS'),
    ('スーパーアドベンチャー ロックマン','PS|SS'),('ロックマンX コマンドミッション','PS2|GC'),
    ('ロックマン7 宿命の対決!','SFC|New3DS-VC'),
    ('ロックマン','PS|3DS-VC'),('ロックマン2 Dr.ワイリーの謎','PS|3DS-VC'),
    ('ロックマン3 Dr.ワイリーの最期!?','PS|3DS-VC'),('ロックマン4 新たなる野望!!','PS|3DS-VC'),
    ('ロックマン5 ブルースの罠!?','PS|3DS-VC'),('ロックマン6 史上最大の戦い!!','PS|3DS-VC')
]: work(ROCK,e(platforms,title))
work('https://www.famitsu.com/game/title/6477/page/1',e('PS|SS|SFC|New3DS-VC','ロックマンX3'))
work('https://www.capcom.co.jp/support/faq/platform_psp_rockdash_036901.html',e('PS|N64|PSP','ロックマンDASH 鋼の冒険心'))

SONIC='https://sonic.sega.jp/SonicChannel/history/'
for title,platforms in [
    ('ソニック&テイルス2','GG|3DS-VC'),('ソニックドリフト2','GG|3DS-VC'),
    ('テイルスアドベンチャー','GG|3DS-VC'),('ソニックラビリンス','GG|3DS-VC'),('Gソニック','GG|3DS-VC'),
    ('ソニック ジェムズ コレクション','PS2|GC'),('シャドウザヘッジホッグ','PS2|GC'),('ソニックライダーズ','PS2|GC')
]: work(SONIC,e(platforms,title))
work('https://sonic.sega.jp/SonicChannel/gametitle/SonicHeroes.html',e('PS2|GC','ソニック ヒーローズ'))
work('https://sonic.sega.jp/SonicChannel/gametitle/SonicAdventure.html',e('DC|PS3','ソニックアドベンチャー'),e('GC','ソニックアドベンチャーDX'))
work(SONIC,e('DC|PS3','ソニックアドベンチャー2'),e('GC','ソニックアドベンチャー2 バトル'))
# The GG original and its 3DS VC release are NOT the MD / PS3 2006 game.
work(SONIC,e('GG|3DS-VC','ソニックザヘッジホッグ'))
work(SONIC,e('GG|3DS-VC','ソニックザヘッジホッグ2'))
work(SONIC,e('MD','ソニックザヘッジホッグ'),e('3DS','3D ソニックザヘッジホッグ'))
work(SONIC,e('MD|PS3','ソニックザヘッジホッグ2'),e('3DS','3D ソニックザヘッジホッグ2'))

PUYO='https://puyo.sega.jp/portal/series/'
for title,platforms in [('ぷよぷよ通','MD|GG|SS|WS|NGPC|3DS-VC'),('ぷよぷよフィーバー','GBA|PS2|GC|NDS|PSP|DC'),('ぷよぷよフィーバー2【チュー!】','PS2|PSP|NDS'),('ぷよぷよ7','NDS|PSP'),('なぞぷよ','GG|3DS-VC'),('なぞぷよ2','GG|3DS-VC'),('なぞぷよ アルルのルー','GG|3DS-VC')]:
    work(PUYO,e(platforms,title))
work('https://puyo.sega.jp/portal/series/puyopuyo%21.html',e('NDS|PSP|PS2','ぷよぷよ!'))
work('https://puyo.sega.jp/puyopuyotetris/spec/index.html',e('3DS|PS3|PSV','ぷよぷよテトリス'))

TALES='https://tales-ch.jp/titles/'
for title,platforms in [('テイルズ オブ エターニア','PS|PSP'),('テイルズ オブ デスティニー2','PS2|PSP'),('テイルズ オブ シンフォニア','GC|PS2'),('テイルズ オブ ジ アビス','PS2|3DS')]:
    work(TALES,e(platforms,title))
work('https://www.bandainamcoent.co.jp/cs/list/talesofrebirth_psp/product/',e('PS2|PSP','テイルズ オブ リバース'))
work('https://www.bandainamcoent.co.jp/cs/list/talesofdestiny_ps2/product/',e('PS','テイルズ オブ デスティニー'),e('PS2','テイルズ オブ デスティニー',1),e('PS2','テイルズ オブ デスティニー ディレクターズカット',1))

BIO='https://game.capcom.com/residentevil/ja/lineup.html'
work(BIO,e('PS|SS','バイオハザード'),e('GC','バイオハザード',1))
work(BIO,e('PS|N64|GC','バイオハザード2'),e('DC','バイオハザード2 Value plus'))
work(BIO,e('PS','バイオハザード3 LAST ESCAPE'),e('GC|DC','バイオハザード3 ラストエスケープ'))
work(BIO,e('GC|PS2','バイオハザード4'))
work(BIO,e('PS2|GC|DC','バイオハザード コードベロニカ 完全版'))
work(BIO,e('PS3|PSV','バイオハザード リベレーションズ2'))
work('https://www.capcom.co.jp/support/faq/platform_ps3_biohd_0134652.html',e('GC','バイオハザード'),e('PS3','バイオハザード HDリマスター'))

YS='https://www.falcom.co.jp/ys'
work(YS,e('PCE-CD|PS3|PSP','イースI・II'))
work(YS,e('PCE-SCD|PSP','イースIV The Dawn of Ys'))
work(YS,e('PS2|PSP','イース ナピシュテムの匣'))

PERSONA='https://p-ch.jp/p30th/'
work(PERSONA,e('PS','女神異聞録 ペルソナ'),e('PSP','ペルソナ'))
work(PERSONA,e('PS|PSP','ペルソナ2 罪'))
work(PERSONA,e('PS|PSP','ペルソナ2 罰'))
work(PERSONA,e('PS2','ペルソナ3'),e('PSP','ペルソナ3ポータブル'))
work(PERSONA,e('PS2','ペルソナ4'),e('PSV','ペルソナ4 ザゴールデン'))
ACE='https://store.captown.capcom.com/collections/ace-attorney'
work(ACE,e('GBA','逆転裁判'),e('NDS','逆転裁判 蘇る逆転'))
work(ACE,e('GBA','逆転裁判2'),e('NDS','逆転裁判2 ベスト プライス!'))
work(ACE,e('GBA|NDS','逆転裁判3'))
work(ACE,e('NDS|3DS','逆転裁判4'))


def build(data, existing):
    result=copy.deepcopy(existing)
    result['checkedAt']='2026-09-07'
    result['scope']='登録済みタイトルのシリーズを照合。他機種版・リメイクは作品ごとの明示的な対応表で関連付け。同名だけの自動関連付けは行わない。'
    series_by_id={s['id']:s for s in result['series']}
    for sid,name,include,exclude,source in SERIES:
        members=[g['id'] for g in data['games'] if re.search(include,title_key(g['title'])) and not (exclude and re.search(exclude,title_key(g['title'])))]
        assert len(members)>=2,(sid,'not enough matches')
        sources=list(dict.fromkeys(series_by_id.get(sid,{}).get('sources',[])+[source]))
        series_by_id[sid]={'id':sid,'name':name,'games':members,'sources':sources}
    result['series']=list(series_by_id.values())
    links={frozenset((x['a'],x['b'])):x for x in result['links'] if x.get('managedBy')!='build_game_relations'}
    for source,releases in WORKS:
        matched={}
        for platforms,title,generation in releases:
            matches=[g for g in data['games'] if g['platform'] in platforms.split('|') and title_key(g['title'])==title_key(title)]
            assert matches,('missing work edition',platforms,title)
            for g in matches:matched[g['id']]=(g,generation)
        assert len(matched)>1,('work has only one release',releases)
        for (a,ga),(b,gb) in itertools.combinations(matched.values(),2):
            if a['platform']==b['platform'] and ga==gb:continue
            if ga>gb:a,b,ga,gb=b,a,gb,ga
            if ga==gb and (a['releaseDate'],a['id'])>(b['releaseDate'],b['id']):a,b=b,a
            pair=frozenset((a['id'],b['id']))
            kind='remake' if ga!=gb else 'edition'
            if pair in links:
                assert links[pair]['kind']==kind,(a['title'],b['title'],'conflicting relation kinds')
                links[pair]['sources']=list(dict.fromkeys(links[pair]['sources']+[source]))
            else:links[pair]={'a':a['id'],'b':b['id'],'kind':kind,'sources':[source],'managedBy':'build_game_relations'}
    result['links']=list(links.values())
    apply_relations(data,result)
    return result


if __name__=='__main__':
    facts=build(app.library(),app.read_json(app.ROOT/'作品の関連情報.json'))
    app.write_atomic(app.ROOT/'作品の関連情報.json',facts)
    print('Series:',len(facts['series']),'records:',len({g for s in facts['series'] for g in s['games']}),'version pairs:',len(facts['links']))
    for series in facts['series']:print(series['name'],len(series['games']))
