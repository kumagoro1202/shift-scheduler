"""
休暇管理ページ（V3.0）
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

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
    get_month_range,
)

st.set_page_config(page_title="休暇管理", page_icon="🏖️", layout="wide")

init_database()

st.title("🏖️ 休暇管理")

st.info("💡 **デフォルト動作**: 休暇登録のない日は、職員の勤務形態に応じて自動的に勤務可能と判定されます。休暇を取る日のみ登録してください。")

# 職員選択
employees = [emp.to_dict() for emp in list_employees()]
if not employees:
    st.warning("⚠️ 職員が登録されていません")
    st.stop()

# 年月選択
# セッション状態の初期化
if 'vacation_year' not in st.session_state:
    st.session_state.vacation_year = datetime.now().year
if 'vacation_month' not in st.session_state:
    st.session_state.vacation_month = datetime.now().month

# 矢印ボタンの処理（selectbox作成前に実行）
col_arrow1, col_date1, col_date2, col_arrow2 = st.columns([1, 3, 3, 1])

# 前月ボタンの処理
prev_clicked = col_arrow1.button("◀", key="prev_month_vacation")
if prev_clicked:
    if st.session_state.vacation_month == 1:
        st.session_state.vacation_month = 12
        st.session_state.vacation_year -= 1
    else:
        st.session_state.vacation_month -= 1
    st.rerun()

# 次月ボタンの処理
next_clicked = col_arrow2.button("▶", key="next_month_vacation")
if next_clicked:
    if st.session_state.vacation_month == 12:
        st.session_state.vacation_month = 1
        st.session_state.vacation_year += 1
    else:
        st.session_state.vacation_month += 1
    st.rerun()

# 年のselectbox
with col_date1:
    year_options = list(range(datetime.now().year - 1, datetime.now().year + 3))
    year_index = year_options.index(st.session_state.vacation_year) if st.session_state.vacation_year in year_options else 0
    
    selected_year = st.selectbox(
        "年",
        options=year_options,
        index=year_index,
        key=f"year_select_{st.session_state.vacation_year}_{st.session_state.vacation_month}"
    )
    
    if selected_year != st.session_state.vacation_year:
        st.session_state.vacation_year = selected_year
        st.rerun()

# 月のselectbox
with col_date2:
    selected_month = st.selectbox(
        "月",
        options=list(range(1, 13)),
        index=st.session_state.vacation_month - 1,
        key=f"month_select_{st.session_state.vacation_year}_{st.session_state.vacation_month}"
    )
    
    if selected_month != st.session_state.vacation_month:
        st.session_state.vacation_month = selected_month
        st.rerun()

# プルダウンの値をセッション状態に反映
year = st.session_state.vacation_year
month = st.session_state.vacation_month

# 20日締めの期間を取得
start_date_str, end_date_str = get_month_range(year, month)
start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

# 表示用のカレンダー範囲を計算
st.info(f"📅 対象期間: {start_date_str} 〜 {end_date_str}")

# タブで表示切り替え
tab1, tab2 = st.tabs(["� 日程別表示", "👤 職員別表示"])

# タブ1: 日程別表示
with tab1:
    st.subheader(f"{year}年{month}月 日程別休暇カレンダー（{start_date.day}日〜翌{end_date.day}日）")
    
    # 全職員の休暇情報を日付ごとに集計
    absences_by_date = {}
    for emp in employees:
        emp_absences = list_absences_for_employee(
            emp['id'],
            start_date=start_date_str,
            end_date=end_date_str,
        )
        for absence in emp_absences:
            abs_dict = absence.to_dict()
            date_key = abs_dict['absence_date']
            if date_key not in absences_by_date:
                absences_by_date[date_key] = []
            absences_by_date[date_key].append({
                'employee_name': emp['name'],
                'absence_type': abs_dict['absence_type'],
                'reason': abs_dict.get('reason', '')
            })
    
    # 表示用の日付リストを作成
    weekday_names = ['月', '火', '水', '木', '金', '土', '日']
    display_dates = []
    current = start_date
    while current < end_date:
        display_dates.append(current)
        current += timedelta(days=1)
    
    # 週単位でグループ化
    weeks = []
    current_week = []
    for date_obj in display_dates:
        day_of_week = date_obj.weekday()
        
        # 月曜日（0）の場合、かつすでに週の途中なら新しい週を開始
        if day_of_week == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        
        # 週の最初に空白を追加（週の途中から始まる場合）
        if not current_week and len(weeks) == 0:
            for _ in range(day_of_week):
                current_week.append(None)
        
        current_week.append(date_obj)
        
        # 日曜日（6）の場合は週を完了
        if day_of_week == 6:
            weeks.append(current_week)
            current_week = []
    
    # 最後の週が残っている場合は追加
    if current_week:
        # 日曜日まで空白で埋める
        while len(current_week) < 7:
            current_week.append(None)
        weeks.append(current_week)
    
    # ヘッダー
    header_cols = st.columns(7)
    for idx, day_name in enumerate(weekday_names):
        with header_cols[idx]:
            st.markdown(f"**{day_name}**")
    
    # カレンダー本体
    for week_idx, week in enumerate(weeks):
        cols = st.columns(7)
        for idx, date_obj in enumerate(week):
            with cols[idx]:
                if date_obj is None:
                    st.markdown("&nbsp;")
                    continue
                
                date_str = date_obj.strftime("%Y-%m-%d")
                day = date_obj.day
                is_sunday = idx == 6
                
                # その日の休暇取得者を取得
                day_absences = absences_by_date.get(date_str, [])
                absence_count = len(day_absences)
                
                # 表示設定
                if is_sunday:
                    icon = "🌙"
                    status = "定休"
                    bg_color = "#2c2c2c"
                    detail_text = ""
                elif absence_count > 0:
                    icon = "🏖️"
                    status = f"休暇: {absence_count}名"
                    bg_color = "#ff6b6b"
                    # 詳細テキスト作成
                    detail_lines = []
                    for abs_info in day_absences[:3]:  # 最大3名まで表示
                        type_icon = {
                            'full_day': '🏖️',
                            'morning': '🌅',
                            'afternoon': '🌆'
                        }.get(abs_info['absence_type'], '📝')
                        detail_lines.append(f"{type_icon} {abs_info['employee_name']}")
                    if absence_count > 3:
                        detail_lines.append(f"他 {absence_count - 3}名")
                    detail_text = "\n".join(detail_lines)
                else:
                    icon = "✅"
                    status = "全員出勤"
                    bg_color = "#51cf66"
                    detail_text = ""
                
                # 日付と状態を表示
                st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 5px; min-height: 100px;">
                        <div style="font-size: 20px; font-weight: bold; color: white;">{day}</div>
                        <div style="font-size: 24px;">{icon}</div>
                        <div style="font-size: 11px; color: white; margin-top: 5px;">{status}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # 詳細表示
                if not is_sunday and day_absences:
                    with st.expander("詳細", expanded=False):
                        for abs_info in day_absences:
                            type_map = {
                                'full_day': '🏖️ 終日',
                                'morning': '🌅 午前',
                                'afternoon': '🌆 午後'
                            }
                            type_label = type_map.get(abs_info['absence_type'], abs_info['absence_type'])
                            reason_text = f" - {abs_info['reason']}" if abs_info['reason'] else ""
                            st.write(f"**{abs_info['employee_name']}**: {type_label}{reason_text}")

    
    # 統計情報
    st.markdown("---")
    st.subheader("📊 休暇統計")
    
    col1, col2, col3 = st.columns(3)
    
    total_absences = sum(len(abs_list) for abs_list in absences_by_date.values())
    total_full_days = sum(
        sum(1 for a in abs_list if a['absence_type'] == 'full_day')
        for abs_list in absences_by_date.values()
    )
    total_half_days = total_absences - total_full_days
    
    with col1:
        st.metric("総休暇件数", f"{total_absences}件")
    with col2:
        st.metric("終日休暇", f"{total_full_days}件")
    with col3:
        st.metric("半休（午前/午後）", f"{total_half_days}件")

# タブ2: 職員別表示（既存の機能）
with tab2:
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

    # カレンダー表示
    st.subheader(f"{year}年{month}月 休暇カレンダー（{start_date.day}日〜翌{end_date.day}日）")

    # 月の日付リスト生成（20日締め対応）
    weekday_names = ['月', '火', '水', '木', '金', '土', '日']

    # 表示用の日付リストを作成
    display_dates = []
    current = start_date
    while current < end_date:
        display_dates.append(current)
        current += timedelta(days=1)

    # 週単位でグループ化
    weeks = []
    current_week = []
    for date_obj in display_dates:
        day_of_week = date_obj.weekday()
        
        # 月曜日（0）の場合、かつすでに週の途中なら新しい週を開始
        if day_of_week == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        
        # 週の最初に空白を追加（週の途中から始まる場合）
        if not current_week and len(weeks) == 0:
            for _ in range(day_of_week):
                current_week.append(None)
        
        current_week.append(date_obj)
        
        # 日曜日（6）の場合は週を完了
        if day_of_week == 6:
            weeks.append(current_week)
            current_week = []

    # 最後の週が残っている場合は追加
    if current_week:
        # 日曜日まで空白で埋める
        while len(current_week) < 7:
            current_week.append(None)
        weeks.append(current_week)

    # ヘッダー
    header_cols = st.columns(7)
    for idx, day_name in enumerate(weekday_names):
        with header_cols[idx]:
            st.markdown(f"**{day_name}**")

    # カレンダー本体
    for week_idx, week in enumerate(weeks):
        cols = st.columns(7)
        for idx, date_obj in enumerate(week):
            with cols[idx]:
                if date_obj is None:
                    st.markdown("&nbsp;")
                    continue
                
                date_str = date_obj.strftime("%Y-%m-%d")
                day = date_obj.day
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
        
        # デフォルト値を20日締めの期間に設定
        default_start = start_date.date()
        default_end = (end_date - timedelta(days=1)).date()
        
        bulk_start = st.date_input("開始日", value=default_start, key="tab2_bulk_start")
        bulk_end = st.date_input("終了日", value=default_end, key="tab2_bulk_end")
        bulk_type = st.selectbox("休暇種別", ["終日休暇", "午前休", "午後休"], key="tab2_bulk_type")
        bulk_reason = st.text_input("理由", key="tab2_bulk_reason")
        
        if st.button("一括登録", key="tab2_bulk_register"):
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
        
        # 20日締めの期間を使用
        absences = [
            absence.to_dict()
            for absence in list_absences_for_employee(
                selected_employee['id'],
                start_date=start_date_str,
                end_date=end_date_str,
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
                    if st.button("削除", key=f"tab2_delete_{abs_data['id']}"):
                        remove_absence(selected_employee['id'], abs_data['absence_date'], abs_data['absence_type'])
                        st.rerun()
        else:
            st.info("この月の休暇登録はありません")
