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

# --- TAB 1: DATA UPLOAD ---
with tab1:
    file = st.file_uploader("Upload Lead List (Excel)", type=["xlsx"])
    if file and st.button("Generate 8-Part Sequences"):
        df = pd.read_excel(file)
        
        # Robust header cleaning to prevent KeyErrors
        df.columns = df.columns.str.strip().str.lower()
        
        # Mapping based on your spreadsheet structure
        name_col = 'company employee name'
        comp_col = 'company name'
        pos_col = 'position'
        link_col = 'linkedin'

        df = df.drop_duplicates(subset=[name_col, comp_col])
        
        for _, row in df.iterrows():
            name = row[name_col]
            company = row[comp_col]
            industry = row[pos_col] 
            linkedin = row[link_col]
            
            if not is_duplicate(name, company):
                ai_input = {'Name': name, 'Company': company, 'Industry': industry}
                seq = generate_vamshi_sequence(ai_input)
                save_full_sequence(name, company, industry, linkedin, seq)
        st.success(f"Campaign Ready for {len(df)} leads!")

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
    
    # FIXED: Removed 'created_at' to prevent DatabaseError
    master_df = pd.read_sql_query("SELECT name, company, industry, linkedin FROM prospects", conn)
    
    if not master_df.empty:
        st.dataframe(master_df, use_container_width=True, hide_index=True)
        st.download_button(
            label="📥 Download CSV",
            data=master_df.to_csv(index=False),
            file_name="fusionx_master_list.csv",
            mime="text/csv"
        )
    else:
        st.info("The database is currently empty.")
    conn.close()