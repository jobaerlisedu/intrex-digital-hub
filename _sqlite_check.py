import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
for t in tables:
    cnt = cursor.execute(f'SELECT COUNT(*) FROM "{t[0]}"').fetchone()[0]
    print(f'{t[0]:45s} {cnt} rows')
conn.close()
