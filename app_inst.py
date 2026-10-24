"""機関アクセスモード用のエントリーポイント。

Streamlit Community Cloud は同じリポジトリ・ブランチ・ファイルの組を二重にデプロイできないため、
自分専用インスタンス（Secrets に SCOPUS_API_KEY と SCOPUS_INSTTOKEN を設定）はこのファイルを
メインファイルに指定してデプロイする。中身は app.py と完全に同じ。
"""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
