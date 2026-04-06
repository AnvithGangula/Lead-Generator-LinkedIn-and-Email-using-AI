import sqlite3
from datetime import datetime
import os

# Create data directory if missing
if not os.path.exists("data"):
    os.makedirs("data")

DB_NAME = "data/fusionx_unified.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("PRAGMA foreign_keys = ON")

    # Prospects Table with all required columns
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            industry TEXT,
            linkedin TEXT,
            email TEXT,
            created_at TEXT
        )
    """
    )

    # Unified Messages Table for LinkedIn and Email
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER,
            channel TEXT, 
            stage TEXT,
            subject TEXT,
            content TEXT,
            status TEXT DEFAULT '0', 
            sent_at TEXT,
            next_followup TEXT,
            FOREIGN KEY(prospect_id) REFERENCES prospects(id)
        )
    """
    )
    conn.commit()
    conn.close()


def is_duplicate(name, company):
    conn = get_connection()
    exists = conn.execute(
        "SELECT id FROM prospects WHERE name = ? AND company = ?", (name, company)
    ).fetchone()
    conn.close()
    return exists is not None


def save_prospect_dual(
    name, company, industry, linkedin, email, li_seq=None, em_seq=None
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO prospects (name, company, industry, linkedin, email, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, company, industry, linkedin, email, datetime.now().strftime("%Y-%m-%d")),
    )

    # FIX: Changed p_id = cursor.lastrow_id to lastrowid
    p_id = cursor.lastrowid

    if li_seq:
        for stage, text in li_seq.items():
            cursor.execute(
                "INSERT INTO messages (prospect_id, channel, stage, content, status) VALUES (?, ?, ?, ?, ?)",
                (p_id, "linkedin", stage, text, "0"),
            )

    if em_seq:
        for i, step in enumerate(em_seq):
            cursor.execute(
                "INSERT INTO messages (prospect_id, channel, stage, subject, content, status) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    p_id,
                    "email",
                    step.get("label", f"Step {i+1}"),
                    step.get("sub", ""),
                    step.get("body", ""),
                    "0",
                ),
            )

    conn.commit()
    conn.close()


def update_message_status(msg_id, status, next_date=None):
    conn = get_connection()
    if next_date:
        conn.execute(
            "UPDATE messages SET status = ?, sent_at = ?, next_followup = ? WHERE id = ?",
            (status, datetime.now().strftime("%Y-%m-%d"), next_date, msg_id),
        )
    else:
        conn.execute(
            "UPDATE messages SET status = ?, sent_at = ? WHERE id = ?",
            (status, datetime.now().strftime("%Y-%m-%d"), msg_id),
        )
    conn.commit()
    conn.close()


def save_linkedin_only(name, company, industry, linkedin, li_seq):
    """Saves a prospect and their LinkedIn-specific sequence"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Insert or get Prospect
        cursor.execute(
            "INSERT OR IGNORE INTO prospects (name, company, industry, linkedin, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, company, industry, linkedin, datetime.now().strftime("%Y-%m-%d")),
        )

        # Get ID
        p_id = cursor.lastrowid
        if p_id == 0:
            existing = cursor.execute(
                "SELECT id FROM prospects WHERE name = ? AND company = ?",
                (name, company),
            ).fetchone()
            p_id = existing[0] if existing else None

        # 2. Insert LinkedIn Messages
        if p_id and li_seq:
            for stage, content in li_seq.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO messages (prospect_id, channel, stage, content, status) VALUES (?, ?, ?, ?, ?)",
                    (p_id, "linkedin", stage, content, "0"),
                )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def update_linkedin_status(msg_id, status="1"):
    try:
        conn = sqlite3.connect("data/fusionx_unified.db")
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Schedule next follow-up 3 days from now
        next_followup = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

        cursor.execute(
            """
            UPDATE messages 
            SET status = ?, sent_at = ?, next_followup = ?
            WHERE id = ?
            """,
            (status, now, next_followup, msg_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database Error: {e}")
        return False
