from django.core.management.base import BaseCommand
from django.db import transaction

from apps.learning.models import Exercise, Lesson, LevelExam, SkillCategory, Word
from apps.users.models import CEFRLevel


BEGINNER_WORDS = [
    ("hello", "привет", "/həˈləʊ/", "Hello, Anna!"),
    ("goodbye", "до свидания", "/ˌɡʊdˈbaɪ/", "Goodbye! See you tomorrow."),
    ("please", "пожалуйста", "/pliːz/", "Water, please."),
    ("thanks", "спасибо", "/θæŋks/", "Thanks for your help."),
    ("yes", "да", "/jes/", "Yes, I understand."),
    ("no", "нет", "/nəʊ/", "No, thank you."),
    ("sorry", "извините", "/ˈsɒri/", "Sorry, I do not understand."),
    ("name", "имя", "/neɪm/", "My name is Alex."),
    ("I", "я", "/aɪ/", "I am Maria."),
    ("you", "ты; вы", "/juː/", "How are you?"),
    ("he", "он", "/hiː/", "He is my friend."),
    ("she", "она", "/ʃiː/", "She is my sister."),
    ("we", "мы", "/wiː/", "We are ready."),
    ("they", "они", "/ðeɪ/", "They are at home."),
    ("one", "один", "/wʌn/", "I have one book."),
    ("two", "два", "/tuː/", "Two coffees, please."),
    ("three", "три", "/θriː/", "I see three cats."),
    ("red", "красный", "/red/", "It is red."),
    ("blue", "синий", "/bluː/", "The bag is blue."),
    ("green", "зелёный", "/ɡriːn/", "I like green."),
    ("black", "чёрный", "/blæk/", "My phone is black."),
    ("white", "белый", "/waɪt/", "The cup is white."),
    ("mother", "мама", "/ˈmʌðə/", "This is my mother."),
    ("father", "папа", "/ˈfɑːðə/", "My father is at home."),
    ("brother", "брат", "/ˈbrʌðə/", "I have one brother."),
    ("sister", "сестра", "/ˈsɪstə/", "She is my sister."),
    ("friend", "друг; подруга", "/frend/", "Tom is my friend."),
    ("water", "вода", "/ˈwɔːtə/", "I need water."),
    ("food", "еда", "/fuːd/", "The food is good."),
    ("coffee", "кофе", "/ˈkɒfi/", "Coffee, please."),
    ("tea", "чай", "/tiː/", "I would like tea."),
    ("bread", "хлеб", "/bred/", "I need bread."),
    ("home", "дом; дома", "/həʊm/", "I am at home."),
    ("work", "работа; работать", "/wɜːk/", "I work every day."),
    ("school", "школа", "/skuːl/", "The school is here."),
    ("left", "налево; левый", "/left/", "Turn left."),
    ("right", "направо; правый", "/raɪt/", "Turn right."),
    ("here", "здесь", "/hɪə/", "I am here."),
    ("where", "где", "/weə/", "Where is the station?"),
    ("what", "что; какой", "/wɒt/", "What is your name?"),
    ("want", "хотеть", "/wɒnt/", "I want coffee."),
    ("need", "нуждаться; нужно", "/niːd/", "I need help."),
    ("like", "нравиться", "/laɪk/", "I like tea."),
    ("understand", "понимать", "/ˌʌndəˈstænd/", "I understand."),
    ("help", "помощь; помогать", "/help/", "Can you help me?"),
    ("speak", "говорить", "/spiːk/", "Do you speak English?"),
    ("slowly", "медленно", "/ˈsləʊli/", "Speak slowly, please."),
    ("today", "сегодня", "/təˈdeɪ/", "I work today."),
    ("tomorrow", "завтра", "/təˈmɒrəʊ/", "See you tomorrow."),
    ("yesterday", "вчера", "/ˈjestədeɪ/", "I worked yesterday."),
]
WORD_TRANSLATIONS = {english.casefold(): russian for english, russian, _, _ in BEGINNER_WORDS}


def lesson(title, title_ru, category, description, theory, examples, exercises):
    return {
        "title": title, "title_ru": title_ru, "category": category,
        "description": description, "theory": theory,
        "examples": examples, "exercises": exercises,
    }


