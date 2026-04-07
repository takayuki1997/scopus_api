# Scopus 論文情報取得ツール

## デプロイ
- URL: https://scopus-publication-viewer.streamlit.app
- Streamlit Community Cloud / masterブランチから自動デプロイ

## ユーザー情報
- Scopus Author ID: 57218980100 (Takayuki Sato)

## InstToken
- InstToken取得済み（2026-03-17）。`st.secrets["SCOPUS_INSTTOKEN"]` から読み込み、`X-ELS-Insttoken` ヘッダーとして送信
- InstTokenの規約: サーバーサイドのみ、ブラウザ側コード・URLバーに露出禁止、HTTPS必須、予告なく失効の可能性あり
- 個人キーにInstTokenを付けると401になる（2026-03-30 検証済み）。現在のコードは常にInstTokenを付与するため、個人キーでは動作しない

## 今後の課題

### FWCI (Field Weighted Citation Impact)
- Scopus APIでは取得不可。SciVal APIが必要だが、SciValの契約がない
- Scopusのブラウザ上では表示されるが、スクレイピングは規約違反
- CSVに空のFWCI列を追加して手入力する案あり
- 出版から約3年経たないと値が安定しない点にも注意
