import sqlite3
import os
from datetime import datetime

DB_PATH = "data/fusionx_crm.db"

def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Updated prospects table to include linkedin column
    c.execute('''CREATE TABLE IF NOT EXISTS prospects
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, company TEXT, industry TEXT, linkedin TEXT,
                  UNIQUE(name, company))''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  prospect_id INTEGER, stage TEXT, content TEXT, 
                  status INTEGER DEFAULT 0, sent_at TEXT,
                  FOREIGN KEY(prospect_id) REFERENCES prospects(id))''')

    # Migration: Check for missing columns in prospects (linkedin)
    c.execute("PRAGMA table_info(prospects)")
    prospect_cols = [col[1] for col in c.fetchall()]
    if 'linkedin' not in prospect_cols:
        c.execute("ALTER TABLE prospects ADD COLUMN linkedin TEXT")

    # Migration: Check for missing columns in messages (status, sent_at)
    c.execute("PRAGMA table_info(messages)")
    message_cols = [col[1] for col in c.fetchall()]
    if 'status' not in message_cols:
        c.execute("ALTER TABLE messages ADD COLUMN status INTEGER DEFAULT 0")
    if 'sent_at' not in message_cols:
        c.execute("ALTER TABLE messages ADD COLUMN sent_at TEXT")
    
    conn.commit()
    conn.close()

def update_message_status(msg_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status else None
    # Explicitly cast msg_id to int to avoid query errors
    c.execute("UPDATE messages SET status = ?, sent_at = ? WHERE id = ?", (status, timestamp, int(msg_id)))
    conn.commit()
    conn.close()

def is_duplicate(name, company):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM prospects WHERE name = ? AND company = ?", (name, company))
    res = c.fetchone()
    conn.close()
    return res is not None

def save_full_sequence(name, company, industry, linkedin, sequence_dict):
    """Saves a new prospect and their 8-part message sequence"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Added linkedin to the insert statement
        c.execute("INSERT INTO prospects (name, company, industry, linkedin) VALUES (?, ?, ?, ?)", 
                  (name, company, industry, linkedin))
        p_id = c.lastrowid
        for stage, content in sequence_dict.items():
            c.execute("INSERT INTO messages (prospect_id, stage, content) VALUES (?, ?, ?)",
                      (p_id, stage, content))
        conn.commit()
    except sqlite3.IntegrityError:
        pass 
    conn.close()