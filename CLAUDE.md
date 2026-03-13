# Scopus 論文情報取得ツール

## 今後の課題

### 研究者名の取得
- Author Retrieval API (`/content/author/author_id/`) と Author Search API (`/content/search/author`) の両方で 401 Unauthorized エラーが発生
- APIキーの権限問題の可能性。Elsevier側の仕様変更や一時的制限かもしれない
- 代替案: 論文検索結果の `dc:creator` フィールドから取得可能だが、第一著者でない論文では別人の名前になる制約がある

### FWCI (Field Weighted Citation Impact)
- Scopus APIでは取得不可。SciVal APIが必要だが、SciValの契約がない
- Scopusのブラウザ上では表示されるが、スクレイピングは規約違反
- CSVに空のFWCI列を追加して手入力する案あり
- 出版から約3年経たないと値が安定しない点にも注意
