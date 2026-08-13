from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.learning.models import ReadingText
from apps.learning.data.graded_readers import SHORT_READERS


class Command(BaseCommand):
    help = "Seed the CEFR-aligned adult course and original graded readers"

    def handle(self, *args, **options):
        self.stdout.write("Seeding the complete CEFR-aligned adult curriculum...")
        call_command("seed_curriculum_v2")
        self._seed_books()
        self.stdout.write(self.style.SUCCESS(
            "Done! Full Pre-A1/A1 course and original reading library are ready."
        ))

    def _seed_books(self):
        ReadingText.objects.filter(
            source="graded", source_id__in=["book_a1_1", "book_a2_1"]
        ).delete()
        books = [
            {
                "source_id": "original_a1_new_city",
                "title": "A New Week in Minsk",
                "title_ru": "Новая неделя в Минске",
                "level": "A1",
                "cover_emoji": "🏙️",
                "description": "Оригинальная история о знакомстве, работе и ежедневных делах.",
                "chapters": [
                    {
                        "title": "1. Monday Morning",
                        "text": "Alex lives in Minsk. He gets up at seven and has tea and bread for breakfast. At eight, he takes the bus to work. The office is near a small park. Alex is new, so he asks, ‘Where is room twelve?’ A woman smiles and shows him the room.",
                        "text_ru": "Алекс живёт в Минске. Он встаёт в семь и завтракает чаем и хлебом. В восемь он едет на работу на автобусе. Офис находится рядом с небольшим парком. Алекс здесь новичок, поэтому спрашивает: «Где кабинет двенадцать?» Женщина улыбается и показывает ему кабинет.",
                        "word_count": 51,
                    },
                    {
                        "title": "2. Lunch with Anna",
                        "text": "At one o’clock, Anna asks Alex to have lunch. They go to a café across from the office. Alex orders soup and water. Anna has a salad and tea. They talk about music and films. Alex does not understand one question, so he says, ‘Sorry, can you repeat that slowly?’",
                        "text_ru": "В час Анна зовёт Алекса пообедать. Они идут в кафе напротив офиса. Алекс заказывает суп и воду. Анна берёт салат и чай. Они говорят о музыке и фильмах. Алекс не понимает один вопрос и говорит: «Извините, можете повторить это медленно?»",
                        "word_count": 52,
                    },
                    {
                        "title": "3. A Simple Plan",
                        "text": "After work, Alex needs some food. He buys apples, bread and milk. Then Anna sends a message: ‘Would you like coffee on Friday?’ Alex is busy on Friday, but he is free on Saturday. They agree to meet at six. Alex is happy because his new city feels friendlier now.",
                        "text_ru": "После работы Алексу нужны продукты. Он покупает яблоки, хлеб и молоко. Затем Анна пишет: «Хочешь выпить кофе в пятницу?» Алекс занят в пятницу, но свободен в субботу. Они договариваются встретиться в шесть. Алекс рад, потому что новый город теперь кажется дружелюбнее.",
                        "word_count": 52,
                    },
                ],
            },
            {
                "source_id": "original_a1_weekend_trip",
                "title": "The Weekend Trip",
                "title_ru": "Поездка на выходные",
                "level": "A1",
                "cover_emoji": "🚌",
                "description": "Оригинальная история о транспорте, гостинице и прошедшем дне.",
                "chapters": [
                    {
                        "title": "1. At the Station",
                        "text": "Maya and Leo are going to visit a small town. The train is fast but expensive, so they take the bus. At the station, Leo asks for two tickets. The bus leaves at half past nine. They have twenty minutes, so they buy water and wait near platform four.",
                        "text_ru": "Майя и Лео собираются посетить небольшой город. Поезд быстрый, но дорогой, поэтому они едут на автобусе. На вокзале Лео просит два билета. Автобус отправляется в половине десятого. У них есть двадцать минут, поэтому они покупают воду и ждут у четвёртой платформы.",
                        "word_count": 51,
                    },
                    {
                        "title": "2. The Hotel",
                        "text": "The hotel is opposite the bank. Maya has a reservation for one room. She asks what time breakfast starts. In the room, the Wi-Fi does not work. Leo calls reception and asks for help. A hotel worker comes five minutes later and fixes it.",
                        "text_ru": "Гостиница находится напротив банка. У Майи забронирован один номер. Она спрашивает, во сколько начинается завтрак. В номере не работает Wi-Fi. Лео звонит на стойку регистрации и просит помощи. Сотрудник гостиницы приходит через пять минут и всё исправляет.",
                        "word_count": 46,
                    },
                    {
                        "title": "3. Sunday Evening",
                        "text": "On Saturday they walked around the town, saw an old church and had lunch by the river. It rained in the afternoon, but they had a good day. On Sunday evening, they came home tired. Maya is going to print their photos tomorrow, and Leo is going to plan another trip.",
                        "text_ru": "В субботу они гуляли по городу, увидели старую церковь и пообедали у реки. Днём шёл дождь, но день был хорошим. В воскресенье вечером они вернулись домой уставшими. Завтра Майя собирается распечатать фотографии, а Лео — спланировать ещё одну поездку.",
                        "word_count": 53,
                    },
                ],
            },
        ]

        for book in books:
            chapters = book["chapters"]
            ReadingText.objects.update_or_create(
                source=ReadingText.Source.ENGLISH_JOURNEY_ORIGINAL,
                source_id=book["source_id"],
                defaults={
                    "title": book["title"],
                    "title_ru": book["title_ru"],
                    "author": "English Journey",
                    "level": book["level"],
                    "cover_emoji": book["cover_emoji"],
                    "description": book["description"],
                    "chapters": chapters,
                    "total_words": sum(chapter["word_count"] for chapter in chapters),
                    "is_published": True,
                },
            )

        for source_id, title, title_ru, emoji, text, text_ru in SHORT_READERS:
            ReadingText.objects.update_or_create(
                source=ReadingText.Source.ENGLISH_JOURNEY_ORIGINAL,
                source_id=source_id,
                defaults={
                    "title": title,
                    "title_ru": title_ru,
                    "author": "English Journey",
                    "level": "A1",
                    "cover_emoji": emoji,
                    "description": "Короткий оригинальный практический текст уровня A1.",
                    "chapters": [{
                        "title": title,
                        "text": text,
                        "text_ru": text_ru,
                        "word_count": len(text.split()),
                    }],
                    "total_words": len(text.split()),
                    "is_published": True,
                },
            )
