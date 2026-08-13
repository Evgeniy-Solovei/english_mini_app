import re
from typing import Iterator

GUTENBERG_START_MARKERS = [
    "*** START OF THE PROJECT GUTENBERG",
    "*** START OF THIS PROJECT GUTENBERG",
    "*END*THE SMALL PRINT",
]

GUTENBERG_END_MARKERS = [
    "*** END OF THE PROJECT GUTENBERG",
    "*** END OF THIS PROJECT GUTENBERG",
    "End of the Project Gutenberg",
]


def strip_gutenberg_boilerplate(text: str) -> str:
    upper = text.upper()
    start = 0
    for marker in GUTENBERG_START_MARKERS:
        idx = upper.find(marker.upper())
        if idx != -1:
            line_end = text.find("\n", idx)
            start = line_end + 1 if line_end != -1 else idx + len(marker)
            break

    end = len(text)
    for marker in GUTENBERG_END_MARKERS:
        idx = upper.find(marker.upper())
        if idx != -1:
            end = idx
            break

    cleaned = text[start:end]
    cleaned = re.sub(r"\r\n?", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def split_into_chapters(text: str, max_words: int = 800) -> list[dict]:
    """Split text into readable chapters (~800 words each)."""
    chapter_pattern = re.compile(
        r"^(?:CHAPTER|Chapter|PART|Part|STORY|Story|LETTER|Letter|TALE|Tale)\s+[IVXLCDM\d]+",
        re.MULTILINE,
    )
    parts = chapter_pattern.split(text)
    headers = chapter_pattern.findall(text)

    chapters = []
    if headers and len(parts) > 1:
        for i, body in enumerate(parts[1:], 0):
            title = headers[i] if i < len(headers) else f"Part {i + 1}"
            body = body.strip()
            if body:
                chapters.extend(_split_long_text(title, body, max_words))
    else:
        chapters = _split_long_text("Chapter 1", text, max_words)

    return [c for c in chapters if c["word_count"] >= 50]


def _split_long_text(title: str, text: str, max_words: int) -> list[dict]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chapters = []
    current_title = title
    current_parts: list[str] = []
    current_words = 0
    chapter_num = 1

    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > max_words and current_parts:
            chapters.append(_make_chapter(current_title, current_parts))
            chapter_num += 1
            current_title = f"{title} (continued {chapter_num})"
            current_parts = []
            current_words = 0
        current_parts.append(para)
        current_words += para_words

    if current_parts:
        chapters.append(_make_chapter(current_title, current_parts))

    return chapters


def _make_chapter(title: str, paragraphs: list[str]) -> dict:
    text = "\n\n".join(paragraphs)
    return {
        "title": title.strip(),
        "text": text,
        "word_count": len(text.split()),
    }


def extract_vocabulary_from_text(text: str, limit: int = 20) -> list[str]:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "is", "was", "are", "were", "be", "been", "being", "have", "has",
        "had", "do", "does", "did", "will", "would", "could", "should", "may",
        "might", "shall", "can", "it", "its", "he", "she", "they", "we", "you",
        "i", "me", "my", "his", "her", "their", "our", "your", "this", "that",
        "these", "those", "with", "from", "by", "as", "not", "so", "if", "then",
        "than", "when", "what", "which", "who", "how", "all", "each", "every",
        "both", "few", "more", "most", "other", "some", "such", "no", "nor",
        "only", "own", "same", "too", "very", "just", "also", "now", "here",
        "there", "where", "after", "before", "up", "down", "out", "about",
    }
    seen = set()
    result = []
    for w in words:
        if len(w) < 3 or w in stopwords or w in seen:
            continue
        seen.add(w)
        result.append(w)
        if len(result) >= limit:
            break
    return result
