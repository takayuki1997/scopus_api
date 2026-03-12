import csv
import io
import re

import extra_streamlit_components as stx
import requests
import streamlit as st

st.set_page_config(page_title="Scopus 論文情報取得ツール", layout="wide")

# --- Cookie管理 ---
cookie_manager = stx.CookieManager()

# --- パスワード認証 ---
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")


def check_auth():
    """パスワード認証。Cookie記憶あり。"""
    if not APP_PASSWORD:
        return True  # パスワード未設定なら認証スキップ

    # session_stateまたはCookieで認証済みならスキップ
    if st.session_state.get("authenticated"):
        return True
    auth_cookie = cookie_manager.get("authenticated")
    if auth_cookie == "true":
        st.session_state["authenticated"] = True
        return True

    col, _ = st.columns([1, 2])
    with col:
        password = st.text_input("パスワードを入力してください", type="password")
        st.button("ログイン", type="primary")
    if not password:
        st.stop()
    if password != APP_PASSWORD:
        st.error("パスワードが正しくありません。")
        st.stop()

    st.session_state["authenticated"] = True
    cookie_manager.set("authenticated", "true", key="set_auth", max_age=365 * 24 * 60 * 60)
    st.rerun()


check_auth()

st.title("Scopus 論文情報取得ツール")
st.caption("研究者のScopus Author IDから論文情報とCiteScoreパーセンタイルを取得します")

# --- サイドバー：APIキー入力 ---
saved_api_key = cookie_manager.get("scopus_api_key") or ""

api_key = st.sidebar.text_input(
    "Scopus APIキー",
    value=saved_api_key,
    type="password",
    help="Elsevier Developer Portalで取得したAPIキーを入力してください",
)

# APIキーが変更されたら自動保存
if api_key and api_key != saved_api_key:
    cookie_manager.set("scopus_api_key", api_key, key="set_api_key", max_age=365 * 24 * 60 * 60)

# --- 研究者ID入力 ---
raw_input = st.text_area(
    "Scopus Author ID（複数可：改行またはカンマ区切り）",
    placeholder="57218980100\n12345678901",
    height=150,
)

# --- 定数 ---
BASE_URL = "https://api.elsevier.com/content/search/scopus"
SERIAL_TITLE_URL = "https://api.elsevier.com/content/serial/title"


# --- 関数定義 ---
def get_journal_citescore(source_id: str, headers: dict, cache: dict) -> dict:
    if source_id in cache:
        return cache[source_id]
    try:
        resp = requests.get(
            SERIAL_TITLE_URL,
            headers=headers,
            params={"source-id": source_id, "view": "CITESCORE"},
            timeout=30,
        )
        resp.raise_for_status()
        entries = resp.json().get("serial-metadata-response", {}).get("entry", [])
        if not entries:
            cache[source_id] = {}
            return {}

        cs_info = entries[0].get("citeScoreYearInfoList", {})
        result = {
            "current_citescore": cs_info.get("citeScoreCurrentMetric"),
            "current_year": cs_info.get("citeScoreCurrentMetricYear"),
            "years": {},
        }
        for year_info in cs_info.get("citeScoreYearInfo", []):
            year = year_info.get("@year")
            status = year_info.get("@status")
            info_list = year_info.get("citeScoreInformationList", [])
            if info_list:
                cite_info = info_list[0].get("citeScoreInfo", [])
                if cite_info:
                    info = cite_info[0]
                    subject_ranks = info.get("citeScoreSubjectRank", [])
                    result["years"][year] = {
                        "citescore": info.get("citeScore"),
                        "percentile": subject_ranks[0].get("percentile") if subject_ranks else None,
                        "status": status,
                    }
        cache[source_id] = result
        return result
    except requests.RequestException as e:
        st.warning(f"CiteScore取得エラー (source_id={source_id}): {e}")
        cache[source_id] = {}
        return {}


def get_researcher_publications(researcher_id: str, headers: dict, max_results: int = 100) -> list[dict]:
    results = []
    start = 0
    count_per_request = 25

    while start < max_results:
        params = {
            "query": f"AU-ID({researcher_id})",
            "count": min(count_per_request, max_results - start),
            "start": start,
            "sort": "-coverDate",
        }
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        entries = resp.json().get("search-results", {}).get("entry", [])
        if not entries:
            break

        for entry in entries:
            results.append({
                "title": entry.get("dc:title", "N/A"),
                "source_title": entry.get("prism:publicationName", "N/A"),
                "source_id": entry.get("source-id", "N/A"),
                "cover_date": entry.get("prism:coverDate", "N/A"),
                "doi": entry.get("prism:doi", "N/A"),
                "citation_count": entry.get("citedby-count", "0"),
            })
        start += len(entries)
        if len(entries) < count_per_request:
            break

    return results


