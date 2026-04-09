import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import (
    init_db,
    update_message_status,
    save_prospect_dual,
    is_duplicate,
    save_linkedin_only,
    update_linkedin_status,
)
from ai_engine import generate_vamshi_sequence, get_8_step_email_sequence
from auth import init_auth, show_login_page, show_user_management
from database import get_cooldown_settings, update_cooldown_settings


# --- AUTH INIT ---
init_auth()

# --- AUTH GATE ---
if not st.session_state.get("logged_in", False):
    show_login_page()
    st.stop()  # ⛔ Stops rest of app

# --- SESSION STATE INIT ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "selected_prospect" not in st.session_state:
    st.session_state.selected_prospect = None

if "preview_email_id" not in st.session_state:
    st.session_state.preview_email_id = None
st.set_page_config(
    page_title="FusionX Founder Control Center", page_icon="🎯", layout="wide"
)
from streamlit_autorefresh import st_autorefresh

# Auto-refresh every 5 minutes (300000 ms) — adjust as needed
st_autorefresh(
    interval=3000, limit=1000, key="cooldown_refresh"
)  # limit prevents infinite loops

init_db()

st.markdown(
    """
<style>
    .stApp { background-color: #ffffff; color: #000000; }
    [data-testid="stSidebar"] { background-color: #DEDEDE ; }
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; transition: 0.3s; }
    div.stButton > button:first-child { background-color: #FFD000; color: black; border: 2px solid #FFD000; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #FFD000; }
    [data-testid="stMetricValue"] { color: #000000; font-size: 24px; }
</style>
""",
    unsafe_allow_html=True,
)

# --- SESSION STATE ---
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if "focus_prospect_id" not in st.session_state:
    st.session_state.focus_prospect_id = None
if "focus_source" not in st.session_state:
    st.session_state.focus_source = None