PRE_A1_LESSONS = [
    lesson("First sounds and words", "Первые звуки и слова", "alphabet", "Узнаём и произносим первые полезные слова.", "Название буквы и звук в слове часто отличаются. Сначала слушайте и повторяйте целое слово: hello, yes, no.", [("Hello!", "Привет!"), ("Yes. / No.", "Да. / Нет.")], [
        ("mc", "Choose ‘привет’:", "Выберите перевод «привет»:", ["Hello", "Goodbye", "Please", "No"], "Hello"),
        ("mc", "Choose ‘да’:", "Выберите перевод «да»:", ["No", "Yes", "Sorry", "Thanks"], "Yes"),
        ("fill", "Complete: h_llo", "Вставьте букву: h_llo", None, "e"),
        ("translate", "Translate: ‘нет’", "Напишите по-английски: «нет»", None, "no"),
        ("speak", "Say: Hello", "Нажмите запись и скажите Hello.", None, "hello"),
    ]),
    lesson("Greetings", "Приветствия и прощание", "vocabulary", "Здороваемся, спрашиваем «как дела?» и прощаемся.", "Hello — нейтральное «привет». Hi — неформальное. How are you? — «Как дела?». Goodbye / Bye — прощание.", [("Hello! How are you?", "Привет! Как дела?"), ("I am fine, thanks.", "У меня всё хорошо, спасибо.")], [
        ("mc", "What do you say when you meet someone?", "Что сказать при встрече?", ["Hello", "Goodbye", "No", "Sorry"], "Hello"),
        ("mc", "Choose ‘Как дела?’", "Выберите «Как дела?»", ["What is your name?", "How are you?", "Where are you?", "Who are you?"], "How are you?"),
        ("fill", "I am fine, ___ .", "Я в порядке, спасибо: I am fine, ___ .", None, "thanks", ["thank you"]),
        ("translate", "Translate: ‘Пока’", "Напишите по-английски: «Пока»", None, "bye", ["goodbye"]),
        ("speak", "Say: Hello, how are you?", "Произнесите фразу приветствия.", None, "hello how are you"),
    ]),
    lesson("Introduce yourself", "Как представиться", "speaking", "Говорим своё имя и спрашиваем имя собеседника.", "My name is ... — «Меня зовут ...». I am ... — короткий вариант. What is your name? — «Как вас зовут?».", [("My name is Anna.", "Меня зовут Анна."), ("Nice to meet you.", "Приятно познакомиться.")], [
        ("mc", "Choose ‘Меня зовут Анна’:", "Выберите правильную фразу:", ["My name is Anna", "Your name is Anna", "I name Anna", "She is Anna"], "My name is Anna"),
        ("mc", "How do you ask a person's name?", "Как спросить имя?", ["What is your name?", "How are you?", "Where are you?", "Are you name?"], "What is your name?"),
        ("fill", "My ___ is Alex.", "Вставьте слово: My ___ is Alex.", None, "name"),
        ("translate", "Translate: ‘Я Анна’", "Напишите по-английски: «Я Анна»", None, "I am Anna", ["I'm Anna"]),
        ("speak", "Say: My name is Alex", "Произнесите: My name is Alex.", None, "my name is alex"),
    ]),
    lesson("Polite words", "Вежливые слова", "vocabulary", "Используем please, thank you и sorry.", "Please добавляем к просьбе. Thank you / Thanks — благодарность. Sorry — извинение. You're welcome — ответ на благодарность.", [("Water, please.", "Воды, пожалуйста."), ("Thank you! — You're welcome.", "Спасибо! — Пожалуйста.")], [
        ("mc", "Choose a polite request:", "Выберите вежливую просьбу:", ["Water, please", "Water now", "Give water", "I water"], "Water, please"),
        ("mc", "Someone says ‘Thank you’. You answer:", "Вам сказали «Спасибо». Ответьте:", ["You're welcome", "Goodbye", "Sorry", "No"], "You're welcome"),
        ("fill", "___, I do not understand.", "Извините, я не понимаю: ___, I do not understand.", None, "sorry"),
        ("translate", "Translate: ‘Спасибо’", "Напишите по-английски: «Спасибо»", None, "thank you", ["thanks"]),
        ("speak", "Say: Water, please", "Произнесите вежливую просьбу.", None, "water please"),
    ]),
    lesson("Numbers 0–10", "Числа от 0 до 10", "vocabulary", "Считаем до десяти и называем количество.", "zero 0 · one 1 · two 2 · three 3 · four 4 · five 5 · six 6 · seven 7 · eight 8 · nine 9 · ten 10", [("Two coffees, please.", "Два кофе, пожалуйста."), ("I have three books.", "У меня три книги.")], [
        ("mc", "Choose number 3:", "Как будет 3?", ["two", "three", "five", "eight"], "three"),
        ("mc", "What comes after four?", "Какое число идёт после four?", ["three", "five", "seven", "ten"], "five"),
        ("fill", "one, two, ___", "Продолжите: one, two, ___", None, "three"),
        ("translate", "Translate: ‘два кофе, пожалуйста’", "Напишите фразу по-английски.", None, "two coffees please", ["two coffee please"]),
        ("speak", "Count: one, two, three", "Произнесите: one, two, three.", None, "one two three"),
    ]),
    lesson("Colors and objects", "Цвета и предметы", "vocabulary", "Называем цвет простого предмета.", "red — красный, blue — синий, green — зелёный, black — чёрный, white — белый. It is blue — «Это синее».", [("The phone is black.", "Телефон чёрный."), ("It is a red book.", "Это красная книга.")], [
        ("mc", "Choose ‘зелёный’:", "Выберите перевод:", ["red", "green", "blue", "black"], "green"),
        ("mc", "Snow is ...", "Снег ...", ["white", "black", "red", "green"], "white"),
        ("fill", "The phone is ___ . (чёрный)", "Вставьте цвет.", None, "black"),
        ("translate", "Translate: ‘Это синее’", "Напишите по-английски.", None, "It is blue", ["It's blue"]),
        ("speak", "Say: It is a red book", "Произнесите фразу.", None, "it is a red book"),
    ]),
    lesson("My family", "Моя семья", "vocabulary", "Учимся говорить о близких.", "mother — мама, father — папа, brother — брат, sister — сестра, friend — друг или подруга. This is my ... — «Это мой/моя ...».", [("This is my sister.", "Это моя сестра."), ("He is my friend.", "Он мой друг.")], [
        ("mc", "Choose ‘сестра’:", "Выберите перевод:", ["mother", "sister", "brother", "friend"], "sister"),
        ("mc", "‘This is my father’ means:", "Выберите перевод фразы:", ["Это мой папа", "Это моя мама", "Это мой брат", "Это мой друг"], "Это мой папа"),
        ("fill", "This is my ___ . (мама)", "Вставьте слово.", None, "mother"),
        ("translate", "Translate: ‘Он мой друг’", "Напишите по-английски.", None, "He is my friend", ["He's my friend"]),
        ("speak", "Say: This is my family", "Произнесите фразу.", None, "this is my family"),
    ]),
    lesson("I am, you are", "Глагол to be: am, is, are", "grammar", "Строим первые полные предложения.", "I am · you/we/they are · he/she/it is. В английском настоящем времени нельзя пропускать am/is/are.", [("I am here.", "Я здесь."), ("She is at home.", "Она дома."), ("We are ready.", "Мы готовы.")], [
        ("mc", "I ___ ready.", "Выберите am/is/are:", ["am", "is", "are", "be"], "am"),
        ("mc", "She ___ at home.", "Выберите am/is/are:", ["am", "is", "are", "be"], "is"),
        ("fill", "We ___ here.", "Вставьте am/is/are.", None, "are"),
        ("translate", "Translate: ‘Я дома’", "Напишите по-английски.", None, "I am at home", ["I'm at home"]),
        ("speak", "Say: I am ready", "Произнесите фразу.", None, "i am ready"),
    ]),
    lesson("I want and I need", "Я хочу и мне нужно", "speaking", "Просим воду, еду или помощь.", "I want ... — «Я хочу ...». I need ... — «Мне нужно ...». I would like ... — более вежливое «Я бы хотел ...».", [("I need help.", "Мне нужна помощь."), ("I would like tea, please.", "Я бы хотел чай, пожалуйста.")], [
        ("mc", "You need help. Choose the phrase:", "Вам нужна помощь. Выберите фразу:", ["I need help", "I am help", "I help need", "Help is I"], "I need help"),
        ("mc", "Choose the polite order:", "Выберите вежливый заказ:", ["I would like coffee, please", "Coffee now", "You coffee", "I am coffee"], "I would like coffee, please"),
        ("fill", "I ___ water.", "Мне нужна вода: I ___ water.", None, "need"),
        ("translate", "Translate: ‘Я хочу чай’", "Напишите по-английски.", None, "I want tea", ["I'd like tea", "I would like tea"]),
        ("speak", "Say: I need help, please", "Произнесите просьбу.", None, "i need help please"),
    ]),
    lesson("Simple questions", "Простые вопросы", "grammar", "Спрашиваем «что?» и «где?».", "What? — что? Where? — где? Where is ...? — где находится ...? What is this? — что это?", [("Where is the station?", "Где станция?"), ("What is this? — It is tea.", "Что это? — Это чай.")], [
        ("mc", "Choose ‘Где?’:", "Выберите перевод:", ["What?", "Where?", "Who?", "How?"], "Where?"),
        ("mc", "You are looking for a station. Ask:", "Вы ищете станцию. Спросите:", ["Where is the station?", "What station?", "Station is you?", "How station?"], "Where is the station?"),
        ("fill", "___ is this?", "Что это? Вставьте слово.", None, "what"),
        ("translate", "Translate: ‘Где мой телефон?’", "Напишите по-английски.", None, "Where is my phone", ["Where's my phone"]),
        ("speak", "Say: Where is the station?", "Произнесите вопрос.", None, "where is the station"),
    ]),
    lesson("I do not understand", "Если вы не понимаете", "speaking", "Просим повторить или говорить медленнее.", "I do not understand — «Я не понимаю». Please repeat — «Повторите, пожалуйста». Speak slowly, please — «Говорите медленнее, пожалуйста».", [("Sorry, I do not understand.", "Извините, я не понимаю."), ("Can you repeat, please?", "Можете повторить?")], [
        ("mc", "You did not understand. Say:", "Вы не поняли. Скажите:", ["I do not understand", "I am not English", "No understand you", "I understand"], "I do not understand"),
        ("mc", "Ask the person to speak slowly:", "Попросите говорить медленнее:", ["Speak slowly, please", "Speak fast", "Do not speak", "Slow is speak"], "Speak slowly, please"),
        ("fill", "Please ___ . (повторите)", "Вставьте слово.", None, "repeat"),
        ("translate", "Translate: ‘Извините, я не понимаю’", "Напишите по-английски.", None, "Sorry I do not understand", ["Sorry I don't understand"]),
        ("speak", "Say: Can you repeat, please?", "Произнесите просьбу.", None, "can you repeat please"),
    ]),
    lesson("First conversation", "Первый разговор", "dialogue", "Собираем фразы в короткий диалог.", "Hello! — Hello! What is your name? — My name is Anna. Nice to meet you. — Nice to meet you too. Goodbye!", [("Nice to meet you too.", "Мне тоже приятно познакомиться."), ("See you tomorrow!", "Увидимся завтра!")], [
        ("mc", "A person says ‘Hello!’. You answer:", "Вам сказали Hello. Ответьте:", ["Hello!", "No", "Sorry", "Please"], "Hello!"),
        ("mc", "A person asks ‘What is your name?’. You answer:", "Вас спросили имя. Ответьте:", ["My name is Alex", "I am fine", "Goodbye", "Yes, please"], "My name is Alex"),
        ("fill", "Nice to ___ you.", "Приятно познакомиться: Nice to ___ you.", None, "meet"),
        ("translate", "Translate: ‘Увидимся завтра’", "Напишите по-английски.", None, "See you tomorrow"),
        ("speak", "Say: Hello, my name is Alex", "Представьтесь вслух.", None, "hello my name is alex"),
    ]),
]


