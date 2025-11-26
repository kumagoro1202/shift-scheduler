"""
シフト生成ページ
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import (
    init_database,
    get_all_employees,
    get_all_time_slots,
    is_employee_available,
    create_shift,
    delete_shifts_by_date_range
)
from optimizer import generate_shift, calculate_skill_balance
from utils import get_month_range

st.set_page_config(page_title="シフト生成", page_icon="🎯", layout="wide")

# データベース初期化
init_database()

st.title("🎯 シフト自動生成")
st.markdown("---")

# 職員と時間帯の取得
employees = get_all_employees()
time_slots = get_all_time_slots()

# 事前チェック
if not employees:
    st.error("❌ 職員が登録されていません")
    st.info("👥 まず職員を登録してください")
    st.stop()

if not time_slots:
    st.error("❌ 時間帯が登録されていません")
    st.info("⏰ まず時間帯を設定してください")
    st.stop()

# 必要人数のチェック
total_required = sum(ts['required_employees'] for ts in time_slots)
if len(employees) < max(ts['required_employees'] for ts in time_slots):
    st.warning(f"⚠️ 職員数({len(employees)}名)が時間帯の最大必要人数より少ない可能性があります")

st.subheader("📊 現在の状況")

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.metric("登録職員数", f"{len(employees)}名")

with col_info2:
    st.metric("時間帯数", f"{len(time_slots)}個")

with col_info3:
    avg_skill = sum(e['skill_score'] for e in employees) / len(employees)
    st.metric("平均スキル", f"{avg_skill:.1f}")

st.markdown("---")

# 生成パラメータ設定
st.subheader("⚙️ 生成パラメータ")

# 期間選択
col_param1, col_param2 = st.columns(2)

with col_param1:
    method = st.radio(
        "期間選択方法",
        options=["月単位で選択", "日付範囲で指定"],
        index=0
    )

if method == "月単位で選択":
    col_month1, col_month2 = st.columns(2)
    
    with col_month1:
        year = st.selectbox(
            "年",
            options=range(datetime.now().year, datetime.now().year + 2),
            index=0
        )
    
    with col_month2:
        month = st.selectbox(
            "月",
            options=range(1, 13),
            index=datetime.now().month - 1
        )
    
    start_date, end_date = get_month_range(year, month)
else:
    col_date1, col_date2 = st.columns(2)
    
    with col_date1:
        start_date_input = st.date_input(
            "開始日",
            value=datetime.now().date()
        )
        start_date = start_date_input.strftime("%Y-%m-%d")
    
    with col_date2:
        end_date_input = st.date_input(
            "終了日",
            value=(datetime.now() + timedelta(days=30)).date()
        )
        end_date = end_date_input.strftime("%Y-%m-%d")

# 選択期間の表示
st.info(f"📅 生成期間: {start_date} 〜 {end_date}")

# 日数計算
start_dt = datetime.strptime(start_date, "%Y-%m-%d")
end_dt = datetime.strptime(end_date, "%Y-%m-%d")
days = (end_dt - start_dt).days + 1

st.info(f"📊 {days}日間のシフトを生成します")

st.markdown("---")

# 生成オプション
st.subheader("🔧 オプション")

overwrite = st.checkbox(
    "既存のシフトを上書きする",
    value=True,
    help="チェックを入れると、指定期間の既存シフトを削除してから新規生成します"
)

st.markdown("---")

# 生成ボタン
col_btn1, col_btn2 = st.columns([3, 1])

with col_btn1:
    if st.button("🚀 シフトを生成", type="primary", use_container_width=True):
        with st.spinner("🔄 シフトを生成中..."):
            # 既存シフトの削除
            if overwrite:
                deleted = delete_shifts_by_date_range(start_date, end_date)
                if deleted > 0:
                    st.info(f"🗑️ 既存のシフト {deleted}件を削除しました")
            
            # 最適化実行
            result_shifts = generate_shift(
                employees=employees,
                time_slots=time_slots,
                start_date=start_date,
                end_date=end_date,
                availability_func=is_employee_available
            )
            
            if result_shifts is None:
                st.error("❌ シフト生成に失敗しました")
                st.warning("""
                **失敗の原因として考えられること:**
                - 職員数が不足している
                - 勤務可能情報で「勤務不可」の設定が多すぎる
                - 時間帯の必要人数が多すぎる
                
                **重要:** 
                - 勤務可能情報を登録していない場合は、自動的に「全日程勤務可能」として扱われます
                - 上記の診断情報で、どの日時で人数が不足しているか確認してください
                
                **対処方法:**
                1. 「📅 勤務可能情報」ページで勤務不可の設定を見直す
                2. 「⏰ 時間帯設定」で必要人数を減らす
                3. 「👥 職員管理」で職員を追加する
                """)
            else:
                # データベースに保存
                success_count = 0
                for shift in result_shifts:
                    shift_id = create_shift(
                        shift['date'],
                        shift['time_slot_id'],
                        shift['employee_id']
                    )
                    if shift_id:
                        success_count += 1
                
                st.success(f"✅ シフト生成完了！ {success_count}件のシフトを作成しました")
                st.balloons()
                
                # 統計情報表示
                stats = calculate_skill_balance(result_shifts)
                
                st.markdown("### 📊 生成結果の統計")
                
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                
                with col_stat1:
                    st.metric("平均スキル合計", f"{stats['avg_skill']:.1f}")
                
                with col_stat2:
                    st.metric("標準偏差", f"{stats['std_skill']:.2f}")
                
                with col_stat3:
                    st.metric("最小値", f"{stats['min_skill']:.0f}")
                
                with col_stat4:
                    st.metric("最大値", f"{stats['max_skill']:.0f}")
                
                if stats['std_skill'] < 10:
                    st.success("🌟 スキルバランスが非常に良好です！")
                elif stats['std_skill'] < 20:
                    st.info("✨ スキルバランスは良好です")
                else:
                    st.warning("⚠️ スキルにやや偏りがあります")
                
                st.markdown("---")
                st.info("📋 「シフト表示」ページで生成されたシフトを確認できます")

with col_btn2:
    if st.button("🔄 リセット", use_container_width=True):
        st.rerun()

# サイドバーにヘルプ
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    
    with st.expander("シフト生成について"):
        st.markdown("""
        **自動最適化:**
        - 各時間帯のスキルが均等になるよう調整
        - 必要人数を必ず満たす
        - 勤務可能時間のみ割り当て
        - 1人1日1シフトまで
        
        **処理時間:**
        - 5名×30日: 数秒〜10秒程度
        - 10名×30日: 10秒〜30秒程度
        """)
    
    with st.expander("失敗する場合"):
        st.markdown("""
        **チェックポイント:**
        
        1. 職員数は十分か？
           - 最低でも最大必要人数以上
        
        2. 勤務可能情報について
           - **デフォルトで全日程勤務可能です**
           - 勤務不可の日時のみ登録してください
           - 勤務不可が多すぎる場合は失敗します
        
        3. 制約が厳しすぎないか？
           - 各日時で勤務可能な職員数が必要人数以上必要
           - エラーメッセージで不足している日時を確認
        """)
    
    with st.expander("最適化の仕組み"):
        st.markdown("""
        **目標:**
        各時間帯のスキル合計値が
        均等になるよう調整
        
        **制約:**
        - 必要人数を満たす
        - 勤務可能時間のみ
        - 1人1日1シフト
        
        **結果:**
        どの時間帯も同程度の
        スキルレベルになる
        """)
