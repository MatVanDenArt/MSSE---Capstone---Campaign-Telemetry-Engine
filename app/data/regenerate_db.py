import sqlite3
import os

DB_PATH = 'capstone.db'
SEED_FILE = 'seed.sql'

def regenerate():
    # If the database exists, remove it to start completely fresh
    if os.path.exists(DB_PATH):
        print(f"Removing old {DB_PATH}...")
        os.remove(DB_PATH)
    
    print(f"Connecting to new {DB_PATH} and reading {SEED_FILE}...")
    conn = sqlite3.connect(DB_PATH)
    
    with open(SEED_FILE, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    print("Executing SQL dump... This might take a few seconds.")
    conn.executescript(sql)
    
    print("Database regeneration complete!")
    
if __name__ == "__main__":
    regenerate()
