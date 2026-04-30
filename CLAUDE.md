# Scopus 論文情報取得ツール

## デプロイ
- URL: https://scopus-publication-viewer.streamlit.app
- Streamlit Community Cloud / masterブランチから自動デプロイ

## ユーザー情報
- Scopus Author ID: 57218980100 (Takayuki Sato)

## APIキー
- 個人キー（Elsevier Developer Portalで無料取得）のみ対応
- 他ユーザーにも自分のAPIキーを取得してもらい利用してもらう前提
- InstTokenは非対応（機関契約に紐づき、他ユーザーに提供すると規約違反のため）

## 著者情報
- 筆頭著者のみ表示（`dc:creator`、例: "Sato T."）
- 全著者取得（`view=COMPLETE` の `author` 配列）は機関アクセス（InstTokenや大学ネットワーク）が必要なため非対応
- 学内ネットワークやInstTokenありなら動くが、学外・Streamlit Cloudからは401になる

## h-index
- 取得した論文の被引用数から計算（追加API不要）
- Scopusには直近10年のみで算出するh-indexもあるが、本ツールでは全期間版のみ実装
- 取得上限が1000件あるため、自前計算でも公式値との誤差はほぼゼロ（h-index = N なら N本以上の論文があれば足りる）

## ドキュメント
- README.md: 日本語の利用解説（デプロイURL・使い方・取得項目・制約・ローカル実行手順）
- LICENSE: MIT License（Copyright 2026 Takayuki Sato）

## ライブラリ選定

### pybliometrics は採用しない
Scopus APIのPythonラッパーとして [pybliometrics](https://pybliometrics.readthedocs.io/) があるが、本プロジェクトでは採用しない。

採用しない理由:
- **Streamlit Cloudとの相性が悪い**: pybliometricsはデフォルトで `~/.cache/pybliometrics/` にレスポンスをディスクキャッシュする設計だが、Streamlit Cloudのファイルシステムは揮発的でキャッシュの恩恵がない
- **APIキー管理モデルが合わない**: pybliometricsはグローバルなconfigファイル (`pybliometrics.cfg`) にAPIキーを保存する設計。本ツールはユーザごとに異なるキーをブラウザから受け取るマルチユーザ運用なので噛み合わない
- **InstToken制約は変わらない**: 全著者取得などの制約はライブラリを変えても解決しない

唯一のメリットは `AuthorRetrieval` で公式h-indexが取れること。ただし上記の通り自前計算で誤差がほぼないため、メリットが薄い。

個人ローカル利用ならキャッシュが効くので有効だが、本ツールの想定用途（学内研究者への配布）では現状の `requests` 直叩きで十分。

## 今後の課題

### FWCI (Field Weighted Citation Impact)
- Scopus APIでは取得不可。SciVal APIが必要だが、SciValの契約がない
- Scopusのブラウザ上では表示されるが、スクレイピングは規約違反
- CSVに空のFWCI列を追加して手入力する案あり
- 出版から約3年経たないと値が安定しない点にも注意
