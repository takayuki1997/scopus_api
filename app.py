import csv
import io
import re

import requests
import streamlit as st
from streamlit_cookies_controller import CookieController

st.set_page_config(page_title="Scopus 論文情報取得ツール", layout="wide")

# --- Cookie管理 ---
cookies = CookieController()

# --- パスワード認証 ---
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")


def check_auth():
    """認証状態を確認する（UIは描画しない）。"""
    if not APP_PASSWORD:
        return True
    if st.session_state.get("authenticated"):
        return True
    # Cookieコンポーネントの初期化を待つ
    # getAll() は None → {} → 完全なデータ と段階的に返る場合がある
    all_cookies = cookies.getAll()
    if not st.session_state.get("cookies_ready"):
        if not all_cookies:
            st.spinner("読み込み中...")
            st.stop()
        st.session_state["cookies_ready"] = True
    if all_cookies and all_cookies.get("authenticated"):
        st.session_state["authenticated"] = True
        return True
    return False


if not check_auth():
    col, _ = st.columns([1, 2])
    with col:
        password = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン", type="primary"):
            if password == APP_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            elif password:
                st.error("パスワードが正しくありません。")
    st.stop()

# 認証済み: Cookieが未保存なら保存（rerun後なのでJSが正常に実行される）
if not cookies.get("authenticated"):
    cookies.set("authenticated", "true", max_age=365 * 24 * 60 * 60)

col_title, col_settings = st.columns([8, 1])
with col_title:
    st.title("Scopus 論文情報取得ツール")
st.caption("研究者のScopus Author IDから論文情報とCiteScoreパーセンタイルを取得します")

# --- APIキー入力 ---
saved_api_key = cookies.get("scopus_api_key") or ""

if saved_api_key:
    # APIキー入力済み → ポップアップに収める
    with col_settings:
        st.write("")  # タイトルとの高さ合わせ
        with st.popover("⚙️"):
            st.markdown("<style>div[data-testid='stPopoverBody'] { min-width: 500px; }</style>", unsafe_allow_html=True)
            api_key = st.text_input(
                "Scopus APIキー",
                value=saved_api_key,
                type="password",
            )
            st.caption(
                "APIキーは [Elsevier Developer Portal](https://dev.elsevier.com/) で取得できます"
            )
else:
    # APIキー未入力 → 直接表示して入力を促す
    api_key = st.text_input(
        "Scopus APIキー",
        type="password",
    )
    st.caption(
        "APIキーは [Elsevier Developer Portal](https://dev.elsevier.com/) で"
        "無料取得できます  \n"
        "1. 上記リンクから「I want an API Key」をクリック  \n"
        "2. ログイン（アカウントがない場合は無料で作成）  \n"
        "3. 「Create API Key」をクリック  \n"
        "4. Label（任意の名前）を入力（Websiteは空欄で可）  \n"
        "5. 表示されたAPIキーをコピーして上の入力欄に貼り付け"
    )

# APIキーが変更されたら自動保存
if api_key and api_key != saved_api_key:
    cookies.set("scopus_api_key", api_key, max_age=365 * 24 * 60 * 60)

