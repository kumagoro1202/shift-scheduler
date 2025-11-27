"""
V2.0 機能テストスクリプト
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import (
    get_all_employees,
    get_all_time_slots,
    get_all_work_patterns,
    create_employee,
    create_time_slot
)
from migration import get_db_version, check_migration_needed


def test_database_migration():
    """データベースマイグレーションのテスト"""
    print("=" * 60)
    print("データベースマイグレーションテスト")
    print("=" * 60)
    
    version = get_db_version()
    print(f"✓ データベースバージョン: {version}")
    
    if version == '2.0':
        print("✓ V2.0にマイグレーション済み")
    else:
        print("✗ マイグレーションが必要")
        return False
    
    print()
    return True


def test_work_patterns():
    """勤務パターンテスト"""
    print("=" * 60)
    print("勤務パターンテスト")
    print("=" * 60)
    
    patterns = get_all_work_patterns()
    print(f"✓ 勤務パターン数: {len(patterns)}")
    
    if len(patterns) < 6:
        print("✗ 勤務パターンが不足しています")
        return False
    
    for p in patterns:
        print(f"  - {p['id']}: {p['name']} ({p['work_type']})")
    
    print()
    return True


def test_employee_v2_fields():
    """職員V2フィールドテスト"""
    print("=" * 60)
    print("職員V2フィールドテスト")
    print("=" * 60)
    
    employees = get_all_employees()
    
    if not employees:
        print("⚠ 職員が登録されていません（テストスキップ）")
        print()
        return True
    
    print(f"✓ 職員数: {len(employees)}")
    
    # V2フィールドの存在確認
    v2_fields = [
        'employee_type', 'employment_type', 'work_type', 'work_pattern',
        'skill_reha_room', 'skill_reception_am', 'skill_reception_pm', 'skill_flexibility'
    ]
    
    emp = employees[0]
    missing_fields = []
    
    for field in v2_fields:
        if field not in emp:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"✗ 不足フィールド: {', '.join(missing_fields)}")
        return False
    
    print("✓ すべてのV2フィールドが存在します")
    
    # サンプル職員の表示
    for emp in employees[:3]:
        print(f"\n  {emp['name']}:")
        print(f"    タイプ: {emp.get('employee_type', 'N/A')}")
        print(f"    雇用形態: {emp.get('employment_type', 'N/A')}")
        print(f"    勤務形態: {emp.get('work_type', 'N/A')}")
        print(f"    スキル: リハ室={emp.get('skill_reha_room', 0)}, " +
              f"受付AM={emp.get('skill_reception_am', 0)}, " +
              f"受付PM={emp.get('skill_reception_pm', 0)}, " +
              f"総合={emp.get('skill_flexibility', 0)}")
    
    print()
    return True


def test_timeslot_v2_fields():
    """時間帯V2フィールドテスト"""
    print("=" * 60)
    print("時間帯V2フィールドテスト")
    print("=" * 60)
    
    time_slots = get_all_time_slots()
    
    if not time_slots:
        print("⚠ 時間帯が登録されていません（テストスキップ）")
        print()
        return True
    
    print(f"✓ 時間帯数: {len(time_slots)}")
    
    # V2フィールドの存在確認
    v2_fields = [
        'area_type', 'time_period', 'required_employees_min', 'required_employees_max',
        'target_skill_score', 'skill_weight'
    ]
    
    ts = time_slots[0]
    missing_fields = []
    
    for field in v2_fields:
        if field not in ts:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"✗ 不足フィールド: {', '.join(missing_fields)}")
        return False
    
    print("✓ すべてのV2フィールドが存在します")
    
    # サンプル時間帯の表示
    for ts in time_slots[:3]:
        print(f"\n  {ts['name']}:")
        print(f"    エリア: {ts.get('area_type', 'N/A')}")
        print(f"    時間区分: {ts.get('time_period', 'N/A')}")
        print(f"    必要人数: {ts.get('required_employees_min', 0)}〜{ts.get('required_employees_max', 0)}名")
        print(f"    目標スキル: {ts.get('target_skill_score', 0)}")
        print(f"    重み: {ts.get('skill_weight', 1.0)}")
    
    print()
    return True


def test_optimizer_v2_import():
    """V2最適化エンジンインポートテスト"""
    print("=" * 60)
    print("V2最適化エンジンインポートテスト")
    print("=" * 60)
    
    try:
        from optimizer_v2 import (
            generate_shift_v2,
            calculate_skill_score,
            can_assign_to_area,
            calculate_skill_balance_v2
        )
        print("✓ optimizer_v2モジュールのインポート成功")
        
        # 関数の存在確認
        assert callable(generate_shift_v2), "generate_shift_v2が呼び出し可能でない"
        assert callable(calculate_skill_score), "calculate_skill_scoreが呼び出し可能でない"
        assert callable(can_assign_to_area), "can_assign_to_areaが呼び出し可能でない"
        assert callable(calculate_skill_balance_v2), "calculate_skill_balance_v2が呼び出し可能でない"
        
        print("✓ すべての関数が正常にインポートされました")
        print()
        return True
        
    except Exception as e:
        print(f"✗ インポートエラー: {e}")
        print()
        return False


def run_all_tests():
    """すべてのテストを実行"""
    print("\n")
    print("*" * 60)
    print("シフト管理システム V2.0 機能テスト")
    print("*" * 60)
    print("\n")
    
    tests = [
        ("データベースマイグレーション", test_database_migration),
        ("勤務パターン", test_work_patterns),
        ("職員V2フィールド", test_employee_v2_fields),
        ("時間帯V2フィールド", test_timeslot_v2_fields),
        ("V2最適化エンジン", test_optimizer_v2_import)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name}でエラー発生: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 結果サマリ
    print("\n")
    print("=" * 60)
    print("テスト結果サマリ")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"合計: {len(results)}件のテスト")
    print(f"成功: {passed}件")
    print(f"失敗: {failed}件")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓✓✓ すべてのテストが成功しました！ ✓✓✓\n")
        return True
    else:
        print(f"\n✗✗✗ {failed}件のテストが失敗しました ✗✗✗\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
