"""
休憩ローテーション機能テスト
"""
import sys
from pathlib import Path

# パスを追加
sys.path.append(str(Path(__file__).parent.parent))

from src.shift_scheduler.breaks import (
    generate_time_intervals,
    auto_assign_and_save_breaks,
    validate_reception_coverage,
    _window_overlaps
)


def test_time_intervals():
    """時間帯分割のテスト"""
    print("=" * 50)
    print("テスト1: 時間帯分割")
    print("=" * 50)
    
    intervals = generate_time_intervals("08:30", "12:30", 60)
    print(f"08:30-12:30を60分間隔で分割:")
    for start, end in intervals:
        print(f"  {start} - {end}")
    
    assert len(intervals) == 4, "4つの時間帯に分割されるべき"
    print("✓ テスト成功\n")


def test_break_slots():
    """休憩スロット生成のテスト"""
    print("=" * 50)
    print("テスト2: 休憩スロット生成")
    print("=" * 50)
    
    # フルタイム: 2時間休憩、2回分割
    slots = generate_break_slots(2.0, 2)
    print("フルタイム職員（2時間×2回）:")
    for slot in slots:
        print(f"  休憩{slot['number']}: {slot['start']} - {slot['end']}")
    
    assert len(slots) == 2, "2回の休憩があるべき"
    
    # 時短勤務: 1時間休憩、1回
    slots2 = generate_break_slots(1.0, 1)
    print("\n時短勤務職員（1時間×1回）:")
    for slot in slots2:
        print(f"  休憩{slot['number']}: {slot['start']} - {slot['end']}")
    
    assert len(slots2) == 1, "1回の休憩があるべき"
    
    # パート: 休憩なし
    slots3 = generate_break_slots(0.0, 0)
    print("\nパート職員（休憩なし）:")
    print(f"  休憩回数: {len(slots3)}")
    
    assert len(slots3) == 0, "休憩がないべき"
    
    print("✓ テスト成功\n")


def test_overlapping():
    """時間重複チェックのテスト"""
    print("=" * 50)
    print("テスト3: 時間重複チェック")
    print("=" * 50)
    
    # 重複あり
    result1 = is_overlapping("11:00", "12:00", "11:30", "12:30")
    print(f"11:00-12:00 と 11:30-12:30: {'重複' if result1 else '重複なし'}")
    assert result1 == True, "重複しているべき"
    
    # 重複なし
    result2 = is_overlapping("11:00", "12:00", "13:00", "14:00")
    print(f"11:00-12:00 と 13:00-14:00: {'重複' if result2 else '重複なし'}")
    assert result2 == False, "重複していないべき"
    
    # 接触（重複なしとみなす）
    result3 = is_overlapping("11:00", "12:00", "12:00", "13:00")
    print(f"11:00-12:00 と 12:00-13:00: {'重複' if result3 else '重複なし'}")
    assert result3 == False, "接触は重複していないべき"
    
    print("✓ テスト成功\n")


def test_time_parsing():
    """時刻パース/フォーマットのテスト"""
    print("=" * 50)
    print("テスト4: 時刻パース/フォーマット")
    print("=" * 50)
    
    time_str = "08:30"
    dt = parse_time(time_str)
    formatted = format_time(dt)
    
    print(f"元の時刻: {time_str}")
    print(f"パース後フォーマット: {formatted}")
    
    assert time_str == formatted, "パースとフォーマットで元に戻るべき"
    
    print("✓ テスト成功\n")


def run_all_tests():
    """全テストを実行"""
    print("\n")
    print("╔" + "=" * 48 + "╗")
    print("║  休憩ローテーション機能テスト                ║")
    print("╚" + "=" * 48 + "╝")
    print()
    
    tests = [
        test_time_intervals,
        test_break_slots,
        test_overlapping,
        test_time_parsing
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ テスト失敗: {e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ エラー: {e}\n")
            failed += 1
    
    print("=" * 50)
    print("テスト結果サマリ")
    print("=" * 50)
    print(f"合計: {passed + failed}件のテスト")
    print(f"成功: {passed}件")
    print(f"失敗: {failed}件")
    
    if failed == 0:
        print("\n✓✓✓ すべてのテストが成功しました！ ✓✓✓")
    else:
        print(f"\n✗✗✗ {failed}件のテストが失敗しました ✗✗✗")
    
    print()


if __name__ == "__main__":
    run_all_tests()
