"""
シフト生成ページ
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
    list_time_slots,
    create_shift,
    delete_shifts_by_date_range,
    generate_shifts,
    calculate_skill_balance,
    get_month_range,
    ShiftGenerationError,
    auto_assign_and_save_breaks,
    list_shifts,
)

st.set_page_config(page_title="シフト生成", page_icon="🎯", layout="wide")

# データベース初期化
init_database()

st.title("🎯 シフト自動生成")
st.markdown("---")

# 職員と時間帯の取得
employees = list_employees()
time_slots = list_time_slots()

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
max_required = max(ts.required_staff for ts in time_slots)
if len(employees) < max_required:
    st.warning(f"⚠️ 職員数({len(employees)}名)が時間帯の最大必要人数({max_required}名)より少ない可能性があります")

st.subheader("📊 現在の状況")

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.metric("登録職員数", f"{len(employees)}名")

with col_info2:
    st.metric("時間帯数", f"{len(time_slots)}個")

with col_info3:
    avg_skill = sum(
        (emp.skill_reha + emp.skill_reception_am + emp.skill_reception_pm + emp.skill_general) / 4
        for emp in employees
    ) / len(employees)
    st.metric("平均スキル", f"{avg_skill:.1f}")

st.markdown("---")

# 生成パラメータ設定
st.subheader("⚙️ 生成パラメータ")

# 年月選択
st.markdown("#### 📅 対象期間")

# セッション状態の初期化
if 'shift_gen_year' not in st.session_state:
    st.session_state.shift_gen_year = datetime.now().year
if 'shift_gen_month' not in st.session_state:
    st.session_state.shift_gen_month = datetime.now().month

# 矢印ボタンの処理（selectbox作成前に実行）
col_arrow1, col_date1, col_date2, col_arrow2 = st.columns([1, 3, 3, 1])

# 前月ボタンの処理
prev_clicked = col_arrow1.button("◀", key="prev_month_gen")
if prev_clicked:
    if st.session_state.shift_gen_month == 1:
        st.session_state.shift_gen_month = 12
        st.session_state.shift_gen_year -= 1
    else:
        st.session_state.shift_gen_month -= 1

# 次月ボタンの処理
next_clicked = col_arrow2.button("▶", key="next_month_gen")
if next_clicked:
    if st.session_state.shift_gen_month == 12:
        st.session_state.shift_gen_month = 1
        st.session_state.shift_gen_year += 1
    else:
        st.session_state.shift_gen_month += 1

# 年のselectbox
with col_date1:
    year_options = list(range(datetime.now().year - 1, datetime.now().year + 3))
    if st.session_state.shift_gen_year in year_options:
        year_index = year_options.index(st.session_state.shift_gen_year)
    else:
        year_index = 0
    
    def on_year_change_gen():
        st.session_state.shift_gen_year = st.session_state.year_select_gen
    
    st.selectbox(
        "年",
        options=year_options,
        index=year_index,
        key="year_select_gen",
        on_change=on_year_change_gen
    )

# 月のselectbox
with col_date2:
    def on_month_change_gen():
        st.session_state.shift_gen_month = st.session_state.month_select_gen
    
    st.selectbox(
        "月",
        options=list(range(1, 13)),
        index=st.session_state.shift_gen_month - 1,
        key="month_select_gen",
        on_change=on_month_change_gen
    )

# プルダウンの値をセッション状態に反映
year = st.session_state.shift_gen_year
month = st.session_state.shift_gen_month

st.markdown("#### ⚙️ その他のパラメータ")

# 期間選択
col_param1, col_param2 = st.columns(2)

with col_param1:
    method = st.radio(
        "期間選択方法",
        options=["月単位で選択", "日付範囲で指定"],
        index=0
    )

if method == "月単位で選択":
    start_date, end_date = get_month_range(
        st.session_state.shift_gen_year, 
        st.session_state.shift_gen_month
    )
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

# 最適化モード選択
optimization_mode = st.selectbox(
    "最適化モード",
    options=["balance", "skill", "days"],
    format_func=lambda x: {
        "balance": "⚖️ バランス（勤務回数とスキルの両方を考慮）",
        "skill": "🎯 スキル重視（スキル能力の平均化を優先）",
        "days": "📅 日数重視（勤務回数の均等化を優先）"
    }[x],
    index=0,
    help="""
    **バランス**: 勤務回数とスキル能力の両方を考慮して最適化します（推奨）
    **スキル重視**: 各時間帯のスキル能力を平均化し、日によるサービス品質の偏りを防止します
    **日数重視**: 職員の勤務回数をできるだけ均等にすることを優先します
    """
)

overwrite = st.checkbox(
    "既存のシフトを上書きする",
    value=True,
    help="チェックを入れると、指定期間の既存シフトを削除してから新規生成します"
)

st.markdown("---")

# 生成ボタン
col_btn1, col_btn2 = st.columns([3, 1])

with col_btn1:
    if st.button("🚀 シフトを生成", type="primary", width="stretch"):
        with st.spinner("🔄 シフトを生成中..."):
            # 既存シフトの削除
            if overwrite:
                deleted = delete_shifts_by_date_range(start_date, end_date)
                if deleted > 0:
                    st.info(f"🗑️ 既存のシフト {deleted}件を削除しました")
            
            # 最適化実行（V3エンジン）
            try:
                result_shifts = generate_shifts(
                    employees=employees,
                    time_slots=time_slots,
                    start_date=start_date,
                    end_date=end_date,
                    optimisation_mode=optimization_mode,
                )
            except ShiftGenerationError as exc:
                issue = exc.issue
                st.error("❌ シフト生成に失敗しました")
                st.warning(issue.message)

                detail_lines = []
                if issue.date and issue.time_slot_name:
                    detail_lines.append(f"対象: {issue.date} {issue.time_slot_name}")
                if issue.required is not None and issue.available is not None:
                    detail_lines.append(
                        f"必要人数: {issue.required}名 / 確保できた人数: {issue.available}名"
                    )
                if issue.shortage:
                    detail_lines.append(f"不足人数: {issue.shortage}名")

                if detail_lines:
                    st.markdown("\n".join(f"- {line}" for line in detail_lines))

                if issue.available_employees:
                    st.info(
                        "割り当て可能と判断された職員: "
                        + ", ".join(issue.available_employees)
                    )

                if issue.rejections:
                    with st.expander("除外された理由の詳細"):
                        for summary in issue.rejections:
                            label = f"{summary.reason} ({summary.count}名)"
                            st.write(label)
                            if summary.examples:
                                st.write("例: " + ", ".join(summary.examples))
                st.stop()
            else:
                shift_payloads = [shift.to_dict() for shift in result_shifts]

                # データベースに保存
                success_count = 0
                failed_count = 0
                error_messages = []

                for payload in shift_payloads:
                    shift_id = create_shift(
                        payload["date"],
                        payload["time_slot_id"],
                        payload["employee_id"],
                    )
                    if shift_id:
                        success_count += 1
                    else:
                        failed_count += 1
                        error_messages.append(
                            f"{payload['date']} {payload['time_slot_name']} - {payload['employee_name']}"
                        )

                if failed_count > 0:
                    st.warning(f"⚠️ {failed_count}件のシフトが重複のため保存されませんでした")
                    with st.expander("保存に失敗したシフト"):
                        for msg in error_messages[:10]:  # 最初の10件のみ表示
                            st.write(f"- {msg}")

                st.success(f"✅ シフト生成完了！ {success_count}件のシフトを作成しました")
                if success_count > 0:
                    st.balloons()

                # 休憩時間の自動割り当て
                if success_count > 0:
                    with st.spinner("⏰ 休憩時間を自動割り当て中..."):
                        # 生成期間の各日について休憩を割り当て
                        total_break_count = 0
                        break_warnings = []
                        current_date = datetime.strptime(start_date, "%Y-%m-%d")
                        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        
                        while current_date <= end_date_dt:
                            date_str = current_date.strftime("%Y-%m-%d")
                            # その日のシフトを取得
                            daily_shifts = list_shifts(date_str, date_str)
                            
                            if daily_shifts:
                                saved_count, is_valid, warnings = auto_assign_and_save_breaks(
                                    date_str,
                                    daily_shifts
                                )
                                total_break_count += saved_count
                                if warnings:
                                    break_warnings.extend([f"{date_str}: {w}" for w in warnings])
                            
                            current_date += timedelta(days=1)
                        
                        if total_break_count > 0:
                            st.success(f"✅ 休憩時間を {total_break_count}件割り当てました")
                        
                        if break_warnings:
                            with st.expander("⚠️ 休憩割り当ての警告"):
                                for warning in break_warnings[:20]:  # 最大20件表示
                                    st.write(f"- {warning}")

                # 統計情報表示
                stats = calculate_skill_balance(result_shifts, time_slots)
                
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
    if st.button("🔄 リセット", width="stretch"):
        st.rerun()

# サイドバーにヘルプ
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    
    with st.expander("最適化モードについて"):
        st.markdown("""
        **⚖️ バランス（推奨）**:
        - 勤務回数とスキル能力の両方を考慮
        - 最もバランスの取れた結果
        
        **🎯 スキル重視**:
        - 各時間帯のスキル能力を平均化
        - 日によるサービス品質の偏りを防止
        - 受付では医事能力（保険登録、会計など）を優先
        
        **📅 日数重視**:
        - 職員の勤務回数をできるだけ均等に
        - 公平性を最優先する場合
        """)
    
    with st.expander("V2.0の新機能"):
        st.markdown("""
        **4項目スキルスコア対応**:
        - リハ室スキル
        - 受付午前スキル
        - 受付午後スキル
        - 総合対応力
        
        **職員タイプ制約**:
        - TYPE_A: リハ室・受付両方可能
        - TYPE_B: 受付のみ
        - TYPE_C: リハ室のみ（正職員）
        - TYPE_D: リハ室のみ（パート）
        
        **重み付き最適化**:
        - 時間帯ごとに重要度を設定可能
        - 目標スキルスコアに基づく最適化
        """)
    
    with st.expander("シフト生成について"):
        st.markdown("""
        **自動最適化:**
        - 各時間帯のスキルが目標値に近づくよう調整
        - 必要人数（最小〜最大）の範囲で最適化
        - 勤務可能時間のみ割り当て
        - 時間が重なるシフトは割り当てない
        
        **処理時間:**
        - 5名×30日: 数秒〜10秒程度
        - 10名×30日: 10秒〜30秒程度
        """)
    
    with st.expander("失敗する場合"):
        st.markdown("""
        **チェックポイント:**
        
        1. 職員数は十分か？
           - 最低でも最小必要人数以上
           - 職員タイプとエリアの整合性
        
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
        各時間帯のスキル能力を平均化し、
        日によるサービス品質の偏りを防止
        
        **制約:**
        - 必要人数を満たす
        - 勤務可能時間のみ
        - 終日勤務の原則（半休以外は午前・午後両方）
        
        **結果:**
        どの時間帯も同程度の
        スキル能力になる
        """)
