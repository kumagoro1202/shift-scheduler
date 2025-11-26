import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / "src"))

from optimizer import check_time_overlap

# 時間帯
time_slots = [
    {'name': '早番', 'start_time': '08:00', 'end_time': '16:00'},
    {'name': '日勤', 'start_time': '09:00', 'end_time': '17:00'},
    {'name': '遅番', 'start_time': '12:00', 'end_time': '20:00'},
    {'name': '夜勤', 'start_time': '20:00', 'end_time': '08:00'},
]

print("時間帯の重複チェック:")
for i, ts1 in enumerate(time_slots):
    for j, ts2 in enumerate(time_slots):
        if i < j:
            overlap = check_time_overlap(ts1, ts2)
            print(f"  {ts1['name']} と {ts2['name']}: {'重複あり' if overlap else '重複なし'}")
