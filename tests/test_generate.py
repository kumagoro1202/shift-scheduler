import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / "src"))

from database import get_all_employees, get_all_time_slots, is_employee_available
from optimizer import generate_shift

employees = get_all_employees()
time_slots = get_all_time_slots()

print("デバッグ: 2025-12-01の各時間帯で勤務可能な職員")
for ts in time_slots:
    available = []
    for emp in employees:
        if is_employee_available(emp['id'], "2025-12-01", ts['id']):
            available.append(emp['name'])
    print(f"  {ts['name']}: {len(available)}名 ({', '.join(available)})")
    print(f"    必要人数: {ts['required_employees']}名")

print("\n実際にシフト生成...")
result = generate_shift(
    employees=employees,
    time_slots=time_slots,
    start_date="2025-12-01",
    end_date="2025-12-01",
    availability_func=is_employee_available
)

if result:
    print(f"\n✅ 成功: {len(result)}件")
    for shift in result:
        print(f"  {shift['time_slot_name']}: {shift['employee_name']}")
else:
    print("\n❌ 失敗")
