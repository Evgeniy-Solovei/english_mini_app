from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from unittest.mock import patch

from apps.learning.models import Exercise, Lesson, LessonProgress, LevelExam
from apps.learning.services import calculate_level_score
from apps.users.models import CEFRLevel, LearnerProfile


@override_settings(DEBUG=True, TELEGRAM_BOT_TOKEN="")
class LearningApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_curriculum_v2", verbosity=0)
        LearnerProfile.objects.create(telegram_id=0, first_name="Dev")

    def setUp(self):
        self.client = Client()
        self.user = LearnerProfile.objects.get(telegram_id=0)

    def test_beginner_course_has_a_clear_sequence(self):
        lessons = Lesson.objects.filter(level=CEFRLevel.PRE_A1, is_published=True)
        self.assertEqual(lessons.count(), 78)
        self.assertEqual(list(lessons.values_list("order", flat=True)), list(range(1, 79)))
        self.assertTrue(all(lesson.exercises.count() >= 6 for lesson in lessons))
        first = lessons.first()
        self.assertEqual(first.content["module_code"], "F01")
        self.assertTrue(first.content["foundation"])
        self.assertTrue(any(block["type"] == "alphabet" for block in first.content["blocks"]))
        self.assertTrue(all(
            block.get("audio") for block in first.content["blocks"]
            if block["type"] == "example"
        ))

    def test_alphabet_lesson_uses_letter_listening_exercises(self):
        lesson = Lesson.objects.get(
            level=CEFRLevel.PRE_A1,
            content__module_code="F01",
            content__lesson_kind="input",
        )
        exercises = list(lesson.exercises.all())
        self.assertEqual(len(exercises), 7)
        self.assertTrue(all(exercise.exercise_type == "listen" for exercise in exercises))
        self.assertTrue(all(
            len(exercise.data["audio_text"]) == 1 and exercise.data["audio_text"].isupper()
            for exercise in exercises
        ))

    def test_exercises_and_options_are_shuffled_without_leaking_answers(self):
        lesson = Lesson.objects.get(level=CEFRLevel.PRE_A1, order=1)
        original = list(lesson.exercises.order_by("order"))

        with patch(
            "apps.learning.api.random.SystemRandom.shuffle",
            side_effect=lambda values: values.reverse(),
        ):
            response = self.client.get(f"/api/lessons/{lesson.id}/exercises")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([item["id"] for item in payload], [item.id for item in reversed(original)])
        by_id = {exercise.id: exercise for exercise in original}
        for item in payload:
            source = by_id[item["id"]]
            self.assertNotIn("correct_answer", item["data"])
            if source.data.get("options"):
                self.assertEqual(item["data"]["options"], list(reversed(source.data["options"])))

    def test_a1_is_a_full_114_lesson_path(self):
        lessons = Lesson.objects.filter(level=CEFRLevel.A1, is_published=True)
        self.assertEqual(lessons.count(), 114)
        self.assertEqual(list(lessons.values_list("order", flat=True)), list(range(1, 115)))

    def test_every_module_has_input_build_mission_and_dialogue(self):
        from apps.learning.speaking_models import DialogueScenario

        lessons = Lesson.objects.filter(is_published=True, level__in=[CEFRLevel.PRE_A1, CEFRLevel.A1])
        modules = {}
        for lesson in lessons:
            modules.setdefault(lesson.content["module_code"], set()).add(lesson.content["lesson_kind"])
        self.assertEqual(len(modules), 64)
        self.assertTrue(all(kinds == {"input", "build", "mission"} for kinds in modules.values()))
        self.assertEqual(DialogueScenario.objects.filter(is_published=True).count(), 64)

    def test_curriculum_quality_gate_passes(self):
        call_command("audit_curriculum", verbosity=0)

    def test_lesson_score_counts_unstarted_lessons(self):
        first = Lesson.objects.get(level=CEFRLevel.PRE_A1, order=1)
        LessonProgress.objects.create(user=self.user, lesson=first, score=100, status="completed")
        self.assertEqual(calculate_level_score(self.user, CEFRLevel.PRE_A1), 1.3)

    def test_opening_app_starts_streak_once_per_day(self):
        first = self.client.get("/api/dashboard")
        second = self.client.get("/api/dashboard")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["streak_days"], 1)
        self.assertEqual(second.json()["streak_days"], 1)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_activity_date)

    def test_it_track_starts_independently_from_main_course(self):
        first_it = Lesson.objects.filter(
            level=CEFRLevel.PRE_A1, sub_level="ITP01"
        ).order_by("order").first()
        response = self.client.get(f"/api/lessons/{first_it.id}")
        self.assertEqual(response.status_code, 200)

    def test_answer_is_tolerant_to_case_and_punctuation(self):
        self.user.current_level = CEFRLevel.A1
        self.user.save(update_fields=["current_level"])
        exercise = Exercise.objects.filter(
            lesson__level=CEFRLevel.A1,
            exercise_type=Exercise.ExerciseType.TRANSLATE,
            data__correct_answer="I never drink coffee.",
        ).get()
        for previous in Lesson.objects.filter(level=CEFRLevel.A1, order__lt=exercise.lesson.order):
            LessonProgress.objects.create(
                user=self.user, lesson=previous, score=100,
                status=LessonProgress.Status.COMPLETED,
            )
        response = self.client.post(
            f"/api/exercises/{exercise.id}/answer",
            data={"answer": "  I NEVER DRINK COFFEE!  "},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_correct"])

    def test_settings_reject_unknown_level(self):
        response = self.client.post(
            "/api/settings",
            data={"current_level": "LEVEL_9000"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_settings_can_start_from_any_published_level(self):
        response = self.client.post(
            "/api/settings",
            data={"current_level": CEFRLevel.A1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_level, CEFRLevel.A1)

    def test_settings_reject_level_without_a_course(self):
        response = self.client.post(
            "/api/settings",
            data={"current_level": CEFRLevel.B1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_locked_lesson_hides_content_and_exercises(self):
        second = Lesson.objects.get(level=CEFRLevel.PRE_A1, order=2)
        self.assertEqual(self.client.get(f"/api/lessons/{second.id}").status_code, 403)
        self.assertEqual(self.client.get(f"/api/lessons/{second.id}/exercises").status_code, 403)

    def test_speaking_mission_accepts_meaning_not_only_exact_script(self):
        exercise = Exercise.objects.filter(
            lesson__level=CEFRLevel.PRE_A1,
            lesson__content__module_code="P01",
            exercise_type=Exercise.ExerciseType.SPEAK,
            data__expected_keywords__isnull=False,
        ).get()
        for previous in Lesson.objects.filter(
            level=CEFRLevel.PRE_A1, order__lt=exercise.lesson.order
        ):
            LessonProgress.objects.create(
                user=self.user, lesson=previous, score=100,
                status=LessonProgress.Status.COMPLETED,
            )
        response = self.client.post(
            f"/api/exercises/{exercise.id}/answer",
            data={"answer": "Hi, tea please"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_correct"])

    def test_dialogue_does_not_advance_on_irrelevant_english(self):
        from apps.learning.speaking_models import DialogueScenario

        scenario = DialogueScenario.objects.get(slug="mission-p01")
        response = self.client.post(
            f"/api/speak/dialogues/{scenario.id}/reply",
            data={"spoken": "banana yellow", "turn_index": 0},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["passed"])
        self.assertFalse(response.json()["finished"])

    def test_it_track_and_guided_writing_are_published(self):
        self.assertEqual(
            Lesson.objects.filter(sub_level__startswith="IT", is_published=True).count(), 36
        )
        self.assertEqual(
            Exercise.objects.filter(exercise_type=Exercise.ExerciseType.WRITE).count(), 64
        )

    def test_wrong_answer_enters_adaptive_review(self):
        from apps.learning.models import SRSItem

        exercise = Exercise.objects.filter(
            lesson__level=CEFRLevel.PRE_A1, lesson__order=1
        ).first()
        response = self.client.post(
            f"/api/exercises/{exercise.id}/answer",
            data={"answer": "wrong"}, content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SRSItem.objects.filter(user=self.user, lesson=exercise.lesson).exists())

    def test_exam_covers_all_four_cefr_skills(self):
        exam = LevelExam.objects.get(level=CEFRLevel.A1)
        self.assertTrue(
            {"listening", "reading", "writing", "speaking"}.issubset(
                {question.get("skill") for question in exam.questions}
            )
        )
        response = self.client.get(f"/api/exam/{CEFRLevel.A1}")
        self.assertEqual(response.status_code, 200)
        serialized = response.json()["questions"]
        self.assertTrue(all("correct_answer" not in question for question in serialized))
        self.assertTrue(all("expected_keywords" not in question for question in serialized))

    def test_dialogue_requires_two_meaningful_user_turns(self):
        from apps.learning.speaking_models import DialogueScenario

        scenario = DialogueScenario.objects.get(slug="mission-p01")
        first = self.client.post(
            f"/api/speak/dialogues/{scenario.id}/reply",
            data={"spoken": "Hello yes please", "turn_index": 0},
            content_type="application/json",
        )
        self.assertTrue(first.json()["passed"])
        self.assertFalse(first.json()["finished"])
        second = self.client.post(
            f"/api/speak/dialogues/{scenario.id}/reply",
            data={"spoken": "See you later", "turn_index": first.json()["next_turn_index"]},
            content_type="application/json",
        )
        self.assertTrue(second.json()["passed"])
        self.assertTrue(second.json()["finished"])

    def test_original_reading_catalog_has_everyday_and_it_texts(self):
        from apps.learning.data.graded_readers import SHORT_READERS

        self.assertGreaterEqual(len(SHORT_READERS), 15)
        self.assertTrue(any(source_id.startswith("it_") for source_id, *_ in SHORT_READERS))

    def test_reading_detail_and_chapter_contract_match(self):
        from apps.learning.models import ReadingText

        book = ReadingText.objects.create(
            title="Tiny story", level=CEFRLevel.PRE_A1, total_words=2,
            chapters=[{"title": "One", "text": "Hello!", "text_ru": "Привет!", "word_count": 1}],
        )
        detail = self.client.get(f"/api/reading/texts/{book.id}")
        chapter = self.client.get(f"/api/library/{book.id}/chapter/0")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["chapters"][0]["index"], 0)
        self.assertEqual(chapter.json()["text_ru"], "Привет!")
