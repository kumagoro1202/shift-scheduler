"""データベースの状態を確認"""
from src.database import get_all_employees, get_all_time_slots, init_database

init_database()

print('=== 職員一覧 ===')
employees = get_all_employees()
print(f'職員数: {len(employees)}')
for e in employees:
    print(f'{e["id"]}: {e["name"]} (スキル:{e["skill_score"]})')

print('\n=== 時間帯一覧 ===')
time_slots = get_all_time_slots()
print(f'時間帯数: {len(time_slots)}')
for ts in time_slots:
    print(f'{ts["id"]}: {ts["name"]} ({ts["start_time"]}-{ts["end_time"]}) 必要人数:{ts["required_employees"]}')
