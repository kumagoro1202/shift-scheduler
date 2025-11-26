"""
シフト作成システム - メインアプリケーション
"""
import sys
import os
from pathlib import Path

# srcディレクトリをパスに追加
if getattr(sys, 'frozen', False):
    # PyInstallerでビルドされた実行ファイルの場合
    base_path = Path(sys._MEIPASS)
    sys.path.insert(0, str(base_path / "src"))
else:
    # 通常のPythonスクリプトの場合
    base_path = Path(__file__).parent
    sys.path.insert(0, str(base_path / "src"))

def main():
    """メインエントリーポイント"""
    # データベース初期化を最初に実行
    from database import init_database
    init_database()
    
    import streamlit.web.cli as stcli
    
    # 実行ファイルのパスを取得
    if getattr(sys, 'frozen', False):
        # PyInstallerでビルドされた実行ファイルの場合
        application_path = Path(sys._MEIPASS)
        script_path = str(application_path / "main.py")
    else:
        # 通常のPythonスクリプトの場合
        script_path = __file__
    
    # Streamlitを起動
    sys.argv = [
        "streamlit", 
        "run", 
        script_path,
        "--server.headless=true",
        "--server.port=8501",
        "--server.address=localhost",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false"
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    # Streamlitから呼び出された場合は通常のアプリケーションを実行
    if 'streamlit' in sys.argv[0] or (len(sys.argv) > 1 and sys.argv[1] == 'run'):
        import streamlit as st
        from database import init_database

        # ページ設定
        st.set_page_config(
            page_title="シフト作成システム",
            page_icon="📅",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        # データベース初期化
        init_database()

        # メインページ
        st.title("📅 シフト作成システム")
        st.markdown("---")

        # ホーム画面
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### 👥 職員管理")
            st.info("職員の登録・編集とスキルスコアの設定を行います。")
            if st.button("職員管理へ", key="btn_employees", use_container_width=True):
                st.switch_page("pages/1_👥_職員管理.py")

        with col2:
            st.markdown("### ⏰ 時間帯設定")
            st.info("勤務時間帯の登録・編集を行います。")
            if st.button("時間帯設定へ", key="btn_timeslots", use_container_width=True):
                st.switch_page("pages/2_⏰_時間帯設定.py")

        with col3:
            st.markdown("### 📅 勤務可能情報")
            st.info("職員の勤務可能な日時を登録します。")
            if st.button("勤務可能情報へ", key="btn_availability", use_container_width=True):
                st.switch_page("pages/3_📅_勤務可能情報.py")

        st.markdown("---")

        col4, col5 = st.columns(2)

        with col4:
            st.markdown("### 🎯 シフト生成")
            st.success("最適化エンジンでシフトを自動生成します。")
            if st.button("シフト生成へ", key="btn_generate", use_container_width=True):
                st.switch_page("pages/4_🎯_シフト生成.py")

        with col5:
            st.markdown("### 📋 シフト表示")
            st.success("生成されたシフトを確認・編集します。")
            if st.button("シフト表示へ", key="btn_view", use_container_width=True):
                st.switch_page("pages/5_📋_シフト表示.py")

        st.markdown("---")

        # システム情報
        st.markdown("### 📊 システム情報")

        from database import get_all_employees, get_all_time_slots

        employees = get_all_employees()
        time_slots = get_all_time_slots()

        info_col1, info_col2, info_col3 = st.columns(3)

        with info_col1:
            st.metric("登録職員数", f"{len(employees)}名")

        with info_col2:
            st.metric("設定時間帯数", f"{len(time_slots)}個")

        with info_col3:
            if employees:
                avg_skill = sum(e['skill_score'] for e in employees) / len(employees)
                st.metric("平均スキルスコア", f"{avg_skill:.1f}")
            else:
                st.metric("平均スキルスコア", "-")

        # 使い方ガイド
        with st.expander("💡 使い方ガイド"):
            st.markdown("""
            ### 基本的な流れ
            
            1. **👥 職員管理**: 職員を登録し、スキルスコア（1-100）を設定
            2. **⏰ 時間帯設定**: 1日の勤務時間帯を設定（例：午前、午後、夜間）
            3. **📅 勤務可能情報**: 各職員の勤務可能な日時を登録
            4. **🎯 シフト生成**: 期間を指定してシフトを自動生成
            5. **📋 シフト表示**: 生成されたシフトを確認・編集
            
            ### スキルスコアについて
            
            - **90-100**: エキスパート
            - **70-89**: ベテラン
            - **50-69**: 中堅
            - **30-49**: 新人
            - **1-29**: 研修中
            
            各時間帯のスキル合計が均等になるように最適化されます。
            """)

        # フッター
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: gray;'>"
            "シフト作成システム v1.0 | データは data/shift.db に保存されます"
            "</div>",
            unsafe_allow_html=True
        )
    else:
        # 直接実行された場合はStreamlitを起動
        main()

