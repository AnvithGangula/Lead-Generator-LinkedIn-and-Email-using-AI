import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime
from database import init_db, save_full_sequence, is_duplicate, update_message_status
from ai_engine import generate_vamshi_sequence

st.set_page_config(page_title="FusionX Founder CRM", page_icon="🎯", layout="wide")
init_db()

# --- SESSION STATE ---
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if 'focus_prospect_id' not in st.session_state:
    st.session_state.focus_prospect_id = None

if 'focus_source' not in st.session_state:
    st.session_state.focus_source = None

st.title("🏛️ FusionX Founder Control Center")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚀 Launch", "📂 CRM", "🔥 Follow-ups", "🆕 New Leads", "📊 Master View"])

# --- TAB 1: DATA UPLOAD & MANUAL ENTRY ---
with tab1:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("📁 Bulk Upload")
        file = st.file_uploader("Upload Lead List (Excel)", type=["xlsx"])
        if file and st.button("Generate Sequences from Excel", use_container_width=True):
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip().str.lower()
            
            # Mapping based on your spreadsheet structure
            name_col, comp_col, pos_col, link_col = 'company employee name', 'company name', 'position', 'linkedin'
            df = df.drop_duplicates(subset=[name_col, comp_col])
            
            progress_bar = st.progress(0)
            for i, row in df.iterrows():
                name, company, industry, linkedin = row[name_col], row[comp_col], row[pos_col], row[link_col]
                if not is_duplicate(name, company):
                    ai_input = {'Name': name, 'Company': company, 'Industry': industry}
                    seq = generate_vamshi_sequence(ai_input)
                    save_full_sequence(name, company, industry, linkedin, seq)
                progress_bar.progress((i + 1) / len(df))
            st.success(f"✅ Campaign Ready for {len(df)} leads!")

    with col2:
        st.subheader("👤 Manual Entry")
        with st.form("manual_entry_form", clear_on_submit=True):
            m_name = st.text_input("Full Name")
            m_comp = st.text_input("Company Name")
            m_pos = st.text_input("Position / Industry")
            m_link = st.text_input("LinkedIn Profile URL")
            
            submit_manual = st.form_submit_button("Add Lead & Generate Sequence", use_container_width=True)
            
            if submit_manual:
                if m_name and m_comp and m_pos and m_link:
                    if not is_duplicate(m_name, m_comp):
                        # Prepare input for your sequence generator
                        ai_input = {'Name': m_name, 'Company': m_comp, 'Industry': m_pos}
                        seq = generate_vamshi_sequence(ai_input)
                        
                        # Save to Database
                        save_full_sequence(m_name, m_comp, m_pos, m_link, seq)
                        st.success(f"🎯 Added {m_name} to CRM!")
                    else:
                        st.warning("This person already exists in the database.")
                else:
                    st.error("Please fill in all fields.")
# --- TAB 2: CRM SEARCH ---
with tab2:
    conn = sqlite3.connect("data/fusionx_crm.db")
    search_q = st.text_input("🔍 Search Prospects")
    query = "SELECT * FROM prospects"
    if search_q:
        query += f" WHERE name LIKE '%{search_q}%' OR company LIKE '%{search_q}%'"
    
    prospects_df = pd.read_sql_query(query, conn)
    if not prospects_df.empty:
        selection = st.selectbox("Select Prospect", prospects_df.apply(lambda r: f"{r['name']} | {r['company']}", axis=1))
        p_row = prospects_df[prospects_df.apply(lambda r: f"{r['name']} | {r['company']}", axis=1) == selection].iloc[0]
        p_id = p_row['id']
        
        st.link_button(f"🔗 View {p_row['name']}'s Profile", p_row['linkedin'])
        
        msgs = pd.read_sql_query(f"SELECT id, stage, content, status FROM messages WHERE prospect_id = {p_id}", conn)
        for _, row in msgs.iterrows():
            c1, c2 = st.columns([5, 1])
            with c1:
                with st.expander(f"{'✅' if row['status'] else '⏳'} {row['stage']}"):
                    st.code(row['content'], language=None)
            with c2:
                if st.checkbox("Sent", value=bool(row['status']), key=f"crm_{row['id']}"):
                    if not row['status']:
                        update_message_status(row['id'], 1)
                        st.rerun()
    conn.close()

