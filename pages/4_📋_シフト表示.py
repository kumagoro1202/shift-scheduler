"""
シフト表示・編集ページ
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

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
    delete_shift,
    get_break_schedules,
    get_employee,
    auto_assign_and_save_breaks,
    validate_reception_coverage,
    get_month_range,
    get_weekday_jp,
    export_to_excel,
)

st.set_page_config(page_title="シフト表示", page_icon="📋", layout="wide")

# データベース初期化
init_database()

st.title("📋 シフト表示・編集")
st.markdown("---")

# 年月選択
# セッション状態の初期化
if 'display_year' not in st.session_state:
    st.session_state.display_year = datetime.now().year
if 'display_month' not in st.session_state:
    st.session_state.display_month = datetime.now().month

# 矢印ボタンの処理（selectbox作成前に実行）
col_arrow1, col_date1, col_date2, col_arrow2 = st.columns([1, 3, 3, 1])

# 前月ボタンの処理
prev_clicked = col_arrow1.button("◀", key="prev_month_display")
if prev_clicked:
    if st.session_state.display_month == 1:
        st.session_state.display_month = 12
        st.session_state.display_year -= 1
    else:
        st.session_state.display_month -= 1
    st.rerun()

# 次月ボタンの処理
next_clicked = col_arrow2.button("▶", key="next_month_display")
if next_clicked:
    if st.session_state.display_month == 12:
        st.session_state.display_month = 1
        st.session_state.display_year += 1
    else:
        st.session_state.display_month += 1
    st.rerun()

# 年のselectbox
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

# 月のselectbox
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

# プルダウンの値をセッション状態に反映
year = st.session_state.display_year
month = st.session_state.display_month

# 対象期間
start_date, end_date = get_month_range(year, month)

# シフト取得
shifts = list_shifts(start_date, end_date)

st.subheader(f"📅 {start_date} 〜 {end_date} のシフト")

if not shifts:
    st.warning("⚠️ シフトが登録されていません")
    st.info("🎯 「シフト生成」ページでシフトを作成してください")
    st.stop()

st.success(f"✅ {len(shifts)}件のシフトが登録されています")

# タブで表示方法を切り替え
tab1, tab2, tab3, tab4 = st.tabs(["📅 カレンダー表示", "☕ 休憩時間", "📊 統計・分析", "📥 エクスポート"])

# タブ1: カレンダー表示
with tab1:
    st.subheader("📅 カレンダー形式")
    
    # シフトデータを日付ごとに整理
    df = pd.DataFrame(shifts)
    
    # フィルターとコントロールの設定
    col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 1])
    
    with col_filter1:
        # 業務エリア（リハ室/受付）フィルター
        if len(df) > 0:
            # エリア名を抽出（例: "リハ室（月曜午前）" -> "リハ室"）
            df['area'] = df['time_slot_name'].str.extract(r'^([^（]+)', expand=False)
            all_areas = sorted(df['area'].unique().tolist())
        else:
            all_areas = []
        
        selected_areas = st.multiselect(
            "🏢 業務エリアで絞り込み",
            options=all_areas,
            default=all_areas,
            help="表示したい業務エリアを選択してください"
        )
    
    with col_filter2:
        # セッション状態の初期化
        if 'expander_state' not in st.session_state:
            st.session_state.expander_state = False
        
        # 一括開閉ボタン
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("📖 すべて開く", use_container_width=True):
                st.session_state.expander_state = True
        with col_btn2:
            if st.button("📕 すべて閉じる", use_container_width=True):
                st.session_state.expander_state = False
    
    with col_filter3:
        # 状態をリセット
        if st.button("🔄 リセット", use_container_width=True):
            st.session_state.expander_state = False
            st.rerun()
    
    st.markdown("---")
    
    # フィルター適用
    if selected_areas and len(df) > 0:
        df_filtered = df[df['area'].isin(selected_areas)]
    else:
        df_filtered = df
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    # 日付リストを生成
    display_dates = []
    current = start_dt
    while current < end_dt:
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
    
    # 曜日ヘッダー
    weekday_names = ['月', '火', '水', '木', '金', '土', '日']
    header_cols = st.columns(7)
    for idx, day_name in enumerate(weekday_names):
        with header_cols[idx]:
            st.markdown(f"**{day_name}**")
    
    # カレンダーのカスタムCSS（要素間の余白を削除）
    st.markdown("""
        <style>
        .stMarkdown {
            margin-bottom: 0 !important;
        }
        div[data-testid="column"] > div {
            gap: 0 !important;
        }
        div[data-testid="column"] > div > div {
            margin-bottom: 0 !important;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
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
                
                # その日のシフトを取得（フィルター適用）
                day_shifts = df_filtered[df_filtered['date'] == date_str] if len(df_filtered) > 0 else pd.DataFrame()
                
                # 背景色の設定
                if is_sunday:
                    bg_color = "#2c2c2c"
                    text_color = "white"
                elif len(day_shifts) > 0:
                    # シフトありの日
                    avg_skill = day_shifts['skill_score'].mean()
                    if avg_skill >= 4.0:
                        bg_color = "#51cf66"  # 緑: 高スキル
                    elif avg_skill >= 3.0:
                        bg_color = "#74c0fc"  # 青: 中スキル
                    else:
                        bg_color = "#ffa94d"  # オレンジ: 低スキル
                    text_color = "white"
                else:
                    # シフトなしの日
                    bg_color = "#868e96"
                    text_color = "white"
                
                # 日付ヘッダーとシフト情報を表示
                if is_sunday:
                    st.markdown(f"""
                        <div style="background-color: {bg_color}; border-radius: 5px; overflow: hidden;">
                            <div style="padding: 8px 10px; text-align: center;">
                                <div style="font-size: 18px; font-weight: bold; color: {text_color}; line-height: 1.5;">{day}</div>
                            </div>
                            <div style="padding: 5px; text-align: center; min-height: 60px;">
                                <div style="font-size: 20px; color: {text_color};">🌙</div>
                                <div style="font-size: 12px; color: {text_color};">定休</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                elif len(day_shifts) > 0:
                    # エリアと時間帯の情報を抽出
                    day_shifts_copy = day_shifts.copy()
                    # エリア名を抽出（例: "リハ室（月曜午前）" -> "リハ室"）
                    day_shifts_copy['area'] = day_shifts_copy['time_slot_name'].str.extract(r'^([^（]+)', expand=False)
                    # 時間帯を抽出（例: "リハ室（月曜午前）" -> "午前"）
                    day_shifts_copy['period'] = day_shifts_copy['time_slot_name'].str.extract(r'(午前|午後)', expand=False)
                    
                    # エリアごとにグループ化
                    area_groups = day_shifts_copy.groupby('area')
                    
                    # 日付ヘッダーを含めた全体のコンテナ
                    st.markdown(f"""
                        <div style="border-radius: 5px; overflow: hidden;">
                            <div style="background-color: {bg_color}; padding: 8px 10px; text-align: center;">
                                <div style="font-size: 18px; font-weight: bold; color: {text_color}; line-height: 1.5;">{day}</div>
                            </div>
                    """, unsafe_allow_html=True)
                    
                    with st.container():
                        st.markdown(f"""
                            <div style="background-color: white; padding: 2px; border: 1px solid #dee2e6; border-top: none; min-height: 60px;">
                        """, unsafe_allow_html=True)
                        
                        for area_name, area_shifts in area_groups:
                            # エリアごとのexpander
                            expander_expanded = st.session_state.expander_state
                            
                            # エリアのアイコンを設定
                            area_icon = "🏥" if "リハ" in area_name else "📞" if "受付" in area_name else "🏢"
                            
                            with st.expander(f"{area_icon} {area_name}", expanded=expander_expanded):
                                # 時間帯（午前/午後）でさらにグループ化
                                period_groups = area_shifts.groupby(['period', 'start_time', 'end_time'])
                                
                                for (period, start_time, end_time), period_shifts in period_groups:
                                    st.markdown(f"**{period}** ({start_time} - {end_time})")
                                    
                                    # 職員を表示
                                    for _, shift in period_shifts.iterrows():
                                        col_a, col_b = st.columns([3, 1])
                                        with col_a:
                                            st.text(f"👤 {shift['employee_name']}")
                                            st.caption(f"💪 {shift['skill_score']:.1f}")
                                        with col_b:
                                            if st.button("🗑️", key=f"del_{shift['id']}", help="削除"):
                                                if delete_shift(shift['id']):
                                                    st.success("削除")
                                                    st.rerun()
                                    
                                    # 時間帯ごとの小計
                                    period_total = period_shifts['skill_score'].sum()
                                    period_avg = period_shifts['skill_score'].mean()
                                    st.caption(f"合計: {period_total:.1f} / 平均: {period_avg:.1f}")
                                    st.markdown("---")
                        
                        # シフト数とスキル平均を表示
                        shift_count = len(day_shifts)
                        avg_skill = day_shifts['skill_score'].mean()
                        st.metric("シフト数", f"{shift_count}件")
                        st.metric("平均スキル", f"{avg_skill:.1f}")
                        
                        st.markdown("</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div style="background-color: {bg_color}; border-radius: 5px; overflow: hidden;">
                            <div style="padding: 8px 10px; text-align: center;">
                                <div style="font-size: 18px; font-weight: bold; color: {text_color}; line-height: 1.5;">{day}</div>
                            </div>
                            <div style="padding: 5px; text-align: center; min-height: 60px;">
                                <div style="font-size: 20px; color: {text_color};">📭</div>
                                <div style="font-size: 12px; color: {text_color};">シフトなし</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

# タブ2: 休憩時間管理
with tab2:
    st.subheader("☕ 休憩時間管理")
    
    st.info("""
    **休憩時間の基本ルール:**
    - 正職員B/C（月火金）、通常/△（水曜）: 基本的に2時間連続で取得（忙しい日は分割もあり）
    - 正職員A（月火金）、50（水曜）: 60分休憩
    - 時短勤務者、パート午後まで: 60分休憩
    - パート午前（4時間）: 休憩なし
    - 受付窓口には常に2名以上が実働状態である必要があります
    """)
    
    # 日付選択
    col_break1, col_break2 = st.columns([2, 3])
    
    with col_break1:
        df = pd.DataFrame(shifts)
        dates = sorted(df['date'].unique())
        selected_date = st.selectbox(
            "日付を選択",
            options=dates,
            format_func=lambda x: f"{x} ({get_weekday_jp(x)})"
        )
    
    with col_break2:
        if st.button("🔄 休憩時間を自動割り当て", type="primary"):
            # その日のシフトを取得
            date_shifts = [s for s in shifts if s['date'] == selected_date]
            
            # 休憩時間を自動割り当て
            saved_count, is_valid, warnings = auto_assign_and_save_breaks(
                selected_date, date_shifts
            )
            
            if saved_count > 0:
                st.success(f"✅ {saved_count}件の休憩時間を割り当てました")
            elif saved_count == 0 and warnings:
                st.info("ℹ️ 休憩時間の割り当て:")
                for warning in warnings:
                    st.info(f"  {warning}")
            
            if not is_valid and saved_count > 0:
                st.warning("⚠️ 以下の警告があります:")
                for warning in warnings:
                    st.warning(warning)
            
            if saved_count > 0:
                st.rerun()
    
    st.markdown("---")
    
    # 休憩スケジュール表示
    if selected_date:
        st.markdown(f"### 📅 {selected_date} の休憩時間")
        
        break_schedules = get_break_schedules(selected_date)
        
        if not break_schedules:
            st.info("この日の休憩スケジュールはまだ設定されていません")
        else:
            # タイムライン表示
            for break_sch in break_schedules:
                employee = get_employee(break_sch['employee_id'])
                employee_name = employee.name if employee else "不明な職員"
                employment_pattern = employee.employment_pattern_id if employee else ""
                
                col1, col2, col3 = st.columns([2, 3, 2])
                
                with col1:
                    if employment_pattern:
                        st.write(f"**👤 {employee_name}** ({employment_pattern})")
                    else:
                        st.write(f"**👤 {employee_name}**")
                
                with col2:
                    break_info = f"休憩{break_sch['break_number']}: {break_sch['break_start_time']} - {break_sch['break_end_time']}"
                    st.info(break_info)
                
                with col3:
                    duration = (
                        datetime.strptime(break_sch['break_end_time'], "%H:%M") -
                        datetime.strptime(break_sch['break_start_time'], "%H:%M")
                    ).seconds // 60
                    st.metric("時間", f"{duration}分")
            
            st.markdown("---")
            
            # 窓口カバレッジチェック
            st.markdown("### 🔍 窓口カバレッジチェック")
            
            date_shifts = [s for s in shifts if s['date'] == selected_date]
            is_valid, warnings = validate_reception_coverage(
                selected_date, date_shifts, break_schedules
            )
            
            if is_valid:
                st.success("✅ 受付窓口の常駐人数は常に2名以上です")
            else:
                st.error("❌ 受付窓口の常駐人数が不足する時間帯があります")
                for warning in warnings:
                    st.warning(warning)

# タブ3: 統計・分析
with tab3:
    st.subheader("📊 シフト統計")
    
    df = pd.DataFrame(shifts)
    
    # 職員別の勤務日数
    st.markdown("### 👥 職員別勤務日数")
    
    employee_counts = df.groupby('employee_name').size().reset_index(name='勤務日数')
    employee_skills = df.groupby('employee_name')['skill_score'].first().reset_index()
    employee_stats = employee_counts.merge(employee_skills, on='employee_name')
    employee_stats = employee_stats.sort_values('勤務日数', ascending=False)
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # 棒グラフ
        fig = px.bar(
            employee_stats,
            x='employee_name',
            y='勤務日数',
            title='職員別勤務日数',
            labels={'employee_name': '職員名', '勤務日数': '日数'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        # 表で表示
        st.dataframe(
            employee_stats,
            hide_index=True,
            width="stretch"
        )
    
    st.markdown("---")
    
    # 時間帯別のスキル分布
    st.markdown("### ⏰ 時間帯別スキル分布")
    
    st.info("""
    **スキル能力の平均化の目的:**
    - 各時間帯において配置される職員のスキル能力を平均化
    - 特定の日だけ優秀な職員が集中することを防止
    - 受付業務では医事能力（保険登録、会計など）を優先的に評価
    - どの日でも同じレベルのサービス品質を提供
    """)
    
    time_slot_stats = df.groupby(['date', 'time_slot_name', 'time_slot_id']).agg({
        'skill_score': ['sum', 'mean', 'count']
    }).reset_index()
    
    time_slot_stats.columns = ['日付', '時間帯', '時間帯ID', 'スキル合計', 'スキル平均', '人数']
    
    # 時間帯ごとの平均を計算
    time_slot_avg = time_slot_stats.groupby('時間帯').agg({
        'スキル合計': 'mean',
        'スキル平均': 'mean',
        '人数': 'mean'
    }).reset_index()
    
    col_ts1, col_ts2 = st.columns(2)
    
    with col_ts1:
        # スキル合計の推移
        fig2 = px.line(
            time_slot_stats,
            x='日付',
            y='スキル合計',
            color='時間帯',
            title='日別・時間帯別スキル合計',
            markers=True
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with col_ts2:
        # 時間帯別平均
        st.dataframe(
            time_slot_avg,
            hide_index=True,
            width="stretch"
        )
    
    st.markdown("---")
    
    # 全体統計
    st.markdown("### 📈 全体統計")
    
    col_overall1, col_overall2, col_overall3, col_overall4 = st.columns(4)
    
    with col_overall1:
        st.metric("総シフト数", f"{len(df)}件")
    
    with col_overall2:
        st.metric("平均スキル", f"{df['skill_score'].mean():.1f}")
    
    with col_overall3:
        st.metric("スキル標準偏差", f"{df['skill_score'].std():.2f}")
    
    with col_overall4:
        balance_score = df.groupby(['date', 'time_slot_id'])['skill_score'].sum().std()
        st.metric("バランススコア", f"{balance_score:.2f}", help="各時間帯のスキル合計の標準偏差。小さいほど日ごとのスキルバランスが均等")
    
    if balance_score < 10:
        st.success("🌟 スキルバランスが非常に良好です！日ごとの能力が均一化されています。")
    elif balance_score < 20:
        st.info("✨ スキルバランスは良好です。能力の偏りは少ないです。")
    else:
        st.warning("⚠️ スキルにやや偏りがあります。特定の日に能力が偏っている可能性があります。")

# タブ4: エクスポート
with tab4:
    st.subheader("📥 データエクスポート")
    
    # Excelエクスポート
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        if st.button("📊 Excelファイルとしてエクスポート", width="stretch"):
            export_path = Path(__file__).parent.parent / "exports"
            export_path.mkdir(exist_ok=True)
            
            filename = f"shift_{year}{month:02d}.xlsx"
            filepath = export_path / filename
            
            if export_to_excel(shifts, str(filepath)):
                st.success(f"✅ エクスポート完了: exports/{filename}")
                
                # ダウンロードボタン
                with open(filepath, 'rb') as f:
                    st.download_button(
                        label="⬇️ ダウンロード",
                        data=f,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("エクスポートに失敗しました")
    
    with col_export2:
        st.info("""
        **エクスポート形式:**
        - 日付、時間帯、職員名などの基本情報
        - 勤務形態（A/B/C、◯/△、PA、P3など）
        - 各スキルスコア詳細（リハ室、受付午前、受付午後、総合対応力）
        - 印刷や他のシステムでの利用に便利
        
        **今後の拡張予定:**
        - 休憩時間の追加
        - 勤務表CSV形式からのインポート機能
        """)

# サイドバー
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    
    with st.expander("表示について"):
        st.markdown("""
        **カレンダー表示:**
        - 日付ごとにシフトを確認
        - 時間帯別に職員とスキルを表示
        - 個別のシフトを削除可能
        
        **統計・分析:**
        - 職員別の勤務日数
        - 時間帯別のスキル分布
        - 全体のバランス評価
        
        **エクスポート:**
        - Excel形式で出力
        - 印刷や共有に便利
        """)
    
    with st.expander("スキルバランス"):
        st.markdown("""
        **バランススコア:**
        - 各時間帯のスキル合計の標準偏差
        - 小さいほど日ごとのバランスが良い
        
        **目的:**
        - 特定の日だけスキルの高い職員が集中することを防止
        - 各時間帯で安定したサービス品質を提供
        - 受付では医事能力（保険登録、会計など）を優先評価
        
        **目安:**
        - 10未満: 非常に良好 🌟
        - 10-20: 良好 ✨
        - 20以上: 要改善 ⚠️
        """)
