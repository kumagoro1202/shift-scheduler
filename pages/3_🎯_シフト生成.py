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
from optimizer import generate_shift_v2, calculate_skill_balance_v2
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
# required_staff (新スキーマ) または required_employees (旧スキーマ) に対応
total_required = sum(ts.get('required_staff', ts.get('required_employees', 2)) for ts in time_slots)
if len(employees) < max(ts.get('required_staff', ts.get('required_employees', 2)) for ts in time_slots):
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

# 最適化モード選択
optimization_mode = st.selectbox(
    "最適化モード",
    options=["balance", "skill", "days"],
    format_func=lambda x: {
        "balance": "⚖️ バランス（勤務回数とスキルの両方を考慮）",
        "skill": "🎯 スキル重視（目標スキルスコアに近づける）",
        "days": "📅 日数重視（勤務回数の均等化を優先）"
    }[x],
    index=0,
    help="""
    **バランス**: 勤務回数とスキルスコアの両方を考慮して最適化します（推奨）
    **スキル重視**: 各時間帯の目標スキルスコアに近づけることを優先します
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
            
            # 最適化実行（V3エンジン - availability_checkerを使用）
            result_shifts = generate_shift_v2(
                employees=employees,
                time_slots=time_slots,
                start_date=start_date,
                end_date=end_date,
                availability_func=None,  # V3: availability_checkerを使用
                optimization_mode=optimization_mode
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
                failed_count = 0
                error_messages = []
                
                for shift in result_shifts:
                    shift_id = create_shift(
                        shift['date'],
                        shift['time_slot_id'],
                        shift['employee_id']
                    )
                    if shift_id:
                        success_count += 1
                    else:
                        failed_count += 1
                        error_messages.append(
                            f"{shift['date']} {shift['time_slot_name']} - {shift['employee_name']}"
                        )
                
                if failed_count > 0:
                    st.warning(f"⚠️ {failed_count}件のシフトが重複のため保存されませんでした")
                    with st.expander("保存に失敗したシフト"):
                        for msg in error_messages[:10]:  # 最初の10件のみ表示
                            st.write(f"- {msg}")
                
                st.success(f"✅ シフト生成完了！ {success_count}件のシフトを作成しました")
                if success_count > 0:
                    st.balloons()
                
                # 統計情報表示（V2）
                stats = calculate_skill_balance_v2(result_shifts, time_slots)
                
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
        - 勤務回数とスキルの両方を考慮
        - 最もバランスの取れた結果
        
        **🎯 スキル重視**:
        - 各時間帯の目標スキルスコアに近づける
        - 特定の時間帯に高スキル職員が必要な場合
        
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
