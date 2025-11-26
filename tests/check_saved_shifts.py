import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / "src"))

from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute('''
    SELECT s.date, t.name, e.name 
    FROM shifts s 
    JOIN time_slots t ON s.time_slot_id = t.id 
    JOIN employees e ON s.employee_id = e.id 
    ORDER BY s.date, t.start_time
''')

rows = cursor.fetchall()
print(f'保存されているシフト: {len(rows)}件\n')

for row in rows:
    print(f"{row[0]} {row[1]}: {row[2]}")

conn.close()
