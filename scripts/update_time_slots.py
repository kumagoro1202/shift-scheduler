"""
時間帯を午前・午後・1日通しの3つに変更するスクリプト
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from database import get_connection

conn = get_connection()
cursor = conn.cursor()

# 既存データを削除
cursor.execute('DELETE FROM time_slots')
cursor.execute('DELETE FROM shifts')
cursor.execute('DELETE FROM availability')
conn.commit()

# 新しい時間帯を追加
time_slots = [
    ('午前', '08:00', '12:00', 2),
    ('午後', '13:00', '17:00', 2),
    ('1日通し', '08:00', '17:00', 1),
]

for name, start_time, end_time, required_employees in time_slots:
    cursor.execute('''
        INSERT INTO time_slots (name, start_time, end_time, required_employees)
        VALUES (?, ?, ?, ?)
    ''', (name, start_time, end_time, required_employees))

conn.commit()

# 確認
cursor.execute('SELECT * FROM time_slots')
rows = cursor.fetchall()

print('✅ 時間帯を更新しました:')
for row in rows:
    print(f"  {row['name']} ({row['start_time']}-{row['end_time']}): 必要{row['required_employees']}名")

conn.close()
