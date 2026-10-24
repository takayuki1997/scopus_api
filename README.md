# Scopus 論文情報取得ツール

Scopus Author ID から研究者の論文情報と CiteScore パーセンタイルをまとめて取得し、テーブル表示・CSV ダウンロードできる Streamlit アプリです。

## 想定ユーザー

SciVal を契約していない研究機関の研究者・URA・事務担当者向け。Scopus 契約のみで CiteScore・パーセンタイル・h-index を複数研究者分まとめて取得できます（Scopus のブラウザ UI では1論文ずつしか確認できない指標を、API 経由で一括取得・CSV 出力します）。

## デプロイ済みアプリ

ブラウザからすぐに利用できます（インストール不要）：

**<https://scopus-publication-viewer.streamlit.app>**

## 使い方

1. **Scopus API キーを取得**
   - [Elsevier Developer Portal](https://dev.elsevier.com/) にアクセスし「I want an API Key」をクリック
   - ログイン（アカウントがなければ無料で作成）
   - 「Create API Key」→ Label（任意の名前）を入力（Website は空欄で可）
   - 表示された API キーをコピー
2. **アプリに API キーを貼り付け**（一度入力すればブラウザの Cookie に保存されます）
3. **Scopus Author ID を入力**（複数の場合は改行またはカンマ区切り）
   - Author ID は [Scopus の著者検索](https://www.scopus.com/pages/home#author) で調べられます
4. 「論文情報を取得」ボタンを押す

## 取得できる項目

| 項目 | 説明 |
| --- | --- |
| Scopus Author ID | 著者ページへのリンク |
| h-index | 全期間の h-index。公開モードは取得した論文の被引用数から算出、機関アクセスモードは Scopus 公式値 |
| 論文タイトル | |
| 筆頭著者 | `dc:creator`（例: "Sato T."） |
| 掲載誌 | ジャーナル名 |
| 発行年 | |
| 被引用数 | 論文ごとの Scopus 被引用数 |
| FWCI（OpenAlex） | 論文ごとの Field Weighted Citation Impact。OpenAlex 算出（後述） |
| 被引用パーセンタイル（OpenAlex） | 同分野・同年の論文の中での被引用順位（0〜100）。OpenAlex 算出 |
| 分野（FWCI） | OpenAlex が FWCI 算出に用いた分野 |
| パーセンタイル（発行年） | 掲載誌の発行年時点の CiteScore パーセンタイル。複数分野に属する誌は最高値（Scopus の表示と同じ） |
| CiteScore（発行年） | 掲載誌の発行年時点の CiteScore |
| 分野（CiteScore） | 上記パーセンタイルの対象となった ASJC 分野 |
| DOI / Scopus / ジャーナルページへのリンク | |

テーブルの列見出しにある「?」アイコンにマウスを重ねると、各項目の説明が表示されます。

結果はテーブル表示に加え、2 つの形式でダウンロードできます。

| 形式 | 用途 | 構造 |
| --- | --- | --- |
| CSV | 一覧で眺める | 上の表と同じ。1 行 = 研究者 × 論文（共著論文は研究者ごとに行が分かれる）。UTF-8 BOM 付きで Excel でも文字化けしない |
| Excel（4 シート） | 学部・コース単位の集計 | 下記 4 シートに正規化。論文は重複なし、研究者の値は 1 回だけ現れる |

Excel の 4 シート:

| シート | 1 行が表すもの | 主な列 |
| --- | --- | --- |
| 研究者 | 研究者 1 人 | Scopus Author ID、氏名（機関モードのみ）、h-index、論文数、被引用数合計 |
| 論文 | 論文 1 本 | EID、DOI、タイトル、筆頭著者、著者・著者 ID（機関モード）、掲載誌、発行年、被引用数、FWCI（OpenAlex）、分野、掲載誌パーセンタイル、掲載誌 CiteScore |
| 研究者_論文 | 研究者と論文の対応 1 つ | Scopus Author ID、EID、著者順位（機関モードのみ） |
| 掲載誌 | 掲載誌 × 発行年（論文で使われている組のみ） | 掲載誌 ID、年、CiteScore、パーセンタイル |

論文シートの「掲載誌パーセンタイル」「掲載誌 CiteScore」は掲載誌の指標で、論文そのものの評価ではありません。一覧性のために併記しています。元データは掲載誌シートです。

## 動作モード

本ツールには 2 つの動作モードがあり、Secrets の設定内容で自動的に切り替わります。コードは共通です。

| モード | 条件 | API キー | 追加で取得できる項目 |
| --- | --- | --- | --- |
| 公開モード | Secrets に `SCOPUS_API_KEY` / `SCOPUS_INSTTOKEN` がない | 各ユーザーが入力 | なし（上記の項目のみ） |
| 機関アクセスモード | Secrets に `SCOPUS_API_KEY` と `SCOPUS_INSTTOKEN` の両方がある | Secrets のキーを使用（入力欄なし） | 全著者。h-index は Scopus 公式値になる |

公開デプロイ（上記 URL）は公開モードです。

### 機関アクセスモードについて

Elsevier から機関契約に紐づく InstToken を発行してもらうと、学外ネットワーク（Streamlit Cloud を含む）からでも機関アクセスが可能になり、以下が追加されます。

| 項目 | 説明 |
| --- | --- |
| 著者 | 全著者（`view=COMPLETE` の `author` 配列）。「Hu D.; Sato T.; …」の形式。Excel の論文シートには各著者の Scopus Author ID（著者 ID）も同じ順で入る |
| h-index | Author Retrieval API（`view=METRICS`）の Scopus 公式値に置き換わる（取得できない場合は算出値） |

InstToken には次の制約があります。

- **発行時に紐づけた API キーとの組でしか動きません。** 別のキーと組み合わせると `Institution Token is not associated with API Key` で 401 になります。
- **他ユーザーへの提供は規約違反です。** 機関アクセスモードのインスタンスは、必ず `APP_PASSWORD` や Streamlit Cloud の閲覧制限で自分（または自機関の担当者）だけが使える状態にしてください。
- InstToken はサーバー側（Secrets）にのみ置き、ブラウザ側には一切送りません。

機関アクセスモードのインスタンスを立てる手順:

1. `.streamlit/secrets.toml`（ローカル）または Streamlit Cloud の Secrets に以下を設定

   ```toml
   APP_PASSWORD = "任意のパスワード"
   SCOPUS_API_KEY = "InstToken に紐づく API キー"
   SCOPUS_INSTTOKEN = "発行された InstToken"
   ```

2. Streamlit Cloud では、公開モードと同じリポジトリ・ブランチを二重にデプロイできないため、メインファイルに `app_inst.py` を指定してデプロイします（中身は `app.py` と同じです）。

## 制約事項

- **公開モードは個人 API キーのみ対応**。InstToken（機関契約に紐づくトークン）は他ユーザーへの提供が規約違反となるため、公開インスタンスでは使いません（自分専用の機関アクセスモードについては上記参照）。
- **公開モードでは著者は筆頭著者のみ表示**。全著者リストの取得 (`view=COMPLETE`) は機関アクセスが必要です。
- **公開モードの h-index は取得した論文（最大 1000 件）から計算**。1000 件取得できていれば Scopus 公式値との誤差はほぼありません。機関アクセスモードでは公式値を表示します。
- **Scopus/SciVal の FWCI は取得できません**。SciVal API でのみ提供される指標で、InstToken があっても取れません。代わりに [OpenAlex](https://openalex.org/) が算出する FWCI と被引用パーセンタイルを DOI で取得して表示します（チェックボックスで無効化可）。定義は同じですが母集団と分野分類が異なるため、Scopus 上の FWCI とは値が一致しません。報告書等に使う場合は「OpenAlex 算出」と明記してください。DOI の無い論文は空欄になります。

## ローカルで実行する場合

```bash
git clone https://github.com/takayuki1997/scopus_api.git
cd scopus_api

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

streamlit run app.py
```

ブラウザで <http://localhost:8501> を開き、API キーと Author ID を入力してください。

`.streamlit/secrets.toml` がなければ公開モードで起動します。機関アクセスモードで動かす場合は上記の Secrets を `.streamlit/secrets.toml` に書いてください（このファイルは `.gitignore` 済みです）。

## ライセンス

[MIT License](LICENSE)
