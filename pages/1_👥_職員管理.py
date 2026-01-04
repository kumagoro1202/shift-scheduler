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
    "TYPE_B": "📋 TYPE_B (受付専任)",
    "TYPE_C": "💪 TYPE_C (リハ室専任・正職員)",
    "TYPE_D": "🏃 TYPE_D (リハ室専任・パート)",
    "TYPE_E": "📝 TYPE_E (受付専任・パート)",
    "TYPE_F": "⏰ TYPE_F (受付専任・時短)"
}

PATTERN_CATEGORY_LABELS = {
    "full_time": "フルタイム",
    "short_time": "時短勤務",
    "part_time": "パートタイム",
}

EMPLOYMENT_PATTERNS = list_employment_patterns()
PATTERN_LOOKUP = {pattern.id: pattern for pattern in EMPLOYMENT_PATTERNS}

# 通常モード：タブで表示
tab1, tab2 = st.tabs(["職員一覧", "新規登録"])

# タブ1: 職員一覧
with tab1:
    st.subheader("登録済み職員")
    
    employees = list_employees()
    
    if not employees:
        st.info("📝 職員が登録されていません。「新規登録」タブから登録してください。")
    else:
        # 職員データの準備
        employee_data = []
        for emp in employees:
            pattern = PATTERN_LOOKUP.get(emp.employment_pattern_id)
            # is_pattern_fixedがない場合は後方互換性のためFalseとして扱う
            is_fixed = getattr(emp, 'is_pattern_fixed', False)
            
            # 正職員（通常）で変動割り当ての場合
            if not is_fixed:
                pattern_name = "変動割り当て"
                pattern_time = "早番・中番・遅番"
            else:
                pattern_name = pattern.name if pattern else "未設定"
                pattern_time = f"{pattern.start_time}-{pattern.end_time}" if pattern else "-"
            
            pattern_category = pattern.category if pattern else "unknown"
            total_skill = emp.skill_reha + emp.skill_reception_am + emp.skill_reception_pm + emp.skill_general
            
            employee_data.append({
                'id': emp.id,
                'name': emp.name,
                'employee_type': emp.employee_type,
                'employment_type': emp.employment_type,
                'pattern_name': pattern_name,
                'pattern_time': pattern_time,
                'pattern_id': emp.employment_pattern_id or '',
                'pattern_category': pattern_category,
                'is_pattern_fixed': is_fixed,
                'skill_reha': emp.skill_reha,
                'skill_reception_am': emp.skill_reception_am,
                'skill_reception_pm': emp.skill_reception_pm,
                'skill_general': emp.skill_general,
                'total_skill': total_skill
            })
        
        # フィルター・ソート設定エリア
        col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
        
        with col_filter1:
            # 職員タイプフィルター（日本語表示用のマッピング）
            EMPLOYEE_TYPE_FILTER_LABELS = {
                "TYPE_A": "リハ室・受付両方可能",
                "TYPE_B": "受付専任",
                "TYPE_C": "リハ室専任(正職員)",
                "TYPE_D": "リハ室専任(パート)",
                "TYPE_E": "受付専任(パート)",
                "TYPE_F": "受付専任(時短)"
            }
            all_employee_types_codes = ["全て"] + sorted(list(set([e['employee_type'] for e in employee_data])))
            all_employee_types_labels = ["全て"] + [EMPLOYEE_TYPE_FILTER_LABELS.get(code, code) for code in all_employee_types_codes[1:]]
            filter_employee_type_label = st.selectbox("職員タイプ", all_employee_types_labels, index=0)
            # ラベルからコードに逆変換
            if filter_employee_type_label == "全て":
                filter_employee_type = "全て"
            else:
                filter_employee_type = [k for k, v in EMPLOYEE_TYPE_FILTER_LABELS.items() if v == filter_employee_type_label][0]
        
        with col_filter2:
            # 雇用形態フィルター
            all_employment_types = ["全て"] + sorted(list(set([e['employment_type'] for e in employee_data])))
            filter_employment_type = st.selectbox("雇用形態", all_employment_types, index=0)
        
        with col_filter3:
            # 勤務パターンフィルター
            all_patterns = ["全て"] + sorted(list(set([e['pattern_name'] for e in employee_data])))
            filter_pattern = st.selectbox("勤務パターン", all_patterns, index=0)
        
        with col_filter4:
            # ソート順
            sort_by = st.selectbox(
                "並び順",
                ["雇用形態・勤務パターン", "スキルスコア(降順)", "スキルスコア(昇順)", "名前"],
                index=0
            )
        
        # フィルター適用
        filtered_data = employee_data
        if filter_employee_type != "全て":
            filtered_data = [e for e in filtered_data if e['employee_type'] == filter_employee_type]
        if filter_employment_type != "全て":
            filtered_data = [e for e in filtered_data if e['employment_type'] == filter_employment_type]
        if filter_pattern != "全て":
            filtered_data = [e for e in filtered_data if e['pattern_name'] == filter_pattern]
        
        # ソート処理
        if sort_by == "スキルスコア(降順)":
            filtered_data.sort(key=lambda x: x['total_skill'], reverse=True)
        elif sort_by == "スキルスコア(昇順)":
            filtered_data.sort(key=lambda x: x['total_skill'])
        elif sort_by == "名前":
            filtered_data.sort(key=lambda x: x['name'])
        else:  # 雇用形態・勤務パターン
            filtered_data.sort(key=lambda x: (x['employment_type'], x['pattern_id'], x['name']))
        
        st.markdown("---")
        
        # フィルター結果の表示
        if not filtered_data:
            st.warning("🔍 該当する職員が見つかりませんでした。")
        else:
            st.caption(f"📊 表示件数: {len(filtered_data)}名 / 全{len(employee_data)}名")
            
            # 表形式で一覧表示
            # ヘッダー
            header_cols = st.columns([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1.5])
            headers = ["名前", "職員タイプ", "雇用形態", "勤務パターン", "固定", "リハ室", "受付AM", "受付PM", "総合", "合計", "操作"]
            for col, header in zip(header_cols, headers):
                col.markdown(f"**{header}**")
            
            st.markdown("---")
            
            # データ行 - 編集モード対応
            for emp_data in filtered_data:
                # 編集モードかどうかを判定
                is_editing = st.session_state.get(f"editing_{emp_data['id']}", False)
                
                if is_editing:
                    # 編集モード：フォームで表示
                    with st.form(key=f"edit_form_{emp_data['id']}"):
                        form_cols = st.columns([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1.5])
                        
                        # 名前
                        with form_cols[0]:
                            edit_name = st.text_input("名前", value=emp_data['name'], label_visibility="collapsed", key=f"name_{emp_data['id']}")
                        
                        # 職員タイプ
                        with form_cols[1]:
                            type_options = ["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D", "TYPE_E", "TYPE_F"]
                            type_labels_short = {
                                "TYPE_A": "リハ室・受付両方",
                                "TYPE_B": "受付専任",
                                "TYPE_C": "リハ室専任(正)",
                                "TYPE_D": "リハ室専任(パ)",
                                "TYPE_E": "受付専任(パ)",
                                "TYPE_F": "受付専任(時短)"
                            }
                            current_type_idx = type_options.index(emp_data['employee_type'])
                            edit_type = st.selectbox("タイプ", type_options, index=current_type_idx, 
                                                    format_func=lambda x: type_labels_short[x],
                                                    label_visibility="collapsed", key=f"type_{emp_data['id']}")
                        
                        # 雇用形態
                        with form_cols[2]:
                            employment_options = ["正職員", "パート"]
                            current_employment_idx = 0 if emp_data['employment_type'] == "正職員" else 1
                            edit_employment = st.selectbox("雇用形態", employment_options, index=current_employment_idx,
                                                          label_visibility="collapsed", key=f"employment_{emp_data['id']}")
                        
                        # 勤務パターン
                        with form_cols[3]:
                            if edit_employment == "正職員":
                                pattern_category = st.session_state.get(f"pattern_cat_{emp_data['id']}", emp_data['pattern_category'])
                                if pattern_category not in ["full_time", "short_time"]:
                                    pattern_category = "full_time"
                                # 時短勤務の場合は固定、それ以外は変動
                                edit_is_fixed = (pattern_category == "short_time")
                            else:
                                pattern_category = "part_time"
                                edit_is_fixed = True  # パートは固定
                            
                            pattern_candidates = [p for p in EMPLOYMENT_PATTERNS if p.category == pattern_category]
                            if pattern_candidates:
                                current_pattern_idx = next((i for i, p in enumerate(pattern_candidates) if p.id == emp_data['pattern_id']), 0)
                                edit_pattern = st.selectbox("パターン", pattern_candidates, index=current_pattern_idx,
                                                           format_func=lambda p: p.name,
                                                           label_visibility="collapsed", key=f"pattern_{emp_data['id']}")
                                edit_pattern_id = edit_pattern.id
                            else:
                                st.caption("パターンなし")
                                edit_pattern_id = None
                        
                        # パターン固定
                        with form_cols[4]:
                            fixed_icon = "📌" if edit_is_fixed else "🔄"
                            fixed_text = "固定" if edit_is_fixed else "変動"
                            st.markdown(f"{fixed_icon}{fixed_text}")
                        
                        # スキルスコア
                        with form_cols[5]:
                            edit_reha = st.number_input("リハ室", 0, 100, emp_data['skill_reha'], 
                                                       disabled=(edit_type in ["TYPE_B", "TYPE_E", "TYPE_F"]),
                                                       label_visibility="collapsed", key=f"reha_{emp_data['id']}")
                        with form_cols[6]:
                            edit_am = st.number_input("受付AM", 0, 100, emp_data['skill_reception_am'],
                                                     disabled=(edit_type in ["TYPE_C", "TYPE_D"]),
                                                     label_visibility="collapsed", key=f"am_{emp_data['id']}")
                        with form_cols[7]:
                            edit_pm = st.number_input("受付PM", 0, 100, emp_data['skill_reception_pm'],
                                                     disabled=(edit_type in ["TYPE_C", "TYPE_D"]),
                                                     label_visibility="collapsed", key=f"pm_{emp_data['id']}")
                        with form_cols[8]:
                            edit_general = st.number_input("総合", 0, 100, emp_data['skill_general'],
                                                          label_visibility="collapsed", key=f"general_{emp_data['id']}")
                        
                        with form_cols[9]:
                            total = edit_reha + edit_am + edit_pm + edit_general
                            st.markdown(f"**{total}**")
                        
                        # 保存・キャンセルボタン
                        with form_cols[10]:
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                save_btn = st.form_submit_button("💾", help="保存")
                            with btn_col2:
                                cancel_btn = st.form_submit_button("❌", help="キャンセル")
                            
                            if save_btn:
                                # 更新処理
                                update_params = {
                                    'name': edit_name.strip(),
                                    'employee_type': edit_type,
                                    'employment_type': edit_employment,
                                    'employment_pattern_id': edit_pattern_id,
                                    'is_pattern_fixed': edit_is_fixed,
                                    'skill_reha': edit_reha if edit_type not in ["TYPE_B", "TYPE_E", "TYPE_F"] else 0,
                                    'skill_reception_am': edit_am if edit_type not in ["TYPE_C", "TYPE_D"] else 0,
                                    'skill_reception_pm': edit_pm if edit_type not in ["TYPE_C", "TYPE_D"] else 0,
                                    'skill_general': edit_general
                                }
                                if update_employee(emp_data['id'], **update_params):
                                    st.session_state[f"editing_{emp_data['id']}"] = False
                                    st.success(f"✅ {edit_name}さんの情報を更新しました")
                                    st.rerun()
                                else:
                                    st.error("更新に失敗しました")
                            
                            if cancel_btn:
                                st.session_state[f"editing_{emp_data['id']}"] = False
                                st.rerun()
                else:
                    # 通常表示モード
                    data_cols = st.columns([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1.5])
                    
                    # 職員タイプを日本語表示に変換
                    employee_type_labels_short = {
                        "TYPE_A": "リハ室・受付両方",
                        "TYPE_B": "受付専任",
                        "TYPE_C": "リハ室専任(正)",
                        "TYPE_D": "リハ室専任(パ)",
                        "TYPE_E": "受付専任(パ)",
                        "TYPE_F": "受付専任(時短)"
                    }
                    employee_type_display = employee_type_labels_short.get(emp_data['employee_type'], emp_data['employee_type'])
                    
                    # パターン固定アイコン
                    fixed_icon = "📌" if emp_data['is_pattern_fixed'] else "🔄"
                    fixed_text = "固定" if emp_data['is_pattern_fixed'] else "変動"
                    
                    data_cols[0].markdown(emp_data['name'])
                    data_cols[1].markdown(employee_type_display)
                    data_cols[2].markdown(emp_data['employment_type'])
                    data_cols[3].markdown(f"{emp_data['pattern_name']}")
                    data_cols[4].markdown(f"{fixed_icon}{fixed_text}")
                    data_cols[5].markdown(f"{emp_data['skill_reha']}")
                    data_cols[6].markdown(f"{emp_data['skill_reception_am']}")
                    data_cols[7].markdown(f"{emp_data['skill_reception_pm']}")
                    data_cols[8].markdown(f"{emp_data['skill_general']}")
                    data_cols[9].markdown(f"**{emp_data['total_skill']}**")
                    
                    with data_cols[10]:
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("✏️", key=f"edit_{emp_data['id']}", help="編集"):
                                st.session_state[f"editing_{emp_data['id']}"] = True
                                st.rerun()
                        with btn_col2:
                            if st.button("🗑️", key=f"delete_{emp_data['id']}", help="削除"):
                                if delete_employee(emp_data['id']):
                                    st.success(f"✅ {emp_data['name']}さんを削除しました")
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
with tab2:
    st.subheader("新規職員の登録")

