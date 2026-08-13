import hashlib
import io
import logging
import re
import math
import tempfile
import base64
import json
from html import escape
from difflib import SequenceMatcher
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# Common RU→EN pronunciation pitfalls
PHONEME_TIPS = {
    "th": "Звук TH: язык между зубами. Think = /θɪŋk/, This = /ðɪs/.",
    "w": "W ≠ V: губы округли как для «у». Wine, water, what.",
    "v": "V — верхние зубы на нижнюю губу. Very, voice.",
    "r": "Английский R без дрожания — язык назад, не касайся нёба.",
    "h": "H — лёгкий выдох, не «х» по-русски. Hello, house.",
    "ng": "NG в конце: tongue, thing — не добавляй «г» громко.",
    "ee": "Долгий /iː/: see, tree — улыбнись, держи звук.",
    "i": "Короткий /ɪ/: sit, ship — короче, чем «и».",
    "æ": "Звук /æ/ в cat, bad — шире, чем русское «э».",
}


def _cache_path(text: str, lang: str = "en", slow: bool = False, voice: str = "") -> Path:
    key = hashlib.md5(f"{lang}:{slow}:{voice}:{text}".encode()).hexdigest()
    cache_dir = Path(settings.VOICE_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.mp3"


def text_to_speech(
    text: str, lang: str = "en", slow: bool = False, voice: str = ""
) -> Path | None:
    if not text.strip():
        return None

    cached = _cache_path(text, lang, slow, voice)
    if cached.exists():
        return cached

    azure_path = _azure_text_to_speech(text, slow, voice, cached)
    if azure_path:
        return azure_path

    try:
        from gtts import gTTS

        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(str(cached))
        return cached
    except Exception as e:
        logger.warning("gTTS failed (%s), trying pyttsx3 fallback", e)

    try:
        import pyttsx3

        engine = pyttsx3.init()
        if slow:
            rate = engine.getProperty("rate")
            engine.setProperty("rate", max(100, rate - 50))
        wav_path = cached.with_suffix(".wav")
        engine.save_to_file(text, str(wav_path))
        engine.runAndWait()
        if wav_path.exists():
            from pydub import AudioSegment

            AudioSegment.from_wav(str(wav_path)).export(str(cached), format="mp3")
            wav_path.unlink(missing_ok=True)
            return cached
    except Exception as e2:
        logger.error("TTS fallback failed: %s", e2)

    return None


def _azure_text_to_speech(text: str, slow: bool, voice: str, output: Path) -> Path | None:
    key = getattr(settings, "AZURE_SPEECH_KEY", "")
    region = getattr(settings, "AZURE_SPEECH_REGION", "")
    if not key or not region:
        return None
    allowed = {
        "female": "en-US-AvaMultilingualNeural",
        "male": "en-US-AndrewMultilingualNeural",
        "british_female": "en-GB-SoniaNeural",
        "british_male": "en-GB-RyanNeural",
    }
    voice_name = allowed.get(voice, allowed["female"])
    rate = "-25%" if slow else "0%"
    ssml = (
        f'<speak version="1.0" xml:lang="en-US"><voice name="{voice_name}">'
        f'<prosody rate="{rate}">{escape(text)}</prosody></voice></speak>'
    )
    try:
        import httpx

        response = httpx.post(
            f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                "User-Agent": "EnglishJourney",
            },
            content=ssml.encode("utf-8"), timeout=20,
        )
        response.raise_for_status()
        output.write_bytes(response.content)
        return output
    except Exception as exc:
        logger.warning("Azure neural TTS unavailable: %s", exc)
        return None


