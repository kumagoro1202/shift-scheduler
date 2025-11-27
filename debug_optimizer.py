"""オプティマイザーのデバッグ"""
from src.database import get_all_employees, get_all_time_slots, init_database, is_employee_available
from src.optimizer import generate_shift

init_database()

employees = get_all_employees()
time_slots = get_all_time_slots()

print(f'職員数: {len(employees)}')
print(f'時間帯数: {len(time_slots)}')

# シフト生成をテスト
result = generate_shift(
    employees=employees,
    time_slots=time_slots,
    start_date="2025-11-01",
    end_date="2025-11-03",  # まず3日間でテスト
    availability_func=is_employee_available
)

if result:
    print(f"\n生成されたシフト数: {len(result)}")
    for shift in result[:10]:  # 最初の10件を表示
        print(f"{shift['date']} {shift['time_slot_name']}: {shift['employee_name']}")
else:
    print("\nシフト生成に失敗しました")
