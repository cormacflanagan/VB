"""Beach NTDP Summer Training Series 2026 rosters, resolved to Volleyball Life player IDs.

Names and USAV regions come from USA Volleyball's published roster page. IDs were
resolved by name search against Volleyball Life and checked against date of birth,
graduation year, club and competition footprint.
"""

GROUPS = {
    "18U": {
        "label": "Girls U18",
        "roster": [
            ("Simrin Adams", 25289, "So. Cal / So. Nevada"),
            ("Sarah Albers", 84161, "Gateway"),
            ("Sienna Castillo", 29854, "Northern California"),
            ("Sarah Cowan", 84725, "Florida"),
            ("Sadie Harris", 94909, "So. Cal / So. Nevada"),
            ("Olivia Herron", 28688, "North Texas"),
            ("Sage Illian", 91052, "Heart of America"),
            ("Lauren Leach", 8426, "So. Cal / So. Nevada"),
            ("Georgeann Lee", 61785, "Aloha"),
            ("Janie McCanna", 24515, "Puget Sound"),
            ("Milaniakai Padilla", 95165, "Aloha"),
            ("Sadie Stafford", 147394, "Old Dominion"),
            ("Jordyn Wilson", 23868, "So. Cal / So. Nevada"),
        ],
    },
    "17U": {
        "label": "Girls U17",
        "roster": [
            ("Regina Stella Broshear", 64782, "Northern California"),
            ("Ella Buchanan", 98125, "So. Cal / So. Nevada"),
            ("Reagan Carlin", 92974, "So. Cal / So. Nevada"),
            ("Sienna Cicero", 124871, "So. Cal / So. Nevada"),
            ("Cayden Dorger", 128445, "Gulf Coast"),
            ("Haisley Flanagan", 64896, "Northern California"),
            ("Madison Gillinger", 99596, "So. Cal / So. Nevada"),
            ("Julianna Godbey", 58303, "North Texas"),
            ("Taylie Hansen", 99506, "Florida"),
            ("Emerson Harper", 80837, "So. Cal / So. Nevada"),
            ("Charlotte Jansen", 161398, "So. Cal / So. Nevada"),
            ("Nariah Johnson", 92193, "So. Cal / So. Nevada"),
            ("Olivia LeDoyen", 30929, "So. Cal / So. Nevada"),
            ("Lucy Matuszak", 22544, "So. Cal / So. Nevada"),
            ("Brooke Proctor", 91896, "So. Cal / So. Nevada"),
            ("Milana Rivera", 60877, "Lone Star"),
            ("Ashley Ruschill", 105245, "North Texas"),
            ("Elyse Smelcer", 77570, "Carolina"),
            ("Elle Sossong", 33084, "Keystone"),
            ("Ella Whiteside", 70421, "North Texas"),
        ],
    },
}

# The class-of-2028 group is generated, not published: see discover2028.py. Its roster is
# the 30 highest-TruVolley girls in a partner-graph crawl of the class (449 found, 410
# rated). A convergence pass over the top 60's partners surfaced 50 more players and none
# above the #30 cut, so the top 30 is stable.
try:
    import json as _json, os as _os
    _p = _os.path.join(_os.path.dirname(__file__), "roster_2028.json")
    _d = _json.load(open(_p))
    GROUPS["2028"] = {"label": _d["label"],
                      "roster": [tuple(x) for x in _d["roster"]],
                      "meta": _d.get("meta", {}), "thresh": 8}
except FileNotFoundError:
    pass

WINDOW = ("2025-08-09", "2026-08-09")
