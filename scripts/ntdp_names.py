"""Canonical athlete names for the Beach NTDP rosters.

USAV publishes the same girl under several spellings. Three kinds occur, and
they need different treatment:

  * footnote markers and casing -- "Nariah* Johnson", "ELLA Dueck". Mechanical,
    fixed by `clean()`.
  * two Volleyball Life profiles, or one spelling that resolves and one that
    does not -- caught downstream by merging on the resolved profile id.
  * nicknames and dropped middle names -- "Abby"/"Abigail Moffett",
    "Gabriella Sandie"/"Sandie Souza". Neither mechanical nor resolvable, so
    they are listed below by hand.

Same-surname pairs are NOT merged on a shared birthdate: Mallory and Molly
LaBreche are twins with separate profiles, as are several other sister pairs.
"""
import re, unicodedata

# Roster spelling -> the spelling it is filed under. Each pair was checked for
# a shared surname, a plausible nickname, and no overlapping series.
ALIAS = {
    "Abigail Moffett": "Abby Moffett",              # 2026 Fall only; Abby 2023-2026
    "Lillian Sprague": "Lily Sprague",
    "Gabriella Sandie Souza": "Sandie Souza",
    "Emmerson Champagne": "Emma Champagne",         # 2nd VBL profile, 0 matches, same dob
    "JoJo Wilson": "Kylee (JoJo) Wilson",
    "JoJo (Kylee-Jo) Wilson": "Kylee (JoJo) Wilson",
}


def clean(s):
    """Strip footnote markers and stray whitespace; leave casing alone."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[*†‡#^~¹²³]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def key(first, last):
    """The case- and marker-insensitive identity of a roster line."""
    return ALIAS.get(f"{clean(first)} {clean(last)}",
                     f"{clean(first)} {clean(last)}").lower()


def display(variants):
    """The nicest of the spellings seen for one athlete.

    An alias target wins outright -- it is the spelling this file chose. Failing
    that, prefer a spelling with no SHOUTED word, then the longest (which keeps
    a parenthetical nickname), then alphabetical, so the pick is stable.
    """
    for v in variants:
        if v in ALIAS.values():
            return v
    shout = lambda v: sum(1 for w in v.split() if len(w) > 1 and w.isupper())
    return sorted(variants, key=lambda v: (shout(v), -len(v), v))[0]
