import sqlite3

conn = sqlite3.connect('./nextgen_fusion.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Existing tables:')
for row in tables:
    print(row[0])
conn.close()