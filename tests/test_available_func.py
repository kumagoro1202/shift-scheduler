import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / "src"))

from database import is_employee_available

# テスト
print("2025-11-01のチェック:")
result1 = is_employee_available(1, "2025-11-01", 1)
print(f"  職員1, 2025-11-01, 時間帯1: {result1}")

print("\n2025-12-01のチェック:")
result2 = is_employee_available(1, "2025-12-01", 1)
print(f"  職員1, 2025-12-01, 時間帯1: {result2}")

print("\n2025-12-01のチェック(全職員・全時間帯):")
for emp_id in range(1, 6):
    for ts_id in range(1, 5):
        result = is_employee_available(emp_id, "2025-12-01", ts_id)
        if not result:
            print(f"  職員{emp_id}, 時間帯{ts_id}: {result}")

# 勤務可能な職員のカウント
available_count = 0
for emp_id in range(1, 6):
    for ts_id in range(1, 5):
        if is_employee_available(emp_id, "2025-12-01", ts_id):
            available_count += 1

print(f"\n合計: {available_count}件が勤務可能")