A1_LESSONS = [
    ("Daily routine", "Распорядок дня", "vocabulary", "I wake up at seven. I work in the morning. I go home in the evening.", [("mc", "Choose ‘Я работаю каждый день’:", "Выберите перевод.", ["I work every day", "I am work every day", "I worked tomorrow", "I every work"], "I work every day"), ("fill", "I ___ up at seven.", "Вставьте слово wake.", None, "wake"), ("translate", "Translate: ‘Я иду домой вечером’", "Напишите по-английски.", None, "I go home in the evening"), ("speak", "Say: I work every day", "Произнесите фразу.", None, "i work every day")]),
    ("Present Simple", "Present Simple: привычки", "grammar", "I/you/we/they work. He/she works. Для he/she обычно добавляем -s.", [("mc", "She ___ every day.", "Выберите форму глагола.", ["work", "works", "working", "is work"], "works"), ("fill", "They ___ English. (study)", "Поставьте study в правильную форму.", None, "study"), ("translate", "Translate: ‘Он любит кофе’", "Напишите по-английски.", None, "He likes coffee"), ("speak", "Say: She speaks English", "Произнесите фразу.", None, "she speaks english")]),
    ("Questions with do", "Вопросы с do и does", "grammar", "Do you speak English? Does she work here? После do/does основной глагол идёт без -s.", [("mc", "___ you like tea?", "Выберите Do или Does.", ["Do", "Does", "Are", "Is"], "Do"), ("fill", "Does he ___ here? (work)", "Вставьте правильную форму.", None, "work"), ("translate", "Translate: ‘Ты говоришь по-английски?’", "Напишите по-английски.", None, "Do you speak English"), ("speak", "Say: Do you speak English?", "Произнесите вопрос.", None, "do you speak english")]),
    ("Can and cannot", "Могу и не могу", "grammar", "I can help. I cannot (can't) come. После can глагол не меняется.", [("mc", "Choose ‘Я могу помочь’:", "Выберите перевод.", ["I can help", "I can to help", "I am help", "I helps"], "I can help"), ("fill", "She can ___ English. (speak)", "Вставьте глагол.", None, "speak"), ("translate", "Translate: ‘Я не могу прийти’", "Напишите по-английски.", None, "I cannot come", ["I can't come"]), ("speak", "Say: Can you help me?", "Произнесите просьбу.", None, "can you help me")]),
    ("At a cafe", "В кафе", "dialogue", "I would like a coffee, please. Anything else? That's all, thank you. How much is it?", [("mc", "Order politely:", "Сделайте вежливый заказ.", ["I would like tea, please", "Give tea", "Tea now", "I tea"], "I would like tea, please"), ("fill", "How ___ is it?", "Сколько это стоит?", None, "much"), ("translate", "Translate: ‘Это всё, спасибо’", "Напишите по-английски.", None, "That is all thank you", ["That's all thank you"]), ("speak", "Say: I would like a coffee, please", "Сделайте заказ вслух.", None, "i would like a coffee please")]),
    ("Directions", "Как спросить дорогу", "speaking", "Where is the station? Go straight. Turn left. Turn right. It is next to the bank.", [("mc", "Choose ‘Поверните налево’:", "Выберите перевод.", ["Turn left", "Turn right", "Go back", "Stop here"], "Turn left"), ("fill", "Go ___ . (прямо)", "Вставьте слово.", None, "straight"), ("translate", "Translate: ‘Где автобусная остановка?’", "Напишите по-английски.", None, "Where is the bus stop"), ("speak", "Say: Go straight and turn right", "Объясните дорогу вслух.", None, "go straight and turn right")]),
    ("Yesterday", "Первое прошедшее время", "grammar", "Для многих глаголов добавляем -ed: work → worked. Частые исключения: go → went, see → saw, have → had.", [("mc", "Past form of go:", "Прошедшая форма go:", ["goed", "went", "gone", "goes"], "went"), ("fill", "Yesterday I ___ at home. (work)", "Поставьте work в прошедшее время.", None, "worked"), ("translate", "Translate: ‘Вчера я видел друга’", "Напишите по-английски.", None, "Yesterday I saw a friend", ["I saw a friend yesterday"]), ("speak", "Say: I worked yesterday", "Произнесите фразу.", None, "i worked yesterday")]),
    ("Plans", "Планы на завтра", "grammar", "Для простого плана используйте be going to: I am going to study tomorrow.", [("mc", "Choose a future plan:", "Выберите план на будущее.", ["I am going to study tomorrow", "I studied yesterday", "I study now", "I going study"], "I am going to study tomorrow"), ("fill", "We are going to ___ English.", "Вставьте study.", None, "study"), ("translate", "Translate: ‘Я собираюсь работать завтра’", "Напишите по-английски.", None, "I am going to work tomorrow", ["I'm going to work tomorrow"]), ("speak", "Say: I am going to study English", "Расскажите о плане.", None, "i am going to study english")]),
]


