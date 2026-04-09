import sqlite3
import os
from datetime import datetime, timedelta


# Create data directory if missing
if not os.path.exists("data"):
    os.makedirs("data")

DB_NAME = "data/fusionx_unified.db"


def get_connection():
    import sqlite3

    conn = sqlite3.connect("data/fusionx_unified.db")
    # THIS IS THE KEY: It labels the data so you can use ['name']
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    # Updated Prospects Table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            industry TEXT,
            linkedin TEXT,
            email TEXT,
            created_at TEXT,
            UNIQUE(name, company) -- Final wall against duplicate people
        )
    """
    )

    # Updated Messages Table
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
            FOREIGN KEY(prospect_id) REFERENCES prospects(id),
            UNIQUE(prospect_id, channel, stage) -- Final wall against duplicate emails
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
    # FIXED: Strip markdown characters at save time
    name = name.strip().replace("*", "").replace("_", "").strip() if name else name
    company = (
        company.strip().replace("*", "").replace("_", "").strip()
        if company
        else company
    )

    conn = get_connection()
    cursor = conn.cursor()
    # ... rest of function unchanged

    try:
        # Use OR IGNORE to skip duplicates without throwing an error
        cursor.execute(
            "INSERT OR IGNORE INTO prospects (name, company, industry, linkedin, email, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                name,
                company,
                industry,
                linkedin,
                email,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

        # Get the ID (lastrowid will be 0 if the row was ignored)
        p_id = cursor.lastrowid

        # If p_id is 0, it means it was a duplicate and ignored.
        # We fetch the existing ID to ensure we don't duplicate messages either.
        if p_id == 0:
            existing = cursor.execute(
                "SELECT id FROM prospects WHERE name = ? AND company = ?",
                (name, company),
            ).fetchone()
            p_id = existing[0] if existing else None

        # Proceed with messages only if we have a valid p_id
        if p_id:
            # --- SAVE EMAIL MESSAGES ---
            if em_seq:
                for i, step in enumerate(em_seq):
                    db_stage = "Initial" if i == 0 else f"Follow-up {i}"
                    cursor.execute(
                        "INSERT OR IGNORE INTO messages (prospect_id, channel, stage, subject, content, status) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            p_id,
                            "email",
                            db_stage,
                            step.get("sub", ""),
                            step.get("body", ""),
                            "0",
                        ),
                    )

            # --- SAVE LINKEDIN MESSAGES ---
            if li_seq:
                for stage, content in li_seq.items():
                    cursor.execute(
                        "INSERT OR IGNORE INTO messages (prospect_id, channel, stage, content, status) VALUES (?, ?, ?, ?, ?)",
                        (p_id, "linkedin", stage, content, "0"),
                    )

        conn.commit()
    except sqlite3.Error as e:
        # This handles other database errors like 'database is locked' gracefully
        print(f"Database error: {e}")
    finally:
        conn.close()


def update_message_status(msg_id, status, next_date=None):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get the message channel to apply correct cooldown
    msg_info = conn.execute(
        "SELECT channel, prospect_id FROM messages WHERE id = ?", (msg_id,)
    ).fetchone()

    if not msg_info:
        conn.close()
        return False

    channel = msg_info["channel"]
    prospect_id = msg_info["prospect_id"]

    # Get cooldown settings
    li_cooldown, email_cooldown = get_cooldown_settings()

    # Calculate next followup date based on channel
    if channel == "linkedin":
        next_followup = (datetime.now() + timedelta(days=li_cooldown)).strftime(
            "%Y-%m-%d"
        )
    else:  # email
        next_followup = (datetime.now() + timedelta(days=email_cooldown)).strftime(
            "%Y-%m-%d"
        )

    # Update the sent message
    conn.execute(
        "UPDATE messages SET status = ?, sent_at = ? WHERE id = ?",
        (status, now, msg_id),
    )

    # Update next_followup for the next unsent message
    conn.execute(
        """
        UPDATE messages SET next_followup = ?
        WHERE id = (
            SELECT m2.id FROM messages m2
            WHERE m2.prospect_id = ?
            AND m2.channel = ?
            AND m2.status = '0'
            ORDER BY m2.id ASC
            LIMIT 1
        )
        """,
        (next_followup, prospect_id, channel),
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
            (
                name,
                company,
                industry,
                linkedin,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
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

        # Get cooldown setting
        li_cooldown, _ = get_cooldown_settings()

        # Schedule next follow-up based on cooldown setting
        next_followup = (datetime.now() + timedelta(days=li_cooldown)).strftime(
            "%Y-%m-%d"
        )

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


def get_cooldown_settings():
    """Get cooldown settings from database"""
    try:
        conn = sqlite3.connect("data/fusionx_unified.db")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )

        # Get LinkedIn cooldown (default 3 days)
        li_cooldown = conn.execute(
            "SELECT value FROM settings WHERE key='linkedin_cooldown_days'"
        ).fetchone()
        li_cooldown = int(li_cooldown[0]) if li_cooldown else 3

        # Get Email cooldown (default 7 days)
        email_cooldown = conn.execute(
            "SELECT value FROM settings WHERE key='email_cooldown_days'"
        ).fetchone()
        email_cooldown = int(email_cooldown[0]) if email_cooldown else 7

        conn.close()
        return li_cooldown, email_cooldown
    except:
        return 3, 7


def update_cooldown_settings(linkedin_days=None, email_days=None):
    """Update cooldown settings"""
    try:
        conn = sqlite3.connect("data/fusionx_unified.db")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )

        if linkedin_days is not None:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('linkedin_cooldown_days', ?)",
                (str(linkedin_days),),
            )

        if email_days is not None:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('email_cooldown_days', ?)",
                (str(email_days),),
            )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating cooldown settings: {e}")
        return False


# Add these functions to your existing database.py (don't modify existing functions)


def get_cooldown_settings():
    """Get cooldown settings from database - creates default if not exists"""
    try:
        conn = sqlite3.connect("data/fusionx_unified.db")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )

        # Get LinkedIn cooldown (default 3 days)
        li_cooldown = conn.execute(
            "SELECT value FROM settings WHERE key='linkedin_cooldown_days'"
        ).fetchone()
        li_cooldown = int(li_cooldown[0]) if li_cooldown else 3

        # Get Email cooldown (default 7 days)
        email_cooldown = conn.execute(
            "SELECT value FROM settings WHERE key='email_cooldown_days'"
        ).fetchone()
        email_cooldown = int(email_cooldown[0]) if email_cooldown else 7

        conn.close()
        return li_cooldown, email_cooldown
    except Exception as e:
        print(f"Error getting cooldown settings: {e}")
        return 3, 7


def update_cooldown_settings(linkedin_days=None, email_days=None):
    """Update cooldown settings"""
    try:
        conn = sqlite3.connect("data/fusionx_unified.db")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )

        if linkedin_days is not None:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('linkedin_cooldown_days', ?)",
                (str(linkedin_days),),
            )

        if email_days is not None:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('email_cooldown_days', ?)",
                (str(email_days),),
            )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating cooldown settings: {e}")
        return False
