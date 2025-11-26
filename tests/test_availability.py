import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / "src"))

from database import get_connection

conn = get_connection()
cursor = conn.cursor()

# 勤務可能情報の件数
cursor.execute("SELECT COUNT(*) as cnt FROM availability")
total = cursor.fetchone()['cnt']
print(f"勤務可能情報: {total}件")

# サンプルデータ
cursor.execute("SELECT * FROM availability LIMIT 10")
rows = cursor.fetchall()
for row in rows:
    print(f"  職員{row['employee_id']} 日付{row['date']} 時間帯{row['time_slot_id']} 可能={row['is_available']}")

# 勤務不可(is_available=0)の件数
cursor.execute("SELECT COUNT(*) as cnt FROM availability WHERE is_available = 0")
unavailable = cursor.fetchone()['cnt']
print(f"\n勤務不可: {unavailable}件")

conn.close()
