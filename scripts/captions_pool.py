"""
Shared caption pools for all scheduling, recovery, and rebuild scripts.

Centralizes MICRO_HOOKS, VALUE_CAPTIONS, and CTA_CAPTIONS so the
engagement pivot (30% CTA / 30% Empty / 22% Micro-hook / 18% Value)
stays consistent across schedule_5_per_day.py, rebuild_viral_queue.py,
and update_empty_posts.py without drift.

Last updated: 2026-05-20 — Engagement Pivot (expanded CTA pool from 4 → 21).
"""

MICRO_HOOKS = [
    "Clean line, hard drop. Could you fly this? 👇",
    "Too smooth. What do you rate this? 1-10",
    "Locked in. Tag your flight partner.",
    "Frame it tighter. Wait for the exit...",
    "Built for rewatch. Notice the yaw?",
    "Precision beats speed. Agree or disagree? 👇",
    "One pass only. Did I nail it?",
    "The angle matters. Watch the horizon.",
    "Worth the reset. How many tries did this take?",
    "Watch the pacing. Too slow or just right?",
]

VALUE_CAPTIONS = [
    "Save this: 3 drone moves that instantly look more cinematic. 1. Low and slow tilt-up. 2. The orbit reveal. 3. Top-down tracking.",
    "Save for your next flight: slower yaw, lower altitude, longer hold. That's the cinematic formula.",
    "If your footage feels flat, fix these first: keep your speed consistent, level the horizon, and hold the exit frame.",
    "Save this framing rule: one subject, one direction, one clean exit. Less is more.",
    "Drone edit tip: cut on motion, not just on the beat drop. It hides the cut.",
    "Save this if you shoot real estate: reveal late. Don't show the whole property in the first 2 seconds.",
    "Save this workflow: shoot in 4K 16:9, crop to 9:16 for Reels, and 1:1 for the grid. Maximize your flight time.",
]

CTA_CAPTIONS = [
    "Rate this flight 1-10 below 👇",
    "FPV or Cinematic? Vote below 👇",
    "Tag your travel partner ✈️",
    "Drop a 🚁 if you'd fly this line.",
    "Who else needs this vibe right now? ✨",
    "Where is this? (Wrong answers only) 👇",
    "Drop a 🔥 if you want the location.",
    "Rate this 1-10.",
    "Tag someone who needs a vacation here.",
    "Would you fly this drone?",
    "Best place for a flight?",
    "What's the first thing you'd shoot here?",
    "Could you handle this drop?",
    "Yes or No?",
    "Tag your flight partner.",
    "Drop a ❤️ if you want to be here.",
    "Which angle won?",
    "Which shot would you keep?",
    "Too slow or just right?",
    "Would you post this take?",
    "Which angle hits harder?",
]
