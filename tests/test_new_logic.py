import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / "src"))

from database import get_all_employees, get_all_time_slots, is_employee_available
from optimizer import generate_shift

employees = get_all_employees()
time_slots = get_all_time_slots()

print("時間帯情報:")
for ts in time_slots:
    print(f"  {ts['name']}: {ts['start_time']}-{ts['end_time']} (必要{ts['required_employees']}名)")

print(f"\n職員: {len(employees)}名")

print("\n=== シフト生成テスト ===\n")

result = generate_shift(
    employees=employees,
    time_slots=time_slots,
    start_date="2025-12-01",
    end_date="2025-12-03",
    availability_func=is_employee_available
)

if result:
    print(f"\n✅ 成功: {len(result)}件のシフトが生成されました\n")
    
    # 日付ごとに表示
    from collections import defaultdict
    by_date = defaultdict(list)
    for shift in result:
        by_date[shift['date']].append(shift)
    
    for date in sorted(by_date.keys()):
        print(f"{date}:")
        for shift in sorted(by_date[date], key=lambda s: s['start_time']):
            print(f"  {shift['time_slot_name']}: {shift['employee_name']} (スキル{shift['skill_score']})")
        
        # この日の各時間帯の人数を確認
        morning_count = sum(1 for s in by_date[date] if '午前' in s['time_slot_name'] or '1日' in s['time_slot_name'])
        afternoon_count = sum(1 for s in by_date[date] if '午後' in s['time_slot_name'] or '1日' in s['time_slot_name'])
        print(f"  → 午前: {morning_count}名, 午後: {afternoon_count}名")
        print()
else:
    print("\n❌ シフト生成に失敗しました")
