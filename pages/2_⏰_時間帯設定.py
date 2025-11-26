"""
時間帯設定ページ
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
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 2])
                
                with col1:
                    st.markdown(f"**{ts['name']}**")
                
                with col2:
                    st.text(f"🕐 {ts['start_time']} - {ts['end_time']}")
                
                with col3:
                    st.text(f"👥 必要人数: {ts['required_employees']}名")
                
                with col4:
                    if st.button("✏️", key=f"edit_{ts['id']}", help="編集"):
                        st.session_state['edit_time_slot_id'] = ts['id']
                        st.rerun()
                
                with col5:
                    if st.button("🗑️ 削除", key=f"delete_{ts['id']}", type="secondary"):
                        if delete_time_slot(ts['id']):
                            st.success(f"✅ {ts['name']}を削除しました")
                            st.rerun()
                        else:
                            st.error("削除に失敗しました")
                
                st.markdown("---")

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
            placeholder="例: 午前、午後、夜間"
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
        
        required_employees = st.number_input(
            "必要人数 *",
            min_value=1,
            max_value=10,
            value=time_slot['required_employees'] if time_slot else 2,
            help="この時間帯に必要な職員の人数"
        )
        
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
        else:
            start_str = start_time.strftime("%H:%M")
            end_str = end_time.strftime("%H:%M")
            
            if edit_mode:
                # 更新
                if update_time_slot(
                    st.session_state['edit_time_slot_id'],
                    name.strip(),
                    start_str,
                    end_str,
                    required_employees
                ):
                    st.success(f"✅ {name}を更新しました")
                    del st.session_state['edit_time_slot_id']
                    st.rerun()
                else:
                    st.error("更新に失敗しました")
            else:
                # 新規登録
                time_slot_id = create_time_slot(
                    name.strip(),
                    start_str,
                    end_str,
                    required_employees
                )
                if time_slot_id:
                    st.success(f"✅ {name}を登録しました")
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
    
    with st.expander("時間帯の設定例"):
        st.markdown("""
        **3交代制の例:**
        - 午前: 08:00 - 16:00
        - 午後: 16:00 - 24:00
        - 夜間: 00:00 - 08:00
        
        **2交代制の例:**
        - 日勤: 09:00 - 18:00
        - 夜勤: 18:00 - 09:00
        
        **1日の例:**
        - 午前: 09:00 - 12:00
        - 午後: 13:00 - 17:00
        """)
    
    with st.expander("必要人数について"):
        st.markdown("""
        各時間帯に必要な職員の人数を設定します。
        
        シフト生成時、必ずこの人数が
        割り当てられるよう最適化されます。
        
        **例:**
        - 忙しい時間帯: 3-4名
        - 通常の時間帯: 2名
        - 閑散時間帯: 1名
        """)