def assess_pronunciation(audio_bytes: bytes, expected_text: str) -> dict | None:
    """Use phoneme-aware Azure assessment when configured; otherwise return None."""
    key = getattr(settings, "AZURE_SPEECH_KEY", "")
    region = getattr(settings, "AZURE_SPEECH_REGION", "")
    if not key or not region or not audio_bytes or not expected_text.strip():
        return None
    try:
        import httpx

        wav = _to_wav_bytes(audio_bytes)
        config = base64.b64encode(json.dumps({
            "ReferenceText": expected_text,
            "GradingSystem": "HundredMark",
            "Granularity": "Phoneme",
            "Dimension": "Comprehensive",
            "EnableProsodyAssessment": True,
        }).encode()).decode()
        response = httpx.post(
            f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1",
            params={"language": "en-US", "format": "detailed"},
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Pronunciation-Assessment": config,
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                "Accept": "application/json",
            },
            content=wav, timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        best = (payload.get("NBest") or [{}])[0]
        scores = best.get("PronunciationAssessment", {})
        if not scores:
            return None
        words = []
        for word in best.get("Words", []):
            assessment = word.get("PronunciationAssessment", {})
            words.append({
                "expected": word.get("Word", ""),
                "spoken": word.get("Word", ""),
                "score": round(assessment.get("AccuracyScore", 0)),
                "ok": assessment.get("AccuracyScore", 0) >= 60,
                "error_type": assessment.get("ErrorType", "None"),
                "phonemes": word.get("Phonemes", []),
            })
        score = round(scores.get("PronScore", scores.get("AccuracyScore", 0)))
        return {
            "score": score,
            "accuracy": round(scores.get("AccuracyScore", 0)),
            "fluency": round(scores.get("FluencyScore", 0)),
            "completeness": round(scores.get("CompletenessScore", 0)),
            "prosody": round(scores.get("ProsodyScore", 0)),
            "spoken": best.get("Display", payload.get("DisplayText", "")),
            "expected": expected_text,
            "passed": score >= 60,
            "grade": "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 60 else "D",
            "feedback": "Акустическая оценка: проверены точность звуков, беглость и полнота.",
            "words": words,
            "tips": _tips_for_phrase(expected_text) if score < 85 else [],
            "assessment_provider": "azure_pronunciation",
        }
    except Exception as exc:
        logger.warning("Azure pronunciation assessment unavailable: %s", exc)
        return None


def _to_wav_bytes(audio_bytes: bytes) -> bytes:
    from pydub import AudioSegment

    buf = io.BytesIO(audio_bytes)
    audio = None
    for fmt in ("webm", "ogg", "mp3", "wav", "m4a"):
        try:
            buf.seek(0)
            audio = AudioSegment.from_file(buf, format=fmt)
            break
        except Exception:
            continue
    if audio is None:
        buf.seek(0)
        audio = AudioSegment.from_file(buf)

    audio = audio.set_frame_rate(16000).set_channels(1)
    out = io.BytesIO()
    audio.export(out, format="wav")
    return out.getvalue()


def speech_to_text(audio_bytes: bytes, language: str = "en") -> str:
    """Transcribe with Whisper if available, else SpeechRecognition Google API."""
    if not audio_bytes:
        return ""

    # Try openai-whisper first
    try:
        import whisper

        wav = _to_wav_bytes(audio_bytes)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav)
            tmp_path = tmp.name
        try:
            model_name = getattr(settings, "WHISPER_MODEL", "base")
            model = _get_whisper_model(model_name)
            result = model.transcribe(tmp_path, language=language[:2], fp16=False)
            text = (result.get("text") or "").strip()
            if text:
                return text
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.info("Whisper STT unavailable, falling back: %s", e)

    # Fallback: SpeechRecognition + Google
    try:
        import speech_recognition as sr

        wav = _to_wav_bytes(audio_bytes)
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(wav)) as source:
            audio_data = recognizer.record(source)
        lang = "en-US" if language.startswith("en") else language
        return recognizer.recognize_google(audio_data, language=lang)
    except Exception as e:
        logger.error("STT failed: %s", e)
        return ""


_whisper_model = None


def _get_whisper_model(name: str = "base"):
    global _whisper_model
    if _whisper_model is None:
        import whisper

        _whisper_model = whisper.load_model(name)
    return _whisper_model


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s']", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _levenshtein_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _word_scores(spoken: str, expected: str) -> list[dict]:
    s_words = spoken.split()
    e_words = expected.split()
    result = []
    for i, ew in enumerate(e_words):
        if i < len(s_words):
            sw = s_words[i]
            ratio = _levenshtein_ratio(sw, ew)
            result.append({
                "expected": ew,
                "spoken": sw,
                "score": round(ratio * 100),
                "ok": ratio >= 0.75,
            })
        else:
            result.append({"expected": ew, "spoken": "", "score": 0, "ok": False})
    return result


def _tips_for_phrase(expected: str) -> list[str]:
    tips = []
    low = expected.lower()
    checks = [
        (r"\bth", "th"),
        (r"\bw", "w"),
        (r"\bv", "v"),
        (r"\br", "r"),
        (r"\bh", "h"),
        (r"ng\b", "ng"),
        (r"ee|ea", "ee"),
        (r"\b(sit|ship|bit|it)\b", "i"),
        (r"\b(cat|bad|man|apple)\b", "æ"),
    ]
    seen = set()
    for pattern, key in checks:
        if key not in seen and re.search(pattern, low):
            tip = PHONEME_TIPS.get(key)
            if tip:
                tips.append(tip)
                seen.add(key)
        if len(tips) >= 2:
            break
    return tips


