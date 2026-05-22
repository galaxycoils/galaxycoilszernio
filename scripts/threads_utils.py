import random
import re

def enrich_for_threads(caption: str) -> str:
    """
    Transforms an Instagram caption into a high-engagement Threads post.
    - Removes excessive hashtag blocks.
    - Adds conversational 'Thread openers'.
    - Injects engagement-focused questions.
    """
    # 1. Strip the hashtag block (standard Instagram clutter)
    clean_text = re.sub(r'\n\n#\S+.*$', '', caption, flags=re.MULTILINE).strip()
    
    # 2. Randomly select a high-engagement 'Thread Opener'
    openers = [
        "Unpopular opinion: Drone shots are better than static photography. 🚁 Here's why:",
        "Stop scrolling. You need to see this angle. 👇",
        "The drone community on Threads is unmatched. What do you think of this line?",
        "Real talk: How much would you pay for a view like this?",
        "POV: You're flying FPV and the world just disappears.",
        "Quick question for the pilots here: What's your go-to ND filter for this light?",
        "If you could fly anywhere in the world tomorrow, where would it be?",
        "Leveling up the cinematic game one flight at a time.",
    ]
    
    # 3. Randomly select a 'Engagement Closer'
    closers = [
        "Drop a 'REPLY' if you want to see the raw unedited take.",
        "Quote this and tag your favorite drone pilot. 👥",
        "Help me decide: Should I keep the color grade or go natural?",
        "Tap the ❤️ if you're feeling this vibe today.",
        "Check the link in bio for the full 4K breakdown. 📈",
    ]
    
    thread_post = f"{random.choice(openers)}\n\n{clean_text}\n\n{random.choice(closers)}"
    
    # 4. Final limit check (Threads is 500 chars)
    if len(thread_post) > 480:
        return thread_post[:477] + "..."
        
    return thread_post
