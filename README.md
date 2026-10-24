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
| h-index | 取得した論文の被引用数から算出（全期間） |
| 論文タイトル | |
| 筆頭著者 | `dc:creator`（例: "Sato T."） |
| 掲載誌 | ジャーナル名 |
| 発行年 | |
| パーセンタイル（発行年） | 発行年時点の CiteScore パーセンタイル |
| 被引用数 | |
| CiteScore（発行年） | |
| DOI / Scopus / ジャーナルページへのリンク | |

結果はテーブル表示に加え、CSV（Excel で文字化けしない UTF-8 BOM 付き）でダウンロードできます。

## 動作モード

本ツールには 2 つの動作モードがあり、Secrets の設定内容で自動的に切り替わります。コードは共通です。

| モード | 条件 | API キー | 追加で取得できる項目 |
| --- | --- | --- | --- |
| 公開モード | Secrets に `SCOPUS_API_KEY` / `SCOPUS_INSTTOKEN` がない | 各ユーザーが入力 | なし（上記の項目のみ） |
| 機関アクセスモード | Secrets に `SCOPUS_API_KEY` と `SCOPUS_INSTTOKEN` の両方がある | Secrets のキーを使用（入力欄なし） | 全著者、h-index（Scopus 公式） |

公開デプロイ（上記 URL）は公開モードです。

### 機関アクセスモードについて

Elsevier から機関契約に紐づく InstToken を発行してもらうと、学外ネットワーク（Streamlit Cloud を含む）からでも機関アクセスが可能になり、以下が追加されます。

| 項目 | 説明 |
| --- | --- |
| 著者 | 全著者（`view=COMPLETE` の `author` 配列）。「Hu D.; Sato T.; …」の形式 |
| h-index（Scopus 公式） | Author Retrieval API（`view=METRICS`）から取得した公式値 |

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
- **h-index は取得した論文（最大 1000 件）から計算**。1000 件取得できていれば Scopus 公式値との誤差はほぼありません。機関アクセスモードでは公式値も並べて表示します。
- **FWCI（Field Weighted Citation Impact）は非対応**。FWCI は SciVal API でのみ取得可能で、Scopus API では提供されていません。

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
