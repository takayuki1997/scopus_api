# Scopus 論文情報取得ツール

## デプロイ
- URL: https://scopus-publication-viewer.streamlit.app
- Streamlit Community Cloud / masterブランチから自動デプロイ

## ユーザー情報
- Scopus Author ID: 57218980100 (Takayuki Sato)

## APIキー
- 個人キー（Elsevier Developer Portalで無料取得）のみ対応
- InstTokenは削除済み（著者名取得廃止により不要になった）

## 今後の課題

### FWCI (Field Weighted Citation Impact)
- Scopus APIでは取得不可。SciVal APIが必要だが、SciValの契約がない
- Scopusのブラウザ上では表示されるが、スクレイピングは規約違反
- CSVに空のFWCI列を追加して手入力する案あり
- 出版から約3年経たないと値が安定しない点にも注意