# --- 実行ボタン ---
if st.button("論文情報を取得", type="primary"):  # テーマカラー（オレンジ）
    if not api_key:
        st.error("サイドバーでScopus APIキーを入力してください。")
        st.stop()

    researcher_ids = [id_.strip() for id_ in re.split(r"[,\n]+", raw_input) if id_.strip()]
    if not researcher_ids:
        st.error("研究者IDを入力してください。")
        st.stop()

    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    citescore_cache: dict = {}
    all_publications: list[dict] = []

    progress_bar = st.progress(0, text="論文情報を取得中...")

    for idx, researcher_id in enumerate(researcher_ids):
        progress_bar.progress(
            idx / len(researcher_ids),
            text=f"研究者 {researcher_id} の論文情報を取得中... ({idx + 1}/{len(researcher_ids)})",
        )

        try:
            publications = get_researcher_publications(researcher_id, headers)
        except requests.RequestException as e:
            st.error(f"研究者 {researcher_id} の論文取得に失敗しました: {e}")
            continue

        for pub in publications:
            source_id = pub["source_id"]
            if source_id and source_id != "N/A":
                cs = get_journal_citescore(source_id, headers, citescore_cache)
                if cs:
                    pub["current_citescore"] = cs.get("current_citescore", "")
                    pub["current_citescore_year"] = cs.get("current_year", "")

                    pub_year = pub["cover_date"][:4] if pub["cover_date"] != "N/A" else None
                    years = cs.get("years", {})
                    fallback_used = False

                    if pub_year and pub_year in years:
                        year_data = years[pub_year]
                        pub["pub_year_citescore"] = year_data.get("citescore", "")
                        pub["pub_year_percentile"] = year_data.get("percentile", "")
                    else:
                        complete_years = [y for y, d in years.items() if d.get("status") == "Complete"]
                        if complete_years:
                            latest_year = max(complete_years)
                            year_data = years[latest_year]
                            pub["pub_year_citescore"] = year_data.get("citescore", "")
                            pub["pub_year_percentile"] = year_data.get("percentile", "")
                            fallback_used = True

                    pub["percentile_note"] = f"発表年データなし。{latest_year}年で代替" if fallback_used else ""

            pub["researcher_id"] = researcher_id
            all_publications.append(pub)

    progress_bar.progress(1.0, text="完了！")

    if not all_publications:
        st.warning("論文が見つかりませんでした。")
        st.stop()

    st.success(f"合計 {len(all_publications)} 件の論文を取得しました。")

    # --- テーブル表示 ---
    display_data = []
    for pub in all_publications:
        cover_date = pub.get("cover_date", "")
        pub_year = cover_date[:4] if cover_date and cover_date != "N/A" else ""
        display_data.append({
            "研究者ID": pub.get("researcher_id", ""),
            "論文タイトル": pub.get("title", ""),
            "掲載誌": pub.get("source_title", ""),
            "発表年": pub_year,
            "パーセンタイル": pub.get("pub_year_percentile", ""),
            "パーセンタイル注": pub.get("percentile_note", ""),
            "被引用数": pub.get("citation_count", ""),
            "DOI": pub.get("doi", ""),
            "CiteScore": pub.get("current_citescore", ""),
        })

    st.dataframe(display_data, use_container_width=True)

    # --- CSVダウンロード ---
    fieldnames = [
        "研究者ID", "論文タイトル", "掲載誌", "発表年", "パーセンタイル",
        "パーセンタイル注", "発表日", "DOI", "被引用数",
        "CiteScore（現在）", "CiteScore取得年", "CiteScore（発表年）", "ジャーナルID",
    ]

    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM（Excel文字化け防止）
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for pub in all_publications:
        cover_date = pub.get("cover_date", "")
        pub_year = cover_date[:4] if cover_date and cover_date != "N/A" else ""
        writer.writerow({
            "研究者ID": pub.get("researcher_id", ""),
            "論文タイトル": pub.get("title", ""),
            "掲載誌": pub.get("source_title", ""),
            "発表年": pub_year,
            "パーセンタイル": pub.get("pub_year_percentile", ""),
            "パーセンタイル注": pub.get("percentile_note", ""),
            "発表日": cover_date,
            "DOI": pub.get("doi", ""),
            "被引用数": pub.get("citation_count", ""),
            "CiteScore（現在）": pub.get("current_citescore", ""),
            "CiteScore取得年": pub.get("current_citescore_year", ""),
            "CiteScore（発表年）": pub.get("pub_year_citescore", ""),
            "ジャーナルID": pub.get("source_id", ""),
        })

    st.download_button(
        label="CSVダウンロード",
        data=buf.getvalue(),
        file_name="publications.csv",
        mime="text/csv",
    )
