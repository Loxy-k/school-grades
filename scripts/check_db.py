import sqlite3
import sys
from pathlib import Path

db_path = Path('db.sqlite3')
if not db_path.exists():
    print('db.sqlite3 not found at', db_path.resolve())
    sys.exit(1)

con = sqlite3.connect(str(db_path))
cur = con.cursor()

print('PRAGMA table_info(grades_student):')
for row in cur.execute("PRAGMA table_info('grades_student')"):
    print(row)

print('\nSchema for grades_student (CREATE):')
for row in cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='grades_student'"):
    print(row)

print('\nApplied migrations for app grades:')
for row in cur.execute("SELECT name, applied FROM (SELECT name, 1 as applied FROM django_migrations WHERE app='grades') ORDER BY name"):
    print(row)

con.close()
