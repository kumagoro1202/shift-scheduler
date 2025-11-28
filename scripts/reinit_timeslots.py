"""
時間帯マスタ再初期化スクリプト
V3.0仕様に準拠したリハ室と受付の時間帯を再設定します
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import init_fixed_time_slots, get_all_time_slots


def reinit_timeslots():
    """時間帯マスタを再初期化"""
    
    print("=" * 60)
    print("時間帯マスタ再初期化（V3.0仕様）")
    print("=" * 60)
    
    print("\n⚠️  この操作により、既存の時間帯データが上書きされます")
    print("    既存のシフトデータには影響しません")
    response = input("\n続行しますか？ (y/N): ")
    
    if response.lower() != 'y':
        print("キャンセルしました")
        return
    
    print("\n🔄 時間帯マスタを再初期化中...")
    init_fixed_time_slots()
    print("  ✅ 時間帯マスタを再作成しました")
    
    # 確認
    time_slots = get_all_time_slots()
    
    print(f"\n📊 登録された時間帯: {len(time_slots)}個")
    
    # 業務エリア別に集計
    reha_slots = [ts for ts in time_slots if ts.get('area') == 'リハ室']
    reception_slots = [ts for ts in time_slots if ts.get('area') == '受付']
    
    print(f"  - リハ室: {len(reha_slots)}個")
    print(f"  - 受付: {len(reception_slots)}個")
    
    print("\n📋 時間帯一覧:")
    print("-" * 60)
    
    # 曜日別に表示
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    for day_idx, day_name in enumerate(weekdays):
        day_slots = [ts for ts in time_slots if ts.get('day_of_week') == day_idx]
        if day_slots:
            print(f"\n【{day_name}曜日】")
            for ts in sorted(day_slots, key=lambda x: (x['area'], x['start_time'])):
                print(f"  {ts['area']:6s} | {ts['start_time']}-{ts['end_time']} | {ts['display_name']}")
    
    print("\n" + "=" * 60)
    print("✅ 時間帯マスタの再初期化が完了しました")
    print("=" * 60)
    print("\nアプリケーションを再起動して確認してください:")
    print("  streamlit run main.py")
    print()


if __name__ == "__main__":
    reinit_timeslots()
