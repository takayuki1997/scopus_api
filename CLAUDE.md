# Scopus 論文情報取得ツール

## デプロイ
- URL: https://scopus-publication-viewer.streamlit.app
- Streamlit Community Cloud / masterブランチから自動デプロイ

## ユーザー情報
- Scopus Author ID: 57218980100 (Takayuki Sato)

## 動作モード（コードは1つ、デプロイは2つ）
`app.py` は Secrets の内容で2モードに自動で切り替わる（`INST_MODE`）。

| モード | 条件 | APIキー | 追加項目 |
| --- | --- | --- | --- |
| 公開モード | `SCOPUS_API_KEY`/`SCOPUS_INSTTOKEN` なし | ユーザー入力（Cookie保存） | なし |
| 機関アクセスモード | 両方あり | Secretsのキー（入力欄なし、Cookie保存なし） | 全著者。h-indexはScopus公式値に置き換わる |

設計方針:
- **公開インスタンスには InstToken を置かない**。モード分岐のバグで他ユーザーに機関アクセスを提供してしまうと規約違反になるため、安全性はロジックではなく「Secretsが存在しない」ことで構造的に担保する
- 機関アクセスモードは自分専用インスタンス（`APP_PASSWORD` + Streamlit Cloudの閲覧制限）として別デプロイ。Streamlit Cloudは同一リポジトリ・ブランチ・ファイルの二重デプロイができないため、メインファイルに `app_inst.py`（`app.py` を `runpy` で実行するだけ）を指定する
- 完全に別リポジトリにはしない（9割のコードが共通で、修正を2回入れることになるため）
- `get_secret()` は secrets.toml が無い環境でも例外を出さない（フォークしてローカル実行する人のため）

## APIキー・InstToken
- 公開モード: 個人キー（Elsevier Developer Portalで無料取得）を各ユーザーに取得してもらう前提
- InstToken（福島大学の機関契約に紐づく）は**発行時に紐づけたAPIキーとの組でしか効かない**。別のキーと組ませると `Institution Token is not associated with API Key` で401。InstToken専用キーはInstTokenなしだと `Invalid API Key` になる
- InstTokenはサーバーサイド（Secrets）のみで使用。ブラウザ側コード・URL・クライアント送信は禁止。他ユーザーへの提供も規約違反
- InstTokenがあれば学外（Streamlit Cloud含む）からでも機関アクセスが効く。VPNは不要
- ローカルの `.env` の `SCOPUS_API_KEY` は公開モード用の別キー。機関モードのキーは `.streamlit/secrets.toml` 側にある

## 著者情報
- 公開モード: 筆頭著者のみ（`dc:creator`、例: "Sato T."）。全著者取得（`view=COMPLETE`）は機関アクセスが必要
- 機関アクセスモード: `view=COMPLETE` の `author` 配列を「Hu D.; Sato T.; …」形式で「著者」列に追加
- `view=COMPLETE` は count 上限が25件/リクエスト（STANDARDは200件）。本ツールは元から25件で統一している

## h-index
- 取得した論文の被引用数から計算（追加API不要）
- Scopusには直近10年のみで算出するh-indexもあるが、本ツールでは全期間版のみ実装
- 取得上限が1000件あるため、自前計算でも公式値との誤差はほぼゼロ（h-index = N なら N本以上の論文があれば足りる）
- 機関アクセスモードでは Author Retrieval API（`view=METRICS`）の公式値を同じ「h-index」列に表示（取れなければ算出値にフォールバック）。列を2つ並べると混乱するので1列に統一した。デフォルトビューでは h-index が返らないので `view=METRICS` 指定が必須
- 列見出しの説明は `COLUMN_HELP`（column_config の `help`）で一元管理。h-index の説明文はモードで切り替わる

## 出力形式
- CSV: テーブルと同じ平らな表（1行 = 研究者 × 論文）。一覧用
- Excel（`export.py` の `build_excel`）: 研究者 / 論文 / 研究者_論文 / 掲載誌 の4シートに正規化。学部・コース集計用
  - 論文シートは EID で重複排除（共著論文は1本）。一覧性のため掲載誌の指標を「掲載誌パーセンタイル」「掲載誌CiteScore」の列名で併記（論文の評価ではない旨を列名で示す）
  - 氏名・著者順位は機関モードのみ（COMPLETEビューの author 配列から researcher_id に一致する著者を引く）
  - 将来、別途作る教員リスト（Author ID / 学部 / コース）と Author ID で結合して集計する想定
- `export.py` は Streamlit 非依存の純関数なので合成データで単体テスト可能

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

### 機関アクセスモードの拡張候補
- Citation Overview API による論文ごとの年別被引用数（年次報告などの期間集計向け）
- Abstract Retrieval API（FULL view）による所属機関・参考文献

### FWCI (Field Weighted Citation Impact)
- Scopus APIでは取得不可。SciVal APIが必要だが、SciValの契約がない。InstTokenがあっても取れない
- Scopusのブラウザ上では表示されるが、スクレイピングは規約違反
- **代替として OpenAlex の FWCI・被引用パーセンタイル・分野（primary_topic.subfield）を実装済み**（`get_openalex_metrics`）
  - DOI で 50 件ずつまとめて filter 検索し、見つからない DOI は `works/doi:` で個別再問い合わせ。キーは小文字化した DOI
  - 定義は同じだが母集団・分野分類が OpenAlex 独自なので Scopus の FWCI と値は一致しない。UI・README で「OpenAlex 算出」と明記
  - チェックボックスで無効化可（既定は有効）。API キー不要、mailto で polite pool
- 出版から約3年経たないと値が安定しない点にも注意

## CiteScore パーセンタイルの分野
- 掲載誌は複数の ASJC 分野に属し、分野ごとにパーセンタイルがある（`citeScoreSubjectRank`）。Scopus の表示に合わせて**最高値**を採用し、その分野名を「分野（CiteScore）」として出す（以前は配列先頭の分野を使っていた）
- 分野名は Serial Title API の `subject-area`（`@code` → `$`）から引く。Excel の掲載誌シートには全分野のパーセンタイルも併記
