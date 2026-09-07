"""Reviewed edition relationships and Japanese omissions; no personal records."""
MAME = 'https://raw.githubusercontent.com/mamedev/mame/master/hash/gameboy.xml'
PCE = 'https://pcefan.com/pcengine/entry15.html'
CATALOG = 'https://gamezero.online/special/pcecp/'
UNLICENSED = 'https://tororon-lifehach.com/2021/10/05/%EF%BD%90%EF%BD%83%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%B3%E9%9D%9E%E5%85%AC%E8%AA%8D%E3%82%BF%E3%82%A4%E3%83%88%E3%83%AB%E3%81%BE%E3%81%A8%E3%82%81%E3%80%80%E3%82%BD%E3%83%95%E3%83%88%E3%82%AB%E3%82%BF/'
REISSUES = 'https://ameblo.jp/ritslow/entry-12367136678.html'
WIZ = 'https://emonoya.net/info/news/already.html'

# Source ID, retained first-release ID, reason, evidence.
MERGES = [
 ('gb-667','gb-573','同一作品の価格改定版。', [REISSUES]),
 ('gb-676','gb-062','ハッピープライス版を通常版に統合。', [REISSUES]),
 ('gb-677','gb-310','ハッピープライス版を通常版に統合。', [REISSUES]),
 ('gb-678','gb-336','ハッピープライス版を通常版に統合。', [REISSUES]),
 ('gb-680','gb-488','ハッピープライス版を通常版に統合。', [REISSUES]),
 ('gb-684','gb-555','モノクロ版の再発売。カラー対応のスーパーボンブリスDXとは別。', [REISSUES,MAME]),
 ('gb-706','gb-399','ハッピープライス版を通常版に統合。', [REISSUES]),
 ('gb-707','gb-485','ハッピープライス版を通常版に統合。', [REISSUES]),
 ('gb-783','gb-474','廉価版はアイマックスのDMG-YNJ-1。通常版DMG-YNJに対応し、他社の詰め将棋とは分ける。', ['https://www.furu1.online/product/detail/10023820',MAME]),
 ('gb-818','gb-221','復刻発売時の告知にゲーム内容の変更なしと明記。', [WIZ,'https://emonoya.net/goods/game/handheld.html']),
 ('gb-819','gb-366','復刻発売時の告知にゲーム内容の変更なしと明記。', [WIZ,'https://emonoya.net/goods/game/handheld.html']),
 ('gb-820','gb-427','復刻発売時の告知にゲーム内容の変更なしと明記。', [WIZ,'https://emonoya.net/goods/game/handheld.html']),
 ('gb-1225','gb-1140','HUDSON THE BESTの価格改定版。', [REISSUES]),
 ('gb-1264','gb-831','同じ学習作品のスペシャルエディション。再販・付属品の違いは別版の記録として保存。MAMEでも通常版に対応づけられている。2002年版は月までの記載のため発売日は月単位で残す。', [MAME,REISSUES,'https://www.saruyama-gamesoft.com/gameboy.htm']),
 ('gb-1265','gb-877','同じ学習作品のスペシャルエディション。MAMEの通常版との対応を確認。2002年版の発売日は月単位で残す。', [MAME,REISSUES]),
 ('gb-1266','gb-905','同じ学習作品のスペシャルエディション。MAMEの通常版との対応を確認。2002年版の発売日は月単位で残す。', [MAME,REISSUES]),
 ('gb-1267','gb-925','同じ学習作品のスペシャルエディション。MAMEの通常版との対応を確認。2002年版の発売日は月単位で残す。', [MAME,REISSUES]),
 ('gb-1268','gb-991','同じ学習作品のスペシャルエディション。MAMEの通常版との対応を確認。2002年版の発売日は月単位で残す。', [MAME,REISSUES]),
 ('gb-1283','gb-1182','同じ学習作品の再販。版ごとの型番・元の発売日記録は保存し、作品としては初版に統合。', [MAME,REISSUES,'https://www.saruyama-gamesoft.com/gameboy.htm']),
 ('gb-1284','gb-1183','同じ学習作品の再販。版ごとの型番・元の発売日記録は保存し、作品としては初版に統合。', [MAME,REISSUES,'https://www.saruyama-gamesoft.com/gameboy.htm']),
 ('gb-664','gb-324','名作シリーズの再販。MAMEの初版製品情報に1997-07-25の再販を明記。', [MAME]),
 ('gb-665','gb-096','名作シリーズの再販。MAMEの初版製品情報に1997-07-25の再販を明記。', [MAME]),
 ('gb-809','gb-796','実物比較でライト版と通常青版のカートリッジ型番DMG-ABEJ-JPN・刻印が一致。ライト版の説明書はバーコード入力を省くコマンドを案内。付属品の異なるパッケージとして統合。', ['https://note.com/can_kids_banana/n/na2aca8defdd2']),
]
KEEP = [
 ('md-504','タイトル中の2が示す続編。セガ公式一覧でも前作と別の型番・容量で掲載されている。', ['https://www.sega.jp/history/hard/megadrive/software_l.html']),
 ('md-439','マークIII／マスターシステム作品をメガドライブ向けに発売した別機種版。機種の異なる作品は統合しない。', ['https://www.sega.jp/history/hard/megadrive/software_l.html']),
 ('gb-730','追加シナリオ・ダンジョン・図鑑等を含む内容変更版のため、元の作品とは別登録を維持。', ['https://way78.com/gb/1998/gmf/changes.html']),
 ('gb-938','カラー対応とゲームモードの追加があるDX版。単なる廉価再販ではないため維持。', ['https://game.watch.impress.co.jp/docs/preview/1638758.html','https://www.asahi-net.or.jp/~ua4s-njm/gb_soft/gochi34.html']),
]

