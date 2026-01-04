"""
シフト表示・編集ページ - マトリクス形式
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).resolve().parent.parent

src_path = base_path / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from shift_scheduler import (
    init_database,
    list_shifts,
    list_employees,
    get_month_range,
)

st.set_page_config(page_title="シフト表示", page_icon="📋", layout="wide")

# データベース初期化
init_database()

st.title("📋 シフト表示")
st.markdown("---")

# 年月選択
if 'display_year' not in st.session_state:
    st.session_state.display_year = datetime.now().year
if 'display_month' not in st.session_state:
    st.session_state.display_month = datetime.now().month

col_arrow1, col_date1, col_date2, col_arrow2 = st.columns([1, 3, 3, 1])

prev_clicked = col_arrow1.button("◀", key="prev_month_display")
if prev_clicked:
    if st.session_state.display_month == 1:
        st.session_state.display_month = 12
        st.session_state.display_year -= 1
    else:
        st.session_state.display_month -= 1
    st.rerun()

next_clicked = col_arrow2.button("▶", key="next_month_display")
if next_clicked:
    if st.session_state.display_month == 12:
        st.session_state.display_month = 1
        st.session_state.display_year += 1
    else:
        st.session_state.display_month += 1
    st.rerun()

with col_date1:
    year_options = list(range(datetime.now().year - 1, datetime.now().year + 3))
    year_index = year_options.index(st.session_state.display_year) if st.session_state.display_year in year_options else 0
    selected_year = st.selectbox(
        "年",
        options=year_options,
        index=year_index,
        key=f"year_select_display_{st.session_state.display_year}_{st.session_state.display_month}"
    )
    if selected_year != st.session_state.display_year:
        st.session_state.display_year = selected_year
        st.rerun()

with col_date2:
    selected_month = st.selectbox(
        "月",
        options=list(range(1, 13)),
        index=st.session_state.display_month - 1,
        key=f"month_select_display_{st.session_state.display_year}_{st.session_state.display_month}"
    )
    if selected_month != st.session_state.display_month:
        st.session_state.display_month = selected_month
        st.rerun()

year = st.session_state.display_year
month = st.session_state.display_month

# 対象期間（21日〜翌月20日）
start_date, end_date = get_month_range(year, month)

# 職員とシフトを取得
employees = list_employees(active_only=True)
shifts = list_shifts(start_date, end_date)

st.subheader(f"📅 {start_date} 〜 {end_date} のシフト")

if not employees:
    st.warning("⚠️ 職員が登録されていません")
    st.stop()

if not shifts:
    st.warning("⚠️ シフトが登録されていません")
    st.info("🎯 「シフト生成」ページでシフトを作成してください")
    st.stop()

st.success(f"✅ {len(shifts)}件のシフトが登録されています")
st.markdown("---")

# シフトデータをDataFrameに変換
df_shifts = pd.DataFrame(shifts)

# 日付リストを生成
start_dt = datetime.strptime(start_date, "%Y-%m-%d")
end_dt = datetime.strptime(end_date, "%Y-%m-%d")
date_list = []
current = start_dt
while current < end_dt:
    if current.weekday() != 6:  # 日曜日を除外
        date_list.append(current)
    current += timedelta(days=1)

# 勤務パターンの凡例マッピング
pattern_legend = {
    "full_early": "早",
    "full_mid": "中",
    "full_late": "遅",
    "short_time": "短",
    "part_morning_early": "パ早",
    "part_morning": "パ",
    "part_morning_ext": "パ延",
}

# 職員ごとのシフトマトリクスを作成
st.markdown("### 📊 職員別シフト一覧")

# カスタムCSS
st.markdown("""
<style>
    .shift-table {
        font-size: 12px;
        width: 100%;
        border-collapse: collapse;
    }
    .shift-table th {
        background-color: #2c3e50;
        color: white;
        padding: 8px 4px;
        text-align: center;
        border: 1px solid #ddd;
        font-weight: bold;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .shift-table td {
        padding: 4px;
        text-align: center;
        border: 1px solid #ddd;
        min-width: 60px;
    }
    .shift-table tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    .employee-name {
        font-weight: bold;
        text-align: left;
        padding-left: 8px !important;
        white-space: nowrap;
        background-color: #ecf0f1;
        position: sticky;
        left: 0;
        z-index: 5;
    }
    .date-header {
        writing-mode: vertical-rl;
        text-orientation: mixed;
        min-width: 30px !important;
        padding: 4px 2px !important;
    }
    .shift-cell {
        font-size: 11px;
        line-height: 1.2;
    }
    .reha-am { background-color: #a8e6cf; }
    .reha-pm { background-color: #87ceeb; }
    .reception-am { background-color: #ffd3b6; }
    .reception-pm { background-color: #ffaaa5; }
    .off-day { background-color: #e8e8e8; color: #999; }
</style>
""", unsafe_allow_html=True)

# テーブルヘッダー
html = '<div style="overflow-x: auto;"><table class="shift-table">'
html += '<thead><tr><th style="min-width: 120px;">職員名</th>'

for date_obj in date_list:
    date_str = date_obj.strftime("%m/%d")
    weekday = ["月", "火", "水", "木", "金", "土"][date_obj.weekday()]
    html += f'<th class="date-header">{date_str}<br>({weekday})</th>'

html += '</tr></thead><tbody>'

# 各職員の行を作成
for emp in employees:
    html += f'<tr><td class="employee-name">{emp.name}</td>'
    
    # 各日付のシフトを確認
    for date_obj in date_list:
        date_str = date_obj.strftime("%Y-%m-%d")
        
        # その日のその職員のシフトを取得
        emp_shifts = df_shifts[
            (df_shifts['employee_id'] == emp.id) & 
            (df_shifts['date'] == date_str)
        ]
        
        if len(emp_shifts) == 0:
            # シフトなし
            html += '<td class="shift-cell off-day">-</td>'
        else:
            # シフトがある場合、時間帯とエリアごとに集計
            cell_content = []
            
            # リハ室午前
            reha_am = emp_shifts[
                (emp_shifts['time_slot_name'].str.contains('リハ室')) &
                (emp_shifts['time_slot_name'].str.contains('午前'))
            ]
            if len(reha_am) > 0:
                pattern = reha_am.iloc[0].get('employment_pattern_id', '')
                legend = pattern_legend.get(pattern, pattern[:2] if pattern else '●')
                cell_content.append(f'<div class="reha-am">リ{legend}</div>')
            
            # リハ室午後
            reha_pm = emp_shifts[
                (emp_shifts['time_slot_name'].str.contains('リハ室')) &
                (emp_shifts['time_slot_name'].str.contains('午後'))
            ]
            if len(reha_pm) > 0:
                pattern = reha_pm.iloc[0].get('employment_pattern_id', '')
                legend = pattern_legend.get(pattern, pattern[:2] if pattern else '●')
                cell_content.append(f'<div class="reha-pm">リ{legend}</div>')
            
            # 受付午前
            reception_am = emp_shifts[
                (emp_shifts['time_slot_name'].str.contains('受付')) &
                (emp_shifts['time_slot_name'].str.contains('午前'))
            ]
            if len(reception_am) > 0:
                pattern = reception_am.iloc[0].get('employment_pattern_id', '')
                legend = pattern_legend.get(pattern, pattern[:2] if pattern else '●')
                cell_content.append(f'<div class="reception-am">受{legend}</div>')
            
            # 受付午後
            reception_pm = emp_shifts[
                (emp_shifts['time_slot_name'].str.contains('受付')) &
                (emp_shifts['time_slot_name'].str.contains('午後'))
            ]
            if len(reception_pm) > 0:
                pattern = reception_pm.iloc[0].get('employment_pattern_id', '')
                legend = pattern_legend.get(pattern, pattern[:2] if pattern else '●')
                cell_content.append(f'<div class="reception-pm">受{legend}</div>')
            
            if cell_content:
                html += f'<td class="shift-cell">{"".join(cell_content)}</td>'
            else:
                html += '<td class="shift-cell">●</td>'
    
    html += '</tr>'

html += '</tbody></table></div>'

st.markdown(html, unsafe_allow_html=True)

# 凡例を表示
st.markdown("---")
st.markdown("### 📖 凡例")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**勤務パターン:**")
    st.markdown("- **早**: フルタイム早番 (08:30-18:30)")
    st.markdown("- **中**: フルタイム中番 (08:45-18:45)")
    st.markdown("- **遅**: フルタイム遅番 (09:00-19:00)")
    st.markdown("- **短**: 時短勤務 (08:45-16:45)")

with col2:
    st.markdown("**パートタイム:**")
    st.markdown("- **パ早**: パート午前早番 (08:30-12:30)")
    st.markdown("- **パ**: パート午前 (08:45-12:45)")
    st.markdown("- **パ延**: パート午前延長 (08:45-13:45)")
    st.markdown("- **-**: 休み")

with col3:
    st.markdown("**業務エリア:**")
    st.markdown("- 🟢 **リ**: リハ室（午前）")
    st.markdown("- 🔵 **リ**: リハ室（午後）")
    st.markdown("- 🟠 **受**: 受付（午前）")
    st.markdown("- 🔴 **受**: 受付（午後）")

# サイドバー
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    
    with st.expander("表示について"):
        st.markdown("""
        **マトリクス表示:**
        - 縦軸: 職員一覧
        - 横軸: 日付（21日〜翌月20日）
        - 各セル: 時間帯×エリアごとの勤務形態
        
        **セルの見方:**
        - リハ室と受付が上下に分かれて表示
        - 午前・午後それぞれに表示
        - 凡例で勤務パターンを確認
        
        **色分け:**
        - 緑: リハ室午前
        - 青: リハ室午後
        - オレンジ: 受付午前
        - 赤: 受付午後
        """)
