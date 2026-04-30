# Scopus 論文情報取得ツール

Scopus Author ID から研究者の論文情報と CiteScore パーセンタイルをまとめて取得し、テーブル表示・CSV ダウンロードできる Streamlit アプリです。

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

## 制約事項

- **個人 API キーのみ対応**。InstToken（機関契約に紐づくトークン）は他ユーザーへの提供が規約違反となるため非対応です。
- **著者は筆頭著者のみ表示**。全著者リストの取得 (`view=COMPLETE`) は機関アクセスが必要なため非対応です。学内ネットワークや InstToken 環境では取得可能ですが、Streamlit Cloud や学外からは 401 エラーになります。
- **h-index は取得した論文（最大 1000 件）から計算**。Scopus 公式値の取得には別 API が必要ですが、1000 件取得できていれば誤差はほぼありません。
- **FWCI（Field Weighted Citation Impact）は非対応**。FWCI は SciVal API でのみ取得可能で、Scopus API では提供されていません。

## ローカルで実行する場合

```bash
git clone https://github.com/<your-account>/scopus_api.git
cd scopus_api

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

streamlit run app.py
```

ブラウザで <http://localhost:8501> を開き、API キーと Author ID を入力してください。

## ライセンス

[MIT License](LICENSE)
