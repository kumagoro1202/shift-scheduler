"""
休暇管理ページ（V3.0）
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
import calendar

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).resolve().parent.parent

src_path = base_path / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from shift_scheduler import (
    init_database,
    list_employees,
    record_absence,
    remove_absence,
    get_absence,
    list_absences_for_employee,
)

st.set_page_config(page_title="休暇管理", page_icon="🏖️", layout="wide")

init_database()

st.title("🏖️ 休暇管理")

st.info("💡 **デフォルト動作**: 休暇登録のない日は自動的に「勤務可能」です。休暇を取る日のみ登録してください。")

# 職員選択
employees = [emp.to_dict() for emp in list_employees()]
if not employees:
    st.warning("⚠️ 職員が登録されていません")
    st.stop()

# セッション状態の初期化
if 'selected_employee_idx' not in st.session_state:
    st.session_state.selected_employee_idx = 0

selected_idx = st.selectbox(
    "職員を選択",
    options=range(len(employees)),
    format_func=lambda x: f"{employees[x]['name']} ({employees[x].get('employment_pattern_id', employees[x].get('work_pattern', 'フルタイム'))})",
    index=st.session_state.selected_employee_idx,
    key='employee_selector'
)

st.session_state.selected_employee_idx = selected_idx
selected_employee = employees[selected_idx]

# 年月選択
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("年", range(datetime.now().year, datetime.now().year + 2), index=0)
with col2:
    month = st.selectbox("月", range(1, 13), index=datetime.now().month - 1)

# カレンダー表示
st.subheader(f"{year}年{month}月 休暇カレンダー")

# 月の日付リスト生成
cal = calendar.monthcalendar(year, month)
weekday_names = ['月', '火', '水', '木', '金', '土', '日']

# ヘッダー
header_cols = st.columns(7)
for idx, day_name in enumerate(weekday_names):
    with header_cols[idx]:
        st.markdown(f"**{day_name}**")

# カレンダー本体
for week_idx, week in enumerate(cal):
    cols = st.columns(7)
    for idx, day in enumerate(week):
        with cols[idx]:
            if day == 0:
                st.markdown("&nbsp;")
                continue
            
            date_obj = datetime(year, month, day)
            date_str = date_obj.strftime("%Y-%m-%d")
            is_sunday = idx == 6
            
            # 休暇情報取得
            absence_obj = get_absence(selected_employee['id'], date_str)
            absence = absence_obj.to_dict() if absence_obj else None
            
            # 表示アイコン
            if is_sunday:
                icon = "🌙"
                status = "定休"
                bg_color = "#2c2c2c"
            elif absence:
                if absence['absence_type'] == 'full_day':
                    icon = "🏖️"
                    status = "終日休暇"
                    bg_color = "#ff6b6b"
                elif absence['absence_type'] == 'morning':
                    icon = "🌅"
                    status = "午前休"
                    bg_color = "#ffa94d"
                else:
                    icon = "🌆"
                    status = "午後休"
                    bg_color = "#74c0fc"
            else:
                icon = "✅"
                status = "勤務可能"
                bg_color = "#51cf66"
            
            # 日付と状態を表示
            st.markdown(f"""
                <div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 5px;">
                    <div style="font-size: 20px; font-weight: bold; color: white;">{day}</div>
                    <div style="font-size: 24px;">{icon}</div>
                    <div style="font-size: 12px; color: white;">{status}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # 設定ボタン
            if not is_sunday:
                with st.expander("設定", expanded=False):
                    current_type = absence['absence_type'] if absence else None
                    
                    # 現在の状態に応じたインデックスを設定
                    if current_type == 'full_day':
                        default_idx = 1
                    elif current_type == 'morning':
                        default_idx = 2
                    elif current_type == 'afternoon':
                        default_idx = 3
                    else:
                        default_idx = 0
                    
                    absence_type = st.radio(
                        "状態",
                        ["勤務可能", "終日休暇", "午前休", "午後休"],
                        index=default_idx,
                        key=f"absence_{date_str}"
                    )
                    
                    reason = st.text_input(
                        "理由", 
                        value=absence.get('reason', '') if absence else '', 
                        key=f"reason_{date_str}"
                    )
                    
                    if st.button("保存", key=f"save_{date_str}"):
                        if absence_type == "勤務可能":
                            remove_absence(selected_employee['id'], date_str)
                            st.success("✅ 勤務可能に設定しました")
                        else:
                            type_map = {
                                "終日休暇": "full_day",
                                "午前休": "morning",
                                "午後休": "afternoon"
                            }
                            record_absence(
                                selected_employee['id'],
                                date_str,
                                type_map[absence_type],
                                reason
                            )
                            st.success(f"✅ {absence_type}を登録しました")
                        st.rerun()

# 一括操作セクション
st.markdown("---")
st.subheader("📋 一括操作")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**期間指定で休暇登録**")
    bulk_start = st.date_input("開始日", value=datetime(year, month, 1))
    bulk_end = st.date_input("終了日", value=datetime(year, month, calendar.monthrange(year, month)[1]))
    bulk_type = st.selectbox("休暇種別", ["終日休暇", "午前休", "午後休"], key="bulk_type")
    bulk_reason = st.text_input("理由", key="bulk_reason")
    
    if st.button("一括登録", key="bulk_register"):
        type_map = {
            "終日休暇": "full_day",
            "午前休": "morning",
            "午後休": "afternoon"
        }
        
        count = 0
        current = bulk_start
        while current <= bulk_end:
            # 日曜日はスキップ
            if current.weekday() != 6:
                record_absence(
                    selected_employee['id'],
                    current.strftime("%Y-%m-%d"),
                    type_map[bulk_type],
                    bulk_reason
                )
                count += 1
            current += timedelta(days=1)
        
        st.success(f"✅ {count}日分の{bulk_type}を登録しました")
        st.rerun()

with col2:
    st.markdown("**休暇一覧（当月）**")
    
    # 月初と月末
    month_start = datetime(year, month, 1).strftime("%Y-%m-%d")
    month_end = datetime(year, month, calendar.monthrange(year, month)[1]).strftime("%Y-%m-%d")
    
    absences = [
        absence.to_dict()
        for absence in list_absences_for_employee(
            selected_employee['id'],
            start_date=month_start,
            end_date=month_end,
        )
    ]
    
    if absences:
        for abs_data in absences:
            date_obj = datetime.strptime(abs_data['absence_date'], "%Y-%m-%d")
            type_map = {
                'full_day': '終日休暇',
                'morning': '午前休',
                'afternoon': '午後休'
            }
            
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.text(f"{date_obj.strftime('%m/%d')} {type_map[abs_data['absence_type']]} - {abs_data.get('reason', '')}")
            with col_b:
                if st.button("削除", key=f"delete_{abs_data['id']}"):
                    remove_absence(selected_employee['id'], abs_data['absence_date'], abs_data['absence_type'])
                    st.rerun()
    else:
        st.info("この月の休暇登録はありません")
