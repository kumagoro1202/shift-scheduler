"""
V3.0 勤務可否判定のテスト
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from availability_checker import is_employee_available, get_unavailable_reason
from database import (
    init_database,
    create_employee,
    add_absence,
    get_all_time_slots,
    init_employment_patterns_table,
    init_fixed_time_slots,
    init_employee_absences_table,
    add_employment_pattern_to_employees
)


def setup_test_environment():
    """テスト環境をセットアップ"""
    print("🔧 テスト環境をセットアップ中...")
    
    # データベース初期化
    init_database()
    init_employment_patterns_table()
    init_employee_absences_table()
    add_employment_pattern_to_employees()
    init_fixed_time_slots()
    
    print("✅ セットアップ完了")


def test_full_day_absence():
    """終日休暇のテスト"""
    print("\n📝 Test 1: 終日休暇のテスト")
    
    emp_id = create_employee(
        name="テスト職員1",
        employment_pattern_id="full_early"
    )
    
    employee = {'id': emp_id, 'employment_pattern_id': 'full_early'}
    
    # 終日休暇登録（2025-12-02は月曜日）
    add_absence(emp_id, "2025-12-02", "full_day", "テスト休暇")
    
    time_slots = get_all_time_slots()
    
    # 月曜日の午前・午後で勤務不可のはず
    for ts in time_slots:
        if ts['day_of_week'] == 0:  # 月曜日
            result = is_employee_available(employee, "2025-12-02", ts)
            reason = get_unavailable_reason(employee, "2025-12-02", ts)
            
            if result:
                print(f"  ❌ FAIL: {ts['display_name']} - 勤務可能になっている（期待: 不可）")
                return False
            else:
                print(f"  ✅ PASS: {ts['display_name']} - 勤務不可 ({reason})")
    
    print("✅ Test 1: 完了")
    return True


def test_morning_absence():
    """午前休のテスト"""
    print("\n📝 Test 2: 午前休のテスト")
    
    emp_id = create_employee(
        name="テスト職員2",
        employment_pattern_id="full_mid"
    )
    
    employee = {'id': emp_id, 'employment_pattern_id': 'full_mid'}
    
    # 午前休登録（2025-12-03は火曜日）
    add_absence(emp_id, "2025-12-03", "morning", "通院")
    
    time_slots = get_all_time_slots()
    
    # 火曜日の午前は不可、午後は可のはず
    for ts in time_slots:
        if ts['day_of_week'] == 1:  # 火曜日
            result = is_employee_available(employee, "2025-12-03", ts)
            reason = get_unavailable_reason(employee, "2025-12-03", ts)
            
            if ts['period'] == 'morning':
                if result:
                    print(f"  ❌ FAIL: {ts['display_name']} - 勤務可能になっている（期待: 不可）")
                    return False
                else:
                    print(f"  ✅ PASS: {ts['display_name']} - 勤務不可 ({reason})")
            else:  # afternoon
                if not result:
                    print(f"  ❌ FAIL: {ts['display_name']} - 勤務不可になっている（期待: 可）, 理由: {reason}")
                    return False
                else:
                    print(f"  ✅ PASS: {ts['display_name']} - 勤務可能")
    
    print("✅ Test 2: 完了")
    return True


def test_afternoon_absence():
    """午後休のテスト"""
    print("\n📝 Test 3: 午後休のテスト")
    
    emp_id = create_employee(
        name="テスト職員3",
        employment_pattern_id="full_late"
    )
    
    employee = {'id': emp_id, 'employment_pattern_id': 'full_late'}
    
    # 午後休登録（2025-12-04は水曜日）
    add_absence(emp_id, "2025-12-04", "afternoon", "私用")
    
    time_slots = get_all_time_slots()
    
    # 水曜日の午前は可、午後は不可のはず
    for ts in time_slots:
        if ts['day_of_week'] == 2:  # 水曜日
            result = is_employee_available(employee, "2025-12-04", ts)
            reason = get_unavailable_reason(employee, "2025-12-04", ts)
            
            if ts['period'] == 'afternoon':
                if result:
                    print(f"  ❌ FAIL: {ts['display_name']} - 勤務可能になっている（期待: 不可）")
                    return False
                else:
                    print(f"  ✅ PASS: {ts['display_name']} - 勤務不可 ({reason})")
            else:  # morning
                if not result:
                    print(f"  ❌ FAIL: {ts['display_name']} - 勤務不可になっている（期待: 可）, 理由: {reason}")
                    return False
                else:
                    print(f"  ✅ PASS: {ts['display_name']} - 勤務可能")
    
    print("✅ Test 3: 完了")
    return True


def test_part_time_afternoon():
    """パート職員の午後勤務不可テスト"""
    print("\n📝 Test 4: パート職員の午後勤務不可テスト")
    
    emp_id = create_employee(
        name="テスト職員4",
        employment_pattern_id="part_morning"
    )
    
    employee = {'id': emp_id, 'employment_pattern_id': 'part_morning'}
    
    time_slots = get_all_time_slots()
    
    # パート午前職員は午後勤務不可のはず
    for ts in time_slots:
        # 月曜日でテスト
        if ts['day_of_week'] == 0:
            result = is_employee_available(employee, "2025-12-01", ts)
            reason = get_unavailable_reason(employee, "2025-12-01", ts)
            
            if ts['period'] == 'afternoon':
                if result:
                    print(f"  ❌ FAIL: {ts['display_name']} - 勤務可能になっている（期待: 不可）")
                    return False
                else:
                    print(f"  ✅ PASS: {ts['display_name']} - 勤務不可 ({reason})")
            else:  # morning
                if not result:
                    print(f"  ❌ FAIL: {ts['display_name']} - 勤務不可になっている（期待: 可）, 理由: {reason}")
                    return False
                else:
                    print(f"  ✅ PASS: {ts['display_name']} - 勤務可能")
    
    print("✅ Test 4: 完了")
    return True


def test_short_time():
    """時短勤務職員の午後勤務不可テスト"""
    print("\n📝 Test 5: 時短勤務職員の午後勤務不可テスト")
    
    emp_id = create_employee(
        name="テスト職員5",
        employment_pattern_id="short_time"
    )
    
    employee = {'id': emp_id, 'employment_pattern_id': 'short_time'}
    
    time_slots = get_all_time_slots()
    
    # 時短勤務は午後勤務不可のはず
    for ts in time_slots:
        if ts['day_of_week'] == 0:  # 月曜日
            result = is_employee_available(employee, "2025-12-01", ts)
            reason = get_unavailable_reason(employee, "2025-12-01", ts)
            
            if ts['period'] == 'afternoon':
                if result:
                    print(f"  ❌ FAIL: {ts['display_name']} - 勤務可能になっている（期待: 不可）")
                    return False
                else:
                    print(f"  ✅ PASS: {ts['display_name']} - 勤務不可 ({reason})")
            else:  # morning
                if not result:
                    print(f"  ❌ FAIL: {ts['display_name']} - 勤務不可になっている（期待: 可）, 理由: {reason}")
                    return False
                else:
                    print(f"  ✅ PASS: {ts['display_name']} - 勤務可能")
    
    print("✅ Test 5: 完了")
    return True


def test_sunday():
    """日曜日は全員勤務不可のテスト"""
    print("\n📝 Test 6: 日曜日は全員勤務不可のテスト")
    
    emp_id = create_employee(
        name="テスト職員6",
        employment_pattern_id="full_early"
    )
    
    employee = {'id': emp_id, 'employment_pattern_id': 'full_early'}
    
    # 2025-12-07は日曜日
    time_slots = get_all_time_slots()
    
    for ts in time_slots:
        result = is_employee_available(employee, "2025-12-07", ts)
        reason = get_unavailable_reason(employee, "2025-12-07", ts)
        
        if result:
            print(f"  ❌ FAIL: {ts['display_name']} - 日曜日なのに勤務可能になっている")
            return False
        else:
            print(f"  ✅ PASS: {ts['display_name']} - 勤務不可 ({reason})")
    
    print("✅ Test 6: 完了")
    return True


def main():
    """テスト実行"""
    print("=" * 60)
    print("V3.0 勤務可否判定テスト")
    print("=" * 60)
    
    setup_test_environment()
    
    results = []
    
    results.append(test_full_day_absence())
    results.append(test_morning_absence())
    results.append(test_afternoon_absence())
    results.append(test_part_time_afternoon())
    results.append(test_short_time())
    results.append(test_sunday())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ 全テスト合格")
    else:
        print("❌ 一部のテストが失敗しました")
    print("=" * 60)


if __name__ == "__main__":
    main()
