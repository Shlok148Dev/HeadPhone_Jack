"""Demo world (ADR-0010): personas shared by core-api's seed and ingest-ml's simulator.

Every persona's plays go through the real push endpoint, so the no-false-Live rule and the
honest platform gaps apply exactly as they would for a real user.
"""

import base64
import hashlib
import hmac
from dataclasses import dataclass, field

from .enums import Platform

DEMO_EMAIL = "demo@jingle.local"
DEMO_PASSWORD_DEFAULT = "jingle-demo-2026"  # demo-only, documented in README


@dataclass(frozen=True)
class Track:
    artist: str
    title: str
    album: str
    duration_s: int


CATALOG: tuple[Track, ...] = (
    Track("Arijit Singh", "Kesariya", "Brahmastra", 268),
    Track("Arijit Singh", "Tum Hi Ho", "Aashiqui 2", 262),
    Track("Pritam", "Channa Mereya", "Ae Dil Hai Mushkil", 289),
    Track("Prateek Kuhad", "cold/mess", "cold/mess", 301),
    Track("Prateek Kuhad", "Kasoor", "cold/mess", 212),
    Track("AP Dhillon", "Excuses", "Excuses", 176),
    Track("Diljit Dosanjh", "Lover", "MoonChild Era", 187),
    Track("The Local Train", "Choo Lo", "Aalas Ka Pedh", 244),
    Track("Anuv Jain", "Husn", "Husn", 218),
    Track("Kendrick Lamar", "Not Like Us", "GNX", 274),
    Track("Taylor Swift", "Cruel Summer", "Lover", 178),
    Track("The Weeknd", "Blinding Lights", "After Hours", 200),
    Track("Billie Eilish", "Birds of a Feather", "Hit Me Hard and Soft", 210),
    Track("Dua Lipa", "Levitating", "Future Nostalgia", 203),
    Track("Radiohead", "Weird Fishes/Arpeggi", "In Rainbows", 318),
    Track("Frank Ocean", "Pink + White", "Blonde", 184),
    Track("SZA", "Snooze", "SOS", 201),
    Track("Tame Impala", "The Less I Know the Better", "Currents", 216),
    Track("Lucky Ali", "O Sanam", "Sunoh", 305),
    Track("A.R. Rahman", "Kun Faya Kun", "Rockstar", 473),
    # Sprint R1 (redesign): a wider real catalogue so every screen shows real covers.
    Track('Arijit Singh', 'Phir Bhi Tumko Chaahunga', 'Half Girlfriend', 349),
    Track('Arijit Singh', 'Agar Tum Saath Ho', 'Tamasha', 341),
    Track('Shreya Ghoshal', 'Teri Ore', 'Singh Is Kinng', 281),
    Track('Atif Aslam', 'Tera Hone Laga Hoon', 'Ajab Prem Ki Ghazab Kahani', 364),
    Track('Jubin Nautiyal', 'Raataan Lambiyan', 'Shershaah', 230),
    Track('Vishal-Shekhar', 'Ghungroo', 'War', 302),
    Track('Sachet-Parampara', 'Bekhayali', 'Kabir Singh', 371),
    Track('A.R. Rahman', 'Jai Ho', 'Slumdog Millionaire', 319),
    Track('Shankar Mahadevan', 'Dil Chahta Hai', 'Dil Chahta Hai', 318),  # the singer, as stores credit it
    Track('Amit Trivedi', 'Ik Kudi', 'Udta Punjab', 244),
    Track('Ritviz', 'Udd Gaye', 'Udd Gaye', 177),
    Track('Ritviz', 'Liggi', 'Liggi', 171),
    Track('Anuv Jain', 'Baarishein', 'Baarishein', 233),
    Track('Anuv Jain', 'Jo Tum Mere Ho', 'Jo Tum Mere Ho', 253),
    Track('Prateek Kuhad', 'Tum Jab Paas', 'in tokens & charms', 213),
    Track('When Chai Met Toast', 'Firefly', 'Firefly', 224),
    Track('The Yellow Diary', 'Roz Roz', 'Roz Roz', 276),
    Track('Lifafa', 'Jaago', 'Superfast Zindagi', 215),
    Track('Taba Chake', 'Shaayad', 'Bombay Dreams', 205),
    Track("Nikhil D'Souza", 'Silver Linings', 'Silver Linings', 223),
    Track('AP Dhillon', 'With You', 'Hidden Gems', 195),
    Track('AP Dhillon', 'Brown Munde', 'Brown Munde', 267),
    Track('Diljit Dosanjh', 'Born to Shine', 'G.O.A.T.', 189),
    Track('Karan Aujla', 'Softly', 'Making Memories', 162),
    Track('Sidhu Moose Wala', '295', 'Moosetape', 269),
    Track('Shubh', 'Still Rollin', 'Still Rollin', 168),
    Track('Seedhe Maut', 'Nanchaku', 'Nayaab', 193),
    Track('DIVINE', 'Mirchi', 'Punya Paap', 229),
    Track('Raftaar', 'Swag Mera Desi', 'Swag Mera Desi', 213),
    Track('KR$NA', 'Machayenge 4', 'Machayenge 4', 203),
    Track('Emiway Bantai', 'Firse Machayenge', 'Firse Machayenge', 222),
    Track('Taylor Swift', 'Anti-Hero', 'Midnights', 201),
    Track('Taylor Swift', 'Blank Space', '1989', 231),
    Track('The Weeknd', 'Save Your Tears', 'After Hours', 215),
    Track('Billie Eilish', 'bad guy', 'When We All Fall Asleep, Where Do We Go?', 194),
    Track('Dua Lipa', "Don't Start Now", 'Future Nostalgia', 183),
    Track('Harry Styles', 'As It Was', "Harry's House", 167),
    Track('Olivia Rodrigo', 'drivers license', 'SOUR', 242),
    Track('Sabrina Carpenter', 'Espresso', "Short n' Sweet", 175),
    Track('Ed Sheeran', 'Shape of You', '÷', 233),
    Track('Bruno Mars', 'Uptown Funk', 'Uptown Special', 270),
    Track('Ariana Grande', '7 rings', 'thank u, next', 178),
    Track('Chappell Roan', 'Good Luck, Babe!', 'Good Luck, Babe!', 218),
    Track('Kendrick Lamar', 'HUMBLE.', 'DAMN.', 177),
    Track('Kendrick Lamar', 'Money Trees', 'good kid, m.A.A.d city', 386),
    Track('Drake', 'Hotline Bling', 'Views', 267),
    Track('Travis Scott', 'SICKO MODE', 'ASTROWORLD', 312),
    Track('Frank Ocean', 'Nights', 'Blonde', 307),
    Track('SZA', 'Kill Bill', 'SOS', 153),
    Track('Tyler, The Creator', 'See You Again', 'Flower Boy', 180),
    Track('Kanye West', 'Stronger', 'Graduation', 311),
    Track('Doja Cat', 'Say So', 'Hot Pink', 237),
    Track('Coldplay', 'Yellow', 'Parachutes', 266),
    Track('Coldplay', 'Viva la Vida', 'Viva la Vida or Death and All His Friends', 242),
    Track('Radiohead', 'Creep', 'Pablo Honey', 238),
    Track('Arctic Monkeys', 'Do I Wanna Know?', 'AM', 272),
    Track('Arctic Monkeys', '505', 'Favourite Worst Nightmare', 253),
    Track('The Strokes', 'Last Nite', 'Is This It', 193),
    Track('Tame Impala', 'Let It Happen', 'Currents', 467),
    Track('Queen', 'Bohemian Rhapsody', 'A Night at the Opera', 355),
    Track('Nirvana', 'Smells Like Teen Spirit', 'Nevermind', 301),
    Track('Fleetwood Mac', 'Dreams', 'Rumours', 257),
    Track('The Beatles', 'Here Comes the Sun', 'Abbey Road', 185),
    Track('Imagine Dragons', 'Believer', 'Evolve', 204),
    Track('Linkin Park', 'Numb', 'Meteora', 185),
    Track('Phoebe Bridgers', 'Motion Sickness', 'Stranger in the Alps', 229),
    Track('Daft Punk', 'Get Lucky', 'Random Access Memories', 369),
    Track('Daft Punk', 'One More Time', 'Discovery', 320),
    Track('Calvin Harris', 'Summer', 'Motion', 222),
    Track('Avicii', 'Wake Me Up', 'True', 247),
    Track('Fred again..', 'Delilah (pull me out of this)', 'Actual Life 3', 225),
    Track('Disclosure', 'Latch', 'Settle', 255),
    Track('Nucleya', 'Bass Rani', 'Bass Rani', 229),
    Track('Bad Bunny', 'Tití Me Preguntó', 'Un Verano Sin Ti', 243),
    Track('BTS', 'Dynamite', 'BE', 199),
    Track('NewJeans', 'Hype Boy', 'New Jeans', 179),
    Track('Rosalía', 'DESPECHÁ', 'MOTOMAMI +', 157),
    Track('Michael Jackson', 'Billie Jean', 'Thriller', 294),
    Track('Amy Winehouse', 'Back to Black', 'Back to Black', 241),
    Track('Frank Sinatra', 'Fly Me to the Moon', 'It Might as Well Be Swing', 147),
    Track('Norah Jones', "Don't Know Why", 'Come Away with Me', 186),
    Track('Kishore Kumar', 'Pal Pal Dil Ke Paas', 'Blackmail', 321),
    Track('Lata Mangeshkar', 'Lag Ja Gale', 'Woh Kaun Thi?', 259),
    Track('R.D. Burman', 'Chura Liya Hai Tumne', 'Yaadon Ki Baaraat', 280),
)