# 入力フォーム（新規登録モードのみ）
with st.form("employee_form"):
    name = st.text_input(
        "職員名 *",
        value="",
        placeholder="例: 山田太郎",
    )

    st.markdown("---")
    st.subheader("基本情報")

    col1, col2 = st.columns(2)

    with col1:
        employment_type = st.radio(
            "雇用形態 *",
            ["正職員", "パート"],
            index=0,
        )

    with col2:
        employee_type = st.selectbox(
            "職員タイプ *",
            ["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D", "TYPE_E", "TYPE_F"],
            index=0,
            format_func=lambda x: EMPLOYEE_TYPE_LABELS[x],
        )

    # 勤務パターンの選択
    if employment_type == "正職員":
        category_options = ["full_time", "short_time"]
        default_category = "full_time"
        category_index = 0
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
        default_index = 0
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
            value=0,
            disabled=(employee_type in ["TYPE_B", "TYPE_E", "TYPE_F"]),
            help="TYPE_B, TYPE_E, TYPE_Fは受付専任のため入力不可",
        )

        skill_am = st.number_input(
            "受付午前スキル（医事業務能力を優先）",
            min_value=0,
            max_value=100,
            value=0,
            disabled=(employee_type in ["TYPE_C", "TYPE_D"]),
            help="TYPE_C, TYPE_Dはリハ室専任のため入力不可",
        )

    with col_s2:
        skill_pm = st.number_input(
            "受付午後スキル（医事業務能力を優先）",
            min_value=0,
            max_value=100,
            value=0,
            disabled=(employee_type in ["TYPE_C", "TYPE_D"]),
            help="TYPE_C, TYPE_Dはリハ室専任のため入力不可",
        )

        skill_flex = st.number_input(
            "総合対応力",
            min_value=0,
            max_value=100,
            value=0,
            help="柔軟性や総合的な対応力を評価",
        )
    
    st.markdown("---")
    
    submit_button = st.form_submit_button(
        "✅ 登録",
        type="primary",
        use_container_width=True
    )

