"""
職員管理ページ（V2.0対応）
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import (
    init_database,
    get_all_employees,
    create_employee,
    update_employee,
    delete_employee,
    get_employee_by_id,
    get_all_work_patterns,
    get_work_patterns_by_type,
    get_work_patterns_by_employment_type,
    get_all_employment_patterns,
    get_employment_patterns_by_category
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

# タブで機能を分ける
tab1, tab2 = st.tabs(["職員一覧", "新規登録"])

# タブ1: 職員一覧
with tab1:
    st.subheader("登録済み職員")
    
    employees = get_all_employees()
    
    if not employees:
        st.info("📝 職員が登録されていません。「新規登録」タブから登録してください。")
    else:
        # 職員リストを表示
        for emp in employees:
            with st.expander(f"**{emp['name']}** - {EMPLOYEE_TYPE_LABELS.get(emp.get('employee_type', 'TYPE_A'), 'TYPE_A')}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**職員タイプ**: {emp.get('employee_type', 'TYPE_A')}")
                    st.markdown(f"**雇用形態**: {emp.get('employment_type', '正職員')}")
                    st.markdown(f"**勤務形態**: {emp.get('work_type', 'フルタイム')}")
                    
                    # V3.0対応: employment_pattern_idを優先表示
                    if emp.get('employment_pattern_id'):
                        st.markdown(f"**勤務パターン**: {emp.get('employment_pattern_id')} (V3)")
                    else:
                        st.markdown(f"**勤務パターン**: {emp.get('work_pattern', 'P1')}")
                    
                    # スキルスコア表示
                    st.markdown("**スキルスコア**:")
                    skill_cols = st.columns(4)
                    with skill_cols[0]:
                        st.metric("リハ室", emp.get('skill_reha', 0))
                    with skill_cols[1]:
                        st.metric("受付(午前)", emp.get('skill_reception_am', 0))
                    with skill_cols[2]:
                        st.metric("受付(午後)", emp.get('skill_reception_pm', 0))
                    with skill_cols[3]:
                        st.metric("総合対応力", emp.get('skill_general', 0))
                
                with col2:
                    # 編集・削除ボタン
                    if st.button("✏️ 編集", key=f"edit_{emp['id']}"):
                        st.session_state['edit_employee_id'] = emp['id']
                        st.rerun()
                    
                    if st.button("🗑️ 削除", key=f"delete_{emp['id']}", type="secondary"):
                        if delete_employee(emp['id']):
                            st.success(f"✅ {emp['name']}さんを削除しました")
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
            full_time = len([e for e in employees if e.get('work_type') == 'フルタイム'])
            st.metric("フルタイム", f"{full_time}名")
        
        with col_stat3:
            part_time = len([e for e in employees if e.get('employment_type') == 'パート'])
            st.metric("パート", f"{part_time}名")
        
        with col_stat4:
            avg_reha = sum(e.get('skill_reha', 0) for e in employees) / len(employees)
            st.metric("平均リハ室スキル", f"{avg_reha:.1f}")

# タブ2: 新規登録/編集
with tab2:
    # 編集モードのチェック
    edit_mode = 'edit_employee_id' in st.session_state and st.session_state['edit_employee_id']
    
    if edit_mode:
        st.subheader("✏️ 職員情報の編集")
        employee = get_employee_by_id(st.session_state['edit_employee_id'])
        if not employee:
            st.error("職員情報が見つかりません")
            del st.session_state['edit_employee_id']
            st.rerun()
    else:
        st.subheader("新規職員の登録")
        employee = None
    
    # 入力フォーム
    with st.form("employee_form"):
        name = st.text_input(
            "職員名 *",
            value=employee['name'] if employee else "",
            placeholder="例: 山田太郎"
        )
        
        st.markdown("---")
        st.subheader("基本情報")
        
        col1, col2 = st.columns(2)
        
        with col1:
            employment_type = st.radio(
                "雇用形態 *",
                ["正職員", "パート"],
                index=0 if not employee else (0 if employee.get('employment_type') == '正職員' else 1)
            )
        
        with col2:
            employee_type = st.selectbox(
                "職員タイプ *",
                ["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"],
                format_func=lambda x: EMPLOYEE_TYPE_LABELS[x],
                index=["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"].index(employee.get('employee_type', 'TYPE_A')) if employee else 0
            )
        
        # 勤務形態の選択（雇用形態に連動）
        if employment_type == "正職員":
            work_type_options = ["フルタイム", "時短勤務"]
            default_work_type = employee.get('work_type', 'フルタイム') if employee else 'フルタイム'
        else:
            work_type_options = ["パートタイム"]
            default_work_type = "パートタイム"
        
        work_type = st.selectbox(
            "勤務形態 *",
            work_type_options,
            index=work_type_options.index(default_work_type) if default_work_type in work_type_options else 0
        )
        
        # 勤務パターンの選択
        # V3.0対応: employment_patternsを優先的に使用
        all_emp_patterns = get_all_employment_patterns()
        
        if all_emp_patterns:
            # V3.0方式: employment_patterns使用
            if employment_type == "正職員":
                if work_type == "フルタイム":
                    available_patterns = [p for p in all_emp_patterns if p['category'] == 'full_time']
                else:  # 時短勤務
                    available_patterns = [p for p in all_emp_patterns if p['category'] == 'short_time']
            else:
                available_patterns = [p for p in all_emp_patterns if p['category'] == 'part_time']
            
            default_pattern_id = employee.get('employment_pattern_id', 'full_early') if employee else 'full_early'
            pattern_ids = [p['id'] for p in available_patterns]
            
            if pattern_ids:
                employment_pattern_id = st.selectbox(
                    "勤務パターン * (V3.0)",
                    pattern_ids,
                    format_func=lambda x: next((f"{p['name']} ({p['start_time']}-{p['end_time']})" for p in available_patterns if p['id'] == x), x),
                    index=pattern_ids.index(default_pattern_id) if default_pattern_id in pattern_ids else 0
                )
            else:
                employment_pattern_id = 'full_early'
                st.warning("⚠️ 利用可能な勤務パターンがありません")
        else:
            # V2.0互換: work_patterns使用
            employment_pattern_id = None
            patterns = get_work_patterns_by_type(work_type)
            if patterns:
                default_pattern = employee.get('work_pattern', 'P1') if employee else 'P1'
                pattern_ids = [p['id'] for p in patterns]
                work_pattern = st.selectbox(
                    "勤務パターン *",
                    pattern_ids,
                    format_func=lambda x: next((f"{p['name']} ({p['start_time']}-{p['end_time']})" for p in patterns if p['id'] == x), x),
                    index=pattern_ids.index(default_pattern) if default_pattern in pattern_ids else 0
                )
            else:
                work_pattern = st.text_input("勤務パターン *", value=employee.get('work_pattern', 'P1') if employee else 'P1')
        
        st.markdown("---")
        st.subheader("スキルスコア（0〜100）")
        st.caption("職員タイプによって入力できる項目が制限されます")
        
        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            # リハ室スキル（TYPE_B以外）
            skill_reha = st.number_input(
                "リハ室スキル",
                0, 100,
                value=employee.get('skill_reha', 0) if employee else 0,
                disabled=(employee_type == "TYPE_B"),
                help="TYPE_Bは受付専門のため入力不可"
            )
            
            # 受付午前スキル（TYPE_C, TYPE_D以外）
            skill_am = st.number_input(
                "受付午前スキル",
                0, 100,
                value=employee.get('skill_reception_am', 0) if employee else 0,
                disabled=(employee_type in ["TYPE_C", "TYPE_D"]),
                help="TYPE_C, TYPE_Dはリハ室専門のため入力不可"
            )
        
        with col_s2:
            # 受付午後スキル（TYPE_C, TYPE_D以外）
            skill_pm = st.number_input(
                "受付午後スキル",
                0, 100,
                value=employee.get('skill_reception_pm', 0) if employee else 0,
                disabled=(employee_type in ["TYPE_C", "TYPE_D"]),
                help="TYPE_C, TYPE_Dはリハ室専門のため入力不可"
            )
            
            # 総合対応力
            skill_flex = st.number_input(
                "総合対応力",
                0, 100,
                value=employee.get('skill_general', 0) if employee else 0,
                help="柔軟性や総合的な対応力を評価"
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