# --- 研究者ID入力 ---
st.markdown(
    "<style>[data-testid='stTextArea'] { max-width: 400px; }</style>",
    unsafe_allow_html=True,
)
raw_input = st.text_area(
    "Scopus Author ID（複数可：改行またはカンマ区切り）",
    placeholder="57218980100\n12345678901",
    height=150,
    help="Scopus Author IDは [Scopusの著者検索](https://www.scopus.com/pages/home#author) で調べられます",
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


def get_researcher_publications(
    researcher_id: str,
    headers: dict,
    max_results: int = 1000,
    progress_callback=None,
) -> list[dict]:
    results = []
    start = 0
    count_per_request = 25
    total_results = None

    while start < max_results:
        params = {
            "query": f"AU-ID({researcher_id})",
            "count": min(count_per_request, max_results - start),
            "start": start,
            "sort": "-coverDate",
        }
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        search_results = resp.json().get("search-results", {})
        if total_results is None:
            try:
                total_results = min(int(search_results.get("opensearch:totalResults", 0)), max_results)
            except (TypeError, ValueError):
                total_results = max_results
        entries = search_results.get("entry", [])
        if not entries:
            break

        for entry in entries:
            doi = entry.get("prism:doi", "")
            eid = entry.get("eid", "")
            # EIDから数字部分を抽出（例: "2-s2.0-84885457192" → "84885457192"）
            eid_num = eid.split("-")[-1] if eid else ""
            source_id = entry.get("source-id", "")
            results.append({
                "title": entry.get("dc:title", "N/A"),
                "source_title": entry.get("prism:publicationName", "N/A"),
                "source_id": source_id,
                "journal_url": f"https://www.scopus.com/sourceid/{source_id}" if source_id else "",
                "cover_date": entry.get("prism:coverDate", "N/A"),
                "doi_url": f"https://doi.org/{doi}" if doi else "",
                "scopus_url": f"https://www.scopus.com/pages/publications/{eid_num}" if eid_num else "",
                "citation_count": entry.get("citedby-count", "0"),
            })
        start += len(entries)
        if progress_callback and total_results:
            progress_callback(min(len(results), total_results), total_results)
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

    n_researchers = len(researcher_ids)

    for idx, researcher_id in enumerate(researcher_ids):
        base_ratio = idx / n_researchers
        # 1人あたりの進捗を「論文取得 70% + CiteScore取得 30%」で配分
        fetch_share = 0.7 / n_researchers
        citescore_share = 0.3 / n_researchers

        def update_fetch_progress(done: int, total: int, rid=researcher_id, base=base_ratio, share=fetch_share):
            ratio = base + share * (done / total if total else 1.0)
            progress_bar.progress(
                min(ratio, 1.0),
                text=f"[{idx + 1}/{n_researchers}] 研究者 {rid}: 論文情報を取得中 ({done}/{total})",
            )

        progress_bar.progress(
            base_ratio,
            text=f"[{idx + 1}/{n_researchers}] 研究者 {researcher_id}: 論文情報を取得中...",
        )

        try:
            publications = get_researcher_publications(
                researcher_id, headers, progress_callback=update_fetch_progress
            )
        except requests.RequestException as e:
            st.error(f"研究者 {researcher_id} の論文取得に失敗しました: {e}")
            continue

        n_pubs = len(publications)
        for pub_idx, pub in enumerate(publications):
            if n_pubs:
                ratio = base_ratio + fetch_share + citescore_share * (pub_idx / n_pubs)
                progress_bar.progress(
                    min(ratio, 1.0),
                    text=f"[{idx + 1}/{n_researchers}] 研究者 {researcher_id}: CiteScore取得中 ({pub_idx + 1}/{n_pubs})",
                )
            source_id = pub["source_id"]
            if source_id and source_id != "N/A":
                cs = get_journal_citescore(source_id, headers, citescore_cache)
                if cs:
                    pub["current_citescore"] = cs.get("current_citescore", "")
                    pub["current_citescore_year"] = cs.get("current_year", "")

                    pub_year = pub["cover_date"][:4] if pub["cover_date"] != "N/A" else None
                    years = cs.get("years", {})

                    if pub_year and pub_year in years:
                        year_data = years[pub_year]
                        pub["pub_year_citescore"] = year_data.get("citescore", "")
                        pub["pub_year_percentile"] = year_data.get("percentile", "")

            pub["researcher_id"] = researcher_id
            pub["author_url"] = f"https://www.scopus.com/authid/detail.uri?authorId={researcher_id}"
            all_publications.append(pub)

    progress_bar.progress(1.0, text="完了！")

    if not all_publications:
        st.warning("論文が見つかりませんでした。")
        st.stop()

    st.success(f"合計 {len(all_publications)} 件の論文を取得しました。")

    # --- 研究者ごとのh-index計算 ---
    h_index_by_researcher: dict[str, int] = {}
    citations_by_researcher: dict[str, list[int]] = {}
    for pub in all_publications:
        rid = pub.get("researcher_id", "")
        try:
            cnt = int(pub.get("citation_count", "0") or 0)
        except (TypeError, ValueError):
            cnt = 0
        citations_by_researcher.setdefault(rid, []).append(cnt)
    for rid, citations in citations_by_researcher.items():
        sorted_cites = sorted(citations, reverse=True)
        h = 0
        for i, c in enumerate(sorted_cites, start=1):
            if c >= i:
                h = i
            else:
                break
        h_index_by_researcher[rid] = h

    # --- テーブル表示（ブラウザ用：厳選した列のみ） ---
    import pandas as pd

    display_data = []
    for pub in all_publications:
        cover_date = pub.get("cover_date", "")
        pub_year = cover_date[:4] if cover_date and cover_date != "N/A" else ""
        doi = pub.get("doi_url", "")
        display_data.append({
            "Scopus Author ID": pub.get("author_url", ""),
            "h-index": h_index_by_researcher.get(pub.get("researcher_id", ""), ""),
            "論文タイトル": pub.get("title", ""),
            "掲載誌": pub.get("source_title", ""),
            "発行年": pub_year,
            "パーセンタイル（発行年）": pub.get("pub_year_percentile", ""),
            "被引用数": pub.get("citation_count", ""),
            "CiteScore": pub.get("pub_year_citescore", ""),
            "DOIリンク": pub.get("doi_url", ""),
            "Scopusページ": pub.get("scopus_url", ""),
            "ジャーナルページ": pub.get("journal_url", ""),
        })

    df = pd.DataFrame(display_data)
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "h-index": st.column_config.NumberColumn("h-index", width=50),
            "論文タイトル": st.column_config.TextColumn("論文タイトル", width=200),
            "掲載誌": st.column_config.TextColumn("掲載誌", width=160),
            "発行年": st.column_config.TextColumn("発行年", width=50),
            "パーセンタイル（発行年）": st.column_config.NumberColumn("パーセンタイル（発行年）", width=50),
            "CiteScore": st.column_config.NumberColumn("CiteScore", width=50),
            "被引用数": st.column_config.NumberColumn("被引用数", width=50),
            "Scopus Author ID": st.column_config.LinkColumn("Scopus Author ID", width=100, display_text=r"authorId=(\d+)"),
            "DOIリンク": st.column_config.LinkColumn("DOI", width=100, display_text=r"doi\.org/(.+)"),
            "Scopusページ": st.column_config.LinkColumn("Scopus", width=100, display_text=r"publications/(\d+)"),
            "ジャーナルページ": st.column_config.LinkColumn("Journal", width=100, display_text=r"sourceid/(\d+)"),
        },
    )

    # --- CSVダウンロード ---
    @st.fragment
    def download_csv():
        fieldnames = [
            "Scopus Author ID", "h-index", "論文タイトル", "掲載誌", "発行年", "パーセンタイル（発行年）",
            "被引用数", "CiteScore（発行年）",
            "DOIリンク", "Scopusページ", "ジャーナルページ",
        ]

        buf = io.StringIO()
        buf.write("\ufeff")  # UTF-8 BOM（Excel文字化け防止）
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for pub in all_publications:
            cover_date = pub.get("cover_date", "")
            pub_year = cover_date[:4] if cover_date and cover_date != "N/A" else ""
            writer.writerow({
                "Scopus Author ID": pub.get("researcher_id", ""),
                "h-index": h_index_by_researcher.get(pub.get("researcher_id", ""), ""),
                "論文タイトル": pub.get("title", ""),
                "掲載誌": pub.get("source_title", ""),
                "発行年": pub_year,
                "パーセンタイル（発行年）": pub.get("pub_year_percentile", ""),
                "DOIリンク": pub.get("doi_url", ""),
                "Scopusページ": pub.get("scopus_url", ""),
                "被引用数": pub.get("citation_count", ""),
                "CiteScore（発行年）": pub.get("pub_year_citescore", ""),
                "ジャーナルページ": pub.get("journal_url", ""),
            })

        st.download_button(
            label="CSVダウンロード",
            data=buf.getvalue(),
            file_name="publications.csv",
            mime="text/csv",
        )

    download_csv()
