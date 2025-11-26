"""
職員管理ページ
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import (
    get_all_employees,
    create_employee,
    update_employee,
    delete_employee,
    get_employee_by_id
)

st.set_page_config(page_title="職員管理", page_icon="👥", layout="wide")

st.title("👥 職員管理")
st.markdown("---")

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
            col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
            
            with col1:
                st.markdown(f"**{emp['name']}**")
            
            with col2:
                # スキルスコアをプログレスバーで表示
                st.progress(emp['skill_score'] / 100, 
                           text=f"スキル: {emp['skill_score']}")
            
            with col3:
                # 編集ボタン
                if st.button("✏️ 編集", key=f"edit_{emp['id']}"):
                    st.session_state['edit_employee_id'] = emp['id']
            
            with col4:
                # 削除ボタン
                if st.button("🗑️ 削除", key=f"delete_{emp['id']}", type="secondary"):
                    if delete_employee(emp['id']):
                        st.success(f"✅ {emp['name']}さんを削除しました")
                        st.rerun()
                    else:
                        st.error("削除に失敗しました")
        
        st.markdown("---")
        
        # 統計情報
        st.subheader("📊 統計情報")
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            st.metric("総職員数", f"{len(employees)}名")
        
        with col_stat2:
            avg_skill = sum(e['skill_score'] for e in employees) / len(employees)
            st.metric("平均スキルスコア", f"{avg_skill:.1f}")
        
        with col_stat3:
            max_emp = max(employees, key=lambda x: x['skill_score'])
            st.metric("最高スキル", f"{max_emp['skill_score']} ({max_emp['name']})")

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
        
        skill_score = st.slider(
            "スキルスコア *",
            min_value=1,
            max_value=100,
            value=employee['skill_score'] if employee else 50,
            help="職員の能力や経験を1-100で評価してください"
        )
        
        # スキルレベルの目安を表示
        if skill_score >= 80:
            skill_level = "🌟 エキスパート"
        elif skill_score >= 60:
            skill_level = "⭐ ベテラン"
        elif skill_score >= 40:
            skill_level = "✨ 中堅"
        else:
            skill_level = "📝 新人"
        
        st.info(f"現在の設定: {skill_level}")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            submit_button = st.form_submit_button(
                "✅ 更新" if edit_mode else "✅ 登録",
                type="primary",
                use_container_width=True
            )
        
        with col_btn2:
            if edit_mode:
                cancel_button = st.form_submit_button(
                    "❌ キャンセル",
                    use_container_width=True
                )
    
    # フォーム送信処理
    if submit_button:
        # 重複送信防止チェック
        submission_key = f"employee_submitted_{name}_{skill_score}"
        if submission_key in st.session_state and st.session_state[submission_key]:
            # 既に処理済み
            pass
        elif not name.strip():
            st.error("❌ 職員名を入力してください")
        else:
            if edit_mode:
                # 更新
                if update_employee(st.session_state['edit_employee_id'], name.strip(), skill_score):
                    st.success(f"✅ {name}さんの情報を更新しました")
                    del st.session_state['edit_employee_id']
                    # 送信済みフラグをクリア
                    if submission_key in st.session_state:
                        del st.session_state[submission_key]
                    st.rerun()
                else:
                    st.error("更新に失敗しました")
            else:
                # 新規登録
                employee_id = create_employee(name.strip(), skill_score)
                if employee_id:
                    st.success(f"✅ {name}さんを登録しました（ID: {employee_id}）")
                    st.balloons()
                    # 送信済みフラグを設定
                    st.session_state[submission_key] = True
                    st.rerun()
                else:
                    st.error("登録に失敗しました")
    
    if edit_mode and 'cancel_button' in locals() and cancel_button:
        del st.session_state['edit_employee_id']
        st.rerun()

# サイドバーにヘルプ
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    with st.expander("スキルスコアとは？"):
        st.markdown("""
        職員の能力や経験を1-100の数値で表します。
        
        **目安:**
        - 80-100: エキスパート（長年の経験）
        - 60-79: ベテラン（3年以上）
        - 40-59: 中堅（1-3年）
        - 1-39: 新人（1年未満）
        
        シフト生成時、各時間帯のスキルが
        均等になるよう自動調整されます。
        """)