class Command(BaseCommand):
    help = "Replace noisy auto-generated lessons with a practical Pre-A1/A1 course"

    @transaction.atomic
    def handle(self, *args, **options):
        Lesson.objects.filter(category=SkillCategory.READING).delete()
        self._seed_words()
        self._seed_lessons(CEFRLevel.PRE_A1, PRE_A1_LESSONS)
        self._seed_a1()
        self._seed_exam()
        count = Lesson.objects.filter(level__in=[CEFRLevel.PRE_A1, CEFRLevel.A1], is_published=True).count()
        self.stdout.write(self.style.SUCCESS(f"Beginner course ready: {count} lessons"))

    def _seed_words(self):
        curated = {row[0] for row in BEGINNER_WORDS}
        Word.objects.exclude(english__in=curated).delete()
        for rank, (english, russian, transcription, example) in enumerate(BEGINNER_WORDS, 1):
            Word.objects.update_or_create(english=english, defaults={
                "russian": russian, "transcription": transcription,
                "level": CEFRLevel.PRE_A1 if rank <= 32 else CEFRLevel.A1,
                "frequency_rank": rank, "example_sentence": example,
            })

    def _seed_lessons(self, level, lessons):
        for order, data in enumerate(lessons, 1):
            lesson_obj, _ = Lesson.objects.update_or_create(level=level, order=order, defaults={
                "title": data["title"], "title_ru": data["title_ru"], "description": data["description"],
                "category": data["category"], "content": {"blocks": [
                    {"type": "text", "title": "Коротко и понятно", "body": data["theory"]},
                    *({"type": "example", "en": en, "ru": ru} for en, ru in data["examples"]),
                ]}, "estimated_minutes": 10, "xp_reward": 20, "is_published": True,
            })
            self._replace_exercises(lesson_obj, data["exercises"], data["category"])
        Lesson.objects.filter(level=level, order__gt=len(lessons)).exclude(category=SkillCategory.READING).update(is_published=False)

    def _seed_a1(self):
        for order, (title, title_ru, category, theory, exercises) in enumerate(A1_LESSONS, 1):
            lesson_obj, _ = Lesson.objects.update_or_create(level=CEFRLevel.A1, order=order, defaults={
                "title": title, "title_ru": title_ru, "description": "Практический урок уровня A1 с короткими фразами для речи.",
                "category": category, "content": {"blocks": [{"type": "text", "title": "Правило", "body": theory}]},
                "estimated_minutes": 12, "xp_reward": 25, "is_published": True,
            })
            self._replace_exercises(lesson_obj, exercises, category)
        Lesson.objects.filter(level=CEFRLevel.A1, order__gt=len(A1_LESSONS)).update(is_published=False)

    def _replace_exercises(self, lesson_obj, specs, skill):
        lesson_obj.exercises.all().delete()
        for order, spec in enumerate(specs, 1):
            ex_type, question, question_ru, options, answer, *rest = spec
            alternatives = rest[0] if rest else []
            data = {"correct_answer": answer, "explanation": "Вернитесь к примерам урока и попробуйте ещё раз."}
            if options:
                data["options"] = options
            if alternatives:
                data["alternatives"] = alternatives
            if ex_type == Exercise.ExerciseType.SPEAK:
                data["audio_text"] = answer
            translation = WORD_TRANSLATIONS.get(str(answer).casefold())
            if translation:
                data["srs_front"] = answer
                data["srs_back"] = translation
            Exercise.objects.create(lesson=lesson_obj, order=order, exercise_type=ex_type, question=question,
                                    question_ru=question_ru, data=data, points=5, skill=skill)

    def _seed_exam(self):
        LevelExam.objects.update_or_create(level=CEFRLevel.PRE_A1, defaults={
            "title": "Pre-A1: первый разговор", "description": "Проверьте базовые фразы перед переходом к A1.",
            "pass_score": 75, "time_limit_minutes": 10, "questions": [
                {"type": "mc", "question": "Choose ‘Привет’", "options": ["Hello", "Goodbye", "Sorry"], "correct_answer": "Hello"},
                {"type": "fill", "question": "My ___ is Alex.", "correct_answer": "name"},
                {"type": "fill", "question": "I ___ ready.", "correct_answer": "am"},
                {"type": "translate", "question": "Переведите: «Мне нужна помощь»", "correct_answer": "I need help"},
                {"type": "translate", "question": "Переведите: «Говорите медленнее, пожалуйста»", "correct_answer": "Speak slowly please", "alternatives": ["Speak slowly, please"]},
                {"type": "translate", "question": "Переведите: «Где станция?»", "correct_answer": "Where is the station", "alternatives": ["Where's the station"]},
            ],
        })
