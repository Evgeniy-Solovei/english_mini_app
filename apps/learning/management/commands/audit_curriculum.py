from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError

from apps.learning.models import Exercise, Lesson
from apps.learning.speaking_models import DialogueScenario, PhrasePack


class Command(BaseCommand):
    help = "Audit curriculum volume, skill balance, answers, and speaking coverage"

    def handle(self, *args, **options):
        problems = []
        lessons = Lesson.objects.filter(is_published=True, level__in=["PRE_A1", "A1"])
        by_level = Counter(lessons.values_list("level", flat=True))
        if by_level["PRE_A1"] < 78:
            problems.append("Pre-A1 must contain at least 78 lessons including reading foundations and IT")
        if by_level["A1"] < 114:
            problems.append("A1 must contain at least 114 lessons including IT")

        module_kinds = defaultdict(set)
        for lesson in lessons:
            code = lesson.content.get("module_code")
            kind = lesson.content.get("lesson_kind")
            if not code or not lesson.content.get("can_do"):
                problems.append(f"Lesson {lesson.pk} has no module/can-do metadata")
            module_kinds[code].add(kind)
            if lesson.exercises.count() < 6:
                problems.append(f"Lesson {lesson.pk} has fewer than 6 exercises")

        for code, kinds in module_kinds.items():
            if kinds != {"input", "build", "mission"}:
                problems.append(f"Module {code} lacks input/build/mission progression")

        types = Counter()
        for exercise in Exercise.objects.filter(lesson__in=lessons):
            types[exercise.exercise_type] += 1
            answer = str(exercise.data.get("correct_answer", "")).strip()
            if not answer:
                problems.append(f"Exercise {exercise.pk} has no answer")
            if exercise.exercise_type in {"mc", "listen"} and answer not in exercise.data.get("options", []):
                problems.append(f"Exercise {exercise.pk} answer is absent from options")
            if exercise.exercise_type == "write":
                if not exercise.data.get("expected_keywords") or not exercise.data.get("min_words"):
                    problems.append(f"Writing exercise {exercise.pk} has no rubric")

        for required in ("listen", "speak", "translate", "fill", "order", "mc", "read", "write"):
            if types[required] < 40:
                problems.append(f"Not enough {required} exercises: {types[required]}")

        module_count = len(module_kinds)
        if PhrasePack.objects.filter(is_published=True).count() < module_count:
            problems.append("Every module must have a speaking pack")
        dialogues = DialogueScenario.objects.filter(is_published=True)
        if dialogues.count() < module_count:
            problems.append("Every module must have a dialogue mission")
        for dialogue in dialogues:
            user_turns = [turn for turn in dialogue.turns if turn.get("role") == "user"]
            if len(user_turns) < 2 or any(not turn.get("keywords") for turn in user_turns):
                problems.append(f"Dialogue {dialogue.pk} has no meaning-based user target")

        if problems:
            raise CommandError("Curriculum audit failed:\n- " + "\n- ".join(problems))
        self.stdout.write(self.style.SUCCESS(
            f"Curriculum audit passed: {module_count} modules, {lessons.count()} lessons, "
            f"{sum(types.values())} exercises; types={dict(types)}"
        ))