# --- TAB 3: FOLLOW-UP ALERTS ---
with tab3:
    if time.time() - st.session_state.last_refresh > 10:
        st.session_state.last_refresh = time.time()
        st.rerun()

    conn = sqlite3.connect("data/fusionx_crm.db")
    if st.session_state.focus_prospect_id and st.session_state.focus_source == "tab3":
        p_id = st.session_state.focus_prospect_id
        p_info = pd.read_sql_query(f"SELECT * FROM prospects WHERE id = {p_id}", conn).iloc[0]
        st.info(f"🚀 **Action Mode:** {p_info['name']} @ {p_info['company']}")
        
        next_msg = pd.read_sql_query(f"SELECT id, stage, content FROM messages WHERE prospect_id={p_id} AND status=0 ORDER BY id ASC LIMIT 1", conn)
        if not next_msg.empty:
            st.subheader(f"Next Message: {next_msg['stage'].values[0]}")
            st.code(next_msg['content'].values[0], language=None)
            
            col_left, col_space, col_right = st.columns([1, 3, 1.5])
            with col_left:
                if st.button("✅ Confirm Sent", type="primary", key="conf_tab3", use_container_width=True):
                    update_message_status(next_msg['id'].values[0], 1)
                    st.session_state.focus_prospect_id = None
                    st.session_state.focus_source = None
                    st.rerun()
            with col_right:
                st.link_button("🔗 Open LinkedIn to Paste", p_info['linkedin'], use_container_width=True)
            
            if st.button("Back to List", key="back_tab3"):
                st.session_state.focus_prospect_id = None
                st.session_state.focus_source = None
                st.rerun()
    else:
        st.subheader("⏰ Due for Follow-up")
        due_query = "SELECT p.name, m.id, m.stage, m.prospect_id FROM messages m JOIN prospects p ON m.prospect_id = p.id WHERE m.status = 0 AND m.prospect_id IN (SELECT prospect_id FROM messages WHERE status = 1)"
        due_df = pd.read_sql_query(due_query, conn)
        if not due_df.empty:
            for _, row in due_df.groupby('name').first().reset_index().iterrows():
                last_sent_q = f"SELECT sent_at FROM messages WHERE status=1 AND prospect_id={row['prospect_id']} ORDER BY sent_at DESC LIMIT 1"
                last_sent_data = pd.read_sql_query(last_sent_q, conn)
                if not last_sent_data.empty:
                    diff = (datetime.now() - datetime.strptime(last_sent_data['sent_at'][0], "%Y-%m-%d %H:%M:%S")).total_seconds()
                    if diff >= 60:
                        st.warning(f"**{row['name']}** is due for **{row['stage']}**")
                        if st.button(f"👉 Get Message", key=f"alert_{row['id']}"):
                            st.session_state.focus_prospect_id = row['prospect_id']
                            st.session_state.focus_source = "tab3"
                            st.rerun()
                    else:
                        st.caption(f"⏳ {row['name']}: Next step in {int(60 - diff)}s")
    conn.close()

# --- TAB 4: NEW LEADS ---
with tab4:
    conn = sqlite3.connect("data/fusionx_crm.db")
    if st.session_state.focus_prospect_id and st.session_state.focus_source == "tab4":
        p_id = st.session_state.focus_prospect_id
        p_info = pd.read_sql_query(f"SELECT * FROM prospects WHERE id = {p_id}", conn).iloc[0]
        st.info(f"🚀 **Action Mode:** {p_info['name']} @ {p_info['company']}")
        
        start_msg = pd.read_sql_query(f"SELECT id, stage, content FROM messages WHERE prospect_id={p_id} AND stage='START'", conn)
        if not start_msg.empty:
            st.subheader("Send Initial Outreach")
            st.code(start_msg['content'].values[0], language=None)
            
            col_left, col_space, col_right = st.columns([1, 3, 1.5])
            with col_left:
                if st.button("✅ Confirm Sent", type="primary", key="conf_tab4", use_container_width=True):
                    update_message_status(start_msg['id'].values[0], 1)
                    st.session_state.focus_prospect_id = None
                    st.session_state.focus_source = None
                    st.rerun()
            with col_right:
                st.link_button("🔗 Open LinkedIn to Paste", p_info['linkedin'], use_container_width=True)
                
            if st.button("Cancel", key="back_tab4"):
                st.session_state.focus_prospect_id = None
                st.session_state.focus_source = None
                st.rerun()
    else:
        st.subheader("🆕 Untouched Prospects")
        new_df = pd.read_sql_query("SELECT * FROM prospects WHERE id NOT IN (SELECT DISTINCT prospect_id FROM messages WHERE status = 1)", conn)
        if not new_df.empty:
            for idx, row in new_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{row['name']}**")
                        st.caption(f"{row['company']} | {row['industry']}")
                    with col2:
                        if st.button("🚀 Start", key=f"start_{row['id']}"):
                            st.session_state.focus_prospect_id = row['id']
                            st.session_state.focus_source = "tab4"
                            st.rerun()
    conn.close()

# --- TAB 5: MASTER VIEW ---
with tab5:
    st.subheader("📊 Master Prospect Database")
    conn = sqlite3.connect("data/fusionx_crm.db")
    
    # This query joins the tables to calculate status and counts
    query = """
    SELECT 
        p.name AS "Name", 
        p.company AS "Company", 
        p.industry AS "Position",
        p.linkedin AS "LinkedIn",
        MAX(CASE WHEN m.stage = 'START' THEN 
            (CASE WHEN m.status = 1 THEN '✅ Sent' ELSE '⏳ Pending' END) 
        END) AS "Start Status",
        SUM(CASE WHEN m.stage != 'START' AND m.status = 1 THEN 1 ELSE 0 END) AS "Follow-ups Sent"
    FROM prospects p
    LEFT JOIN messages m ON p.id = m.prospect_id
    GROUP BY p.id
    ORDER BY p.id DESC
    """
    
    master_df = pd.read_sql_query(query, conn)
    
    if not master_df.empty:
        # Display the interactive table
        st.dataframe(
            master_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "LinkedIn": st.column_config.LinkColumn("LinkedIn URL")
            }
        )
        
        st.download_button(
            label="📥 Download Full Report (CSV)",
            data=master_df.to_csv(index=False),
            file_name=f"fusionx_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("The database is currently empty. Upload leads in the 'Launch' tab to get started.")
    conn.close()