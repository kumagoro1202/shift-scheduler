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
    init_database,
    get_all_employees,
    get_all_time_slots,
    set_availability,
    is_employee_available
)
from utils import get_month_range

st.set_page_config(page_title="勤務可能情報", page_icon="📅", layout="wide")

# データベース初期化
init_database()

st.title("📅 勤務可能情報")

st.info("💡 **デフォルトの動作**: 勤務可能情報を登録していない日時は、自動的に「勤務可能」として扱われます。勤務できない日時のみ登録してください。")

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
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            for ts in time_slots:
                set_availability(selected_employee['id'], date_str, ts['id'], True)
            current += timedelta(days=1)
        st.success("✅ 全日程を「可能」に設定しました")
        st.rerun()

with col_bulk2:
    if st.button("❌ 全日程を「不可」に設定", type="secondary", use_container_width=True):
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            for ts in time_slots:
                set_availability(selected_employee['id'], date_str, ts['id'], False)
            current += timedelta(days=1)
        st.success("❌ 全日程を「不可」に設定しました")
        st.rerun()

st.markdown("---")

# カレンダー形式で月全体を表示
st.subheader("📅 月間カレンダー")

# 月の最初の日の曜日を取得
first_day_weekday = start.weekday()  # 月曜=0, 日曜=6

# カレンダーのヘッダー（曜日）
header_cols = st.columns(7)
weekday_names = ['月', '火', '水', '木', '金', '土', '日']
for idx, day_name in enumerate(weekday_names):
    with header_cols[idx]:
        st.markdown(f"**{day_name}**")

# 日付データの準備
dates_list = []
current_date = start
while current_date <= end:
    dates_list.append(current_date)
    current_date += timedelta(days=1)

# カレンダー表示（週単位で行を作成）
calendar_data = []
week = [None] * first_day_weekday  # 月の最初の週の空白

for date_obj in dates_list:
    week.append(date_obj)
    if len(week) == 7:
        calendar_data.append(week)
        week = []

# 最後の週の残り
if week:
    while len(week) < 7:
        week.append(None)
    calendar_data.append(week)

# カレンダーの各週を表示
for week in calendar_data:
    cols = st.columns(7)
    for idx, date_obj in enumerate(week):
        with cols[idx]:
            if date_obj is None:
                st.markdown("&nbsp;")  # 空白セル
            else:
                date_str = date_obj.strftime("%Y-%m-%d")
                day = date_obj.day
                is_weekend = date_obj.weekday() >= 5
                
                # 各時間帯の勤務可能状況を取得
                availability_status = []
                all_available = True
                for ts in time_slots:
                    is_avail = is_employee_available(
                        selected_employee['id'],
                        date_str,
                        ts['id']
                    )
                    availability_status.append(is_avail)
                    if not is_avail:
                        all_available = False
                
                # 状態に応じた表示
                if all_available:
                    status_icon = "✅"
                    status_color = "green"
                elif not any(availability_status):
                    status_icon = "❌"
                    status_color = "red"
                else:
                    status_icon = "⚠️"
                    status_color = "orange"
                
                # 日付とステータスを表示
                if is_weekend:
                    st.markdown(f"**{day}** 🎌")
                else:
                    st.markdown(f"**{day}**")
                
                st.markdown(f":{status_color}[{status_icon}]")
                
                # 詳細設定用のexpander
                with st.expander("設定", expanded=False):
                    for ts in time_slots:
                        is_available = is_employee_available(
                            selected_employee['id'],
                            date_str,
                            ts['id']
                        )
                        
                        new_availability = st.checkbox(
                            f"{ts['name']} ({ts['start_time']}-{ts['end_time']})",
                            value=is_available,
                            key=f"avail_{date_str}_{ts['id']}"
                        )
                        
                        if new_availability != is_available:
                            set_availability(
                                selected_employee['id'],
                                date_str,
                                ts['id'],
                                new_availability
                            )

# 凡例
st.markdown("---")
col_legend1, col_legend2, col_legend3 = st.columns(3)
with col_legend1:
    st.markdown("✅ **全時間帯で勤務可能**")
with col_legend2:
    st.markdown("⚠️ **一部の時間帯で勤務可能**")
with col_legend3:
    st.markdown("❌ **全時間帯で勤務不可**")

# サイドバーにヘルプ
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    
    with st.expander("勤務可能情報とは？"):
        st.markdown("""
        各職員が勤務できる日時を登録します。
        
        **重要:**
        - 登録していない日時は自動的に「勤務可能」として扱われます
        - 勤務できない日時のみ登録すればOKです
        
        **カレンダー表示:**
        - ✅ 全時間帯で勤務可能
        - ⚠️ 一部の時間帯で勤務可能
        - ❌ 全時間帯で勤務不可
        
        **使い方:**
        1. 職員を選択
        2. 年月を選択
        3. 各日付の「設定」をクリックして詳細を編集
        
        **自動保存:**
        チェックを入れると自動的に保存されます。
        """)
    
    with st.expander("一括設定について"):
        st.markdown("""
        **全日程を「可能」に設定:**
        - 選択月のすべての日時を勤務可能にします
        - カレンダー上で全て✅になります
        - 基本的に勤務可能な職員に使用
        
        **全日程を「不可」に設定:**
        - 選択月のすべての日時を勤務不可にします
        - カレンダー上で全て❌になります
        - 休暇予定がある場合などに使用
        
        個別の日時は後からカレンダーで変更できます。
        """)
    
    st.markdown("---")
    st.info(f"""
    **現在の設定対象:**
    
    👤 {selected_employee['name']}
    📅 {year}年{month}月
    """)
