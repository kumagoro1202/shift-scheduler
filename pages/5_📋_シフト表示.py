"""
シフト表示・編集ページ
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px

sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import (
    init_database,
    get_shifts_by_date_range,
    get_all_employees,
    get_all_time_slots,
    delete_shift,
    create_shift
)
from utils import get_month_range, get_weekday_jp, export_to_excel

st.set_page_config(page_title="シフト表示", page_icon="📋", layout="wide")

# データベース初期化
init_database()

st.title("📋 シフト表示・編集")
st.markdown("---")

# 年月選択
col_date1, col_date2 = st.columns(2)

with col_date1:
    year = st.selectbox(
        "年",
        options=range(datetime.now().year - 1, datetime.now().year + 2),
        index=1
    )

with col_date2:
    month = st.selectbox(
        "月",
        options=range(1, 13),
        index=datetime.now().month - 1
    )

# 対象期間
start_date, end_date = get_month_range(year, month)

# シフト取得
shifts = get_shifts_by_date_range(start_date, end_date)

st.subheader(f"📅 {year}年{month}月のシフト")

if not shifts:
    st.warning("⚠️ シフトが登録されていません")
    st.info("🎯 「シフト生成」ページでシフトを作成してください")
    st.stop()

st.success(f"✅ {len(shifts)}件のシフトが登録されています")

# タブで表示方法を切り替え
tab1, tab2, tab3 = st.tabs(["📅 カレンダー表示", "📊 統計・分析", "📥 エクスポート"])

# タブ1: カレンダー表示
with tab1:
    # 日付ごとにグループ化
    df = pd.DataFrame(shifts)
    
    # 日付のユニークリストを取得
    dates = sorted(df['date'].unique())
    
    for date in dates:
        date_shifts = df[df['date'] == date]
        weekday = get_weekday_jp(date)
        
        # 日付ヘッダー
        is_weekend = datetime.strptime(date, "%Y-%m-%d").weekday() >= 5
        
        with st.expander(
            f"📅 {date} ({weekday})" + (" 🎌" if is_weekend else ""),
            expanded=len(dates) <= 7  # 7日以内なら展開
        ):
            # 時間帯ごとにグループ化
            time_slot_groups = date_shifts.groupby(['time_slot_id', 'time_slot_name', 'start_time', 'end_time'])
            
            for (ts_id, ts_name, start_time, end_time), ts_shifts in time_slot_groups:
                st.markdown(f"**{ts_name}** ({start_time} - {end_time})")
                
                # この時間帯の割当職員を表示
                cols = st.columns(len(ts_shifts) + 1)
                
                for idx, (_, shift) in enumerate(ts_shifts.iterrows()):
                    with cols[idx]:
                        st.info(f"👤 {shift['employee_name']}\n💪 スキル: {shift['skill_score']}")
                        
                        # 削除ボタン
                        if st.button("🗑️", key=f"del_{shift['id']}", help="このシフトを削除"):
                            if delete_shift(shift['id']):
                                st.success("削除しました")
                                st.rerun()
                
                # スキル合計を表示
                total_skill = ts_shifts['skill_score'].sum()
                avg_skill = ts_shifts['skill_score'].mean()
                
                with cols[-1]:
                    st.metric("合計", f"{total_skill:.0f}")
                    st.metric("平均", f"{avg_skill:.1f}")
                
                st.markdown("---")

# タブ2: 統計・分析
with tab2:
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
            use_container_width=True
        )
    
    st.markdown("---")
    
    # 時間帯別のスキル分布
    st.markdown("### ⏰ 時間帯別スキル分布")
    
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
            use_container_width=True
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
        st.metric("バランススコア", f"{balance_score:.2f}")
    
    if balance_score < 10:
        st.success("🌟 スキルバランスが非常に良好です！")
    elif balance_score < 20:
        st.info("✨ スキルバランスは良好です")
    else:
        st.warning("⚠️ スキルにやや偏りがあります")

# タブ3: エクスポート
with tab3:
    st.subheader("📥 データエクスポート")
    
    # Excelエクスポート
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        if st.button("📊 Excelファイルとしてエクスポート", use_container_width=True):
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
        - 日付、時間帯、職員名などを含むExcelファイル
        - 印刷や他のシステムでの利用に便利
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
        - 各時間帯のスキル合計の偏差
        - 小さいほどバランスが良い
        
        **目安:**
        - 10未満: 非常に良好 🌟
        - 10-20: 良好 ✨
        - 20以上: 要改善 ⚠️
        """)
