def generate_vamshi_sequence(row):
    name = str(row['Name']).split()[0]
    comp = row['Company']
    ind = row['Industry']
    
    return {
        "START": f"Hi {name}, I'm Vamshi from DVK Analytics. We help {ind} teams at {comp} use AI search for data. Open for a 15-minute call?",
        "F1": f"Checking in, {name}! FusionX gives {comp} a 'Google-like' search for your Sisense data. Worth a chat?",
        "F2": f"Hi {name}, most {ind} leaders tell me they're tired of dashboard fatigue. We solve that. Chat this week?",
        "F3": f"Quick thought, {name}—imagine if your team could just ask a question in plain English. Open for 15 mins?",
        "F4": f"Hope your week is great! Just sharing how we help {ind} companies simplify Sisense. Got 15 mins?",
        "F5": f"Hey {name}, our 'Zero-Data Exposure' setup for {comp} keeps your data secure. Open for 15 mins?",
        "F6": f"Happy Friday! If 'dashboard fatigue' is an issue at {comp}, I'd love to show our fix. Next Tuesday?",
        "F7": f"Hi {name}, bumping this one last time. Love to hear your thoughts on AI for {comp}. 15 mins?",
        "F8": f"Final note, {name}—I'll stop bugging you, but here is our link if things change. Always down for a chat!"
    }