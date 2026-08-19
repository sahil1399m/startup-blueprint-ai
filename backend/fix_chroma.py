import sqlite3
import json

conn = sqlite3.connect('chroma_db/chroma.sqlite3')
cur = conn.cursor()

# Get all collections
cur.execute('SELECT id, name, config_json_str FROM collections')
rows = cur.fetchall()

for row in rows:
    id, name, config_json_str = row
    config = json.loads(config_json_str) if config_json_str else {}
    if '_type' not in config:
        config['_type'] = 'CollectionConfigurationInternal'
    
    cur.execute('UPDATE collections SET config_json_str = ? WHERE id = ?', (json.dumps(config), id))

conn.commit()
conn.close()
print("ChromaDB sqlite fixed.")
