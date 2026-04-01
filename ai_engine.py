def generate_vamshi_sequence(data):
    name = data.get('Name', 'there')
    company = data.get('Company', 'your company')
    # Simplified LinkedIn sequence
    return {
        "Intro": f"Hi {name}, saw your profile and loved the work at {company}!",
        "Value": f"I think our NLQ tool could save {company} a lot of time.",
        "Meeting": "Do you have 5 minutes next week?"
    }

def get_8_step_email_sequence(name, company):
    fname = name.split()[0] if name else "there"
    return [
        {"label": "Step 1", "sub": f"Question for {company}", "body": f"Hi {fname}, I noticed {company} handles a lot of data..."},
        {"label": "Step 2", "sub": "Quick follow up", "body": f"Hi {fname}, just checking if you saw my last mail..."},
        {"label": "Step 3", "sub": "Idea for analytics", "body": f"Hi {fname}, we helped similar companies save 10 hours a week..."},
        {"label": "Step 4", "sub": "Removing SQL backlogs", "body": f"Hi {fname}, FusionX can eliminate your SQL backlogs..."},
        {"label": "Step 5", "sub": "Better BI", "body": f"Hi {fname}, imagine natural language querying for your team..."},
        {"label": "Step 6", "sub": "Social proof", "body": f"Hi {fname}, our users love the dashboard customization..."},
        {"label": "Step 7", "sub": "One last try", "body": f"Hi {fname}, thought I'd send one more message..."},
        {"label": "Step 8", "sub": "Moving on", "body": f"Hi {fname}, I'll stop my outreach for now. Best of luck!"}
    ]