# --- SMTP ENGINE ---
def send_email_smtp(to_email, subject, body, sender_email, app_password):
    if not sender_email or not app_password:
        st.error("❌ Setup Required: Configure SMTP in the Settings tab.")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"], msg["To"], msg["Subject"] = sender_email, to_email, subject
        msg.attach(MIMEText(body, "plain"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail Error: {str(e)}")
        return False


def get_smtp_credentials():
    """Load saved SMTP credentials from DB"""
    try:
        conn = sqlite3.connect("data/fusionx_unified.db")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        res_user = conn.execute(
            "SELECT value FROM settings WHERE key='smtp_user'"
        ).fetchone()
        res_pass = conn.execute(
            "SELECT value FROM settings WHERE key='smtp_pass'"
        ).fetchone()
        conn.close()
        return (res_user[0] if res_user else ""), (res_pass[0] if res_pass else "")
    except:
        return "", ""


st.markdown(
    """
    <style>
    /* Style every button inside the sidebar */
    [data-testid="stSidebar"] div.stButton > button {
        background-color: #3d4b5f; /* Deep Slate Grey */
        color: white; 
        border-radius: 8px;
        border: 1px solid #2d3748;
        padding: 0.5rem;
        transition: all 0.3s ease;
    }

    /* Style for when the mouse hovers over the button */
    [data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #4a5568; /* Slightly lighter on hover */
        border: 1px solid #FFD000; /* Electric blue border glow */
        color: #FFD000;
    }

    /* Style for when the button is clicked/active */
    [data-testid="stSidebar"] div.stButton > button:active {
        background-color: #FFD000;
        color: white;
    }

    /* Optional: Make the expander headers look cleaner */
    [data-testid="stSidebar"] .st-expanderHeader {
        background-color: transparent;
        font-weight: bold;
        color: #ccd0d6;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        position: fixed;
        top: 2.875rem; /* Standard Streamlit header height */
        background-color: white; /* Matches page background */
        z-index: 999;
        width: 100%; /* Ensure it spans the full content width */
        padding: 10px 0;
        border-bottom: 1px solid #e6e6e6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- SIDEBAR ---
if "mode" not in st.session_state:
    st.session_state.mode = "🌐LinkedIn System"
with st.sidebar:
    left_co, cent_co, last_co = st.columns([1, 2, 1])

    with cent_co:
        # Display the logo centered in the middle column
        st.image(
            "https://dvk.ai/assets/img/dvk_logo_white_bg_transparent.png",
            width=120,  # Increased width slightly for a centered look
        )

    # 2. Centered Title and User Info
    if st.session_state.get("current_user"):
        user = st.session_state.current_user
        full_name = user["full_name"]
        role = user["role"]
    else:
        # Fallback if no user session exists
        full_name = "Guest"
        role = "Viewer"

    st.markdown(
        f"""
        <div style="text-align: center;">
            <h1 style="margin-top: -10px;">🏛️DVK Marketing Control</h1>
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: -10px; color: #666; font-size: 0.9rem;">
                <span><b>{full_name}</b></span>
                <span style="color: #999;">|</span>
                <span>Role: <i>{role}</i></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    if st.button("🌐 LinkedIn System", use_container_width=True, type="secondary"):
        st.session_state.mode = "🌐LinkedIn System"
        st.rerun()

    if st.button("📧 Email Automation", use_container_width=True):
        st.session_state.mode = "📧Email Automation"
        st.rerun()

    if st.button("📂 Master Database", use_container_width=True):
        st.session_state.mode = "📂Master Database"
        st.rerun()

    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.mode = "⚙️ Settings"
        st.rerun()

    st.divider()

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.mode = "🌐LinkedIn System"
        st.rerun()

mode = st.session_state.mode


# ================== MODE 1: LINKEDIN SYSTEM ==================
if mode == "🌐LinkedIn System":
    st.title("🔗 LinkedIn Control Center")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Dashboard", "📂 All IDs", "📅 Follow-ups", "🆕 New Leads"]
    )

    with tab1:
        conn = sqlite3.connect("data/fusionx_unified.db")

        # 1. Metrics calculations
        total_li = conn.execute(
            "SELECT COUNT(*) FROM prospects WHERE linkedin != ''"
        ).fetchone()[0]
        sent_li = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE channel='linkedin' AND status='1'"
        ).fetchone()[0]
        pending_li = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE channel='linkedin' AND status='0'"
        ).fetchone()[0]
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        due_li = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE channel='linkedin' AND status='0' AND next_followup <= ?",
            (today_str,),
        ).fetchone()[0]

        # 2. Display metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LinkedIn Prospects", total_li)
        c2.metric("Messages Sent", sent_li)
        c3.metric("Pending Outreach", pending_li)
        c4.metric("Follow ups due ", due_li)

        # 3. Data Query
        # Added 'sent_count' and renamed columns to match your dataframe call below
        df_linkedin = pd.read_sql_query(
            """
            SELECT 
                p.name AS 'Employee',
                p.company AS 'Company',
                p.industry AS 'Title/Role',
                m.stage AS 'Status',
                -- Raw count for the lambda calculation
                (SELECT COUNT(*) FROM messages WHERE prospect_id = p.id AND channel = 'linkedin' AND status IN ('1', 'sent')) AS 'Sent',
                -- String progress
                (SELECT COUNT(*) FROM messages WHERE prospect_id = p.id AND channel = 'linkedin' AND status IN ('1', 'sent')) 
                || '/' || 
                (SELECT COUNT(*) FROM messages WHERE prospect_id = p.id AND channel = 'linkedin') AS 'Progress_String',
                p.linkedin AS 'Profile Link',
                m.next_followup AS 'Follow-up Date'
            FROM prospects p
            JOIN messages m ON p.id = m.prospect_id
            WHERE m.channel = 'linkedin'
            AND (
                m.id = (
                    SELECT MAX(id) FROM messages 
                    WHERE prospect_id = p.id AND channel = 'linkedin' AND status IN ('1', 'sent')
                )
                OR 
                (
                    m.id = (SELECT MIN(id) FROM messages WHERE prospect_id = p.id AND channel = 'linkedin' AND status = '0')
                    AND NOT EXISTS (SELECT 1 FROM messages WHERE prospect_id = p.id AND channel = 'linkedin' AND status IN ('1', 'sent'))
                )
            )
            GROUP BY p.id
            """,
            conn,
        )
        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 Outreach Summary")
            if not df_linkedin.empty:
                # This line now works because "Sent" is in the SELECT statement
                df_linkedin["PROGRESS"] = df_linkedin["Sent"].apply(
                    lambda x: f"{int(x)}/9"
                )

                # Ensure these names match the AS aliases in the SQL above
                st.dataframe(
                    df_linkedin[["Company", "Employee", "PROGRESS", "Status"]],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No LinkedIn outreach data found.")

        st.divider()

        with col2:
            st.subheader("📊 Sequence Step Tracker")

            try:
                # 1. SQL handles 'sent' vs '0' based on your screenshot
                df_counts = pd.read_sql_query(
                    """
                    SELECT 
                        stage, 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent
                    FROM messages 
                    WHERE channel = 'email'
                    GROUP BY stage
                """,
                    conn,
                )

                # 2. EXACT MATCH with your screenshot (Note the hyphens)
                stages = [
                    "Initial",
                    "Follow-up 1",
                    "Follow-up 2",
                    "Follow-up 3",
                    "Follow-up 4",
                    "Follow-up 5",
                    "Follow-up 6",
                    "Follow-up 7",
                    "Follow-up 8",
                ]

                for i, label in enumerate(stages, 1):
                    # 3. Filtering logic
                    stage_data = df_counts[df_counts["stage"] == label]

                    if not stage_data.empty:
                        sent_count = int(stage_data["sent"].iloc[0])
                        total_count = int(stage_data["total"].iloc[0])
                    else:
                        sent_count = 0
                        total_count = 0

                    # Determine visual state
                    is_complete = total_count > 0 and sent_count == total_count
                    is_in_progress = sent_count > 0 and sent_count < total_count

                    # Styling colors
                    if is_complete:
                        color, icon, text_col = "#28a745", "✓", "white"  # Done
                    elif is_in_progress:
                        color, icon, text_col = "#ffc107", "▶", "black"  # Some sent
                    else:
                        color, icon, text_col = "#f0f2f6", str(i), "#555"  # Waiting

                    status_desc = (
                        f"Sent {sent_count}/{total_count}"
                        if total_count > 0
                        else "Pending"
                    )

                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; margin-bottom: 12px;">
                            <div style="background-color:{color}; width:30px; height:30px; border-radius:50%; 
                                        display:flex; align-items:center; justify-content:center; 
                                        margin-right:12px; color:{text_col}; font-weight:bold; font-size: 0.9em;">
                                {icon}
                            </div>
                            <div>
                                <div style="font-weight:600; font-size:0.95em;">{label}</div>
                                <div style="font-size:0.8em; color:#666;">{status_desc}</div>
                            </div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                st.error(f"Tracker Error: {e}")

    with tab2:
        conn = sqlite3.connect("data/fusionx_unified.db")

        search_q = st.text_input("🔍 Search LinkedIn Prospects")
        query = "SELECT * FROM prospects WHERE linkedin IS NOT NULL AND linkedin != ''"
        if search_q:
            query += f" AND (name LIKE '%{search_q}%' OR company LIKE '%{search_q}%')"
        p_df = pd.read_sql_query(query, conn)
        if not p_df.empty:
            sel = st.selectbox(
                "Select Prospect",
                p_df.apply(lambda r: f"{r['name']} | {r['company']}", axis=1),
            )
            p_row = p_df[
                p_df.apply(lambda r: f"{r['name']} | {r['company']}", axis=1) == sel
            ].iloc[0]
            st.link_button(f"🔗 View {p_row['name']}'s Profile", p_row["linkedin"])
            msgs = pd.read_sql_query(
                f"SELECT id, stage, content, status FROM messages WHERE prospect_id = {p_row['id']} AND channel='linkedin'",
                conn,
            )
            for _, row in msgs.iterrows():
                with st.expander(
                    f"{'✅' if row['status'] == '1' else '⏳'} {row['stage']}"
                ):
                    st.code(row["content"], language=None)
                    if st.button("Mark as Sent", key=f"li_sent_{row['id']}"):
                        update_message_status(row["id"], "1")
                        st.rerun()
        conn.close()

    with tab3:
        st.subheader("🔥 LinkedIn Follow-up Pipeline")
        st.write(
            "Follow-ups unlock 3 days after the previous message is confirmed sent."
        )

        conn = sqlite3.connect("data/fusionx_unified.db")
        conn.row_factory = sqlite3.Row

        # Fetch the NEXT unsent message for each prospect who has at least one sent message
        query = """
            SELECT 
                p.id as prospect_id, p.name, p.company,
                m.id as msg_id, m.stage, m.content,
                -- FIXED: Get next_followup from the LAST SENT message, not the unsent one
                last_sent.next_followup as next_followup
            FROM messages m
            JOIN prospects p ON m.prospect_id = p.id
            JOIN messages last_sent ON last_sent.id = (
                SELECT MAX(id) FROM messages
                WHERE prospect_id = p.id
                AND channel = 'linkedin'
                AND status = '1'
            )
            WHERE m.status = '0'
            AND m.channel = 'linkedin'
            AND m.id = (
                SELECT MIN(id) FROM messages 
                WHERE prospect_id = p.id 
                AND channel = 'linkedin' 
                AND status = '0'
            )
            AND EXISTS (
                SELECT 1 FROM messages 
                WHERE prospect_id = p.id 
                AND channel = 'linkedin' 
                AND status = '1'
            )
            GROUP BY p.id
        """
        df_followups = pd.read_sql_query(query, conn)
        conn.close()

        if df_followups.empty:
            st.info(
                "📭 No follow-ups scheduled. Start by sending messages in 'New Leads'!"
            )
        else:
            today = pd.Timestamp.now()

            due_now = []
            waiting = []

            for _, row in df_followups.iterrows():
                nf = row["next_followup"]
                if not nf:
                    # No timer set — due immediately
                    due_now.append(row)
                else:
                    unlock_time = pd.to_datetime(nf)
                    if unlock_time <= today:
                        due_now.append(row)
                    else:
                        days_left = (unlock_time - today).days
                        hours_left = int(
                            ((unlock_time - today).total_seconds() % 86400) / 3600
                        )
                        waiting.append((row, days_left, hours_left, unlock_time))

            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("### 🚨 Ready to Send")
                if not due_now:
                    st.success("All clear! No follow-ups due. ✅")
                for lead in due_now:
                    with st.container(border=True):
                        st.markdown(f"**{lead['name']}**")
                        st.caption(f"Next: **{lead['stage']}** | @ {lead['company']}")
                        if st.button(
                            f"⚡ Send to {lead['name']}",
                            key=f"fup_{lead['msg_id']}",
                            use_container_width=True,
                            type="primary",
                        ):
                            st.session_state.selected_prospect = lead["prospect_id"]
                            st.rerun()

            with col_right:
                li_cooldown, _ = get_cooldown_settings()
                st.markdown(f"### ⏳ Cooldown ({li_cooldown} days)")
                if not waiting:
                    st.write("Nothing waiting. ✅")
                for lead, days_left, hours_left, unlock_time in waiting:
                    with st.container(border=True):
                        st.markdown(f"**{lead['name']}** @ {lead['company']}")
                        st.caption(f"Next up: **{lead['stage']}**")
                        if days_left > 0:
                            st.info(
                                f"🔒 Unlocks in **{days_left}d {hours_left}h** ({unlock_time.strftime('%b %d')})"
                            )
                        else:
                            st.info(
                                f"🔒 Unlocks in **{hours_left} hours** ({unlock_time.strftime('%b %d')})"
                            )

            if due_now:
                st.button("🔄 Refresh", use_container_width=True)

        # --- Action Mode Handler ---
        if st.session_state.get("selected_prospect") is not None:
            p_id = st.session_state.selected_prospect
            conn = sqlite3.connect("data/fusionx_unified.db")
            conn.row_factory = sqlite3.Row
            lead_data = conn.execute(
                """
                SELECT p.name, p.company, p.linkedin, m.id as msg_id, m.content, m.stage
                FROM prospects p
                JOIN messages m ON p.id = m.prospect_id
                WHERE p.id = ? AND m.status = '0' AND m.channel = 'linkedin'
                ORDER BY m.id ASC
                LIMIT 1
                """,
                (p_id,),
            ).fetchone()
            conn.close()

            if lead_data:
                st.markdown("---")
                st.info(
                    f"🚀 **Action Mode:** {lead_data['name']} | Stage: **{lead_data['stage']}**"
                )
                st.markdown("### Message to Send")
                st.code(lead_data["content"], language="text")

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button(
                        "✅ Confirm Sent",
                        type="primary",
                        use_container_width=True,
                        key=f"confirm_{lead_data['msg_id']}",
                    ):
                        if update_linkedin_status(lead_data["msg_id"], status="1"):
                            from database import get_cooldown_settings

                            li_cooldown, _ = get_cooldown_settings()
                            next_date = (
                                datetime.now() + timedelta(days=li_cooldown)
                            ).strftime("%b %d, %Y")
                            st.success(
                                f"✅ Marked sent! Next follow-up unlocks on **{next_date}**"
                            )
                            st.session_state.selected_prospect = None
                            st.rerun()
                with c2:
                    if lead_data["linkedin"]:
                        st.link_button(
                            "🔗 Profile",
                            lead_data["linkedin"],
                            use_container_width=True,
                        )
                with c3:
                    if st.button("⬅️ Back", use_container_width=True):
                        st.session_state.selected_prospect = None
                        st.rerun()

    with tab4:
        if st.session_state.selected_prospect is None:
            st.subheader("🆕 Untouched Prospects")
            conn = sqlite3.connect("data/fusionx_unified.db")
            untouched = pd.read_sql_query(
                """
                SELECT DISTINCT p.id, p.name, p.company 
                FROM prospects p
                JOIN messages m ON p.id = m.prospect_id
                WHERE m.channel = 'linkedin' AND m.stage = 'Intro' AND m.status = '0'
                """,
                conn,
            )
            conn.close()

            if untouched.empty:
                st.success(
                    "🎉 No untouched prospects! All initial messages have been sent."
                )
            else:
                for _, row in untouched.iterrows():
                    with st.container(border=True):
                        col_text, col_btn = st.columns([4, 1])
                        with col_text:
                            st.markdown(f"**{row['name']}**")
                            st.caption(row["company"])
                        with col_btn:
                            if st.button(
                                "🚀 Start",
                                key=f"start_{row['id']}",
                                use_container_width=True,
                            ):
                                st.session_state.selected_prospect = row["id"]
                                st.rerun()
        else:
            p_id = st.session_state.selected_prospect
            conn = sqlite3.connect("data/fusionx_unified.db")
            conn.row_factory = sqlite3.Row
            lead = conn.execute(
                """
                SELECT p.name, p.company, p.linkedin, m.id as msg_id, m.content, m.stage
                FROM prospects p
                JOIN messages m ON p.id = m.prospect_id
                WHERE p.id = ? AND m.channel = 'linkedin' AND m.status = '0'
                ORDER BY m.id ASC
                LIMIT 1
                """,
                (p_id,),
            ).fetchone()
            conn.close()

            if lead:
                st.info(f"🚀 **Action Mode:** {lead['name']} @ {lead['company']}")
                st.markdown("### Suggested Message")
                st.code(lead["content"], language="text")

                if st.button(
                    "✅ Confirm Sent",
                    type="primary",
                    use_container_width=True,
                    key=f"action_confirm_{lead['msg_id']}",
                ):
                    if update_linkedin_status(lead["msg_id"]):
                        st.success(
                            f"Message marked as sent at {datetime.now().strftime('%H:%M:%S')}!"
                        )
                        st.session_state.selected_prospect = None
                        st.rerun()
                    else:
                        st.error("Failed to update database.")

                if lead["linkedin"]:
                    st.link_button(
                        "🔗 Open LinkedIn Profile",
                        lead["linkedin"],
                        use_container_width=True,
                    )
                else:
                    st.button(
                        "🔗 Open LinkedIn Profile (No Link Found)",
                        disabled=True,
                        use_container_width=True,
                    )

                if st.button("⬅️ Back to List", use_container_width=True):
                    st.session_state.selected_prospect = None
                    st.rerun()
            else:
                st.warning("No pending LinkedIn messages found for this prospect.")
                if st.button("Back to List"):
                    st.session_state.selected_prospect = None
                    st.rerun()


# ================== MODE 2: EMAIL AUTOMATION ==================
elif mode == "📧Email Automation":
    st.title("📧 Email Control Center")

    # FIXED: Load SMTP creds from DB (no longer from sidebar)
    user_mail, app_pass = get_smtp_credentials()

    tab_dash, tab_gen, tab_track, tab_le = st.tabs(
        ["📊 Dashboard", "✉️ Send Emails", "📅 Follow Tracker", "🆕 New Leads"]
    )

    conn = sqlite3.connect("data/fusionx_unified.db")

    with tab_dash:
        try:
            today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_p = conn.execute(
                "SELECT COUNT(*) FROM prospects WHERE email != ''"
            ).fetchone()[0]
            sent_e = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE channel='email' AND status='sent'"
            ).fetchone()[0]
            pending_e = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE channel='email' AND status='0'"
            ).fetchone()[0]
            due_e = conn.execute(
                """
        SELECT COUNT(*)
        FROM messages
        WHERE channel='email'
        AND status='0'
        AND next_followup <= ?
        """,
                (today_str,),
            ).fetchone()[0]

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Prospects", total_p)
            k2.metric("Emails Sent", sent_e)
            k3.metric("Drafts Pending", pending_e)
            k4.metric("Follow ups due ", due_e)

            st.divider()

            df_summary = pd.read_sql_query(
                f"""
                SELECT
                    p.company as 'Company',
                    p.name as 'Employee',
                    COALESCE(SUM(CASE WHEN m.status='sent' THEN 1 ELSE 0 END), 0) as 'Sent',
                    CASE
                        WHEN COUNT(m.id) = 0 THEN 'No Mail Generated'
                        WHEN MAX(m.next_followup) <= '{today_str}' AND MAX(m.status) = '0' THEN '⚠️ Follow-up Due'
                        WHEN MAX(m.status) = '0' THEN '⏳ Scheduled'
                        ELSE '✅ Completed'
                    END as 'Status'
                FROM prospects p
                LEFT JOIN messages m ON p.id = m.prospect_id AND m.channel='email'
                WHERE p.email != '' AND p.email IS NOT NULL
                GROUP BY p.id, p.company, p.name
            """,
                conn,
            )

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📋 Outreach Summary")
                df_summary["PROGRESS"] = df_summary["Sent"].apply(
                    lambda x: f"{int(x)}/9"
                )
                st.dataframe(
                    df_summary[["Company", "Employee", "PROGRESS", "Status"]],
                    use_container_width=True,
                    hide_index=True,
                )

            with col2:
                st.subheader("📊Sequence Step Tracker")

                try:
                    # 1. SQL handles 'sent' vs '0' based on your screenshot
                    df_counts = pd.read_sql_query(
                        """
                        SELECT 
                            stage, 
                            COUNT(*) as total,
                            SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent
                        FROM messages 
                        WHERE channel = 'email'
                        GROUP BY stage
                    """,
                        conn,
                    )

                    # 2. EXACT MATCH with your screenshot (Note the hyphens)
                    stages = [
                        "Initial",
                        "Follow-up 1",
                        "Follow-up 2",
                        "Follow-up 3",
                        "Follow-up 4",
                        "Follow-up 5",
                        "Follow-up 6",
                        "Follow-up 7",
                        "Follow-up 8",
                    ]

                    for i, label in enumerate(stages, 1):
                        # 3. Filtering logic
                        stage_data = df_counts[df_counts["stage"] == label]

                        if not stage_data.empty:
                            sent_count = int(stage_data["sent"].iloc[0])
                            total_count = int(stage_data["total"].iloc[0])
                        else:
                            sent_count = 0
                            total_count = 0

                        # Determine visual state
                        is_complete = total_count > 0 and sent_count == total_count
                        is_in_progress = sent_count > 0 and sent_count < total_count

                        # Styling colors
                        if is_complete:
                            color, icon, text_col = "#28a745", "✓", "white"  # Done
                        elif is_in_progress:
                            color, icon, text_col = "#ffc107", "▶", "black"  # Some sent
                        else:
                            color, icon, text_col = "#f0f2f6", str(i), "#555"  # Waiting

                        status_desc = (
                            f"Sent {sent_count}/{total_count}"
                            if total_count > 0
                            else "Pending"
                        )

                        st.markdown(
                            f"""
                            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                                <div style="background-color:{color}; width:30px; height:30px; border-radius:50%; 
                                            display:flex; align-items:center; justify-content:center; 
                                            margin-right:12px; color:{text_col}; font-weight:bold; font-size: 0.9em;">
                                    {icon}
                                </div>
                                <div>
                                    <div style="font-weight:600; font-size:0.95em;">{label}</div>
                                    <div style="font-size:0.8em; color:#666;">{status_desc}</div>
                                </div>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    st.error(f"Tracker Error: {e}")
        except Exception as e:
            st.error(f"Dashboard Error: {e}")

    with tab_gen:
        st.subheader("✉️ Smart Review & Send")

        if not user_mail or not app_pass:
            st.warning("⚠️ SMTP not configured. Go to **⚙️ Settings** in the sidebar.")

        # Fetch NEXT due email per prospect
        df_raw = pd.read_sql_query(
            """
            SELECT m.id, m.stage, m.subject, m.content, m.next_followup,
                p.name, p.company, p.email
            FROM messages m
            JOIN prospects p ON p.id = m.prospect_id
            WHERE m.channel = 'email' AND m.status = '0'
            AND m.id = (
                SELECT MIN(m2.id) FROM messages m2
                WHERE m2.prospect_id = p.id
                AND m2.channel = 'email'
                AND m2.status = '0'
            )
            ORDER BY p.name ASC
            """,
            conn,
        )

        if df_raw.empty:
            st.info(
                "No drafts found. Add prospects in Master Database to generate emails."
            )
        else:
            st.markdown("#### 🔍 Filter")
            c1, c2, c3 = st.columns(3)

            with c1:
                u_comps = ["— All Companies —"] + sorted(
                    df_raw["company"].unique().tolist()
                )
                f_comp = st.selectbox("By Company", u_comps, key="gen_filter_comp")

            with c2:
                temp_df = (
                    df_raw
                    if f_comp == "— All Companies —"
                    else df_raw[df_raw["company"] == f_comp]
                )
                u_names = sorted(temp_df["name"].unique().tolist())
                f_name = st.selectbox(
                    "By Employee Name",
                    ["— All Employees —"] + u_names,
                    key="gen_filter_name",
                )

            with c3:
                # Shows only stages that are the CURRENT next step for at least one prospect
                stage_order = ["Initial"] + [f"Follow-up {i}" for i in range(1, 10)]
                present_stages = df_raw["stage"].unique().tolist()
                available_stages = [s for s in stage_order if s in present_stages]
                f_stage = st.selectbox(
                    "By Follow-up Stage",
                    ["— All Stages —"] + available_stages,
                    key="gen_filter_stage",
                )

            # --- Apply all 3 filters ---
            df_filtered = df_raw.copy()
            if f_comp != "— All Companies —":
                df_filtered = df_filtered[df_filtered["company"] == f_comp]
            if f_name != "— All Employees —":
                df_filtered = df_filtered[df_filtered["name"] == f_name]
            if f_stage != "— All Stages —":
                df_filtered = df_filtered[df_filtered["stage"] == f_stage]

            st.divider()

            if df_filtered.empty:
                st.info("No prospects match your current filter criteria.")
            else:
                today = pd.Timestamp.now()
                nf_converted = pd.to_datetime(
                    df_filtered["next_followup"], errors="coerce"
                )

                due_mask = (
                    (df_filtered["stage"] == "Initial")
                    | (nf_converted.isna())
                    | (nf_converted <= today)
                )
                waiting_mask = (
                    (df_filtered["stage"] != "Initial")
                    & (nf_converted.notna())
                    & (nf_converted > today)
                )

                due_df = df_filtered[due_mask].reset_index(drop=True)
                waiting_df = df_filtered[waiting_mask].reset_index(drop=True)

                # ── READY TO SEND ──────────────────────────────────────────
                st.markdown("### 🚨 Ready to Send")
                if due_df.empty:
                    st.success("✅ No emails due right now. All caught up!")
                else:
                    due_df["display_label"] = (
                        due_df["name"] + " (" + due_df["stage"] + ")"
                    )
                    col_sel, col_bulk = st.columns([2, 1])
                    with col_sel:
                        selected_label = st.selectbox(
                            "Select email to review:",
                            due_df["display_label"].tolist(),
                        )
                        row = due_df[due_df["display_label"] == selected_label].iloc[0]
                    with col_bulk:
                        st.write("")
                        if st.button(
                            f"🚀 Send All {len(due_df)} Due Emails",
                            use_container_width=True,
                            type="primary",
                        ):
                            if not user_mail or not app_pass:
                                st.error("Configure SMTP in ⚙️ Settings first!")
                            else:
                                bar = st.progress(0)
                                sent_count = 0
                                for i, (_, r) in enumerate(due_df.iterrows()):
                                    if send_email_smtp(
                                        r["email"],
                                        r["subject"],
                                        r["content"],
                                        user_mail,
                                        app_pass,
                                    ):
                                        update_message_status(r["id"], "sent")
                                        sent_count += 1
                                    bar.progress((i + 1) / len(due_df))
                                st.success(
                                    f"✅ Sent {sent_count} emails! "
                                    f"Next follow-ups unlock in 7 days."
                                )
                                st.rerun()

                    # Email preview + individual send
                    with st.container(border=True):
                        st.write(
                            f"**To:** {row['name']} ({row['email']}) "
                            f"| **Stage:** {row['stage']}"
                        )

                        # Show overdue/due-today banner for follow-ups
                        if row["next_followup"] and row["stage"] != "Initial":
                            due_ts = pd.to_datetime(row["next_followup"])
                            days_overdue = (today - due_ts).days
                            if days_overdue > 0:
                                st.warning(
                                    f"⚠️ This follow-up was due {days_overdue} "
                                    f"day(s) ago ({due_ts.strftime('%b %d')})"
                                )
                            else:
                                st.info(f"📅 Due today: {due_ts.strftime('%b %d, %Y')}")

                        final_sub = st.text_input(
                            "Subject", row["subject"], key=f"s_gen_{row['id']}"
                        )
                        final_body = st.text_area(
                            "Content",
                            row["content"],
                            height=250,
                            key=f"c_gen_{row['id']}",
                        )

                        if st.button(
                            "📤 Send This Email",
                            type="primary",
                            use_container_width=True,
                        ):
                            if send_email_smtp(
                                row["email"],
                                final_sub,
                                final_body,
                                user_mail,
                                app_pass,
                            ):
                                update_message_status(row["id"], "sent")
                                unlock_date = (
                                    datetime.now() + timedelta(days=7)
                                ).strftime("%b %d, %Y")
                                st.success(
                                    f"✅ Sent to {row['name']}! "
                                    f"Next follow-up unlocks on **{unlock_date}**"
                                )
                                st.rerun()

                st.divider()

                # ── WAITING / COOLDOWN ─────────────────────────────────────
                _, email_cooldown = get_cooldown_settings()
                st.markdown(
                    f"### ⏳ Scheduled (Waiting Period — {email_cooldown} days)"
                )
                if waiting_df.empty:
                    st.info("No emails in cooldown.")
                else:
                    for _, w in waiting_df.iterrows():
                        due_on = pd.to_datetime(w["next_followup"])
                        days_left = (due_on - today).days
                        hours_left = int(
                            ((due_on - today).total_seconds() % 86400) / 3600
                        )
                        with st.container(border=True):
                            col_a, col_b, col_c = st.columns([3, 2, 1])
                            with col_a:
                                name_safe = str(w["name"]).replace("*", "")
                                company_safe = str(w["company"]).replace("*", "")
                                st.markdown(f"**{name_safe}** @ {company_safe}")
                                st.caption(f"Next: **{w['stage']}** — {w['subject']}")
                            with col_b:
                                if days_left > 0:
                                    st.info(
                                        f"🔒 Unlocks in **{days_left}d {hours_left}h** "
                                        f"({due_on.strftime('%b %d')})"
                                    )
                                else:
                                    st.info(
                                        f"🔒 Unlocks in **{hours_left} hours** today"
                                    )
                            with col_c:
                                if st.button(
                                    "👁️ Preview & Send",
                                    key=f"override_{w['id']}",
                                    use_container_width=True,
                                ):
                                    st.session_state.preview_email_id = w["id"]
                                    st.rerun()

                # ── PREVIEW / EDIT MODE ────────────────────────────────────
                if st.session_state.preview_email_id is not None:
                    preview_id = st.session_state.preview_email_id

                    with sqlite3.connect("data/fusionx_unified.db") as pconn:
                        pconn.row_factory = sqlite3.Row
                        pemail = pconn.execute(
                            """
                            SELECT m.id, m.subject, m.content, m.stage,
                                p.name, p.email, p.company
                            FROM messages m
                            JOIN prospects p ON p.id = m.prospect_id
                            WHERE m.id = ?
                            """,
                            (preview_id,),
                        ).fetchone()

                    if pemail:
                        st.divider()
                        st.markdown(
                            f"### ✏️ Review & Send — "
                            f"{pemail['name']} ({pemail['stage']})"
                        )
                        with st.container(border=True):
                            st.write(
                                f"**To:** {pemail['name']} ({pemail['email']}) "
                                f"@ {pemail['company']}"
                            )
                            st.write(f"**Stage:** {pemail['stage']}")

                            edited_sub = st.text_input(
                                "Subject",
                                value=pemail["subject"],
                                key=f"preview_sub_{preview_id}",
                            )
                            edited_body = st.text_area(
                                "Content",
                                value=pemail["content"],
                                height=300,
                                key=f"preview_body_{preview_id}",
                            )

                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button(
                                    "⬅️ Cancel",
                                    use_container_width=True,
                                    key="preview_cancel",
                                ):
                                    st.session_state.preview_email_id = None
                                    st.rerun()
                            with c2:
                                if st.button(
                                    "📤 Send Now",
                                    type="primary",
                                    use_container_width=True,
                                    key="preview_send",
                                ):
                                    if send_email_smtp(
                                        pemail["email"],
                                        edited_sub,
                                        edited_body,
                                        user_mail,
                                        app_pass,
                                    ):
                                        update_message_status(preview_id, "sent")
                                        unlock_date = (
                                            datetime.now()
                                            + timedelta(days=email_cooldown)
                                        ).strftime("%b %d, %Y")
                                        st.success(
                                            f"✅ Sent to {pemail['name']}! "
                                            f"Next follow-up unlocks on **{unlock_date}**"
                                        )
                                        st.session_state.preview_email_id = None
                                        st.rerun()
                    else:
                        st.session_state.preview_email_id = None
    with tab_track:
        st.subheader("📅 Sent Outreach History")

        # 1. Fetch and Display Sent Emails
        df_track = pd.read_sql_query(
            """
            SELECT p.name as 'Lead', p.company as 'Company', m.stage as 'Stage',
                m.subject as 'Subject', m.sent_at as 'Sent On',
                m.next_followup as 'Next Follow-up Due'
            FROM messages m 
            JOIN prospects p ON p.id = m.prospect_id 
            WHERE m.channel='email' AND m.status='sent'
            ORDER BY m.sent_at DESC
            """,
            conn,
        )
        st.dataframe(df_track, use_container_width=True, hide_index=True)

        st.divider()

        # 2. Fetch Scheduled/Waiting Emails
        st.markdown("### ⏳ Scheduled")
        df_waiting_track = pd.read_sql_query(
            """
            SELECT m.id, m.stage, m.subject, m.content, m.next_followup,
                p.name, p.company, p.email
            FROM messages m
            JOIN prospects p ON p.id = m.prospect_id
            WHERE m.channel = 'email' AND m.status = '0'
            AND m.next_followup IS NOT NULL
            AND m.id = (
                SELECT MIN(m2.id) FROM messages m2
                WHERE m2.prospect_id = p.id
                AND m2.channel = 'email'
                AND m2.status = '0'
            )
            ORDER BY m.next_followup ASC
            """,
            conn,
        )

        if df_waiting_track.empty:
            st.info("No emails in cooldown.")
        else:
            today_track = pd.Timestamp.now()
            nf_track = pd.to_datetime(
                df_waiting_track["next_followup"], errors="coerce"
            )
            waiting_only = df_waiting_track[nf_track > today_track].reset_index(
                drop=True
            )

            if waiting_only.empty:
                st.info("No emails in cooldown.")
            else:
                # --- LIST VIEW LOOP ---
                for _, w in waiting_only.iterrows():
                    due_on = pd.to_datetime(w["next_followup"])
                    days_left = (due_on - today_track).days
                    hours_left = int(
                        ((due_on - today_track).total_seconds() % 86400) / 3600
                    )

                    with st.container(border=True):
                        col_a, col_b, col_c = st.columns([3, 2, 1])
                        with col_a:
                            name_safe = str(w["name"]).replace("*", "")
                            st.markdown(f"**{name_safe}** @ {w['company']}")
                            st.caption(f"Next: **{w['stage']}** — {w['subject']}")
                        with col_b:
                            if days_left > 0:
                                st.info(
                                    f"🔒 Unlocks in **{days_left}d {hours_left}h** ({due_on.strftime('%b %d')})"
                                )
                            else:
                                st.info(f"🔒 Unlocks in **{hours_left} hours** today")
                        with col_c:
                            # Triggers the preview mode below
                            if st.button(
                                "👁️ Preview & Send",
                                key=f"btn_prev_{w['id']}",
                                use_container_width=True,
                            ):
                                st.session_state.preview_email_id = w["id"]
                                st.rerun()

        # --- 3. PREVIEW / EDIT MODE (Renders OUTSIDE the loop) ---
        if st.session_state.get("preview_email_id") is not None:
            preview_id = st.session_state.preview_email_id

            # Use a context manager for the preview fetch to keep it clean
            with sqlite3.connect("data/fusionx_unified.db") as pconn:
                pconn.row_factory = sqlite3.Row
                pemail = pconn.execute(
                    """
                    SELECT m.id, m.subject, m.content, m.stage,
                        p.name, p.email, p.company
                    FROM messages m
                    JOIN prospects p ON p.id = m.prospect_id
                    WHERE m.id = ?
                    """,
                    (preview_id,),
                ).fetchone()

            if pemail:
                st.divider()
                st.markdown(
                    f"### ✏️ Review & Send — {pemail['name']} ({pemail['stage']})"
                )

                with st.container(border=True):
                    st.write(
                        f"**To:** {pemail['name']} ({pemail['email']}) @ {pemail['company']}"
                    )

                    # FIXED: Argument name updated to 'app_password' to match your function
                    edited_sub = st.text_input(
                        "Subject", value=pemail["subject"], key=f"inp_sub_{preview_id}"
                    )
                    edited_body = st.text_area(
                        "Content",
                        value=pemail["content"],
                        height=300,
                        key=f"inp_body_{preview_id}",
                    )

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(
                            "⬅️ Cancel", use_container_width=True, key="prev_cancel_btn"
                        ):
                            st.session_state.preview_email_id = None
                            st.rerun()
                    with c2:
                        if st.button(
                            "📤 Send Now",
                            type="primary",
                            use_container_width=True,
                            key="prev_send_btn",
                        ):
                            if send_email_smtp(
                                pemail["email"],
                                edited_sub,
                                edited_body,
                                user_mail,
                                app_pass,
                            ):
                                update_message_status(preview_id, "sent")
                                st.success(f"✅ Sent to {pemail['name']}!")
                                st.session_state.preview_email_id = None
                                st.rerun()

    conn.close()

    with tab_le:
        # Initialize session state for lead selection
        if "selected_prospect" not in st.session_state:
            st.session_state.selected_prospect = None

        # Fetch SMTP credentials for the send operations
        user_mail, app_pass = get_smtp_credentials()

        if st.session_state.selected_prospect is None:
            st.subheader("🆕 Untouched Email Prospects")
            st.caption(
                "Select a prospect to review or send all initial emails at once."
            )

            # Use context manager for better connection handling
            with sqlite3.connect("data/fusionx_unified.db") as conn:
                untouched = pd.read_sql_query(
                    """
                    SELECT DISTINCT p.id, p.name, p.company, p.email,
                                    m.id as msg_id, m.subject, m.content
                    FROM prospects p
                    JOIN messages m ON p.id = m.prospect_id
                    WHERE m.channel = 'email' AND m.stage = 'Initial' AND m.status = '0'
                    """,
                    conn,
                )

            if untouched.empty:
                st.success("🎉 All initial Email messages have been sent!")
            else:
                # --- BULK SEND ACTION ---
                col_info, col_bulk = st.columns([2, 1])
                with col_info:
                    st.info(f"Currently tracking **{len(untouched)}** untouched leads.")

                with col_bulk:
                    if st.button(
                        f"🚀 Send All {len(untouched)} Emails",
                        type="primary",
                        use_container_width=True,
                    ):
                        if not user_mail or not app_pass:
                            st.error("Setup SMTP in Settings first!")
                        else:
                            bar = st.progress(0)
                            for i, row in untouched.iterrows():
                                if send_email_smtp(
                                    row["email"],
                                    row["subject"],
                                    row["content"],
                                    user_mail,
                                    app_pass,
                                ):
                                    update_message_status(row["msg_id"], "sent")
                                bar.progress((i + 1) / len(untouched))
                            st.success(f"✅ Sent {len(untouched)} emails successfully!")
                            st.rerun()

                st.divider()

                # --- INDIVIDUAL LIST ---
                for _, row in untouched.iterrows():
                    with st.container(border=True):
                        col_text, col_btn = st.columns([4, 1])
                        with col_text:
                            st.markdown(f"**{row['name']}**")
                            st.caption(f"🏢 {row['company']} | ✉️ {row['email']}")
                        with col_btn:
                            if st.button(
                                "📝 Initial Massages",
                                key=f"start_email_{row['id']}",
                                use_container_width=True,
                            ):
                                st.session_state.selected_prospect = row["id"]
                                st.rerun()
        else:
            # --- INDIVIDUAL ACTION MODE ---
            p_id = st.session_state.selected_prospect
            with sqlite3.connect("data/fusionx_unified.db") as conn:
                conn.row_factory = sqlite3.Row
                lead = conn.execute(
                    """
                    SELECT p.name, p.company, p.email, m.id as msg_id, m.content, m.subject, m.stage
                    FROM prospects p
                    JOIN messages m ON p.id = m.prospect_id
                    WHERE p.id = ? AND m.channel = 'email' AND m.status = '0'
                    ORDER BY m.id ASC LIMIT 1
                    """,
                    (p_id,),
                ).fetchone()

            if lead:
                st.info(
                    f"🎯 **Target:** {lead['name']} | **Company:** {lead['company']}"
                )

                # Editable fields for the individual review
                final_sub = st.text_input("Subject", lead["subject"])
                final_body = st.text_area("Content", lead["content"], height=300)

                c1, c2 = st.columns(2)

                with c2:
                    if st.button(
                        "📤 Send Now", type="primary", use_container_width=True
                    ):
                        if send_email_smtp(
                            lead["email"], final_sub, final_body, user_mail, app_pass
                        ):
                            update_message_status(lead["msg_id"], "sent")
                            st.toast(f"Email sent to {lead['name']}!")
                            st.session_state.selected_prospect = None
                            st.rerun()
            else:
                st.session_state.selected_prospect = None
                st.rerun()

        # --- RECENT ACTIVITY TRACKING ---
        st.divider()
        st.subheader("📊 Recent Activity")
        with sqlite3.connect("data/fusionx_unified.db") as conn:
            df_track = pd.read_sql_query(
                """
                SELECT p.name, p.company, m.stage, m.sent_at
                FROM messages m
                JOIN prospects p ON p.id = m.prospect_id
                WHERE m.status = 'sent' AND m.channel = 'email'
                ORDER BY m.sent_at DESC LIMIT 10
                """,
                conn,
            )
        st.dataframe(df_track, use_container_width=True, hide_index=True)

# ================== MODE 3: MASTER DATABASE ==================
elif mode == "📂Master Database":
    tab_up_list = st.tabs(["📊 Upload", "🗄️Master Table"])
    with tab_up_list[0]:
        col_up1, col_up2 = st.columns(2)

        with col_up1:
            st.markdown("### 📄 Bulk Upload")
            file = st.file_uploader(
                "Upload Excel/CSV", type=["xlsx", "csv"], key="bulk_email"
            )

            if file and st.button("Import & Generate Sequences"):
                df_up = (
                    pd.read_csv(file)
                    if file.name.endswith("csv")
                    else pd.read_excel(file)
                )
                df_up.columns = df_up.columns.str.strip().str.lower()

                progress_bar = st.progress(0)
                total_rows = len(df_up)

                for index, r in df_up.iterrows():
                    name = r.get("company employee name")
                    comp = r.get("company name", "Unknown")
                    pos = r.get("position", "")
                    email = r.get("email")
                    link = r.get("linkedin", "")

                    if name and email:
                        li_seq = generate_vamshi_sequence(
                            {"Name": name, "Company": comp}
                        )
                        em_seq = get_8_step_email_sequence(name, comp)
                        save_prospect_dual(name, comp, pos, link, email, li_seq, em_seq)

                    progress_bar.progress((index + 1) / total_rows)

                st.success("✅ Imported & Sequences Generated Successfully!")
                st.rerun()

        with col_up2:
            st.markdown("### ➕ Add Manual")
            with st.form("manual_email"):
                n = st.text_input("Name")
                c = st.text_input("Company")
                e = st.text_input("Email")
                i = st.text_input("Industry/Position")
                l = st.text_input("LinkedIn URL")

                submitted = st.form_submit_button(
                    "Add & Generate", use_container_width=True
                )

            # FIXED: Move logic OUTSIDE the form block so st.success() renders properly
            if submitted:
                # FIXED: Strip asterisks and extra whitespace from name/company
                n_clean = n.strip().replace("*", "").strip()
                c_clean = c.strip().replace("*", "").strip()

                if n_clean and e:
                    li_seq = generate_vamshi_sequence(
                        {"Name": n_clean, "Company": c_clean}
                    )
                    em_seq = get_8_step_email_sequence(n_clean, c_clean)
                    save_prospect_dual(
                        n_clean,
                        c_clean,
                        i.strip(),
                        l.strip(),
                        e.strip(),
                        li_seq,
                        em_seq,
                    )
                    st.success(
                        f"✅ Added **{n_clean}** from **{c_clean}** and generated all sequences!"
                    )
                    st.rerun()
                else:
                    st.warning("Name and Email are required.")

    conn = sqlite3.connect("data/fusionx_unified.db")
    conn.close()

    with tab_up_list[1]:
        st.title("🗄️ Master Prospect Database")
        conn = sqlite3.connect("data/fusionx_unified.db")
        master_df = pd.read_sql_query(
            "SELECT id, name, company, industry, email, linkedin, created_at FROM prospects",
            conn,
        )
        st.dataframe(master_df, use_container_width=True, hide_index=True)
        conn.close()


# ================== MODE 4: SETTINGS (NOW VISIBLE) ==================
# ================== MODE 4: SETTINGS ==================
elif mode == "⚙️ Settings":
    st.title("⚙️ System Settings")

    # Create tabs for different settings
    settings_tab1, settings_tab2 = st.tabs(["📧 Email/SMTP", "⏰ Cooldown Settings"])

    # Import cooldown functions
    from database import get_cooldown_settings, update_cooldown_settings

    with settings_tab1:
        st.markdown("### SMTP Configuration")
        st.markdown(
            """
        **Setup Instructions:**
        1. Enable **2-Step Verification** in your Google Account.
        2. Go to **Google Account → Security → App Passwords**.
        3. Generate a password for 'Mail' and paste the 16-character code below.
        """
        )

        conn = sqlite3.connect("data/fusionx_unified.db")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )

        res_user = conn.execute(
            "SELECT value FROM settings WHERE key='smtp_user'"
        ).fetchone()
        res_pass = conn.execute(
            "SELECT value FROM settings WHERE key='smtp_pass'"
        ).fetchone()
        saved_user = res_user[0] if res_user else ""
        saved_pass = res_pass[0] if res_pass else ""

        with st.form("smtp_config_form"):
            new_user = st.text_input(
                "Sender Gmail", value=saved_user, placeholder="example@gmail.com"
            )
            new_pass = st.text_input(
                "App Password",
                value=saved_pass,
                type="password",
                placeholder="16-character app password",
            )

            if st.form_submit_button("💾 Save Credentials", use_container_width=True):
                if "@" in new_user and len(new_pass) >= 16:
                    conn.execute(
                        "INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_user', ?)",
                        (new_user,),
                    )
                    conn.execute(
                        "INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_pass', ?)",
                        (new_pass,),
                    )
                    conn.commit()
                    st.success("✅ Settings Saved!")
                else:
                    st.error(
                        "Please enter a valid Gmail and a 16-character App Password."
                    )

        st.divider()
        st.markdown("#### 🧪 Test Your Connection")
        test_to = st.text_input("Send test email to:", placeholder="test@example.com")
        if st.button("🚀 Run Connection Test", use_container_width=True):
            if not saved_user or not saved_pass:
                st.warning("Please save your credentials first.")
            elif not test_to:
                st.error("Enter a recipient email.")
            else:
                with st.spinner("Testing SMTP connection..."):
                    success = send_email_smtp(
                        test_to,
                        "FusionX SMTP Test",
                        "Your SMTP configuration is working perfectly!",
                        saved_user,
                        saved_pass,
                    )
                    if success:
                        st.success(f"✅ Test email sent to {test_to}!")
                    else:
                        st.error("❌ Connection failed.")

        conn.close()

    with settings_tab2:
        st.markdown("### ⏰ Follow-up Cooldown Settings")
        st.markdown(
            "Configure how many days to wait before sending the next follow-up message."
        )

        # Get current settings
        current_li_cooldown, current_email_cooldown = get_cooldown_settings()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔗 LinkedIn Cooldown")
            li_days = st.number_input(
                "Days between LinkedIn follow-ups",
                min_value=1,
                max_value=30,
                value=current_li_cooldown,
                step=1,
                help="Number of days to wait after a LinkedIn message before sending the next follow-up",
            )
            st.caption(f"Current: {current_li_cooldown} day(s)")

        with col2:
            st.markdown("#### 📧 Email Cooldown")
            email_days = st.number_input(
                "Days between Email follow-ups",
                min_value=1,
                max_value=30,
                value=current_email_cooldown,
                step=1,
                help="Number of days to wait after an email before sending the next follow-up",
            )
            st.caption(f"Current: {current_email_cooldown} day(s)")

        if st.button(
            "💾 Save Cooldown Settings", type="primary", use_container_width=True
        ):
            if update_cooldown_settings(li_days, email_days):
                st.success(
                    f"✅ Cooldown settings saved! LinkedIn: {li_days} days, Email: {email_days} days"
                )
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Failed to save settings.")

        st.divider()
        st.info(
            "💡 **Note:** Changes apply to future follow-ups only. Already scheduled follow-ups keep their original dates."
        )
