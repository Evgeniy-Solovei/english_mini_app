import re
from functools import reduce

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.learning.data.curriculum_v2 import SOURCES, UNITS
from apps.learning.data.foundations_curriculum import FOUNDATION_UNITS
from apps.learning.data.it_curriculum import IT_UNITS
from apps.learning.data.translations_ru import TRANSLATIONS_RU
from apps.learning.models import Exercise, Lesson, LevelExam, ReadingText, Word
from apps.learning.speaking_models import DialogueScenario, PhrasePack, ShadowPhrase


KIND_TITLES = [
    ("input", "Понимаю и узнаю"),
    ("build", "Строю фразы"),
    ("mission", "Говорю в ситуации"),
]

KEYWORD_STOPWORDS = {
    "a", "an", "and", "are", "at", "but", "do", "for", "from", "have", "i",
    "i'd", "i'll", "i'm", "in", "is", "it", "my", "of", "on", "the", "this",
    "to", "was", "what", "you",
}

ALL_UNITS = FOUNDATION_UNITS + UNITS + IT_UNITS


class Command(BaseCommand):
    help = "Build the complete adult Pre-A1/A1 course with a backend IT track"

    @transaction.atomic
    def handle(self, *args, **options):
        Lesson.objects.all().delete()
        LevelExam.objects.all().delete()
        PhrasePack.objects.all().delete()
        DialogueScenario.objects.all().delete()
        Word.objects.all().delete()

        level_orders = {"PRE_A1": 0, "A1": 0}
        for module_index, module in enumerate(ALL_UNITS, 1):
            self._create_module(module, module_index, level_orders)
            self._create_speaking(module, module_index)
            self._create_words(module, module_index)

        self._create_exams()
        self._detach_reading_lessons()
        lessons = Lesson.objects.filter(is_published=True).count()
        exercises = Exercise.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Curriculum v3 ready: {len(ALL_UNITS)} modules, {lessons} lessons, "
            f"{exercises} exercises, {ShadowPhrase.objects.count()} speaking phrases"
        ))

    def _create_module(self, module, module_index, level_orders):
        phrases = module["phrases"]
        earlier_same_level = [
            item for item in ALL_UNITS[:module_index - 1]
            if item["level"] == module["level"]
        ]
        previous = earlier_same_level[-1]["phrases"] if earlier_same_level else phrases
        for kind, kind_title in KIND_TITLES:
            level_orders[module["level"]] += 1
            order = level_orders[module["level"]]
            lesson = Lesson.objects.create(
                level=module["level"],
                sub_level=module["code"],
                order=order,
                title=f'{module["code"]} · {kind.title()}',
                title_ru=f'{module["title"]}: {kind_title}',
                description=module["can_do"],
                category=(
                    "alphabet" if module.get("foundation") and kind != "mission"
                    else ("dialogue" if kind == "mission" else ("listening" if kind == "input" else "speaking"))
                ),
                content={
                    "curriculum_version": 3,
                    "module_code": module["code"],
                    "track": module.get("track", "it" if module["code"].startswith("IT") else "main"),
                    "foundation": module.get("foundation", False),
                    "lesson_kind": kind,
                    "can_do": module["can_do"],
                    "grammar": module["grammar"],
                    "source_alignment": [name for name, _ in SOURCES],
                    "blocks": self._blocks(module, kind),
                },
                estimated_minutes=20 if kind != "mission" else 25,
                xp_reward=20 if kind != "mission" else 30,
                is_published=True,
            )
            specs = self._input_specs(phrases) if kind == "input" else (
                self._build_specs(phrases) if kind == "build" else self._mission_specs(module, previous)
            )
            for ex_order, spec in enumerate(specs, 1):
                Exercise.objects.create(lesson=lesson, order=ex_order, **spec)

    def _blocks(self, module, kind):
        blocks = [{"type": "text", "title": "Цель", "body": module["can_do"]}]
        if module.get("alphabet"):
            blocks.append({
                "type": "alphabet",
                "title": module["title"],
                "letters": [
                    {"char": char, "sound": sound}
                    for char, sound in module["alphabet"]
                ],
            })
        if module.get("foundation_reading"):
            blocks.append({
                "type": "reading",
                "title": "Как это читать",
                "body": module["foundation_reading"],
            })
        if kind == "build":
            blocks.append({"type": "text", "title": "Как строится фраза", "body": module["grammar"]})
        for english, russian in module["phrases"]:
            blocks.append({"type": "example", "en": english, "ru": russian})
        if kind == "mission":
            blocks.append({"type": "text", "title": "Задача без перевода", "body": module["mission"][1]})
        return blocks

    def _input_specs(self, phrases):
        specs = []
        translations = [ru for _, ru in phrases]
        for i, (english, russian) in enumerate(phrases[:3]):
            options = [russian, translations[(i + 1) % len(translations)], translations[(i + 2) % len(translations)]]
            specs.append(self._spec("listen", f"Прослушайте и выберите смысл фразы {i + 1}", "Сначала слушайте, затем отвечайте.",
                                    russian, options=options, audio_text=english, skill="listening"))
        for i, (english, russian) in enumerate(phrases[3:6], 3):
            options = [english, phrases[(i + 1) % len(phrases)][0], phrases[(i + 2) % len(phrases)][0]]
            specs.append(self._spec("mc", f"Как сказать: «{russian}»?", "Выберите готовую английскую фразу.",
                                    english, options=options, skill="vocabulary", srs=(english, russian)))
        return specs

    def _build_specs(self, phrases):
        specs = []
        for english, russian in phrases[:2]:
            words = self._words(english)
            blank_index = max(0, len(words) // 2)
            answer = words[blank_index]
            masked = words.copy()
            masked[blank_index] = "___"
            specs.append(self._spec("fill", " ".join(masked), f"Восстановите фразу: {russian}", answer,
                                    alternatives=[answer.casefold()], skill="grammar"))
        for english, russian in phrases[2:4]:
            specs.append(self._spec("order", " · ".join(reversed(self._words(english))),
                                    f"Соберите фразу: {russian}", english, skill="writing"))
        english, russian = phrases[4]
        specs.append(self._spec("translate", f"Переведите: «{russian}»", "Напишите фразу без подсказки.",
                                english, skill="writing", srs=(english, russian)))
        english, russian = phrases[5]
        specs.append(self._spec("speak", f"Скажите вслух: {english}", russian, english,
                                audio_text=english, skill="speaking"))
        return specs

    def _mission_specs(self, module, previous):
        phrases = module["phrases"]
        specs = []
        for english, russian in previous[-2:]:
            specs.append(self._spec("translate", f"Вспомните без урока: «{russian}»", "Повторение прошлого модуля.",
                                    english, skill="writing", srs=(english, russian)))
        for english, russian in phrases[:2]:
            specs.append(self._spec("listen", "Что вы услышали?", "Выберите точную фразу.", english,
                                    options=[english, phrases[2][0], phrases[3][0]], audio_text=english, skill="listening"))
        prompt, hint, answers = module["mission"]
        specs.append(self._spec("read", f"Прочитайте реплику: “{prompt}”", "Что от вас требуется?",
                                hint, options=[hint, "Назвать отдельное слово без связи", "Перевести весь учебник"],
                                skill="reading"))
        specs.append(self._spec(
            "speak", prompt, hint, answers[0], alternatives=answers[1:],
            expected_keywords=self._shared_keywords(answers), audio_text=prompt, skill="speaking",
        ))
        specs.append(self._spec(
            "write", f"Write a short answer: {prompt}", hint, answers[0],
            expected_keywords=self._shared_keywords(answers),
            min_words=4 if module["level"] == "PRE_A1" else 8, skill="writing",
        ))
        specs.append(self._spec("mc", "Какой навык вы сейчас отработали?", module["can_do"],
                                module["can_do"], options=[module["can_do"], "Только запомнил отдельное слово", "Только прочитал правило"],
                                skill="dialogue"))
        return specs

    def _spec(self, exercise_type, question, question_ru, correct, *, options=None,
              alternatives=None, expected_keywords=None, audio_text=None,
              min_words=None, skill="vocabulary", srs=None):
        data = {"correct_answer": correct, "explanation": "Прослушайте пример и повторите попытку."}
        if options:
            data["options"] = list(dict.fromkeys(options))
        if alternatives:
            data["alternatives"] = alternatives
        if expected_keywords:
            data["expected_keywords"] = expected_keywords
        if min_words:
            data["min_words"] = min_words
        if audio_text:
            data["audio_text"] = audio_text
        if srs:
            data["srs_front"], data["srs_back"] = srs
        return {"exercise_type": exercise_type, "question": question, "question_ru": question_ru,
                "data": data, "points": 5, "skill": skill}

    def _create_speaking(self, module, order):
        pack = PhrasePack.objects.create(
            slug=f'course-{module["code"].lower()}', title=module["code"], title_ru=module["title"],
            description=module["can_do"], pack_type="survival" if module["level"] == "PRE_A1" else "shadow",
            level=module["level"], emoji="🗣", order=order, is_published=True,
        )
        for phrase_order, (english, russian) in enumerate(module["phrases"], 1):
            ShadowPhrase.objects.create(pack=pack, order=phrase_order, english=english, russian=russian,
                                        tip=f'Сначала добейтесь понятности, затем повторите в естественном темпе. Модуль {module["code"]}.')
        prompt, hint, answers = module["mission"]
        follow_up_en, follow_up_ru = module["phrases"][-1]
        follow_up_keywords = self._shared_keywords([follow_up_en])
        DialogueScenario.objects.create(
            slug=f'mission-{module["code"].lower()}', title=f'{module["code"]} mission', title_ru=module["title"],
            description=module["can_do"], level=module["level"], emoji="💬", setting="Разговорная миссия",
            order=order, is_published=True, turns=[
                {"role": "bot", "text": prompt, "hint_ru": hint},
                {
                    "role": "user", "text": "Your answer", "hint_ru": hint,
                    "keywords": self._shared_keywords(answers),
                    "retry_bot": "I did not get the key information. Please try again.",
                },
                {
                    "role": "bot", "text": "Good. Add one more useful detail.",
                    "hint_ru": f"Используйте фразу: {follow_up_ru}",
                },
                {
                    "role": "user", "text": "One more detail", "hint_ru": follow_up_ru,
                    "keywords": follow_up_keywords,
                    "retry_bot": "Please add the requested detail.",
                },
                {"role": "bot", "text": "Thank you. I understand you.", "hint_ru": "Миссия завершена."},
            ],
        )

    def _create_words(self, module, module_index):
        existing = set(Word.objects.values_list("english", flat=True))
        for english, _ in module["phrases"]:
            for token in self._words(english):
                key = token.casefold()
                if len(key) < 2 or key in existing or key not in TRANSLATIONS_RU:
                    continue
                Word.objects.create(english=key, russian=TRANSLATIONS_RU[key], level=module["level"],
                                    frequency_rank=module_index * 100 + len(existing), tags=[module["code"]])
                existing.add(key)

    def _create_exams(self):
        for level, title in (("PRE_A1", "Pre-A1 survival conversation"), ("A1", "A1 everyday communication")):
            modules = [m for m in ALL_UNITS if m["level"] == level]
            questions = []
            for index, module in enumerate(modules):
                english, russian = module["phrases"][0]
                mode = ("listening", "reading", "writing", "speaking", "translate")[index % 5]
                if mode == "listening":
                    questions.append({
                        "type": "listening", "skill": "listening", "question": "Listen and choose the meaning.",
                        "audio_text": english, "options": [russian, module["phrases"][1][1], module["phrases"][2][1]],
                        "correct_answer": russian,
                    })
                elif mode == "reading":
                    questions.append({
                        "type": "reading", "skill": "reading",
                        "question": f'Read: “{english}” What does it mean?',
                        "options": [russian, module["phrases"][1][1], module["phrases"][2][1]],
                        "correct_answer": russian,
                    })
                elif mode in {"writing", "speaking"}:
                    prompt, hint, answers = module["mission"]
                    questions.append({
                        "type": mode, "skill": mode, "question": prompt, "hint_ru": hint,
                        "correct_answer": answers[0], "alternatives": answers[1:],
                        "expected_keywords": self._shared_keywords(answers),
                        "min_words": 4 if level == "PRE_A1" else 8,
                    })
                else:
                    questions.append({
                        "type": "translate", "skill": "writing", "question": f"{module['code']}: {russian}",
                        "correct_answer": english, "alternatives": [english.rstrip(".!?")],
                    })
            LevelExam.objects.update_or_create(level=level, defaults={
                "title": title, "description": "Накопительная проверка всех разговорных целей уровня.",
                "pass_score": 80, "time_limit_minutes": 25 if level == "PRE_A1" else 45,
                "questions": questions,
            })

    def _detach_reading_lessons(self):
        ReadingText.objects.update(lesson=None)

    @staticmethod
    def _words(text):
        return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+", text)

    def _shared_keywords(self, answers):
        """Keep the meaning-bearing words shared by valid model replies.

        Dialogue replies are open production tasks: learners do not need to recite
        one sentence verbatim, but they must communicate the requested information.
        """
        keyword_sets = []
        for answer in answers:
            keyword_sets.append({
                word.casefold() for word in self._words(answer)
                if (
                    (word.casefold() not in KEYWORD_STOPWORDS and len(word) > 1)
                    or (len(word) == 1 and word.isupper())
                )
            })
        shared = reduce(set.intersection, keyword_sets) if keyword_sets else set()
        if not shared and keyword_sets:
            shared = keyword_sets[0]
        return sorted(shared)
