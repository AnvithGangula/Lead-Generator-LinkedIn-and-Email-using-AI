# auth.py
import streamlit as st
import sqlite3
import hashlib
import os

DB_PATH = "data/fusionx_unified.db"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_auth():
    """Create users table and default admin if not exists"""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    # Create default admin account if no users exist
    existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing == 0:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            ("admin", hash_password("dvk@2024"), "DVK Admin", "admin"),
        )
        conn.commit()
    conn.close()


def verify_login(username: str, password: str):
    """Returns user dict if valid, None if invalid"""
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute(
        "SELECT id, username, full_name, role FROM users WHERE username=? AND password_hash=?",
        (username, hash_password(password)),
    ).fetchone()
    conn.close()
    if user:
        return {
            "id": user[0],
            "username": user[1],
            "full_name": user[2],
            "role": user[3],
        }
    return None


def add_user(username: str, password: str, full_name: str, role: str = "user"):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), full_name, role),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists


def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    df_users = conn.execute(
        "SELECT id, username, full_name, role, created_at FROM users"
    ).fetchall()
    conn.close()
    return df_users


def delete_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


def show_login_page():
    import sqlite3, hashlib
    import streamlit as st

    # --- Page Styling (Light Theme) ---
    st.markdown(
        """
    <style>
        /* Main background */
        .stApp { 
            background-color: #f7f9fc; 
        }
        
        /* The Login Card */
        [data-testid="stVerticalBlock"] > div:has(div.login-logo) {
            background: white;
            padding: 40px;
            border-radius: 20px;
            border: 1px solid #e1e8f0;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            max-width: 650px; 
            margin: 0 auto;
        }
        
        /* Responsive adjustment for mobile */
        @media (max-width: 640px) {
            [data-testid="stVerticalBlock"] > div:has(div.login-logo) {
                max-width: 90%;
            }
        }
        
        .login-logo {
            text-align: center;
            margin-bottom: 8px;
            font-size: 3em;
        }
        
        .login-title {
            text-align: center;
            color: #1e293b; /* Deep slate */
            font-size: 1.8em;
            font-weight: 800;
            margin-bottom: 4px;
        }
        
        .login-subtitle {
            text-align: center;
            color: #64748b; /* Muted slate */
            font-size: 0.95em;
            margin-bottom: 32px;
        }

        /* Input Fields */
        div[data-testid="stTextInput"] label {
            color: #475569 !important;
            font-weight: 600 !important;
        }

        div[data-testid="stTextInput"] input {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
            color: #1e293b !important;
            padding: 12px !important;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: #3b82f6 !important; /* Bright Blue */
            box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
        }

        /* Submit Button */
        div.stButton > button {
            background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 1.1em !important;
            padding: 14px !important;
            width: 100% !important;
            margin-top: 10px;
            transition: all 0.3s ease !important;
        }

        div.stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
            background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        }

        /* Hide elements */
        [data-testid="stHeader"] { display: none; }
        [data-testid="stSidebar"] { display: none; }
        footer { display: none; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # --- Centered Login Card ---
    _, col2, _ = st.columns([1, 1.5, 1])

    with col2:
        st.markdown(
            '<div class="login-logo"><img src="https://dvk.ai/assets/img/dvk_logo_white_bg_transparent.png" width="120"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="login-title">DVK Marketing</div>', unsafe_allow_html=True
        )
        st.markdown(
            '<div class="login-subtitle">FusionX Founder Control Center</div>',
            unsafe_allow_html=True,
        )

        email = st.text_input("Email Address", placeholder="name@company.com")
        password = st.text_input(
            "Password",
            type="password",
            placeholder="••••••••",
            key="login_pass",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Sign In to Dashboard", use_container_width=True):
            if not email or not password:
                st.warning("Please enter your credentials.")
            else:
                try:
                    conn = sqlite3.connect("data/fusionx_unified.db")
                    conn.row_factory = sqlite3.Row
                    user = conn.execute(
                        "SELECT * FROM users WHERE email = ?", (email,)
                    ).fetchone()
                    conn.close()

                    hashed_input = hashlib.sha256(password.encode()).hexdigest()

                    if user and user["password"] == hashed_input:
                        st.session_state.logged_in = True
                        st.session_state.current_user = dict(user)
                        st.toast(f"Welcome back, {user['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")

                except Exception as e:
                    st.error(f"System error: {e}")

        st.markdown(
            '<p style="text-align:center; color:#94a3b8; font-size:0.8em; margin-top:30px;">'
            "DVK Analytics © 2026 | Secure Founder Access</p>",
            unsafe_allow_html=True,
        )


def show_user_management():
    """Admin panel to manage users — embed this in Settings tab"""
    st.markdown("#### 👥 User Management")

    # Add new user form
    with st.expander("➕ Add New User"):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_fullname = st.text_input("Full Name")
            with col2:
                new_password = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ["user", "admin"])

            if st.form_submit_button("Add User", use_container_width=True):
                if new_username and new_password and new_fullname:
                    if add_user(new_username, new_password, new_fullname, new_role):
                        st.success(f"✅ User '{new_username}' added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Username '{new_username}' already exists.")
                else:
                    st.warning("All fields are required.")

    # List existing users
    st.markdown("**Existing Users:**")
    users = get_all_users()
    current_user_id = st.session_state.current_user["id"]

    for user in users:
        uid, uname, fname, role, created = user
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([3, 1, 1])
            with col_a:
                st.markdown(f"**{fname}** (`{uname}`)")
                st.caption(f"Role: {role} | Joined: {created[:10]}")
            with col_b:
                role_badge = "🔴 Admin" if role == "admin" else "🔵 User"
                st.write(role_badge)
            with col_c:
                # Prevent deleting yourself
                if uid != current_user_id:
                    if st.button(
                        "🗑️ Delete", key=f"del_user_{uid}", use_container_width=True
                    ):
                        delete_user(uid)
                        st.success(f"Deleted user '{uname}'")
                        st.rerun()
                else:
                    st.caption("(You)")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
