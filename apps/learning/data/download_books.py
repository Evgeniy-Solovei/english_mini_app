#!/usr/bin/env python
"""Download bundled Gutenberg books into data/books/."""
import ssl
import urllib.request
from pathlib import Path

BOOKS_DIR = Path(__file__).resolve().parent / "books"
BOOKS_DIR.mkdir(exist_ok=True)

IDS = [
    "11757", "46", "55", "11", "2591", "1400", "84", "120",
    "1661", "1952", "74", "215",
]

ctx = ssl.create_default_context()


def download(book_id: str) -> bool:
    for url in (
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
        f"http://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EnglishJourneyBot/1.0"})
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                data = resp.read()
            path = BOOKS_DIR / f"pg{book_id}.txt"
            path.write_bytes(data)
            print(f"  OK  pg{book_id}.txt ({len(data) // 1024} KB)")
            return True
        except Exception as e:
            print(f"  fail {url}: {e}")
    return False


if __name__ == "__main__":
    print(f"Downloading to {BOOKS_DIR}...")
    ok = sum(download(i) for i in IDS)
    print(f"Done: {ok}/{len(IDS)}")
