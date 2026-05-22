"""
Shared caption pools for all scheduling, recovery, and rebuild scripts.

Centralizes MICRO_HOOKS, VALUE_CAPTIONS, and CTA_CAPTIONS so the
engagement pivot (30% CTA / 30% Empty / 22% Micro-hook / 18% Value)
stays consistent across schedule_5_per_day.py, rebuild_viral_queue.py,
and update_empty_posts.py without drift.

Last updated: 2026-05-21 — V8 SEO & DM Share Optimization.
"""

MICRO_HOOKS = [
    "Clean line, hard drop. Send this to a pilot who needs to see this. 👇",
    "Too smooth. DM this to someone who loves FPV. 1-10?",
    "Locked in. Tag your flight partner or share to their DMs.",
    "Frame it tighter. Share this with your favorite creator.",
    "Built for rewatch. Send this to a friend who needs a mental break.",
    "Precision beats speed. DM this to a speed freak. 👇",
    "One pass only. Share if you think I nailed it.",
    "The angle matters. DM this to a photography nerd.",
    "Worth the reset. Share this with someone who never gives up.",
    "Watch the pacing. DM this to a fellow editor. Too slow?",
    "Which view would you wake up to? Share with your travel buddy. 🏔️",
    "POV: Best city view. Send this to someone who needs a vacation.",
    "The way the light hits... DM this to your favorite person.",
    "Unreal texture. Send this to a friend who loves the outdoors.",
    "Frame by frame perfection. Share this with a tech geek.",
    "High altitude, low stress. DM this to someone who needs this vibe.",
]

VALUE_CAPTIONS = [
    "Save & Share: 3 drone moves for cinematic shots. Send this to a friend learning to fly! 1. Low tilt-up. 2. Orbit reveal. 3. Top-down tracking.",
    "Flight Tip: slower yaw = better footage. DM this to your drone squad.",
    "Fix flat footage: consistent speed & level horizon. Share with a creator who needs this.",
    "Framing Rule: one subject, one direction. Send this to your production partner.",
    "Edit tip: cut on motion, not just beats. DM this to an editor.",
    "Real Estate Reveal: don't show the whole house at once. Share with a realtor friend.",
    "Workflow: 4K 16:9 to 9:16 crop. DM this to someone starting their YouTube journey.",
    "Quick tip: ND filters are essential for motion blur. Share with a camera enthusiast.",
    "Cinematic Settings: 4K/24fps, 1/50 shutter. DM this to a pilot.",
]

CTA_CAPTIONS = [
    "Rate this 1-10 and send to a friend! 👇",
    "FPV or Cinematic? Share your vote with a buddy. 👇",
    "Tag your travel partner & DM them this spot! ✈️",
    "Drop a 🚁 and send this to your drone crew.",
    "Who needs this vibe? Share it to their DMs right now! ✨",
    "Where is this? Send this to a friend and ask them! 👇",
    "Drop a 🔥 and share with someone who loves travel.",
    "Rate this 1-10. DM this to your best friend.",
    "Send this to a friend who needs a vacation here.",
    "Would you fly this? Share with a pilot friend.",
    "Best place for a flight? DM us your favorite spot!",
    "What's the first thing you'd shoot? Share with a creative.",
    "Handle this drop? Send to an FPV daredevil.",
    "Yes or No? Share with someone who needs to see this.",
    "Tag your flight partner & DM them this line.",
    "Drop a ❤️ and share this with your soulmate.",
    "Which angle won? DM a friend to get their opinion.",
    "Which shot would you keep? Share with an editor.",
    "Too slow? DM this to a speed enthusiast.",
    "Would you post this? Share with a social manager.",
    "Which angle hits harder? DM your squad.",
    "Send this to your FPV buddy 🏎️",
    "Share this with someone who needs a 4K reset. 🌍",
    "Save this for your bucket list & DM your travel group. 📍",
    "Who's coming with you? DM them this reel. 👥",
    "Send this to the first person that comes to mind. 📩",
    "POV: New favorite spot. Share with your adventure partner.",
    "Tag your drone squad & DM them this flight path! 🚁",
    "Where next? DM us your ideas! 👇",
    "Rate it 1-100! Send to a friend who loves numbers.",
    "POV: Living in a dream. Share with a dreamer. ✨",
    "Tag someone & DM them this crazy angle.",
    "Best drone move? Share with a pro pilot. 🔥",
    "FPV or standard? DM your choice to a friend. 👇",
    "This is why we fly. Share if you agree. ❤️",
    "Drop a 📍 and share with someone who wants the location.",
    "Notice the transition? DM this to a transition master.",
    "Tag a pilot & share to help them level up. 📈",
    "Could you fly this? Send to a friend and challenge them!",
    "Notice the lighting? DM this to a lighting pro.",
    "Save & Share for your next adventure moodboard.",
    "POV: Zero stress. Send this to someone who needs to relax.",
    "Tag someone who loves this vibe & DM it to them.",
    "Ultimate drone shot? Share with a photography fan. 👇",
    "Smooth as butter. DM this to someone who loves clean edits. 🧈",
]

# Generic Hooks with DM triggers
GENERIC_HOOKS = [
    "Clean lines and high altitude. Share with a friend!",
    "POV: Paradise. DM this to someone who needs a getaway!",
    "The perfect morning. Send this to a morning person.",
    "Just another day. Tag your flight buddy & DM them.",
    "Notice the texture. Share with a design lover.",
    "Locked in. DM this to an FPV pilot.",
    "One take, no edits. Share with a purist.",
    "Drone photography is the future. DM this to a techie.",
    "FPV flow. Share with your flight crew.",
    "Wait for the exit... Send this to a friend who likes surprises.",
]
