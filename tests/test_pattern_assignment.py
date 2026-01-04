"""正職員の勤務パターン動的割り当ての動作確認スクリプト"""
from src.shift_scheduler.optimizer import _get_available_patterns_for_day, _select_best_pattern
from src.shift_scheduler.models import Employee
from datetime import datetime


def test_pattern_functions():
    """勤務パターン選択関数の動作を確認"""
    
    # テスト用の正職員（変動割り当て）
    regular_employee = Employee(
        id=1,
        name="正職員A",
        employee_type="TYPE_A",
        employment_type="正職員",
        employment_pattern_id="weekday_full_A",
        skill_reha=70,
        skill_reception_am=80,
        skill_reception_pm=75,
        skill_general=60,
        is_active=True,
        is_pattern_fixed=False,  # 変動割り当て
    )
    
    # テスト用のパート職員（固定割り当て）
    part_employee = Employee(
        id=2,
        name="パート職員B",
        employee_type="TYPE_B",
        employment_type="パート",
        employment_pattern_id="part_morning",
        skill_reha=0,
        skill_reception_am=60,
        skill_reception_pm=0,
        skill_general=50,
        is_active=True,
        is_pattern_fixed=True,  # 固定
    )
    
    print("=" * 60)
    print("正職員の勤務パターン動的割り当てテスト")
    print("=" * 60)
    
    # 月曜日（weekday: 0）のテスト
    monday = "2026-01-05"
    monday_patterns = _get_available_patterns_for_day(monday, regular_employee)
    print(f"\n【月曜日】 {monday}")
    print(f"  正職員Aの利用可能パターン: {monday_patterns}")
    assert monday_patterns == ["weekday_full_A", "weekday_full_B", "weekday_full_C"], \
        f"月曜日は weekday_full_A/B/C が返されるべきです: {monday_patterns}"
    
    # 水曜日（weekday: 2）のテスト
    wednesday = "2026-01-07"
    wednesday_patterns = _get_available_patterns_for_day(wednesday, regular_employee)
    print(f"\n【水曜日】 {wednesday}")
    print(f"  正職員Aの利用可能パターン: {wednesday_patterns}")
    assert wednesday_patterns == ["wednesday_early", "wednesday_normal", "wednesday_late"], \
        f"水曜日は wednesday_early/normal/late が返されるべきです: {wednesday_patterns}"
    
    # 木曜日（weekday: 3）のテスト
    thursday = "2026-01-08"
    thursday_patterns = _get_available_patterns_for_day(thursday, regular_employee)
    print(f"\n【木曜日】 {thursday}")
    print(f"  正職員Aの利用可能パターン: {thursday_patterns}")
    assert thursday_patterns == ["thu_sat_1", "thu_sat_2", "thu_sat_3"], \
        f"木曜日は thu_sat_1/2/3 が返されるべきです: {thursday_patterns}"
    
    # パート職員（固定）のテスト
    part_patterns = _get_available_patterns_for_day(monday, part_employee)
    print(f"\n【パート職員B（固定）】")
    print(f"  利用可能パターン: {part_patterns}")
    assert part_patterns == ["part_morning"], \
        f"パート職員は固定パターンが返されるべきです: {part_patterns}"
    
    # パターン選択のテスト（偏り防止）
    print(f"\n【パターン選択（偏り防止）】")
    pattern_usage_count = {}
    
    # 6回選択して、使用回数が均等になることを確認
    selected_patterns = []
    for i in range(6):
        pattern = _select_best_pattern(
            regular_employee,
            monday,
            monday_patterns,
            pattern_usage_count
        )
        selected_patterns.append(pattern)
        
        # 選択後に使用回数を更新（実際のgenerate_shifts関数と同様）
        key = (regular_employee.id, pattern)
        pattern_usage_count[key] = pattern_usage_count.get(key, 0) + 1
        
        print(f"  {i+1}回目: {pattern} (現在の使用回数: {pattern_usage_count[key]}回)")
    
    # 各パターンが少なくとも1回は選ばれることを確認
    print(f"\n  選択されたパターン: {selected_patterns}")
    print(f"  最終的なパターン使用回数:")
    for pattern_id in ["weekday_full_A", "weekday_full_B", "weekday_full_C"]:
        count = pattern_usage_count.get((regular_employee.id, pattern_id), 0)
        print(f"    {pattern_id}: {count}回")
    
    # 偏りが少ないことを確認（最大と最小の差が1以下）
    counts = [pattern_usage_count.get((regular_employee.id, p), 0) for p in monday_patterns]
    max_count = max(counts)
    min_count = min(counts)
    assert max_count - min_count <= 1, \
        f"パターン使用回数の偏りが大きすぎます: max={max_count}, min={min_count}"
    
    print(f"\n  ✓ 偏りチェック: 最大{max_count}回 - 最小{min_count}回 = {max_count - min_count} (許容範囲: ≤1)")
    
    print("\n" + "=" * 60)
    print("✅ 全てのテストが成功しました！")
    print("=" * 60)
    print("\n【確認事項】")
    print("  ✓ 月曜日には weekday_full_A/B/C パターンが利用可能")
    print("  ✓ 水曜日には wednesday_early/normal/late パターンが利用可能")
    print("  ✓ 木曜日には thu_sat_1/2/3 パターンが利用可能")
    print("  ✓ パート職員は固定パターンが返される")
    print("  ✓ パターン選択時に使用回数の偏りが防止される")
    print("\n【実装完了】")
    print("  🎉 正職員の勤務パターン動的割り当て機能が正常に動作しています！")


if __name__ == "__main__":
    test_pattern_functions()
