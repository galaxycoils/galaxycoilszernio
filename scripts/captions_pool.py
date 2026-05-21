"""
Shared caption pools for all scheduling, recovery, and rebuild scripts.

Centralizes MICRO_HOOKS, VALUE_CAPTIONS, and CTA_CAPTIONS so the
engagement pivot (30% CTA / 30% Empty / 22% Micro-hook / 18% Value)
stays consistent across schedule_5_per_day.py, rebuild_viral_queue.py,
and update_empty_posts.py without drift.

Last updated: 2026-05-20 — Engagement Pivot (expanded CTA pool from 4 → 21).
"""

MICRO_HOOKS = [
    "Clean line, hard drop.",
    "Too smooth.",
    "Locked in.",
    "Frame it tighter.",
    "Built for rewatch.",
    "Precision beats speed.",
    "One pass only.",
    "The angle matters.",
    "Worth the reset.",
    "Watch the pacing.",
]

VALUE_CAPTIONS = [
    "Save this: 3 drone moves that instantly look more cinematic.",
    "Save for your next flight: slower yaw, lower altitude, longer hold.",
    "If your footage feels flat, fix these first: speed, horizon, entry.",
    "Save this framing rule: one subject, one direction, one clean exit.",
    "Drone edit tip: cut on motion, not on music alone.",
    "Save this if you shoot real estate: reveal late, not immediately.",
    "Save this workflow: shoot once, crop for reels, stories, and ads.",
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