def compare_pronunciation(spoken_text: str, expected_text: str) -> dict:
    """Detailed pronunciation score with word-level feedback."""
    spoken_raw = spoken_text.strip()
    expected_raw = expected_text.strip()
    spoken = _normalize(spoken_raw)
    expected = _normalize(expected_raw)

    if not expected:
        return {
            "score": 0,
            "spoken": spoken_raw,
            "expected": expected_raw,
            "feedback": "No expected phrase.",
            "passed": False,
            "grade": "F",
            "words": [],
            "tips": [],
        }

    if not spoken:
        return {
            "score": 0,
            "spoken": "",
            "expected": expected_raw,
            "feedback": "Не удалось распознать речь. Говори громче и чётче.",
            "passed": False,
            "grade": "F",
            "words": [],
            "tips": _tips_for_phrase(expected_raw),
        }

    # Combined scoring
    full_ratio = _levenshtein_ratio(spoken, expected)
    words = _word_scores(spoken, expected)
    word_avg = sum(w["score"] for w in words) / max(len(words), 1)
    spoken_set = set(spoken.split())
    expected_list = expected.split()
    coverage = sum(1 for w in expected_list if w in spoken_set) / max(len(expected_list), 1)

    score = round(full_ratio * 40 + (word_avg / 100) * 40 + coverage * 20)

    if score >= 95:
        grade, feedback = "A+", "Отлично! Произношение почти идеальное 🎯"
    elif score >= 85:
        grade, feedback = "A", "Супер! Очень близко к эталону 👏"
    elif score >= 70:
        grade, feedback = "B", "Хорошо! Ещё чуть-чуть — и будет идеально."
    elif score >= 50:
        grade, feedback = "C", f"Неплохо. Эталон: «{expected_raw}». Послушай и повтори."
    else:
        grade, feedback = "D", f"Давай ещё раз. Скажи: «{expected_raw}»."

    return {
        "score": score,
        "spoken": spoken_raw,
        "expected": expected_raw,
        "feedback": feedback,
        "passed": score >= 70,
        "grade": grade,
        "words": words,
        "tips": _tips_for_phrase(expected_raw) if score < 90 else [],
    }


def evaluate_free_speech(spoken_text: str, expected_keywords: list[str] | None = None) -> dict:
    """Score free conversation reply (keyword / length based)."""
    spoken = _normalize(spoken_text)
    if not spoken:
        return {
            "score": 0,
            "spoken": "",
            "feedback": "I didn't catch that. Try again in English.",
            "passed": False,
            "english_ok": False,
        }

    words = spoken.split()
    # crude russian detection
    has_cyrillic = bool(re.search(r"[а-яё]", spoken_text.lower()))
    if has_cyrillic:
        return {
            "score": 20,
            "spoken": spoken_text,
            "feedback": "Please answer in English only 🇬🇧",
            "passed": False,
            "english_ok": False,
        }

    score = min(55, 25 + len(words) * 6)
    matched = []
    keyword_coverage = 1.0
    if expected_keywords:
        normalized_keywords = list(dict.fromkeys(_normalize(kw) for kw in expected_keywords))
        spoken_words = set(words)
        for kw in normalized_keywords:
            if kw in spoken_words:
                matched.append(kw)
        keyword_coverage = len(matched) / len(normalized_keywords)
        score = round(min(100, score + keyword_coverage * 45))

    required_keywords = (
        max(1, math.ceil(len(expected_keywords) / 2)) if expected_keywords else 0
    )
    meaning_ok = not expected_keywords or len(matched) >= required_keywords

    if len(words) < 2:
        feedback = "Good start! Try a longer answer (2–5 words)."
        score = min(score, 55)
    elif not meaning_ok:
        feedback = "Good English. Add the key information from the task."
    elif score >= 70:
        feedback = "Nice answer! Keep going 🗣"
    else:
        feedback = "Understood. Add a bit more detail next time."

    return {
        "score": score,
        "spoken": spoken_text,
        "feedback": feedback,
        "passed": len(words) >= 2 and meaning_ok and score >= 60,
        "english_ok": True,
        "matched_keywords": matched,
        "keyword_coverage": round(keyword_coverage, 2),
    }
