import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / "src"))

from database import get_all_time_slots, get_all_employees

ts = get_all_time_slots()
print('時間帯一覧:')
for t in ts:
    print(f'ID:{t["id"]} {t["name"]} ({t["start_time"]}-{t["end_time"]}) 必要{t["required_employees"]}名')

print()

emps = get_all_employees()
print(f'職員一覧: {len(emps)}名')
for e in emps:
    print(f'ID:{e["id"]} {e["name"]} スキル{e["skill_score"]}')