# Host the Companion reports for each web player (music_service in the push payload).
WEB_PLAYER_HOSTS: dict[Platform, str] = {
    Platform.SPOTIFY: "open.spotify.com",
    Platform.APPLE_MUSIC: "music.apple.com",
    Platform.YOUTUBE_MUSIC: "music.youtube.com",
    Platform.AMAZON_MUSIC: "music.amazon.com",
}


@dataclass(frozen=True)
class Persona:
    username: str
    display_name: str
    platform: Platform
    # Share of time spent listening in a browser (Live-capable via the Companion).
    web_share: float
    # Indexes into CATALOG this persona favours.
    favourites: tuple[int, ...]
    college: str = ""
    city: str = "Mumbai"
    tags: tuple[str, ...] = field(default_factory=tuple)


def _i(*titles: str) -> tuple[int, ...]:
    """Catalogue indexes by title, so persona tastes read as music rather than numbers."""
    by_title = {t.title: i for i, t in enumerate(CATALOG)}
    return tuple(by_title[t] for t in titles)


PERSONAS: tuple[Persona, ...] = (
    Persona("demo", "You (demo)", Platform.SPOTIFY, 0.7, (0, 3, 9, 14) + _i("Yellow", "Do I Wanna Know?", "Get Lucky", "Udd Gaye", "Money Trees", "Baarishein"), "KJ Somaiya"),
    Persona("aanya", "Aanya", Platform.SPOTIFY, 0.8, (0, 1, 2, 8) + _i("Agar Tum Saath Ho", "Raataan Lambiyan", "Tum Jab Paas", "Baarishein", "Teri Ore", "Lag Ja Gale"), "KJ Somaiya"),
    Persona("kabir", "Kabir", Platform.SPOTIFY, 0.6, (9, 15, 16, 17) + _i("HUMBLE.", "Money Trees", "SICKO MODE", "Nanchaku", "Mirchi", "See You Again"), "KJ Somaiya"),
    Persona("meera", "Meera", Platform.APPLE_MUSIC, 0.3, (3, 4, 8, 12) + _i("Jo Tum Mere Ho", "Firefly", "Motion Sickness", "Don't Know Why", "Roz Roz", "Silver Linings")),
    Persona("dev", "Dev", Platform.YOUTUBE_MUSIC, 0.7, (5, 6, 1, 0) + _i("With You", "Brown Munde", "Softly", "295", "Still Rollin", "Born to Shine"), "KJ Somaiya"),
    Persona("riya", "Riya", Platform.SPOTIFY, 0.5, (10, 13, 12, 11) + _i("Anti-Hero", "Espresso", "As It Was", "drivers license", "Good Luck, Babe!", "7 rings")),
    Persona("arjun", "Arjun", Platform.AMAZON_MUSIC, 0.4, (18, 19, 2, 1) + _i("Pal Pal Dil Ke Paas", "Chura Liya Hai Tumne", "Jai Ho", "Dil Chahta Hai", "Lag Ja Gale")),
    Persona("zoya", "Zoya", Platform.APPLE_MUSIC, 0.5, (14, 17, 15, 3) + _i("Creep", "505", "Last Nite", "Let It Happen", "Dreams", "Here Comes the Sun")),
    Persona("ishaan", "Ishaan", Platform.YOUTUBE_MUSIC, 0.8, (7, 3, 4, 8) + _i("Udd Gaye", "Liggi", "Shaayad", "Jaago", "Bass Rani", "Firefly"), "KJ Somaiya"),
    Persona("tara", "Tara", Platform.SPOTIFY, 0.4, (11, 13, 10, 16) + _i("Blank Space", "Save Your Tears", "bad guy", "Shape of You", "Dynamite", "Hype Boy")),
    Persona("vikram", "Vikram", Platform.AMAZON_MUSIC, 0.0, (19, 18, 1) + _i("Bohemian Rhapsody", "Billie Jean", "Fly Me to the Moon", "Lag Ja Gale")),  # phone only: never Live
    Persona("sana", "Sana", Platform.YOUTUBE_MUSIC, 0.3, (6, 5, 0, 2) + _i("Ghungroo", "Bekhayali", "Ik Kudi", "Tera Hone Laga Hoon", "Softly")),
    Persona("neel", "Neel", Platform.APPLE_MUSIC, 0.6, (9, 14, 17, 16) + _i("Get Lucky", "One More Time", "Latch", "Delilah (pull me out of this)", "Summer", "Wake Me Up")),
    # Sprint 5: not the demo login's friends, so it has people to be suggested.
    Persona("kiara", "Kiara", Platform.SPOTIFY, 0.6, (0, 1, 2, 8) + _i("Agar Tum Saath Ho", "Raataan Lambiyan", "Teri Ore"), "KJ Somaiya"),  # friend of friends
    Persona("rohan", "Rohan", Platform.YOUTUBE_MUSIC, 0.5, (5, 6, 7, 3) + _i("With You", "Mirchi", "Machayenge 4", "Swag Mera Desi")),  # friend of friends
    Persona("maya", "Maya", Platform.APPLE_MUSIC, 0.5, (0, 3, 9, 14) + _i("Yellow", "Do I Wanna Know?", "Get Lucky", "Udd Gaye"), city="Pune"),  # taste twin
)


def demo_token(username: str, key: str) -> str:
    """Deterministic scrobble token for a demo persona (``jng_`` + 43 urlsafe chars).

    Derived from SERVICE_TOKEN so the seed (core-api) and the simulator (ingest-ml) agree without
    sharing a file. Only valid while JINGLE_DEMO=1 seeded them.
    """
    digest = hmac.new(key.encode(), f"jingle-demo:{username}".encode(), hashlib.sha256).digest()
    return "jng_" + base64.urlsafe_b64encode(digest).decode().rstrip("=")
