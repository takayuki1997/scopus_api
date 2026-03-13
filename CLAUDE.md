# Scopus 論文情報取得ツール

## ユーザー情報
- Scopus Author ID: 57218980100 (Takayuki Sato)

## 研究者名の取得
- Author Retrieval API (`/content/author/author_id/{scopus_id}`) で取得可能（2026-03-13 確認済み）
- レスポンスの `author-profile.preferred-name` から `given-name`, `surname`, `indexed-name` を取得
- 以前発生していた 401 Unauthorized エラーは解消済み

## 今後の課題

### 著者名のローカルキャッシュ
- `author_cache.json` に著者ID→名前のマッピングを保存し、APIコール数を削減する案
- 検索時にまずキャッシュを参照し、未登録のIDだけAPIに問い合わせる

### FWCI (Field Weighted Citation Impact)
- Scopus APIでは取得不可。SciVal APIが必要だが、SciValの契約がない
- Scopusのブラウザ上では表示されるが、スクレイピングは規約違反
- CSVに空のFWCI列を追加して手入力する案あり
- 出版から約3年経たないと値が安定しない点にも注意
