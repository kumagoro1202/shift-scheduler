"""
勤務可能情報ページ
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
import calendar

sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import (
    get_all_employees,
    get_all_time_slots,
    set_availability,
    is_employee_available
)
from utils import get_month_range

st.set_page_config(page_title="勤務可能情報", page_icon="📅", layout="wide")

st.title("📅 勤務可能情報")
st.markdown("---")

# 職員と時間帯の取得
employees = get_all_employees()
time_slots = get_all_time_slots()

if not employees:
    st.warning("⚠️ 職員が登録されていません。先に職員を登録してください。")
    st.stop()

if not time_slots:
    st.warning("⚠️ 時間帯が登録されていません。先に時間帯を設定してください。")
    st.stop()

# 職員選択
selected_employee = st.selectbox(
    "職員を選択",
    options=employees,
    format_func=lambda x: f"{x['name']} (スキル: {x['skill_score']})"
)

if not selected_employee:
    st.stop()

st.markdown("---")

# 年月選択
col_date1, col_date2 = st.columns(2)

with col_date1:
    year = st.selectbox(
        "年",
        options=range(datetime.now().year, datetime.now().year + 2),
        index=0
    )

with col_date2:
    month = st.selectbox(
        "月",
        options=range(1, 13),
        index=datetime.now().month - 1
    )

# 対象月の日付範囲を取得
start_date, end_date = get_month_range(year, month)
start = datetime.strptime(start_date, "%Y-%m-%d")
end = datetime.strptime(end_date, "%Y-%m-%d")

# カレンダー表示
st.subheader(f"{year}年{month}月 の勤務可能情報")

# 曜日ヘッダー
weekdays = ['月', '火', '水', '木', '金', '土', '日']

# 一括設定ボタン
col_bulk1, col_bulk2, col_bulk3 = st.columns(3)

with col_bulk1:
    if st.button("✅ 全日程を「可能」に設定", use_container_width=True):
        # 重複送信防止
        bulk_key = f"bulk_all_available_{selected_employee['id']}_{start}_{end}"
        if bulk_key not in st.session_state or not st.session_state[bulk_key]:
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                for ts in time_slots:
                    set_availability(selected_employee['id'], date_str, ts['id'], True)
                current += timedelta(days=1)
            st.session_state[bulk_key] = True
            st.success("✅ 全日程を「可能」に設定しました")
            st.rerun()

with col_bulk2:
    if st.button("❌ 全日程を「不可」に設定", type="secondary", use_container_width=True):
        # 重複送信防止
        bulk_key = f"bulk_all_unavailable_{selected_employee['id']}_{start}_{end}"
        if bulk_key not in st.session_state or not st.session_state[bulk_key]:
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                for ts in time_slots:
                    set_availability(selected_employee['id'], date_str, ts['id'], False)
                current += timedelta(days=1)
            st.session_state[bulk_key] = True
            st.success("❌ 全日程を「不可」に設定しました")
            st.rerun()

st.markdown("---")

# 日別の可能情報入力
current_date = start
while current_date <= end:
    date_str = current_date.strftime("%Y-%m-%d")
    weekday = weekdays[current_date.weekday()]
    
    # 土日は背景色を変える
    is_weekend = current_date.weekday() >= 5
    
    with st.expander(
        f"📅 {current_date.month}/{current_date.day}({weekday})" + 
        (" 🎌" if is_weekend else ""),
        expanded=False
    ):
        cols = st.columns(len(time_slots))
        
        for idx, ts in enumerate(time_slots):
            with cols[idx]:
                # 現在の設定を取得
                is_available = is_employee_available(
                    selected_employee['id'],
                    date_str,
                    ts['id']
                )
                
                # チェックボックスで設定
                new_availability = st.checkbox(
                    f"{ts['name']}\n{ts['start_time']}-{ts['end_time']}",
                    value=is_available,
                    key=f"avail_{date_str}_{ts['id']}"
                )
                
                # 変更があれば保存
                if new_availability != is_available:
                    set_availability(
                        selected_employee['id'],
                        date_str,
                        ts['id'],
                        new_availability
                    )
    
    current_date += timedelta(days=1)

# サイドバーにヘルプ
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    
    with st.expander("勤務可能情報とは？"):
        st.markdown("""
        各職員が勤務できる日時を登録します。
        
        **使い方:**
        1. 職員を選択
        2. 年月を選択
        3. 各日付の勤務可能な時間帯にチェック
        
        **自動保存:**
        チェックを入れると自動的に保存されます。
        """)
    
    with st.expander("一括設定について"):
        st.markdown("""
        **全日程を「可能」に設定:**
        - 選択月のすべての日時を
          勤務可能にします
        - 基本的に勤務可能な職員に使用
        
        **全日程を「不可」に設定:**
        - 選択月のすべての日時を
          勤務不可にします
        - 休暇予定がある場合などに使用
        
        個別の日時は後から変更できます。
        """)
    
    st.markdown("---")
    st.info(f"""
    **現在の設定対象:**
    
    👤 {selected_employee['name']}
    📅 {year}年{month}月
    """)
