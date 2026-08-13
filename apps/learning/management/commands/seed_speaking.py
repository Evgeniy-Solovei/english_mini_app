from django.core.management.base import BaseCommand

from apps.learning.speaking_models import DialogueScenario, PhrasePack, ShadowPhrase
from apps.users.models import CEFRLevel


class Command(BaseCommand):
    help = "Seed shadowing phrases, phonetics, and dialogue scenarios"

    def handle(self, *args, **options):
        self.stdout.write("Seeding speaking content...")
        self._phonetics()
        self._survival()
        self._small_talk()
        self._shadowing()
        self._dialogues()
        self.stdout.write(self.style.SUCCESS(
            f"Done! Packs: {PhrasePack.objects.count()}, "
            f"Phrases: {ShadowPhrase.objects.count()}, "
            f"Dialogues: {DialogueScenario.objects.count()}"
        ))

    def _pack(self, slug, title, title_ru, pack_type, level, emoji, order, phrases):
        pack, _ = PhrasePack.objects.update_or_create(
            slug=slug,
            defaults={
                "title": title,
                "title_ru": title_ru,
                "pack_type": pack_type,
                "level": level,
                "emoji": emoji,
                "order": order,
                "is_published": True,
                "description": title_ru,
            },
        )
        for i, p in enumerate(phrases, 1):
            ShadowPhrase.objects.update_or_create(
                pack=pack,
                order=i,
                defaults={
                    "english": p[0],
                    "russian": p[1] if len(p) > 1 else "",
                    "phonetic": p[2] if len(p) > 2 else "",
                    "tip": p[3] if len(p) > 3 else "",
                },
            )
        return pack

    def _phonetics(self):
        self._pack(
            "phonetics-th-w-v",
            "Hard Sounds: TH, W, V",
            "Сложные звуки: TH, W, V",
            PhrasePack.PackType.PHONETICS,
            CEFRLevel.PRE_A1,
            "🦷",
            1,
            [
                ("think", "думать", "/θɪŋk/", "TH: язык между зубами, воздух."),
                ("three", "три", "/θriː/", "TH + R — не «сри»."),
                ("this", "это", "/ðɪs/", "Звонкий TH — как мягкое «з» с языком."),
                ("the", "the", "/ðə/", "Самое частое слово — тренируй TH."),
                ("thank you", "спасибо", "/θæŋk juː/", "Thank — глухой TH."),
                ("water", "вода", "/ˈwɔːtər/", "W: губы как «у», не «в»."),
                ("what", "что", "/wɒt/", "What — округли губы."),
                ("where", "где", "/weər/", "W, не V."),
                ("very", "очень", "/ˈveri/", "V: зубы на губу."),
                ("voice", "голос", "/vɔɪs/", "V в начале."),
            ],
        )
        self._pack(
            "phonetics-vowels",
            "Short vs Long Vowels",
            "Короткие и длинные гласные",
            PhrasePack.PackType.PHONETICS,
            CEFRLevel.PRE_A1,
            "👄",
            2,
            [
                ("ship", "корабль", "/ʃɪp/", "Короткий /ɪ/."),
                ("sheep", "овца", "/ʃiːp/", "Долгий /iː/ — улыбнись."),
                ("sit", "сидеть", "/sɪt/", "Короткий i."),
                ("seat", "сиденье", "/siːt/", "Долгий ee."),
                ("cat", "кот", "/kæt/", "Широкий /æ/."),
                ("cut", "резать", "/kʌt/", "Звук /ʌ/ как «а» короткое."),
                ("good", "хороший", "/ɡʊd/", "Короткий oo."),
                ("food", "еда", "/fuːd/", "Долгий oo."),
            ],
        )

    def _survival(self):
        self._pack(
            "survival-a1",
            "100 Survival Phrases (starter)",
            "Фразы для выживания",
            PhrasePack.PackType.SURVIVAL,
            CEFRLevel.A1,
            "🆘",
            10,
            [
                ("Hello!", "Привет!", "/həˈloʊ/", ""),
                ("Hi, how are you?", "Привет, как дела?", "", ""),
                ("I'm fine, thank you.", "Я в порядке, спасибо.", "", ""),
                ("Nice to meet you.", "Приятно познакомиться.", "", ""),
                ("My name is Alex.", "Меня зовут Алекс.", "", ""),
                ("Where are you from?", "Откуда ты?", "", ""),
                ("I'm from Russia.", "Я из России.", "", ""),
                ("I don't understand.", "Я не понимаю.", "", "Говори медленно и чётко."),
                ("Can you repeat that, please?", "Можете повторить?", "", ""),
                ("Can you speak slowly?", "Можете говорить медленнее?", "", ""),
                ("How much is it?", "Сколько это стоит?", "", ""),
                ("Where is the bathroom?", "Где туалет?", "", ""),
                ("I would like water, please.", "Мне воды, пожалуйста.", "", ""),
                ("Excuse me.", "Извините.", "", ""),
                ("Sorry.", "Простите.", "", ""),
                ("Thank you very much.", "Большое спасибо.", "", ""),
                ("You're welcome.", "Пожалуйста / не за что.", "", ""),
                ("See you later!", "Увидимся!", "", ""),
                ("Have a nice day!", "Хорошего дня!", "", ""),
                ("Help!", "Помогите!", "", ""),
            ],
        )

    def _small_talk(self):
        self._pack(
            "smalltalk-a2",
            "Small Talk Essentials",
            "Светская беседа",
            PhrasePack.PackType.SMALL_TALK,
            CEFRLevel.A2,
            "☕️",
            20,
            [
                ("How was your weekend?", "Как прошли выходные?", "", ""),
                ("It was great, thanks!", "Было отлично, спасибо!", "", ""),
                ("What do you do?", "Чем занимаешься / кем работаешь?", "", ""),
                ("I work in an office.", "Я работаю в офисе.", "", ""),
                ("The weather is nice today.", "Сегодня хорошая погода.", "", ""),
                ("Do you like coffee?", "Тебе нравится кофе?", "", ""),
                ("Yes, I love it!", "Да, обожаю!", "", ""),
                ("What are your hobbies?", "Какие у тебя хобби?", "", ""),
                ("I like reading and sports.", "Мне нравится чтение и спорт.", "", ""),
                ("That sounds interesting!", "Звучит интересно!", "", ""),
            ],
        )

    def _shadowing(self):
        self._pack(
            "shadow-daily",
            "Daily Shadowing — Listen & Repeat",
            "Ежедневный shadowing",
            PhrasePack.PackType.SHADOWING,
            CEFRLevel.A1,
            "🎧",
            5,
            [
                ("Good morning!", "Доброе утро!", "", "Слушай → пауза → повтори вслух."),
                ("How are you doing today?", "Как у тебя дела сегодня?", "", ""),
                ("I am learning English every day.", "Я учу английский каждый день.", "", ""),
                ("Could you help me, please?", "Не могли бы вы помочь?", "", ""),
                ("What time is it?", "Который час?", "", ""),
                ("I need to practice speaking.", "Мне нужно практиковать речь.", "", ""),
                ("Let's meet tomorrow at five.", "Давай встретимся завтра в пять.", "", ""),
                ("That is a good idea.", "Это хорошая идея.", "", ""),
                ("I think so too.", "Я тоже так думаю.", "", ""),
                ("See you soon!", "До скорого!", "", ""),
                ("Please call me later.", "Позвоните мне позже, пожалуйста.", "", ""),
                ("I am hungry.", "Я голоден.", "", ""),
                ("Where do you live?", "Где ты живёшь?", "", ""),
                ("I live in a big city.", "Я живу в большом городе.", "", ""),
                ("Open the window, please.", "Открой окно, пожалуйста.", "", ""),
            ],
        )

    def _dialogues(self):
        scenarios = [
            {
                "slug": "meet-and-greet",
                "title": "Meet & Greet",
                "title_ru": "Знакомство",
                "description": "Познакомься с собеседником — отвечай голосом на английском.",
                "level": CEFRLevel.A1,
                "emoji": "🤝",
                "setting": "At a language school",
                "order": 1,
                "turns": [
                    {"role": "bot", "text": "Hello! What's your name?", "hint_ru": "Скажи своё имя: My name is ..."},
                    {"role": "user", "hint_ru": "My name is ... / I'm ...", "keywords": ["name", "i'm", "i am", "my"], "accept": ["My name is Alex", "I'm Alex", "I am Alex"]},
                    {"role": "bot", "text": "Nice to meet you! Where are you from?", "hint_ru": "Откуда ты?"},
                    {"role": "user", "hint_ru": "I'm from ...", "keywords": ["from", "russia", "moscow"], "accept": ["I'm from Russia", "I am from Russia", "I'm from Moscow"]},
                    {"role": "bot", "text": "Cool! How are you today?", "hint_ru": "Как дела?"},
                    {"role": "user", "hint_ru": "I'm fine / good / great, thanks!", "keywords": ["fine", "good", "great", "ok", "well"], "accept": ["I'm fine thank you", "I'm good", "I'm great thanks"]},
                    {"role": "bot", "text": "Great! See you later!", "hint_ru": "Диалог завершён 🎉"},
                ],
            },
            {
                "slug": "cafe-order",
                "title": "At the Cafe",
                "title_ru": "В кафе",
                "description": "Закажи еду и напиток — типичный бытовой диалог.",
                "level": CEFRLevel.A1,
                "emoji": "☕",
                "setting": "Cafe",
                "order": 2,
                "turns": [
                    {"role": "bot", "text": "Hi! What would you like to order?", "hint_ru": "Что будешь заказывать?"},
                    {"role": "user", "hint_ru": "I would like ... / Can I have ...", "keywords": ["coffee", "tea", "water", "like", "have", "want"], "accept": ["I would like a coffee", "Can I have tea please", "I want water"]},
                    {"role": "bot", "text": "Sure. Anything else?", "hint_ru": "Что-нибудь ещё?"},
                    {"role": "user", "hint_ru": "Yes, a sandwich / No, that's all", "keywords": ["sandwich", "cake", "no", "all", "yes"], "accept": ["A sandwich please", "No that's all", "Yes a cake"]},
                    {"role": "bot", "text": "That will be five dollars. Cash or card?", "hint_ru": "Наличные или карта?"},
                    {"role": "user", "hint_ru": "Card, please. / Cash.", "keywords": ["card", "cash"], "accept": ["Card please", "Cash", "By card"]},
                    {"role": "bot", "text": "Thank you! Enjoy your meal!", "hint_ru": "Готово!"},
                ],
            },
            {
                "slug": "shopping",
                "title": "Shopping",
                "title_ru": "В магазине",
                "description": "Спроси цену и купи вещь.",
                "level": CEFRLevel.A2,
                "emoji": "🛍️",
                "setting": "Clothes store",
                "order": 3,
                "turns": [
                    {"role": "bot", "text": "Hello! Can I help you?", "hint_ru": "Нужна помощь?"},
                    {"role": "user", "hint_ru": "Yes, I'm looking for a T-shirt.", "keywords": ["looking", "shirt", "jacket", "yes"], "accept": ["Yes I'm looking for a T-shirt", "I'm looking for a jacket"]},
                    {"role": "bot", "text": "What size do you need?", "hint_ru": "Какой размер?"},
                    {"role": "user", "hint_ru": "Medium / Large, please.", "keywords": ["small", "medium", "large"], "accept": ["Medium please", "Large", "Small"]},
                    {"role": "bot", "text": "Here you are. It's twenty dollars.", "hint_ru": "Вот, 20 долларов."},
                    {"role": "user", "hint_ru": "I'll take it. / How much is it?", "keywords": ["take", "buy", "how", "much"], "accept": ["I'll take it", "I will take it", "How much is it"]},
                    {"role": "bot", "text": "Perfect! Have a nice day!", "hint_ru": "Успех!"},
                ],
            },
            {
                "slug": "directions",
                "title": "Asking for Directions",
                "title_ru": "Как пройти?",
                "description": "Спроси дорогу до станции.",
                "level": CEFRLevel.A2,
                "emoji": "🗺️",
                "setting": "Street",
                "order": 4,
                "turns": [
                    {"role": "bot", "text": "Excuse me, are you lost?", "hint_ru": "Ты заблудился?"},
                    {"role": "user", "hint_ru": "Yes, where is the train station?", "keywords": ["station", "where", "train", "metro"], "accept": ["Where is the train station", "Where is the station please"]},
                    {"role": "bot", "text": "Go straight, then turn left.", "hint_ru": "Иди прямо, потом налево."},
                    {"role": "user", "hint_ru": "Is it far?", "keywords": ["far", "near", "long"], "accept": ["Is it far", "Is it near"]},
                    {"role": "bot", "text": "No, about five minutes.", "hint_ru": "Минут пять."},
                    {"role": "user", "hint_ru": "Thank you so much!", "keywords": ["thank", "thanks"], "accept": ["Thank you so much", "Thanks a lot", "Thank you"]},
                    {"role": "bot", "text": "You're welcome!", "hint_ru": "Готово!"},
                ],
            },
            {
                "slug": "job-chat",
                "title": "Talking about Work",
                "title_ru": "О работе",
                "description": "Простой разговор о работе (B1).",
                "level": CEFRLevel.B1,
                "emoji": "💼",
                "setting": "Networking event",
                "order": 5,
                "turns": [
                    {"role": "bot", "text": "So, what do you do for a living?", "hint_ru": "Кем работаешь?"},
                    {"role": "user", "hint_ru": "I work as a ... / I'm a ...", "keywords": ["work", "job", "engineer", "teacher", "student", "developer"], "accept": ["I work as a developer", "I'm a teacher", "I am a student"]},
                    {"role": "bot", "text": "Interesting! Do you enjoy it?", "hint_ru": "Нравится?"},
                    {"role": "user", "hint_ru": "Yes, I like it because...", "keywords": ["yes", "like", "enjoy", "love", "sometimes"], "accept": ["Yes I like it", "Yes I enjoy it a lot"]},
                    {"role": "bot", "text": "What are you working on these days?", "hint_ru": "Над чем работаешь сейчас?"},
                    {"role": "user", "hint_ru": "I'm working on a new project.", "keywords": ["project", "working", "learning", "app"], "accept": ["I'm working on a new project", "I am learning English"]},
                    {"role": "bot", "text": "Sounds great. Good luck!", "hint_ru": "Отлично!"},
                ],
            },
        ]

        for s in scenarios:
            DialogueScenario.objects.update_or_create(
                slug=s["slug"],
                defaults={
                    "title": s["title"],
                    "title_ru": s["title_ru"],
                    "description": s["description"],
                    "level": s["level"],
                    "emoji": s["emoji"],
                    "setting": s["setting"],
                    "turns": s["turns"],
                    "order": s["order"],
                    "is_published": True,
                },
            )
