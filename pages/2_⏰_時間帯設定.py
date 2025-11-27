"""
時間帯設定ページ（V2.0対応）
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import (
    init_database,
    get_all_time_slots,
    create_time_slot,
    update_time_slot,
    delete_time_slot
)

st.set_page_config(page_title="時間帯設定", page_icon="⏰", layout="wide")

# データベース初期化
init_database()

st.title("⏰ 時間帯設定")
st.markdown("---")

# タブで機能を分ける
tab1, tab2 = st.tabs(["時間帯一覧", "新規登録"])

# タブ1: 時間帯一覧
with tab1:
    st.subheader("登録済み時間帯")
    
    time_slots = get_all_time_slots()
    
    if not time_slots:
        st.info("📝 時間帯が登録されていません。「新規登録」タブから登録してください。")
    else:
        # テーブル形式で表示
        for ts in time_slots:
            with st.expander(f"**{ts['name']}** ({ts['start_time']} - {ts['end_time']})"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**業務エリア**: {ts.get('area_type', '受付')}")
                    st.markdown(f"**時間区分**: {ts.get('time_period', '終日')}")
                    st.markdown(f"**必要人数**: {ts.get('required_employees_min', 1)} 〜 {ts.get('required_employees_max', ts['required_employees'])}名")
                    st.markdown(f"**目標スキルスコア**: {ts.get('target_skill_score', 150)}")
                    st.markdown(f"**重み係数**: {ts.get('skill_weight', 1.0)}")
                
                with col2:
                    if st.button("✏️ 編集", key=f"edit_{ts['id']}"):
                        st.session_state['edit_time_slot_id'] = ts['id']
                        st.rerun()
                    
                    if st.button("🗑️ 削除", key=f"delete_{ts['id']}", type="secondary"):
                        if delete_time_slot(ts['id']):
                            st.success(f"✅ {ts['name']}を削除しました")
                            st.rerun()
                        else:
                            st.error("削除に失敗しました")

# タブ2: 新規登録/編集
with tab2:
    # 編集モードのチェック
    edit_mode = 'edit_time_slot_id' in st.session_state and st.session_state['edit_time_slot_id']
    
    if edit_mode:
        st.subheader("✏️ 時間帯の編集")
        time_slot = next((ts for ts in get_all_time_slots() 
                         if ts['id'] == st.session_state['edit_time_slot_id']), None)
        if not time_slot:
            st.error("時間帯情報が見つかりません")
            del st.session_state['edit_time_slot_id']
            st.rerun()
    else:
        st.subheader("新規時間帯の登録")
        time_slot = None
    
    # 入力フォーム
    with st.form("time_slot_form"):
        name = st.text_input(
            "時間帯名 *",
            value=time_slot['name'] if time_slot else "",
            placeholder="例: 受付午前、リハ室午後"
        )
        
        st.markdown("---")
        st.subheader("基本情報")
        
        col1, col2 = st.columns(2)
        
        with col1:
            area_type = st.radio(
                "業務エリア *",
                ["受付", "リハ室"],
                index=0 if not time_slot else (0 if time_slot.get('area_type') == '受付' else 1)
            )
        
        with col2:
            time_period = st.selectbox(
                "時間区分 *",
                ["午前", "午後", "終日"],
                index=["午前", "午後", "終日"].index(time_slot.get('time_period', '終日')) if time_slot else 2
            )
        
        col_time1, col_time2 = st.columns(2)
        
        with col_time1:
            start_time = st.time_input(
                "開始時刻 *",
                value=None if not time_slot else 
                      __import__('datetime').datetime.strptime(time_slot['start_time'], "%H:%M").time()
            )
        
        with col_time2:
            end_time = st.time_input(
                "終了時刻 *",
                value=None if not time_slot else 
                      __import__('datetime').datetime.strptime(time_slot['end_time'], "%H:%M").time()
            )
        
        st.markdown("---")
        st.subheader("必要人数")
        
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            req_min = st.number_input(
                "最小 *",
                min_value=1,
                max_value=10,
                value=time_slot.get('required_employees_min', 1) if time_slot else 1,
                help="この時間帯に最低限必要な職員数"
            )
        
        with col_r2:
            req_max = st.number_input(
                "最大 *",
                min_value=1,
                max_value=10,
                value=time_slot.get('required_employees_max', 2) if time_slot else 2,
                help="この時間帯に配置できる最大職員数"
            )
        
        st.markdown("---")
        st.subheader("最適化設定")
        
        target_score = st.number_input(
            "目標スキルスコア合計 *",
            min_value=0,
            max_value=1000,
            value=time_slot.get('target_skill_score', 150) if time_slot else 150,
            help="この時間帯に配置する職員のスキルスコア合計の目標値"
        )
        
        skill_weight = st.slider(
            "重み係数 *",
            min_value=0.1,
            max_value=5.0,
            value=float(time_slot.get('skill_weight', 1.0)) if time_slot else 1.0,
            step=0.1,
            help="最適化時の重要度（高いほど優先度が上がる）"
        )
        
        st.markdown("---")
        
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
        if not name.strip():
            st.error("❌ 時間帯名を入力してください")
        elif not start_time or not end_time:
            st.error("❌ 開始時刻と終了時刻を入力してください")
        elif start_time >= end_time:
            st.error("❌ 終了時刻は開始時刻より後にしてください")
        elif req_min > req_max:
            st.error("❌ 最大人数は最小人数以上にしてください")
        else:
            start_str = start_time.strftime("%H:%M")
            end_str = end_time.strftime("%H:%M")
            
            if edit_mode:
                # 更新
                if update_time_slot(
                    st.session_state['edit_time_slot_id'],
                    name=name.strip(),
                    start_time=start_str,
                    end_time=end_str,
                    required_employees=req_max,  # 互換性のため
                    area_type=area_type,
                    time_period=time_period,
                    required_employees_min=req_min,
                    required_employees_max=req_max,
                    target_skill_score=target_score,
                    skill_weight=skill_weight
                ):
                    st.success(f"✅ {name}を更新しました")
                    del st.session_state['edit_time_slot_id']
                    st.rerun()
                else:
                    st.error("更新に失敗しました")
            else:
                # 新規登録
                time_slot_id = create_time_slot(
                    name=name.strip(),
                    start_time=start_str,
                    end_time=end_str,
                    required_employees=req_max,  # 互換性のため
                    area_type=area_type,
                    time_period=time_period,
                    required_employees_min=req_min,
                    required_employees_max=req_max,
                    target_skill_score=target_score,
                    skill_weight=skill_weight
                )
                if time_slot_id:
                    st.success(f"✅ {name}を登録しました（ID: {time_slot_id}）")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("登録に失敗しました")
    
    if edit_mode and 'cancel_button' in locals() and cancel_button:
        del st.session_state['edit_time_slot_id']
        st.rerun()

# サイドバーにヘルプ
with st.sidebar:
    st.markdown("### 💡 ヘルプ")
    
    with st.expander("業務エリアについて"):
        st.markdown("""
        **受付**: 受付業務を行う時間帯
        - TYPE_A、TYPE_Bの職員が配置可能
        - 受付スキルが評価される
        
        **リハ室**: リハビリ業務を行う時間帯
        - TYPE_A、TYPE_C、TYPE_Dの職員が配置可能
        - リハ室スキルが評価される
        """)
    
    with st.expander("時間区分について"):
        st.markdown("""
        **午前**: 午前の時間帯
        - 受付の場合、受付午前スキルが評価される
        
        **午後**: 午後の時間帯
        - 受付の場合、受付午後スキルが評価される
        
        **終日**: 1日を通した時間帯
        - 平均スキルが評価される
        """)
    
    with st.expander("必要人数について"):
        st.markdown("""
        **最小**: この時間帯に最低限必要な職員数
        **最大**: この時間帯に配置できる最大職員数
        
        シフト生成時、最小〜最大の範囲内で
        最適な人数が自動的に決定されます。
        """)
    
    with st.expander("最適化設定について"):
        st.markdown("""
        **目標スキルスコア合計**:
        - この時間帯に配置する職員の
          スキルスコア合計の目標値
        
        **重み係数**:
        - 最適化時の重要度
        - 高いほど優先度が上がる
        - 1.0が標準、0.5で低優先、2.0で高優先
        """)