# フォーム送信処理
if submit_button:
    if not name.strip():
        st.error("❌ 職員名を入力してください")
    else:
        # is_pattern_fixed の自動設定
        # 正職員・フルタイムは変動、それ以外（時短・パート）は固定
        if employment_type == "正職員" and pattern_category == "full_time":
            is_pattern_fixed = False
        else:
            is_pattern_fixed = True
        
        # 職員情報を登録
        update_params = {
            'name': name.strip(),
            'employee_type': employee_type,
            'employment_type': employment_type,
            'employment_pattern_id': employment_pattern_id,
            'is_pattern_fixed': is_pattern_fixed,
            'skill_reha': skill_reha,
            'skill_reception_am': skill_am,
            'skill_reception_pm': skill_pm,
            'skill_general': skill_flex
        }
        
        # 新規登録
        employee_id = create_employee(**update_params)
        if employee_id:
            st.success(f"✅ {name}さんを登録しました（ID: {employee_id}）")
            st.balloons()
            st.rerun()
        else:
            st.error("登録に失敗しました")

# サイドバーにヘルプ
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    
    with st.expander("職員タイプについて"):
        st.markdown("""
        **TYPE_A**: リハ室・受付両方可能
        - 最も柔軟な配置が可能
        - すべてのスキル項目を入力
        
        **TYPE_B**: 受付専任
        - 受付業務専門
        - 受付スキルのみ入力
        
        **TYPE_C**: リハ室専任（正職員）
        - リハビリ業務専門
        - リハ室スキルのみ入力
        
        **TYPE_D**: リハ室専任（パート）
        - パート職員でリハ業務
        - リハ室スキルのみ入力
        
        **TYPE_E**: 受付専任（パート）
        - パート職員で受付業務専門
        - 受付スキルのみ入力
        
        **TYPE_F**: 受付専任（時短）
        - 時短勤務で受付業務専門
        - 受付スキルのみ入力
        """)
    
    with st.expander("スキルスコアについて"):
        st.markdown("""
        各スキルは0〜100で評価します。
        
        **リハ室スキル**:
        - リハビリ業務の能力
        
        **受付午前/午後スキル**:
        - 受付業務の能力（時間帯別）
        - 医事業務能力を優先して評価
        
        **総合対応力**:
        - 柔軟性や総合的な業務対応力
        
        シフト生成時、各時間帯に必要な
        スキルスコアが自動的に計算されます。
        """)
    
    with st.expander("勤務パターンについて"):
        st.markdown("""
        勤務パターンは勤務時間や休憩時間を
        定義します。
        
        **パターン固定について**:
        - 🔄 **変動**: 正職員（通常）は日によって
          早番・中番・遅番を変動的に割り当て
        - 📌 **固定**: パート職員・時短勤務職員は
          登録されたパターンで固定
        
        雇用形態と勤務形態に応じて
        選択可能なパターンが表示されます。
        """)

