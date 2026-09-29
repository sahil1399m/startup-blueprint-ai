"""Inspect ChromaDB SQLite schema and collection config."""
import sqlite3, json, sys

db = sqlite3.connect('C:/Users/SAHIL DESAI/OneDrive/Documents/hackthon/chroma_db/chroma.sqlite3')
db.row_factory = sqlite3.Row
cur = db.cursor()

# Get table names
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r['name'] for r in cur.fetchall()]
print('Tables:', tables)
print()

# Inspect collections table
cur.execute("SELECT * FROM collections LIMIT 10")
rows = cur.fetchall()
if rows:
    print('collections columns:', list(rows[0].keys()))
    for r in rows:
        print('  ID:', r['id'] if 'id' in r.keys() else '?',
              '| name:', r['name'] if 'name' in r.keys() else '?')
        d = dict(r)
        for k, v in d.items():
            if v is not None:
                print(f'    {k}: {str(v)[:200]}')
else:
    print('collections: EMPTY')
print()

# Check segments table  
if 'segments' in tables:
    cur.execute("SELECT * FROM segments LIMIT 10")
    rows = cur.fetchall()
    if rows:
        print('segments columns:', list(rows[0].keys()))
        for r in rows:
            d = dict(r)
            for k, v in d.items():
                if v is not None:
                    print(f'  {k}: {str(v)[:300]}')
            print()
    else:
        print('segments: EMPTY')

# Check collection_configuration_json or similar
if 'collection_configuration_json' in tables:
    cur.execute("SELECT * FROM collection_configuration_json LIMIT 5")
    rows = cur.fetchall()
    print('collection_configuration_json:', [dict(r) for r in rows])

# Check embeddings_queue or other tables
for t in tables:
    cur.execute(f"SELECT COUNT(*) as cnt FROM {t}")
    cnt = cur.fetchone()['cnt']
    print(f"  {t}: {cnt} rows")

db.close()
