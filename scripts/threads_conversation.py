import random
from typing import List

# Pools for high-engagement 'First Replies'
TECHNICAL_QUESTIONS = [
    "What's your drone setup for this shot? ND filters or raw?",
    "Did you use manual exposure or auto for those highlights?",
    "FPV or cinematic drone? The stabilization looks incredible.",
    "What frame rate was this shot at? 60fps slowed down?",
    "Is this the Mavic 3 Pro or the Mini 4? The dynamic range is wild.",
    "How do you handle signal interference in urban areas like this?",
    "What color profile are you using? D-Log M?",
    "Did you have to get a permit for this flight, or is it a 'fly and pray' zone?",
]

HOT_TAKES = [
    "Unpopular opinion: Golden hour is overrated. Blue hour is where the real magic happens. 🌑",
    "POV: People who think drones are just toys haven't seen this.",
    "Stop buying expensive drones until you master the basics of composition. 📸",
    "Vertical video is the future, whether the purists like it or not.",
    "AI-generated backgrounds will never beat the feeling of a real 5am sunrise flight.",
    "Most 'cinematic' drone videos are just 4K shots of nothing. This is actual art.",
    "The best drone is the one you actually have with you. Fight me.",
]

ENGAGEMENT_PROMPTS = [
    "If you could fly here for 24 hours, what's the first thing you'd capture?",
    "Scale of 1-10: How much does this make you want to travel right now?",
    "Drop your favorite drone emoji if you're a pilot! 🚁🛸",
    "Tag a friend who needs to see this view. 👇",
    "Which is better: City lights or Mountain peaks? Let's settle this.",
]

def generate_first_reply() -> str:
    """
    Returns a random high-engagement reply to kickstart the conversation.
    """
    category = random.choice([TECHNICAL_QUESTIONS, HOT_TAKES, ENGAGEMENT_PROMPTS])
    return random.choice(category)

def get_reply_strategy(post_text: str) -> str:
    """
    Analyzes the post text to pick the most relevant reply type.
    (Simple implementation for now)
    """
    text = post_text.lower()
    if any(word in text for word in ["camera", "gear", "setup", "filter", "settings"]):
        return random.choice(TECHNICAL_QUESTIONS)
    if any(word in text for word in ["opinion", "agree", "disagree", "better"]):
        return random.choice(HOT_TAKES)
    
    return generate_first_reply()
