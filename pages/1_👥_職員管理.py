"""
職員管理ページ（V2.0対応）
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from shift_scheduler import (
    init_database,
    list_employees,
    create_employee,
    update_employee,
    delete_employee,
    get_employee,
    list_employment_patterns,
)

st.set_page_config(page_title="職員管理", page_icon="👥", layout="wide")

# データベース初期化
init_database()

st.title("👥 職員管理")
st.markdown("---")

# 職員タイプのラベル辞書
EMPLOYEE_TYPE_LABELS = {
    "TYPE_A": "🌟 TYPE_A (リハ室・受付両方可能)",
    "TYPE_B": "📋 TYPE_B (受付のみ)",
    "TYPE_C": "💪 TYPE_C (リハ室のみ・正職員)",
    "TYPE_D": "🏃 TYPE_D (リハ室のみ・パート)"
}

PATTERN_CATEGORY_LABELS = {
    "full_time": "フルタイム",
    "short_time": "時短勤務",
    "part_time": "パートタイム",
}

EMPLOYMENT_PATTERNS = list_employment_patterns()
PATTERN_LOOKUP = {pattern.id: pattern for pattern in EMPLOYMENT_PATTERNS}

# 編集モードの判定
edit_mode = 'edit_employee_id' in st.session_state and st.session_state.get('edit_employee_id')

if edit_mode:
    # 編集モード：専用画面を表示
    st.subheader("✏️ 職員情報の編集")
    
    # 戻るボタン
    if st.button("← 職員一覧に戻る"):
        del st.session_state['edit_employee_id']
        st.rerun()
    
    st.markdown("---")
    
    employee = get_employee(st.session_state['edit_employee_id'])
    if not employee:
        st.error("職員情報が見つかりません")
        del st.session_state['edit_employee_id']
        st.rerun()
    
    # 編集フォーム（後で定義）
    
else:
    # 通常モード：タブで表示
    employee = None
    tab1, tab2 = st.tabs(["職員一覧", "新規登録"])

# タブ1: 職員一覧（編集モードでない場合のみ表示）
if not edit_mode:
    with tab1:
        st.subheader("登録済み職員")
        
        employees = list_employees()
        
        if not employees:
            st.info("📝 職員が登録されていません。「新規登録」タブから登録してください。")
        else:
            # 職員リストを表示
            for emp in employees:
                pattern = PATTERN_LOOKUP.get(emp.employment_pattern_id)
                with st.expander(f"**{emp.name}** - {EMPLOYEE_TYPE_LABELS.get(emp.employee_type, 'TYPE_A')}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**職員タイプ**: {emp.employee_type}")
                        st.markdown(f"**雇用形態**: {emp.employment_type}")
                        if pattern:
                            st.markdown(
                                f"**勤務パターン**: {pattern.name} ({pattern.start_time}-{pattern.end_time})"
                            )
                        else:
                            st.markdown("**勤務パターン**: 未設定")
                        
                        # スキルスコア表示
                        st.markdown("**スキルスコア**:")
                        skill_cols = st.columns(4)
                        with skill_cols[0]:
                            st.metric("リハ室", emp.skill_reha)
                        with skill_cols[1]:
                            st.metric("受付(午前)", emp.skill_reception_am)
                        with skill_cols[2]:
                            st.metric("受付(午後)", emp.skill_reception_pm)
                        with skill_cols[3]:
                            st.metric("総合対応力", emp.skill_general)
                    
                    with col2:
                        # 編集・削除ボタン
                        if st.button("✏️ 編集", key=f"edit_{emp.id}"):
                            st.session_state['edit_employee_id'] = emp.id
                            st.rerun()
                        
                        if st.button("🗑️ 削除", key=f"delete_{emp.id}", type="secondary"):
                            if delete_employee(emp.id):
                                st.success(f"✅ {emp.name}さんを削除しました")
                                st.rerun()
                            else:
                                st.error("削除に失敗しました")
            
            st.markdown("---")
            
            # 統計情報
            st.subheader("📊 統計情報")
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            
            with col_stat1:
                st.metric("総職員数", f"{len(employees)}名")
            
            with col_stat2:
                regular = len([e for e in employees if e.employment_type == '正職員'])
                st.metric("正職員", f"{regular}名")
            
            with col_stat3:
                part_time = len([e for e in employees if e.employment_type == 'パート'])
                st.metric("パート", f"{part_time}名")
            
            with col_stat4:
                avg_reha = sum(e.skill_reha for e in employees) / len(employees)
                st.metric("平均リハ室スキル", f"{avg_reha:.1f}")

    # タブ2: 新規登録
    # タブ2: 新規登録
    with tab2:
        st.subheader("新規職員の登録")

# 入力フォーム（編集モードまたは新規登録モード）
with st.form("employee_form"):
    name = st.text_input(
        "職員名 *",
        value=employee.name if employee else "",
        placeholder="例: 山田太郎",
    )

    st.markdown("---")
    st.subheader("基本情報")

    col1, col2 = st.columns(2)

    with col1:
        employment_type_index = 0
        if employee and employee.employment_type == "パート":
            employment_type_index = 1
        employment_type = st.radio(
            "雇用形態 *",
            ["正職員", "パート"],
            index=employment_type_index,
        )

    with col2:
        employee_type_index = ["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"].index(
            employee.employee_type if employee else "TYPE_A"
        )
        employee_type = st.selectbox(
            "職員タイプ *",
            ["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"],
            index=employee_type_index,
            format_func=lambda x: EMPLOYEE_TYPE_LABELS[x],
        )

    # 勤務パターンの選択
    if employment_type == "正職員":
        category_options = ["full_time", "short_time"]
        default_category = "full_time"
        if employee and employee.employment_pattern_id:
            pattern = PATTERN_LOOKUP.get(employee.employment_pattern_id)
            if pattern:
                default_category = pattern.category
        category_index = (
            category_options.index(default_category)
            if default_category in category_options
            else 0
        )
        pattern_category = st.radio(
            "勤務区分",
            category_options,
            index=category_index,
            format_func=lambda x: PATTERN_CATEGORY_LABELS[x],
        )
    else:
        pattern_category = "part_time"
        st.caption("パート従業員は午前帯パターンが対象です")

    pattern_candidates = [
        pattern for pattern in EMPLOYMENT_PATTERNS if pattern.category == pattern_category
    ]

    if pattern_candidates:
        default_pattern_id = (
            employee.employment_pattern_id
            if employee and employee.employment_pattern_id
            else pattern_candidates[0].id
        )
        default_index = next(
            (idx for idx, pattern in enumerate(pattern_candidates) if pattern.id == default_pattern_id),
            0,
        )
        selected_pattern = st.selectbox(
            "勤務パターン *",
            pattern_candidates,
            index=default_index,
            format_func=lambda p: f"{p.name} ({p.start_time}-{p.end_time})",
        )
        employment_pattern_id = selected_pattern.id
    else:
        employment_pattern_id = None
        st.warning("⚠️ 選択可能な勤務パターンがありません")

    st.markdown("---")
    st.subheader("スキルスコア（0〜100）")
    st.caption("職員タイプによって入力できる項目が制限されます")

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        skill_reha = st.number_input(
            "リハ室スキル",
            min_value=0,
            max_value=100,
            value=employee.skill_reha if employee else 0,
            disabled=(employee_type == "TYPE_B"),
            help="TYPE_Bは受付専門のため入力不可",
        )

        skill_am = st.number_input(
            "受付午前スキル",
            min_value=0,
            max_value=100,
            value=employee.skill_reception_am if employee else 0,
            disabled=(employee_type in ["TYPE_C", "TYPE_D"]),
            help="TYPE_C, TYPE_Dはリハ室専門のため入力不可",
        )

    with col_s2:
        skill_pm = st.number_input(
            "受付午後スキル",
            min_value=0,
            max_value=100,
            value=employee.skill_reception_pm if employee else 0,
            disabled=(employee_type in ["TYPE_C", "TYPE_D"]),
            help="TYPE_C, TYPE_Dはリハ室専門のため入力不可",
        )

        skill_flex = st.number_input(
            "総合対応力",
            min_value=0,
            max_value=100,
            value=employee.skill_general if employee else 0,
            help="柔軟性や総合的な対応力を評価",
        )
    
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        submit_button = st.form_submit_button(
            "✅ 更新" if edit_mode else "✅ 登録",
            type="primary",
            width="stretch"
        )
    
    with col_btn2:
        if edit_mode:
            cancel_button = st.form_submit_button(
                "❌ キャンセル",
                width="stretch"
            )

# フォーム送信処理
if submit_button:
    if not name.strip():
        st.error("❌ 職員名を入力してください")
    else:
        # 職員情報を登録/更新
        update_params = {
            'name': name.strip(),
            'employee_type': employee_type,
            'employment_type': employment_type,
            'employment_pattern_id': employment_pattern_id,
            'skill_reha': skill_reha,
            'skill_reception_am': skill_am,
            'skill_reception_pm': skill_pm,
            'skill_general': skill_flex
        }
        
        if edit_mode:
            # 更新
            if update_employee(st.session_state['edit_employee_id'], **update_params):
                st.success(f"✅ {name}さんの情報を更新しました")
                del st.session_state['edit_employee_id']
                st.rerun()
            else:
                st.error("更新に失敗しました")
        else:
            # 新規登録
            employee_id = create_employee(**update_params)
            if employee_id:
                st.success(f"✅ {name}さんを登録しました（ID: {employee_id}）")
                st.balloons()
                st.rerun()
            else:
                st.error("登録に失敗しました")

if edit_mode and 'cancel_button' in locals() and cancel_button:
    del st.session_state['edit_employee_id']
    st.rerun()

# サイドバーにヘルプ
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    
    with st.expander("職員タイプについて"):
        st.markdown("""
        **TYPE_A**: リハ室・受付両方可能
        - 最も柔軟な配置が可能
        - すべてのスキル項目を入力
        
        **TYPE_B**: 受付のみ
        - 受付業務専門
        - 受付スキルのみ入力
        
        **TYPE_C**: リハ室のみ（正職員）
        - リハビリ業務専門
        - リハ室スキルのみ入力
        
        **TYPE_D**: リハ室のみ（パート）
        - パート職員でリハ業務
        - リハ室スキルのみ入力
        """)
    
    with st.expander("スキルスコアについて"):
        st.markdown("""
        各スキルは0〜100で評価します。
        
        **リハ室スキル**:
        - リハビリ業務の能力
        
        **受付午前/午後スキル**:
        - 受付業務の能力（時間帯別）
        
        **総合対応力**:
        - 柔軟性や総合的な業務対応力
        
        シフト生成時、各時間帯に必要な
        スキルスコアが自動的に計算されます。
        """)
    
    with st.expander("勤務パターンについて"):
        st.markdown("""
        勤務パターンは勤務時間や休憩時間を
        定義します。
        
        雇用形態と勤務形態に応じて
        選択可能なパターンが表示されます。
        """)

