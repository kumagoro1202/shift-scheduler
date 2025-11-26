import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / "src"))

from database import (
    get_all_employees, 
    get_all_time_slots, 
    is_employee_available,
    create_shift,
    delete_shifts_by_date_range
)
from optimizer import generate_shift

employees = get_all_employees()
time_slots = get_all_time_slots()

print("=== シフト生成と保存のテスト ===\n")

# 既存シフトを削除
deleted = delete_shifts_by_date_range("2025-12-01", "2025-12-03")
print(f"削除: {deleted}件\n")

# シフト生成
result = generate_shift(
    employees=employees,
    time_slots=time_slots,
    start_date="2025-12-01",
    end_date="2025-12-03",
    availability_func=is_employee_available
)

if result:
    print(f"\n生成されたシフト: {len(result)}件\n")
    
    # データベースに保存
    success_count = 0
    failed_count = 0
    
    for i, shift in enumerate(result, 1):
        print(f"{i}. {shift['date']} {shift['time_slot_name']} - {shift['employee_name']} (職員ID:{shift['employee_id']}, 時間帯ID:{shift['time_slot_id']})")
        
        shift_id = create_shift(
            shift['date'],
            shift['time_slot_id'],
            shift['employee_id']
        )
        
        if shift_id:
            print(f"   ✅ 保存成功 (ID: {shift_id})")
            success_count += 1
        else:
            print(f"   ❌ 保存失敗")
            failed_count += 1
    
    print(f"\n結果: 成功{success_count}件, 失敗{failed_count}件")
else:
    print("❌ シフト生成失敗")
