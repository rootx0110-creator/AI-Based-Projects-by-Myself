"""Default wordlist provisioning.

Provides a curated list of well-known weak passwords and generates a starter
wordlist file (with numeric variants) on first use so the cracker always has
something to try out of the box.
"""
from __future__ import annotations

import os

CURATED_WORDS = [
    # classic top-100 style passwords
    "password", "password1", "password123", "password1234", "password12345",
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "12345", "1234", "123", "12", "1", "0",
    "qwerty", "qwerty123", "qwertyuiop", "qwertyuiop123",
    "abc123", "abc1234", "abcd1234", "abcdef", "abcdefg",
    "111111", "1111111", "222222", "333333", "444444", "555555",
    "666666", "777777", "888888", "999999", "000000", "00000000",
    "letmein", "letmein1", "letmein123", "welcome", "welcome1",
    "monkey", "monkey123", "dragon", "dragon1", "dragon123",
    "master", "master1", "master123", "login", "login123",
    "admin", "admin123", "administrator", "root", "root123", "toor",
    "iloveyou", "iloveyou1", "iloveu", "princess", "princess1",
    "sunshine", "sunshine1", "charlie", "charlie1", "trustno1",
    "batman", "batman1", "superman", "superman1", "spiderman", "spiderman1",
    "starwars", "starwars1", "pokemon", "pokemon1", "pokemon123",
    "michael", "michael1", "jennifer", "jennifer1", "jordan23",
    "nicole", "nicole1", "daniel", "daniel1", "daniel123",
    "ashley", "ashley1", "hunter", "hunter1", "hunter2", "shadow", "shadow1",
    "andrew", "andrew1", "jasmine", "jasmine1", "soccer", "soccer1",
    "football", "football1", "baseball", "baseball1", "basketball",
    "hockey", "hockey1", "golfer", "guitar", "guitar1", "coffee", "coffee1",
    "tigger", "tigger1", "passw0rd", "p@ssword", "p@ssw0rd", "pa55word",
    "password!", "Password1", "Password123", "P@ssw0rd", "P@ssw0rd1",
    "hello", "hello123", "helloworld", "goodbye", "testing", "test", "test123",
    "test1234", "test12345", "qazwsx", "qazwsxedc", "1qaz2wsx", "1q2w3e4r",
    "zaq12wsx", "zxcvbnm", "asdfghjkl", "zxcvbnm123", "asdf", "asdfgh",
    "1qazxsw2", "qweasdzxc", "qwerty12", "qwerty12345", "password!23",
    "summer", "summer1", "summer123", "winter", "winter1", "spring",
    "autumn", "autumn1", "lovely", "lovely1", "secret", "secret1", "secret123",
    "myspace1", "myspace123", "mypassword", "mypassword1", "changeme",
    "changeme1", "default", "default1", "guest", "guest1", "unknown",
    "freedom", "freedom1", "freedom123", "shadow123", "killer", "killer1",
    "jesus", "jesus1", "jesus123", "christ", "god", "god123", "forever",
    "forever1", "forever123", "whatever", "whatever1", "whatever123",
    "mustang", "mustang1", "mustang123", "camaro", "camaro1", "corvette",
    "harley", "harley1", "harley123", "yamaha", "yamaha1", "yamaha123",
    "cheese", "cheese1", "cheese123", "pepper", "pepper1", "pepper123",
    "prince", "prince1", "prince123", "cookie", "cookie1", "cookie123",
    "orange", "orange1", "apple", "apple1", "apple123", "banana", "banana1",
    "grapes", "grapes1", "yellow", "yellow1", "purple", "purple1", "purple123",
    "blue", "blue123", "green", "green1", "green123", "red", "red123",
    "black", "black1", "white", "white1", "black123", "silver", "silver1",
    "gold", "gold1", "golden", "golden1", "golden123",
    "lakers", "lakers1", "celtics", "celtics1", "yankees", "yankees1",
    "dallas", "dallas1", "cowboys", "cowboys1", "nascar", "nascar1",
    "falcons", "falcons1", "packers", "packers1", "ravens", "ravens1",
    "burnley", "arsenal", "arsenal1", "chelsea", "chelsea1", "manutd", "manutd1",
    "liverpool", "liverpool1", "barcelona", "barcelona1", "realmadrid",
    # names & personal-type passwords
    "john", "john1", "john123", "johnny", "bob", "bob1", "bobby", "david",
    "david1", "dave", "dave1", "james", "james1", "jimmy", "jimmy1", "robert",
    "robert1", "rob", "steve", "steve1", "steven", "chris", "chris1", "chris123",
    "tom", "tom1", "tommy", "tony", "tony1", "sarah", "sarah1", "sarah123",
    "emma", "emma1", "olivia", "olivia1", "ava", "ava1", "amanda", "amanda1",
    "jessica", "jessica1", "jessica123", "megan", "megan1", "samantha",
    "samantha1", "alex", "alex1", "alex123", "alexis", "alexis1", "jordan1",
    "josh", "josh1", "joshua", "joshua1", "randy", "randy1", "randy123",
    "ryan", "ryan1", "ryan123", "brandon", "brandon1", "brandon123",
    "justin", "justin1", "taylor", "taylor1", "tyler", "tyler1", "tyler123",
    "matthew", "matthew1", "luke", "luke1", "leah", "leah1", "sophia",
    # keyboards / topical / memorable
    "monkey1", "computer", "computer1", "computer123", "science",
    "internet", "internet1", "webmaster", "webmaster1", "website",
    "friends", "friends1", "family", "family1", "birthday", "birthday1",
    "birthday123", "happiness", "happy", "happy1", "happy123", "money",
    "money1", "money123", "casino", "joker", "joker1", "winner", "winner1",
    "martin", "martin1", "martin123", "diamond", "diamond1", "diamond123",
    "samson", "samson1", "titan", "titan1", "zeus", "zeus1", "thunder",
    "thunder1", "lightning", "lightning1", "storm", "storm1", "stormy",
    "skittles", "skittles1", "theman", "theman1", "water", "water1",
    "fire", "fire123", "earth", "earth1", "wind", "wind1", "air", "air1",
    "national", "america", "america1", "country", "country1", "united",
    "freedom123", "justice", "justice1", "peace", "peace1", "magic",
    "magic1", "magic123", "music", "music1", "music123", "party", "party1",
    "party123", "rock", "rock1", "rock123", "metal", "metal1", "punk",
    "rap", "jazz", "jazz1", "blues", "rap1", "hacker", "hacker1", "hack",
    "admin1", "pass", "pass1", "pass123", "pw", "pw123",
    "corona", "covid19", "covid", "covidsucks",
    "smartphone", "android", "android1", "iphone", "apple1234",
    "instagram", "instagram1", "facebook", "facebook1", "twitter",
    "twitter1", "linkedin", "whatsapp", "youtube", "youtube1",
    "netflix", "netflix1", "amazon", "amazon1", "prime", "prime1",
    # repeats & simple patterns
    "1a2b3c", "1a2b3c4d", "a1b2c3", "z1z2z3", "111222", "123123", "123321",
    "321321", "212121", "121212", "112233", "11223344", "554433", "556677",
    "999666", "1231234", "123654", "147258", "159753", "102030", "135790",
    "000001", "674683", "744556", "654321", "789456", "741852", "852963",
]


