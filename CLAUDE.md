# Scopus 論文情報取得ツール

## デプロイ
- URL: https://scopus-publication-viewer.streamlit.app
- Streamlit Community Cloud / masterブランチから自動デプロイ

## ユーザー情報
- Scopus Author ID: 57218980100 (Takayuki Sato)

## APIキー
- 個人キー（Elsevier Developer Portalで無料取得）のみ対応
- 個人キーでも Scopus Search API の `view=COMPLETE` が利用可能（2026-04-21 検証済み）

## 著者情報
- Scopus Search API の `view=COMPLETE` で全著者を一括取得（追加API不要）
- `author[].authname` を `, ` 区切りで結合して表示（例: "Hu D., Mao L., ..."）
- COMPLETE view では `authid`（Author ID）、`afid`（所属機関ID）、アブストラクト、キーワード等も取得可能だが現状は authname のみ利用

## h-index
- 取得した論文の被引用数から計算（追加API不要）
- Scopusには直近10年のみで算出するh-indexもあるが、本ツールでは全期間版のみ実装

## 今後の課題

### FWCI (Field Weighted Citation Impact)
- Scopus APIでは取得不可。SciVal APIが必要だが、SciValの契約がない
- Scopusのブラウザ上では表示されるが、スクレイピングは規約違反
- CSVに空のFWCI列を追加して手入力する案あり
- 出版から約3年経たないと値が安定しない点にも注意
