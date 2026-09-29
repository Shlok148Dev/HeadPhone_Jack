"""Normalisation for track identity (SRS 4.4)."""

import pytest

from ingest_ml.identity.normalize import clean_artist, fold, normalise

CASES = [
    # (artist in, title in, norm_artist, norm_title, featured)
    ("Arijit Singh", 'Kesariya (From "Brahmastra")', "arijit singh", "kesariya", ()),
    ("Arijit Singh", "Kesariya (From “Brahmāstra”)", "arijit singh", "kesariya", ()),
    ("Arijit Singh - Topic", "Tum Hi Ho", "arijit singh", "tum hi ho", ()),
    ("T-Series", "Tum Hi Ho (Official Video)", "t series", "tum hi ho", ()),
    ("Arijit Singh", "Channa Mereya (Lyrics)", "arijit singh", "channa mereya", ()),
    ("Arijit Singh", "Arijit Singh - Kesariya", "arijit singh", "kesariya", ()),
    (
        "Pritam",
        "Kesariya - Brahmastra | Ranbir Kapoor | Alia Bhatt | Arijit Singh",
        "pritam",
        "kesariya brahmastra",
        (),
    ),
    ("AP Dhillon", "Excuses ft. Gurinder Gill", "ap dhillon", "excuses", ("Gurinder Gill",)),
    ("Diljit Dosanjh", "Lover (Official Music Video)", "diljit dosanjh", "lover", ()),
    ("Shubh", "Elevated [Official Audio]", "shubh", "elevated", ()),
    ("Jass Manak", "Lehanga (Full Video)", "jass manak", "lehanga", ()),
    ("Queen", "Bohemian Rhapsody - Remastered 2011", "queen", "bohemian rhapsody", ()),
    ("The Beatles", "Let It Be (Remastered 2009)", "the beatles", "let it be", ()),
    (
        "Justin Bieber",
        "Peaches (feat. Daniel Caesar & Giveon)",
        "justin bieber",
        "peaches",
        ("Daniel Caesar", "Giveon"),
    ),
    ("TaylorSwiftVEVO", "Blank Space", "taylor swift", "blank space", ()),
    ("Sidhu Moose Wala feat. AP Dhillon", "Wavy", "sidhu moose wala", "wavy", ("AP Dhillon",)),
    ("Beyoncé", "Halo", "beyonce", "halo", ()),
    (
        "Simon & Garfunkel",
        "The Sound of Silence",
        "simon and garfunkel",
        "the sound of silence",
        (),
    ),
    ("अरिजीत सिंह", "केसरिया", "अरिजीत सिंह", "केसरिया", ()),
    ("ਦਿਲਜੀਤ ਦੋਸਾਂਝ", "ਲਵਰ (Official Video)", "ਦਿਲਜੀਤ ਦੋਸਾਂਝ", "ਲਵਰ", ()),
    ("The Weeknd", "Blinding Lights [4K]", "the weeknd", "blinding lights", ()),
]


@pytest.mark.parametrize(("artist", "title", "n_artist", "n_title", "feat"), CASES)
def test_normalise(
    artist: str, title: str, n_artist: str, n_title: str, feat: tuple[str, ...]
) -> None:
    n = normalise(artist, title)
    assert n.norm_artist == n_artist
    assert n.norm_title == n_title
    assert n.featured == feat
    assert n.norm_key == f"{n_artist}|{n_title}"


def test_display_strings_keep_case() -> None:
    n = normalise("Arijit Singh - Topic", 'Kesariya (From "Brahmastra")')
    assert (n.artist, n.title) == ("Arijit Singh", "Kesariya")


def test_same_song_from_different_players_shares_key() -> None:
    a = normalise("Arijit Singh", 'Kesariya (From "Brahmastra")')
    b = normalise("Arijit Singh - Topic", "Kesariya [Official Audio]")
    c = normalise("ARIJIT SINGH", "kesariya")
    assert a.norm_key == b.norm_key == c.norm_key


def test_title_that_is_only_noise_falls_back() -> None:
    n = normalise("X", "(Official Video)")
    assert n.title == "(Official Video)"


def test_fold_and_clean_artist_helpers() -> None:
    assert fold("  Café   del  Mar!! ") == "cafe del mar"
    assert clean_artist("Badshah ft. Aastha Gill, Rico") == ("Badshah", ("Aastha Gill", "Rico"))
