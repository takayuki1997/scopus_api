"""取得結果を正規化した 4 シート入り Excel に変換する。

シート構成（1 行が表すもの）:
- 研究者:        研究者 1 人
- 論文:          論文 1 本（研究者をまたいで重複排除。一覧性のため掲載誌の指標も併記）
- 研究者_論文:   「この研究者がこの論文の著者」という対応 1 つ
- 掲載誌:        掲載誌 × 年（CiteScore・パーセンタイルの元データ）
"""

import io

import pandas as pd


def _year_of(pub: dict) -> str:
    cover_date = pub.get("cover_date", "") or ""
    return cover_date[:4] if cover_date and cover_date != "N/A" else ""


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_excel(
    all_publications: list[dict],
    h_index_by_researcher: dict,
    official_metrics: dict,
    citescore_cache: dict,
    inst_mode: bool,
) -> bytes:
    """all_publications は (研究者, 論文) ごとの行。研究者をまたぐ重複はここで解消する。"""

    # --- 研究者 ---
    researcher_rows = []
    rids = []
    for pub in all_publications:
        rid = pub.get("researcher_id", "")
        if rid not in rids:
            rids.append(rid)
    for rid in rids:
        pubs = [p for p in all_publications if p.get("researcher_id") == rid]
        name = ""
        if inst_mode:
            for p in pubs:
                name = (p.get("author_name_by_id") or {}).get(rid, "")
                if name:
                    break
        row = {
            "Scopus Author ID": rid,
            "氏名": name,
            "h-index": h_index_by_researcher.get(rid, ""),
            "論文数（取得分）": len({p.get("eid") for p in pubs}),
            "被引用数合計（取得分）": sum(_to_int(p.get("citation_count")) or 0 for p in pubs),
        }
        if inst_mode:
            m = official_metrics.get(rid, {})
            row["論文数（Scopus公式）"] = _to_int(m.get("document_count"))
            row["被引用数合計（Scopus公式）"] = _to_int(m.get("cited_by_count"))
        row["著者ページ"] = f"https://www.scopus.com/authid/detail.uri?authorId={rid}"
        researcher_rows.append(row)

    # --- 論文（EID で重複排除） ---
    paper_rows = []
    seen_eids = set()
    for pub in all_publications:
        eid = pub.get("eid", "")
        key = eid or pub.get("scopus_url") or pub.get("title")
        if key in seen_eids:
            continue
        seen_eids.add(key)
        row = {
            "EID": eid,
            "DOI": (pub.get("doi_url", "") or "").replace("https://doi.org/", ""),
            "論文タイトル": pub.get("title", ""),
            "筆頭著者": pub.get("first_author", ""),
        }
        if inst_mode:
            row["著者"] = pub.get("authors", "")
            row["著者数"] = pub.get("author_count")
        row.update({
            "掲載誌": pub.get("source_title", ""),
            "掲載誌ID": pub.get("source_id", ""),
            "発行年": _to_int(_year_of(pub)),
            "被引用数": _to_int(pub.get("citation_count")),
            "掲載誌パーセンタイル（発行年）": _to_float(pub.get("pub_year_percentile")),
            "掲載誌CiteScore（発行年）": _to_float(pub.get("pub_year_citescore")),
            "DOIリンク": pub.get("doi_url", ""),
            "Scopusページ": pub.get("scopus_url", ""),
        })
        paper_rows.append(row)

    # --- 研究者_論文 ---
    link_rows = []
    for pub in all_publications:
        rid = pub.get("researcher_id", "")
        row = {"Scopus Author ID": rid, "EID": pub.get("eid", "")}
        if inst_mode:
            seq = (pub.get("author_seq_by_id") or {}).get(rid)
            row["著者順位"] = _to_int(seq)
            row["筆頭著者か"] = "○" if seq == "1" else ("" if seq is None else "")
        link_rows.append(row)

    # --- 掲載誌 × 年（論文で実際に使われている誌 × 発行年の組だけ） ---
    title_by_source = {}
    used_pairs = set()
    for pub in all_publications:
        sid = pub.get("source_id", "")
        if sid and sid not in title_by_source:
            title_by_source[sid] = pub.get("source_title", "")
        if sid and _year_of(pub):
            used_pairs.add((sid, _year_of(pub)))
    journal_rows = []
    for sid, cs in citescore_cache.items():
        if not cs:
            continue
        for year, info in sorted((cs.get("years") or {}).items()):
            if (sid, year) not in used_pairs:
                continue
            journal_rows.append({
                "掲載誌ID": sid,
                "掲載誌": title_by_source.get(sid, ""),
                "年": _to_int(year),
                "CiteScore": _to_float(info.get("citescore")),
                "パーセンタイル": _to_float(info.get("percentile")),
                "状態": info.get("status", ""),
                "ジャーナルページ": f"https://www.scopus.com/sourceid/{sid}",
            })

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet, rows in [
            ("研究者", researcher_rows),
            ("論文", paper_rows),
            ("研究者_論文", link_rows),
            ("掲載誌", journal_rows),
        ]:
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=sheet, index=False)
            ws = writer.sheets[sheet]
            ws.freeze_panes = "A2"
            for col_cells in ws.columns:
                header = str(col_cells[0].value or "")
                longest = max((len(str(c.value)) for c in col_cells if c.value is not None), default=0)
                ws.column_dimensions[col_cells[0].column_letter].width = min(max(len(header) * 2, longest + 2, 8), 60)
    return buf.getvalue()
