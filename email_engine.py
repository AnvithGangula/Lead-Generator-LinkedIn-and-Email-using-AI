import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

def send_email_smtp(to_email, subject, body, sender_email, app_password):
    """Handles the actual sending of the email via Gmail SMTP"""
    if not sender_email or not app_password:
        st.error("❌ Setup Required: Enter Email & App Password in the Sidebar.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail Error: {str(e)}")
        return False

def get_8_step_email_seq(name, company):
    """Generates the 8-part email sequence for a prospect"""
    fname = name.split()[0] if name else "there"
    return [
        {"sub": f"Question regarding {company}'s data workflow", "body": f"Hi {fname},\n\nI’ve been following {company}’s recent growth..."},
        {"sub": f"Data accessibility at {company}", "body": f"Hi {fname},\n\nFollowing up..."},
        {"sub": f"The 'SQL Tax' at {company}", "body": f"Hi {fname},\n\nIn many organizations..."},
        {"sub": "Conversational BI", "body": f"Hi {fname},\n\nImagine typing 'NSR trend'..."},
        {"sub": "Efficiency update", "body": f"Hi {fname},\n\nFusionX automates visualization..."},
        {"sub": "Strategic democratization", "body": f"Hi {fname},\n\nEmpowering users..."},
        {"sub": "Eliminating backlogs", "body": f"Hi {fname},\n\nFusionX acts like a 24/7 analyst..."},
        {"sub": "ROI of AI", "body": f"Hi {fname},\n\nFusionX often pays for itself..."},
        {"sub": "Closing the loop", "body": f"Hi {fname},\n\nI'll stop my outreach for now..."}
    ]