def _numeric_lines() -> list[str]:
    lines: list[str] = []
    years = [str(y) for y in range(1900, 2101)]
    lines.extend(years)
    for i in range(10000):
        n = str(i)
        lines.append(n)
        lines.append(f"{i:04d}")
        lines.append(f"{i:05d}")
        lines.append(f"0{i:04d}")
    return lines


def build_common_words() -> frozenset[str]:
    return frozenset(CURATED_WORDS)


def ensure_default_wordlist(candidates) -> list[str]:
    """Return existing default wordlists, creating one in the first writable dir."""
    if isinstance(candidates, str):
        candidates = [candidates]
    for directory in candidates:
        if not directory:
            continue
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "default_wordlist.txt")
        if os.path.exists(path):
            return [path]
    for directory in candidates:
        if not directory:
            continue
        path = os.path.join(directory, "default_wordlist.txt")
        try:
            lines = list(CURATED_WORDS) + _numeric_lines()
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(lines) + "\n")
            return [path]
        except OSError:
            continue
    return []


def load_words(path: str) -> list[str]:
    """Load a wordlist file into a list of trimmed, non-empty words."""
    words: list[str] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            word = raw.strip()
            if word and " " not in word and "\t" not in word:
                words.append(word)
    return words


COMMON_WORDS: frozenset[str] = build_common_words()