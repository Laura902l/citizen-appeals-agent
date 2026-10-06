"""Reproducible generator of simulated, labelled citizen appeals.

Real appeals contain personal data and cannot be used in the prototype, so the
classifier is trained on synthetic text that imitates typical complaints. The
generator is seeded: the same ``seed`` always yields the same dataset, which is
what makes every reported metric reproducible.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from appeal_agent.models import Appeal

PROBLEMS: dict[str, list[str]] = {
    "roads": [
        "there is a huge pothole in the asphalt",
        "the road surface is cracked and broken",
        "the sidewalk has collapsed near the crossing",
        "the curb is destroyed and cars hit it",
        "deep holes on the road damage car wheels",
        "the pedestrian crossing markings have faded",
        "the road was dug up for repairs and never restored",
    ],
    "lighting": [
        "the street lights do not work at night",
        "the lamp post is broken and the street is dark",
        "streetlights are flickering all evening",
        "a lamp has exposed wires and is sparking",
        "lights in the courtyard are on during the day",
        "the park has no lighting after sunset",
    ],
    "water": [
        "there is no water in the building since morning",
        "a water pipe burst and the street is flooding",
        "the tap water is brown and smells bad",
        "very low water pressure on the upper floors",
        "a manhole is overflowing with sewage",
        "hot water has been switched off for a week",
    ],
    "waste": [
        "the garbage containers have not been emptied for days",
        "trash is piled up next to the bins",
        "the waste collection truck skipped our yard",
        "someone dumped construction waste illegally",
        "the recycling bins are overflowing",
        "rubbish bags are torn open by stray animals",
    ],
    "transport": [
        "the bus does not follow the schedule",
        "bus number 32 skipped our stop again",
        "the bus stop shelter is damaged",
        "buses are overcrowded in the morning",
        "the traffic light at the intersection is not working",
        "the driver was rude and did not stop",
    ],
    "landscaping": [
        "trees in the park have not been trimmed",
        "a fallen tree is blocking the path",
        "the playground equipment is broken",
        "the lawn has not been mowed and weeds are everywhere",
        "benches in the square are broken",
        "the flower beds were destroyed and need replanting",
    ],
    "other": [
        "stray dogs are gathering near the school",
        "loud construction noise at night",
        "graffiti appeared on the building wall",
        "illegal advertising banners were installed",
        "neighbours park cars on the lawn",
        "the information board has wrong phone numbers",
    ],
}

# Phrases that blur category boundaries and make the task realistically noisy.
AMBIGUOUS = [
    "near the bus stop",
    "next to the playground",
    "on the main road",
    "in the dark courtyard",
    "by the garbage area",
    "after the water works",
]

STREETS = [
    "Abay Avenue",
    "Dostyk Avenue",
    "Satpayev Street",
    "Tole Bi Street",
    "Furmanov Street",
    "Zhandosov Street",
    "Seifullin Avenue",
    "Al-Farabi Avenue",
]
OPENINGS = [
    "Hello,",
    "Good afternoon.",
    "Please help!",
    "Dear akimat,",
    "",
    "",
    "Urgent request:",
]
CLOSINGS = [
    "Please fix it as soon as possible.",
    "Thank you.",
    "This has been going on for weeks.",
    "Residents are complaining.",
    "",
    "",
    "Please take action.",
]
URGENT_MARKERS = [
    "It is dangerous for children.",
    "Someone was injured yesterday.",
    "This is an emergency.",
    "There was almost an accident.",
]
FIRST_NAMES = ["Aliya", "Dias", "Madina", "Arman", "Saule", "Timur", "Dana", "Yerlan"]
LAST_NAMES = ["Nurlanova", "Seitkali", "Ibraeva", "Akhmetov", "Zhumabek", "Omarova"]


def _phone(rng: random.Random) -> str:
    digits = "".join(str(rng.randint(0, 9)) for _ in range(7))
    return f"+7 7{rng.randint(0, 9)}{rng.randint(0, 9)} {digits[:3]} {digits[3:5]} {digits[5:]}"


def generate_text(category: str, rng: random.Random, urgent: bool = False) -> tuple[str, str]:
    """Return ``(text, location)`` for one synthetic appeal of ``category``."""
    if category not in PROBLEMS:
        raise ValueError(f"unknown category: {category}")
    street = rng.choice(STREETS)
    location = f"{street} {rng.randint(1, 250)}"
    parts = [rng.choice(OPENINGS), f"At {location}", rng.choice(PROBLEMS[category])]
    if rng.random() < 0.3:
        parts.append(rng.choice(AMBIGUOUS))
    if rng.random() < 0.1:  # multi-problem appeal: the label is the first problem
        other = rng.choice([c for c in PROBLEMS if c != category])
        parts.append(f"and also {rng.choice(PROBLEMS[other])}")
    sentence = " ".join(p for p in parts if p).strip() + "."
    extras = []
    if urgent:
        extras.append(rng.choice(URGENT_MARKERS))
    extras.append(rng.choice(CLOSINGS))
    if rng.random() < 0.4:
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        extras.append(f"My name is {name}, phone {_phone(rng)}.")
    return " ".join([sentence, *[e for e in extras if e]]), location


def generate_appeals(
    n: int,
    *,
    seed: int = 42,
    reference_date: date = date(2026, 10, 5),
    history_days: int = 25,
    urgent_share: float = 0.15,
    closed_share: float = 0.3,
) -> list[Appeal]:
    """Generate ``n`` labelled appeals submitted within ``history_days`` of ``reference_date``."""
    if n < 0:
        raise ValueError("n must be non-negative")
    rng = random.Random(seed)
    categories = list(PROBLEMS)
    appeals: list[Appeal] = []
    for i in range(n):
        category = (
            categories[i % len(categories)] if i < len(categories) else rng.choice(categories)
        )
        urgent = rng.random() < urgent_share
        text, location = generate_text(category, rng, urgent)
        submitted = reference_date - timedelta(days=rng.randint(0, history_days))
        closed_on = None
        if rng.random() < closed_share:
            closed_on = min(reference_date, submitted + timedelta(days=rng.randint(1, 30)))
        appeals.append(
            Appeal(
                appeal_id=f"A{seed:03d}-{i + 1:05d}",
                submitted_on=submitted,
                text=text,
                location=location,
                category=category,
                closed_on=closed_on,
            )
        )
    return appeals