# ID, title, date (year-only is deliberately not a fabricated day), platform,
# publisher, genre, sources, note.
ADDITIONS = [
 ('pce-bikkuri','ビックリマン大事界','1988-12-23','PCE-CD','ハドソン','クイズ',
  [PCE,'https://www.gavas.jp/products/detail.php?product_id=6354','https://w.atwiki.jp/gcmatome/pages/1234.html'], '図鑑にクイズを含むためゲーム収録作品として追加。'),
]
for i, day in enumerate(['1990-06-15','1990-09-28','1990-12-26','1991-05-24','1991-09-27','1992-01-31'], 1):
    urls=[PCE,f'https://www.gavas.jp/products/detail.php?product_id={6320+i}']
    note='CDマガジンだがミニゲームを収録。各号は収録内容が異なるため、それぞれ1本として追加。'
    if i==2:
        urls.append('https://www.furu1.online/product/detail/10139785')
        note+='一覧の6月28日と異なるが、販売店と個別紹介の9月28日を採用。'
    if i==3:
        urls=[PCE,'https://www.suruga-ya.jp/product/detail/162000046','https://raido.moe/staff/pce/pce_ultrabox_3.html','https://www2s.biglobe.ne.jp/~tetuya/FXHP/pcengine/sonota/ultora3.html']
        note+='12月28日という紹介記事もあるが、販売店と一覧の12月26日を採用。'
    if i==5:
        urls.append('https://www2s.biglobe.ne.jp/tetuya/FXHP/pcengine/sonota/ultora5.html')
        note+='一覧の9月20日と異なるが、個別紹介と他一覧の9月27日を採用。'
    if i==6:
        urls.append('https://www2s.biglobe.ne.jp/tetuya/FXHP/pcengine/sonota/ultora6.html')
        note+='紹介記事に1月30日もあるが、複数カタログの1月31日を採用。'
    ADDITIONS.append((f'pce-ultrabox-{i}', 'ULTRABOX '+('創刊号' if i == 1 else f'{i}号'), day,
        'PCE-CD','ビクター音楽産業','バラエティ',
        urls,note))

