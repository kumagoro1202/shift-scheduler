"""
シフト作成システム - メインアプリケーション
"""
import sys
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

def launch_streamlit():
    """Streamlitを起動する（通常のPython実行時のみ）"""
    import streamlit.web.cli as stcli
    script_path = __file__
    
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

# PyInstallerでビルドされた場合は、直接Streamlitアプリとして実行
# 通常のPython実行の場合は、streamlit runから呼ばれた時に実行
if __name__ == "__main__":
    # PyInstallerでビルドされていない場合のみ、launch_streamlit()をチェック
    if not getattr(sys, 'frozen', False):
        # 直接python main.pyで実行された場合（streamlit runではない場合）
        if not ('streamlit' in sys.argv[0] or (len(sys.argv) > 1 and sys.argv[1] == 'run')):
            # streamlit runコマンドを起動
            launch_streamlit()
    # それ以外（streamlit runから呼ばれた、またはPyInstallerビルド）はそのまま下のコードを実行

# Streamlitアプリケーションコード
import streamlit as st
from shift_scheduler import init_database, list_employees, list_time_slots

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
    if st.button("職員管理へ", key="btn_employees", width="stretch"):
        st.switch_page("pages/1_👥_職員管理.py")

with col2:
    st.markdown("### 🏖️ 休暇管理")
    st.info("職員の休暇を日付単位で登録します。")
    if st.button("休暇管理へ", key="btn_vacation", width="stretch"):
        st.switch_page("pages/2_🏖️_休暇管理.py")

with col3:
    st.markdown("### 🎯 シフト生成")
    st.success("最適化エンジンでシフトを自動生成します。")
    if st.button("シフト生成へ", key="btn_generate", width="stretch"):
        st.switch_page("pages/3_🎯_シフト生成.py")

st.markdown("---")

# シフト表示
st.markdown("### 📋 シフト表示")
st.info("生成されたシフトを確認・編集します。")
if st.button("シフト表示へ", key="btn_display", width="stretch"):
    st.switch_page("pages/4_📋_シフト表示.py")

st.markdown("---")

# 診療スケジュール表示
st.subheader("📅 診療スケジュールと業務エリア")

col_schedule1, col_schedule2 = st.columns(2)

with col_schedule1:
    with st.expander("診療時間を確認", expanded=False):
        import pandas as pd
        
        schedule_data = {
            "曜日": ["月", "火", "水", "木", "金", "土", "日"],
            "午前": ["09:00-12:30", "09:00-12:30", "09:00-12:30", "09:00-12:30", "09:00-12:30", "09:00-13:30", "休診"],
            "午後": ["15:30-18:30", "15:30-18:30", "15:30-17:30", "休診", "15:30-18:30", "休診", "休診"]
        }
        
        df = pd.DataFrame(schedule_data)
        st.dataframe(df, width="stretch", hide_index=True)

with col_schedule2:
    with st.expander("業務エリア情報", expanded=False):
        st.markdown("""
        ### リハ室（終日運営）
        - **営業時間**: 08:30〜19:00
        - **必要人数**: 2名（常時）
        - **配置可能**: TYPE_A, TYPE_C, TYPE_D
        
        ### 受付
        - **午前**: 08:30〜13:00（必要人数: 1〜2名）
        - **午後**: 13:00〜19:00（必要人数: 1名）
        - **配置可能**: TYPE_A, TYPE_B
        """)

st.markdown("---")

# システム情報
st.markdown("### 📊 システム情報")

employees = list_employees()
time_slots = list_time_slots()

# 業務エリア別の時間帯数
reha_slots = [ts for ts in time_slots if ts.area == 'リハ室']
reception_slots = [ts for ts in time_slots if ts.area == '受付']

info_col1, info_col2, info_col3, info_col4 = st.columns(4)

with info_col1:
    st.metric("登録職員数", f"{len(employees)}名")

with info_col2:
    st.metric("リハ室時間帯", f"{len(reha_slots)}個")

with info_col3:
    st.metric("受付時間帯", f"{len(reception_slots)}個")

with info_col4:
    if employees:
        total_avg = sum(
            (
                emp.skill_reha
                + emp.skill_reception_am
                + emp.skill_reception_pm
                + emp.skill_general
            )
            / 4
            for emp in employees
        )
        avg_skill = total_avg / len(employees)
        st.metric("平均スキル", f"{avg_skill:.1f}")
    else:
        st.metric("平均スキル", "-")

# 使い方ガイド
with st.expander("💡 使い方ガイド"):
    st.markdown("""
    ### V3.0の基本的な流れ
    
    1. **👥 職員管理**: 職員を登録し、勤務形態とスキルスコアを設定
    2. **🏖️ 休暇管理**: 休暇を取る日を登録（登録しない日は自動的に勤務可能）
    3. **🎯 シフト生成**: 期間を指定してシフトを自動生成
    4. **📋 シフト表示**: 生成されたシフトを確認・編集
    
    ### V3.0の主な変更点
    
    - **時間帯設定**: 固定化され、変更不要になりました
    - **勤務可能情報**: 休暇管理に統合され、日付単位で管理
    - **勤務形態**: 勤務形態マスタから選択可能に
    
    ### スキルスコアについて
    
    - **リハ室スキル**: リハビリ業務の能力
    - **受付午前/午後スキル**: 受付業務の能力（時間帯別）
    - **総合対応力**: 柔軟性や総合的な業務対応力
    
    各時間帯のスキル合計が均等になるように最適化されます。
    """)

# フッター
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "シフト作成システム v3.0 | データは data/shift.db に保存されます"
    "</div>",
    unsafe_allow_html=True
)

