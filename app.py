import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import init_db, update_message_status, save_prospect_dual, is_duplicate
from ai_engine import generate_vamshi_sequence, get_8_step_email_sequence

# --- CONFIG & INIT ---
st.set_page_config(
    page_title="FusionX Founder Control Center", page_icon="🎯", layout="wide"
)
init_db()

# Custom Styling
st.markdown(
    """
<style>
    .stApp { background-color: #ffffff; color: #000000; }
    [data-testid="stSidebar"] { background-color: #f0f2f6; }
    
    /* Pipeline Radio Buttons Navigation Styling */
    div.row-widget.stRadio > div {
        display: flex;
        flex-direction: row;
        justify-content: flex-start;
        gap: 20px;
    }
    
    /* Button Styling */
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; transition: 0.3s; }
    div.stButton > button:first-child { background-color: #00e5ff; color: black; border: 2px solid #00e5ff; }
    
    /* Metric Styling */
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #00e5ff; }
    [data-testid="stMetricValue"] { color: #008fa3; font-size: 24px; }
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
        st.error("❌ Setup Required: Enter Email & App Password in the Sidebar.")
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


# --- SIDEBAR ---
st.sidebar.title("🏛️ FusionX Control")
mode = st.sidebar.radio(
    "Select System", ["LinkedIn System", "Email Automation", "Master Database"]
)
st.sidebar.divider()
st.sidebar.subheader("📩 Mail Config")
user_mail = st.sidebar.text_input("Your Gmail", value="")
app_pass = st.sidebar.text_input("App Password", type="password")

# ================== MODE 1: LINKEDIN SYSTEM ==================
if mode == "LinkedIn System":
    st.title("🔗 LinkedIn Control Center")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🚀 Upload", "📂 All IDs", "🔥 Follow-ups", "🆕 New Leads", "📊 Table"]
    )

    with tab1:
        st.subheader("Bulk Upload")
        file = st.file_uploader("Upload Lead List (Excel)", type=["xlsx"])
        if file and st.button("Generate 8-Part Sequences"):
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip().str.lower()
            for _, row in df.iterrows():
                name = row.get("company employee name")
                comp = row.get("company name", "Unknown")
                ind = row.get("position")
                link = row.get("linkedin")
                email = row.get("email", "")

                if name and not is_duplicate(name, comp):
                    seq = generate_vamshi_sequence(
                        {"Name": name, "Company": comp, "Industry": ind}
                    )
                    save_prospect_dual(name, comp, ind, link, email, li_seq=seq)
            st.success("LinkedIn Campaigns Ready!")

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
        conn = sqlite3.connect("data/fusionx_unified.db")
        due_query = "SELECT p.name, m.id, m.stage, m.prospect_id FROM messages m JOIN prospects p ON m.prospect_id = p.id WHERE m.status = '0' AND m.channel='linkedin' AND m.prospect_id IN (SELECT prospect_id FROM messages WHERE status = '1')"
        due_df = pd.read_sql_query(due_query, conn)
        if due_df.empty:
            st.info("No follow-ups due yet.")
        else:
            for _, row in due_df.iterrows():
                if st.button(
                    f"👉 Get Message for {row['name']} ({row['stage']})",
                    key=f"alert_{row['id']}",
                ):
                    st.session_state.focus_prospect_id = row["prospect_id"]
                    st.session_state.focus_source = "tab3"
                    st.rerun()
        conn.close()

    with tab4:
        conn = sqlite3.connect("data/fusionx_unified.db")
        new_df = pd.read_sql_query(
            "SELECT * FROM prospects WHERE id NOT IN (SELECT DISTINCT prospect_id FROM messages WHERE status = '1' AND channel='linkedin') AND linkedin != ''",
            conn,
        )
        if new_df.empty:
            st.info("No new leads to display.")
        else:
            for _, row in new_df.iterrows():
                with st.container(border=True):
                    st.write(f"**{row['name']}** @ {row['company']}")
                    if st.button("🚀 Start Outreach", key=f"start_{row['id']}"):
                        st.session_state.focus_prospect_id = row["id"]
                        st.session_state.focus_source = "tab4"
                        st.rerun()
        conn.close()

    with tab5:
        conn = sqlite3.connect("data/fusionx_unified.db")
        master_df = pd.read_sql_query(
            "SELECT name, company, industry, linkedin FROM prospects WHERE linkedin != ''",
            conn,
        )
        st.dataframe(master_df, use_container_width=True, hide_index=True)
        conn.close()

# ================== MODE 2: EMAIL AUTOMATION (TABBED UI) ==================
elif mode == "Email Automation":
    st.title("📧 Email Automation Pipeline")

    # Using Tabs for side-by-side navigation
    tab_dash, tab_pros, tab_up, tab_run, tab_gen, tab_track, tab_settings = st.tabs(
        [
            "📊 Dashboard",
            "👥 Prospects",
            "📤 Upload",
            "⚡ Run Pipeline",
            "✉️ Generated",
            "📅 Follow Tracker",
            "⚙️ Settings",
        ]
    )

    conn = sqlite3.connect("data/fusionx_unified.db")

    # --- 1. DASHBOARD ---

    with tab_dash:
        try:
            # 1. KPIs (Fixed table name to 'messages' and status to '0' for pending)
            total_p = conn.execute(
                "SELECT COUNT(*) FROM prospects WHERE email != ''"
            ).fetchone()[0]
            sent_e = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE channel='email' AND status='sent'"
            ).fetchone()[0]
            pending_e = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE channel='email' AND status='0'"
            ).fetchone()[0]

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Prospects", total_p)
            k2.metric("Emails Sent", sent_e)
            k3.metric("Drafts Pending", pending_e)

            st.divider()
            st.subheader("📋 Outreach Summary")

            # 2. Fetch Data (Fixed to use 'messages' table)
            # Note: Removed 'next_followup' as it caused errors in your previous terminal logs
            df_summary = pd.read_sql_query(
                """
                SELECT 
                    p.company as 'Company', 
                    p.name as 'Employee', 
                    COALESCE(SUM(CASE WHEN m.status='sent' THEN 1 ELSE 0 END), 0) as 'Sent',
                    COALESCE(SUM(CASE WHEN m.status='0' THEN 1 ELSE 0 END), 0) as 'Pending',
                    CASE 
                        WHEN COUNT(m.id) = 0 THEN 'No Mail Generated'
                        WHEN MAX(m.status) = '0' THEN '⚠️ Follow-up Due'
                        WHEN MAX(m.status) = 'sent' THEN '✅ Sent'
                        ELSE 'Check Status'
                    END as 'Status'
                FROM prospects p
                LEFT JOIN messages m ON p.id = m.prospect_id AND m.channel='email'
                WHERE p.email != '' AND p.email IS NOT NULL
                GROUP BY p.id, p.company, p.name
            """,
                conn,
            )

            # Styling the table for the 'look' you requested
            def style_status(val):
                if "✅" in val:
                    return "background-color: #d4edda; color: #155724;"
                if "⚠️" in val:
                    return "background-color: #fff3cd; color: #856404;"
                return ""

            if not df_summary.empty:
                st.dataframe(
                    df_summary.style.applymap(style_status, subset=["Status"]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(
                    "No outreach data found. Generate sequences to see the summary."
                )

        except Exception as e:
            st.error(f"Dashboard Error: {e}")
            st.info("Verify that your 'messages' table exists in fusionx_unified.db")

    # --- 2. PROSPECTS ---
    with tab_pros:
        st.subheader("Current Email Leads")
        df_p = pd.read_sql_query(
            "SELECT company, name, email, industry FROM prospects WHERE email != ''",
            conn,
        )
        st.dataframe(df_p, use_container_width=True, hide_index=True)

    # --- 3. UPLOAD & ADD DATA ---
    with tab_up:
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            st.markdown("### 📄 Bulk Import")
            file = st.file_uploader(
                "Upload Excel/CSV", type=["xlsx", "csv"], key="bulk_email"
            )
            if file and st.button("Import Emails"):
                df_up = (
                    pd.read_csv(file)
                    if file.name.endswith("csv")
                    else pd.read_excel(file)
                )
                df_up.columns = df_up.columns.str.strip().str.lower()
                for _, r in df_up.iterrows():
                    # Mapping to your Excel headers from image_a9ef8b.png
                    name = r.get("company employee name")
                    comp = r.get("company name", "Unknown")
                    pos = r.get("position")
                    email = r.get("email")
                    link = r.get("linkedin", "")
                    if name and email:
                        save_prospect_dual(name, comp, pos, link, email)
                st.success("Imported Successfully!")

        with col_up2:
            st.markdown("### ➕ Manual Add")
            with st.form("manual_email"):
                n = st.text_input("Name")
                c = st.text_input("Company")
                e = st.text_input("Email")
                i = st.text_input("Industry/Position")
                if st.form_submit_button("Add Prospect"):
                    save_prospect_dual(n, c, i, "", e)
                    st.success("Added!")

    # --- 4. RUN PIPELINE ---
    # --- 4. RUN PIPELINE ---
    with tab_run:
        st.markdown("### ⚡ Run Pipeline")
        st.markdown("#### Filter Prospects to Generate")

        # 1. Fetch data for filters
        targets = pd.read_sql_query(
            "SELECT id, name, company FROM prospects WHERE email != '' AND email IS NOT NULL",
            conn,
        )

        if not targets.empty:
            # 2. UI Layout for Filters (Matching image_aba6c4.png)
            col1, col2, col3 = st.columns([2, 2, 1.5])

            with col1:
                unique_companies = ["— All Companies —"] + sorted(
                    targets["company"].unique().tolist()
                )
                sel_company = st.selectbox("By Company", unique_companies)

            with col2:
                # Filter employee list based on company selection
                if sel_company == "— All Companies —":
                    employee_list = ["— All Employees —"] + sorted(
                        targets["name"].unique().tolist()
                    )
                else:
                    employee_list = ["— All Employees —"] + sorted(
                        targets[targets["company"] == sel_company]["name"].tolist()
                    )
                sel_employee = st.selectbox("By Employee Name", employee_list)

            with col3:
                st.write("")  # Spacer
                skip_gen = st.toggle("Skip already generated steps?", value=True)

            # 3. Filter Logic
            df_to_gen = targets.copy()
            if sel_company != "— All Companies —":
                df_to_gen = df_to_gen[df_to_gen["company"] == sel_company]
            if sel_employee != "— All Employees —":
                df_to_gen = df_to_gen[df_to_gen["name"] == sel_employee]

            # 4. Action Button (Full width matching image)
            if st.button("🚀 Generate Emails", use_container_width=True):
                if df_to_gen.empty:
                    st.warning("No prospects match your filter criteria.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    for index, p in enumerate(df_to_gen.iterrows()):
                        p_data = p[1]
                        status_text.text(
                            f"Processing {index+1}/{len(df_to_gen)}: {p_data['name']} ({p_data['company']})"
                        )

                        # Logic to skip if already generated
                        if skip_gen:
                            existing = conn.execute(
                                "SELECT COUNT(*) FROM messages WHERE prospect_id=? AND channel='email'",
                                (p_data["id"],),
                            ).fetchone()[0]
                            if existing > 0:
                                progress_bar.progress((index + 1) / len(df_to_gen))
                                continue

                        # Call your existing AI sequence function
                        seq = get_8_step_email_sequence(
                            p_data["name"], p_data["company"]
                        )

                        for step in seq:
                            conn.execute(
                                """
                                INSERT INTO messages (prospect_id, channel, stage, subject, content, status) 
                                VALUES (?, 'email', ?, ?, ?, '0')
                            """,
                                (
                                    p_data["id"],
                                    step["label"],
                                    step["sub"],
                                    step["body"],
                                ),
                            )

                        conn.commit()
                        progress_bar.progress((index + 1) / len(df_to_gen))

                    status_text.empty()
                    st.success(
                        f"Successfully generated sequences for {len(df_to_gen)} leads!"
                    )
        else:
            st.info(
                "No email prospects found in the master database. Please upload leads first."
            )

    # --- 5. GENERATED EMAILS ---
    with tab_gen:
        st.subheader("✉️ Review & Send Emails")

        # 1. Fetch all pending emails (Status '0' = Generated/Draft)
        df_raw = pd.read_sql_query(
            """
            SELECT m.id, m.stage, m.subject, m.content, p.name, p.company, p.email as p_email 
            FROM messages m 
            JOIN prospects p ON p.id = m.prospect_id 
            WHERE m.channel='email' AND m.status='0' 
            ORDER BY m.stage ASC, p.id ASC
        """,
            conn,
        )

        if not df_raw.empty:
            # --- SECTION: FILTERS ---
            st.markdown("#### 🔍 Filter Outreach Targets")
            c1, c2 = st.columns(2)

            f_comp = c1.selectbox(
                "Filter Company",
                ["All"] + sorted(df_raw["company"].unique().tolist()),
                key="gen_c",
            )

            rel_n = df_raw["name"].unique().tolist()
            if f_comp != "All":
                rel_n = df_raw[df_raw["company"] == f_comp]["name"].unique().tolist()
            f_name = c2.selectbox("Filter Person", ["All"] + sorted(rel_n), key="gen_e")

            # Create the filtered view
            df_filtered_view = df_raw.copy()
            if f_comp != "All":
                df_filtered_view = df_filtered_view[
                    df_filtered_view["company"] == f_comp
                ]
            if f_name != "All":
                df_filtered_view = df_filtered_view[df_filtered_view["name"] == f_name]

            st.divider()

            # --- SECTION: BULK SENDING (Linked to Filters) ---
            with st.expander("🚀 Bulk Sending Options", expanded=True):
                # Get sequence steps available WITHIN the filtered list
                filtered_stages = sorted(df_filtered_view["stage"].unique().tolist())

                bulk_col1, bulk_col2 = st.columns([2, 1])
                selected_bulk_stage = bulk_col1.selectbox(
                    "Select Sequence Step to Send", filtered_stages
                )

                bulk_targets = df_filtered_view[
                    df_filtered_view["stage"] == selected_bulk_stage
                ]
                button_label = f"Send {len(bulk_targets)} Mails"

                if bulk_col2.button(
                    button_label, use_container_width=True, type="primary"
                ):
                    if not user_mail or not app_pass:
                        st.error("Configure Email & App Password in the sidebar.")
                    elif len(bulk_targets) == 0:
                        st.warning("No emails match selection.")
                    else:
                        progress_bar = st.progress(0)
                        success_count = 0

                        for i, (_, row) in enumerate(bulk_targets.iterrows()):
                            if send_email_smtp(
                                row["p_email"],
                                row["subject"],
                                row["content"],
                                user_mail,
                                app_pass,
                            ):
                                # Update using your utility function
                                update_message_status(row["id"], "sent")
                                success_count += 1

                            progress_bar.progress((i + 1) / len(bulk_targets))
                            time.sleep(1)  # Gmail Safety

                        st.success(f"Successfully sent {success_count} emails!")
                        time.sleep(1)
                        st.rerun()

            st.divider()

            # --- SECTION: INDIVIDUAL REVIEW ---
            st.markdown("#### 📋 Individual Review & Edit")

            # Display current filtered queue in a table
            st.dataframe(
                df_filtered_view[["company", "name", "stage", "subject"]],
                use_container_width=True,
                hide_index=True,
            )

            # Dropdown for specific mail review
            if "idx" not in st.session_state:
                st.session_state.idx = 0
            st.session_state.idx = min(st.session_state.idx, len(df_filtered_view) - 1)

            opts = [
                f"{r['name']} ({r['company']}) - {r['stage']}"
                for _, r in df_filtered_view.iterrows()
            ]
            sel = st.selectbox(
                "Select Draft to Review", opts, index=st.session_state.idx
            )
            row = df_filtered_view.iloc[opts.index(sel)]

            with st.container(border=True):
                st.write(f"**To:** {row['p_email']}")
                edit_sub = st.text_input(
                    "Subject", row["subject"], key=f"edit_sub_{row['id']}"
                )
                edit_body = st.text_area(
                    "Body Content",
                    row["content"],
                    height=250,
                    key=f"edit_bod_{row['id']}",
                )

                if st.button("📤 Send Individual Email"):
                    if send_email_smtp(
                        row["p_email"], edit_sub, edit_body, user_mail, app_pass
                    ):
                        update_message_status(row["id"], "sent")
                        st.success(f"Sent to {row['name']}!")
                        # Advance index for easier reviewing
                        st.session_state.idx = (st.session_state.idx + 1) % len(
                            df_filtered_view
                        )
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("No pending drafts found. Use 'Run Pipeline' to generate emails.")

    # --- 6. FOLLOW-UP TRACKER ---
    with tab_track:
        st.subheader("Sent Outreach History")
        df_track = pd.read_sql_query(
            """
            SELECT p.name as 'Lead', p.company as 'Company', m.subject as 'Last Subject', m.status 
            FROM messages m JOIN prospects p ON p.id=m.prospect_id 
            WHERE m.channel='email' AND m.status='sent'
        """,
            conn,
        )
        st.dataframe(df_track, use_container_width=True, hide_index=True)

    # --- 7. SMTP SETTINGS (New Tab) ---
    with tab_settings:
        st.subheader("⚙️ Email SMTP Configuration")
        st.markdown(
            """
        **Setup Instructions:**
        1. Enable **2-Step Verification** in your Google Account.
        2. Generate an **App Password** (Select 'Mail' and 'Other/Custom Name').
        3. Paste the 16-character code below.
        """
        )

        # Ensure settings table exists
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )

        # Load existing credentials from DB
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
            new_pass = st.text_input("App Password", value=saved_pass, type="password")

            if st.form_submit_button("💾 Save Credentials"):
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
                    st.success("Settings Saved!")
                    st.rerun()
                else:
                    st.error(
                        "Please enter a valid Gmail and a 16-character App Password."
                    )

        st.divider()

        # Connection Tester
        st.markdown("#### 🧪 SMTP Connection Test")
        test_to = st.text_input(
            "Recipient Email for Test", placeholder="test@example.com"
        )
        if st.button("🚀 Run Test"):
            if not saved_user or not saved_pass:
                st.warning("Please save your credentials first.")
            elif not test_to:
                st.error("Recipient email required.")
            else:
                with st.spinner("Testing connection..."):
                    # Uses your existing send_email_smtp function
                    success = send_email_smtp(
                        test_to,
                        "FusionX SMTP Test",
                        "Your SMTP configuration is working perfectly!",
                        saved_user,
                        saved_pass,
                    )
                    if success:
                        st.success(f"Test email successfully sent to {test_to}!")
                    else:
                        st.error(
                            "Connection failed. Check your App Password or Internet connection."
                        )

    conn.close()


# ================== MODE 3: MASTER DATABASE ==================
elif mode == "Master Database":
    st.title("🗄️ Master Prospect Database")
    conn = sqlite3.connect("data/fusionx_unified.db")
    master_df = pd.read_sql_query(
        "SELECT id, name, company, industry, email, linkedin, created_at FROM prospects",
        conn,
    )
    st.dataframe(master_df, use_container_width=True, hide_index=True)
    conn.close()
