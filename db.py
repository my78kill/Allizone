import sqlite3

conn = sqlite3.connect("packs.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS packs (
    name TEXT UNIQUE
)
""")

conn.commit()
