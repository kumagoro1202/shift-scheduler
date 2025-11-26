import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / "src"))

from database import get_all_time_slots, get_all_employees

ts = get_all_time_slots()
emps = get_all_employees()

total = sum(t['required_employees'] for t in ts)
print(f'職員数: {len(emps)}名')
print(f'1日あたりの必要人数合計: {total}名')
print()
for t in ts:
    print(f'  {t["name"]}: {t["required_employees"]}名')

print()
if total > len(emps):
    print(f"⚠️ 警告: 1日あたりの必要人数({total}名)が職員数({len(emps)}名)より多いです")
    print("   → 1人が1日に複数シフトに入る必要があります")
else:
    print(f"✅ OK: 職員数({len(emps)}名)で対応可能です")
