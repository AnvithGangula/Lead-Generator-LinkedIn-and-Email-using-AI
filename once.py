import sqlite3, hashlib

conn = sqlite3.connect("data/fusionx_unified.db")

password = hashlib.sha256("admin123".encode()).hexdigest()

conn.execute(
    """
INSERT INTO users (full_name, email, password, role)
VALUES (?, ?, ?, ?)
""",
    ("Anvith", "admin@gmail.com", password, "admin"),
)

conn.commit()
conn.close()

print("✅ Admin created!")
