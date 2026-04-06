def generate_vamshi_sequence(data):
    name = data.get("Name", "there")
    fname = name.split()[0] if name else "there"
    company = data.get("Company", "your company")

    return {
        "Intro": f"Hi {fname}! I came across your profile and was really impressed by the work you're doing at {company}. Would love to connect!",
        "Follow-up 1": f"Hey {fname}, thanks for connecting! I noticed {company} works with a lot of data — curious, how does your team currently handle analytics queries?",
        "Follow-up 2": f"Hi {fname}, just wanted to share — we built FusionX to let non-technical teams query data in plain English, no SQL needed. Thought it might be relevant for {company}.",
        "Follow-up 3": f"Hey {fname}, companies like yours have saved 10+ hours/week by eliminating back-and-forth with data teams. Happy to show you a quick demo if you're open to it!",
        "Follow-up 4": f"Hi {fname}, I put together a short 2-min walkthrough of how FusionX works — would it be okay if I sent it over? No strings attached.",
        "Follow-up 5": f"Hey {fname}, just bumping this up in case it got buried! Would a 15-min call next week work to see if FusionX could help {company}'s team?",
        "Follow-up 6": f"Hi {fname}, last nudge from me — if the timing isn't right, totally understand. Just let me know and I'll follow up later down the road.",
        "Follow-up 7": f"Hey {fname}, closing the loop here. If you ever want to explore how FusionX can help {company} move faster with data, I'm just a message away. Wishing you all the best! 🙌",
    }


def get_8_step_email_sequence(name, company):
    fname = name.split()[0] if name else "there"
    return [
        {
            "sub": f"Question regarding {company}'s data workflow",
            "body": f"Hi {fname},\n\nI've been following {company}'s recent growth and wanted to reach out.\n\nWe built FusionX — a tool that lets your team query data in plain English, no SQL needed.\n\nWould love to show you how it works.\n\nBest,\nVamshi",
        },
        {
            "sub": f"Data accessibility at {company}",
            "body": f"Hi {fname},\n\nFollowing up on my last message. Curious — how does your team currently pull reports or answer ad-hoc data questions?\n\nFusionX removes that bottleneck entirely.\n\nBest,\nVamshi",
        },
        {
            "sub": f"The 'SQL Tax' at {company}",
            "body": f"Hi {fname},\n\nIn most companies, analysts spend 60% of their time just writing queries — not analyzing.\n\nFusionX flips that. Your team types questions, gets charts.\n\nWorth a 15-min chat?\n\nBest,\nVamshi",
        },
        {
            "sub": "Conversational BI",
            "body": f"Hi {fname},\n\nImagine typing 'revenue trend last quarter by region' and getting a live chart in seconds.\n\nThat's exactly what FusionX does. No dashboards to build, no tickets to file.\n\nBest,\nVamshi",
        },
        {
            "sub": "Efficiency update",
            "body": f"Hi {fname},\n\nFusionX automates the visualization layer so your team focuses on decisions, not data wrangling.\n\nHappy to send a 2-min demo video if helpful?\n\nBest,\nVamshi",
        },
        {
            "sub": "Strategic data democratization",
            "body": f"Hi {fname},\n\nEmpowering non-technical users at {company} to self-serve their data needs could free up your analysts for high-value work.\n\nThat's the core of what FusionX does.\n\nBest,\nVamshi",
        },
        {
            "sub": "Eliminating backlogs",
            "body": f"Hi {fname},\n\nFusionX acts like a 24/7 analyst for your team — answering data questions instantly, without a queue.\n\nWould love to show you a live example with your use case.\n\nBest,\nVamshi",
        },
        {
            "sub": "ROI of AI at {company}",
            "body": f"Hi {fname},\n\nFusionX typically pays for itself within the first month through hours saved on reporting alone.\n\nIf you're open to a quick call, I can share exactly how.\n\nBest,\nVamshi",
        },
        {
            "sub": "Closing the loop",
            "body": f"Hi {fname},\n\nI'll stop reaching out after this — but if you ever want to explore how FusionX can help {company} move faster with data, I'm just an email away.\n\nWishing you all the best!\n\nVamshi",
        },
    ]