UNLICENSED_GAMES = [
 ('アイドル花札ファンクラブ','1991-12-26','PCE','テーブル'),
 ('究極麻雀 アイドルグラフィック','1992-04-16','PCE','テーブル'),
 ('レディソード ～略奪された10人の乙女～','1992-07-13','PCE','RPG'),
 ('PCパチスロ アイドルギャンブラー','1992-09-14','PCE','テーブル'),
 ('AVポーカー ワールドギャンブラー','1992-11-15','PCE','テーブル'),
 ('ボディコンクエストII 救性主','1993-02-23','PCE','RPG'),
 ('CD麻雀 美少女中心派','1993-07-30','PCE-GE','テーブル'),
 ('究極麻雀II スーパーアイドルグラフィック','1993-10-03','PCE','テーブル'),
 ('しあわせうさぎ 濡れた美少女 初めてなのに…','1993-10-14','PCE-SCD','アドベンチャー'),
 ('J・サンダー ～冷たい肌は少女を濡らす～','1994','PCE-SCD','アドベンチャー'),
 ('ストリップファイターII','1994-03-26','PCE','格闘'),
 ('QUIZ 投稿写真','1994-05-13','PCE','クイズ'),
 ('CDパチスロ 美少女ギャンブラー','1994-07-15','PCE-GE','テーブル'),
 ('ハイレグファンタジー','1994-09-15','PCE-GE','RPG'),
 ('CD花札 美少女ファンクラブ','1994-11-25','PCE-GE','テーブル'),
 ('CD美少女パチンコ 球魔四姉妹','1994-12-29','PCE-GE','テーブル'),
 ('AV誕生','1995-02-24','PCE-GE','シミュレーション'),
 ('クレイジーホスピタル 不思議の国の天使','1997-03-14','PCE-SCD','アドベンチャー'),
 ('しあわせうさぎII とらわれうさぎ セーラーZ','1995-08-01','PCE-SCD','アドベンチャー'),
 ('真説しあわせうさぎ','1995-09-30','PCE-SCD','アドベンチャー'),
 ('美少女雀士 アイドルパイ','1995-11-10','PCE-GE','テーブル'),
 ('真説しあわせうさぎ2 快楽へのインビテーション','1996-02-25','PCE-SCD','アドベンチャー'),
 ('真説しあわせうさぎf 友情よりも愛欲','1997-09-10','PCE-SCD','アドベンチャー'),
]
for i, (title, day, platform, genre) in enumerate(UNLICENSED_GAMES, 1):
    urls = [UNLICENSED]
    note = '国内で発売された非公認ゲームとして追加。発売日は資料の掲載日を採用し、メーカーによる確定日とは区別。'
    publisher = 'ハッカーインターナショナル／GAMES EXPRESS'
    if i in {9,10,19}: publisher = 'アジア研究会'
    if i == 18: publisher = 'アジアソフト研究所'
    if i in {20,22}: publisher = 'ラビットソフト研究所'
    if i == 23: publisher = 'ラビットソフト研究所／プレコ'
    if i in {1,2,3,4,6,12}: urls.append(PCE)
    if i == 5:
        urls += ['https://www.suruga-ya.jp/product/detail/261000276',PCE]
        note += 'PCEfanの12月24日と相違するが、販売店の11月15日を採用。'
    if i == 7: urls += ['https://www.suruga-ya.jp/product/detail/162000237']
    if i == 8:
        urls += ['https://www.suruga-ya.jp/product/detail/161900118',PCE]
        note += 'PCEfanの10月8日と相違するが、販売店の10月3日を採用。'
    if i == 9: urls += ['https://www.suruga-ya.jp/product/detail/162010025']
    if i == 10:
        urls += ['https://www.suruga-ya.jp/kaitori/kaitori_detail/162000400',CATALOG]
        note += '年のみ掲載され、販売店と別カタログにも月日の情報がない。1994年と記録し、日付を捏造せず通番を付けない。'
    if i == 11: urls += ['https://lunchbox360.livedoor.biz/archives/10444999.html']
    if i == 13:
        urls += [CATALOG,'https://geo-online.co.jp/store_info/item/0011249/']
        note += '7月29日・12月23日の記載もあり実発売日は確定できない。紹介記事の7月15日は仮の並び順にのみ使用。'
    if i == 14:
        urls += ['https://www.suruga-ya.com/ja/product/162000327',CATALOG]
        note += '別カタログの9月16日と相違するが、販売店の9月15日を採用。'
    if i == 18:
        urls += ['https://www.suruga-ya.jp/product/detail/162000399',CATALOG]
        note += '紹介記事の1997年3月10日等と食い違う。販売店が掲載する1997年3月14日を採用。'
    if i == 16:
        urls.append(CATALOG)
        note += '別カタログには1995年1月5日の記載もあり実発売日は確定できない。1994年12月29日は仮の並び順にのみ使用。'
    if i in {22,23}: urls.append(CATALOG)
    if platform == 'PCE-GE':
        urls += ['https://www.saruyama-gamesoft.com/oldgamepccdp3sa.htm','https://eropedia.jp/words/1705/']
        note += 'GAMES EXPRESS CD CARDが必要なため通常のSUPER CD-ROM²とは区分を分ける。'
    ADDITIONS.append((f'pce-unlicensed-{i:02}',title,day,platform,publisher,genre,urls,note))

EXCLUSIONS = [
 ('mama Mitte','妊産婦向け体重・体脂肪率計の健康管理用。ゲームではないため追加しない。', ['https://press.tanita.co.jp/opr/1331/','https://www.tanita.co.jp/company/history/']),
 ('マジカルザウルスツアー','実タイトルはマジカルサウルスツアー。ゲーム性を持たない恐竜図鑑のため、ゲーム一覧への追加対象外。', ['https://www.gavas.jp/products/detail.php?product_id=6391','https://w.atwiki.jp/gcmatome/pages/1404.html']),
]
