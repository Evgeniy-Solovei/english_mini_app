import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from apps.learning.services import get_dashboard_stats
from apps.users.models import LearnerProfile
from apps.voice.services import compare_pronunciation, speech_to_text, text_to_speech

logger = logging.getLogger(__name__)

WEBAPP_URL = settings.TELEGRAM_WEBAPP_URL


def register_handlers(app: Application):
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("learn", cmd_learn))
    app.add_handler(CommandHandler("streak", cmd_streak))
    app.add_handler(CommandHandler("speak", cmd_speak))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


def _webapp_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📖 Open English App",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ],
            [
                InlineKeyboardButton("📊 My Progress", callback_data="progress"),
            ],
        ]
    )


def _main_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚀 Start Learning", web_app=WebAppInfo(url=WEBAPP_URL))],
            [
                InlineKeyboardButton("🔥 Streak", callback_data="streak"),
                InlineKeyboardButton("📊 Stats", callback_data="progress"),
            ],
        ]
    )


@sync_to_async
def _get_or_create_user(update: Update) -> LearnerProfile:
    tg = update.effective_user
    user, created = LearnerProfile.objects.get_or_create(
        telegram_id=tg.id,
        defaults={
            "username": tg.username or "",
            "first_name": tg.first_name or "",
            "last_name": tg.last_name or "",
            "language_code": tg.language_code or "ru",
        },
    )
    if not created:
        user.username = tg.username or user.username
        user.first_name = tg.first_name or user.first_name
        user.save(update_fields=["username", "first_name", "updated_at"])
    return user


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update)
    name = user.display_name
    streak = user.streak_days
    streak_msg = f"\n🔥 Streak: {streak} day{'s' if streak != 1 else ''}" if streak else ""

    text = (
        f"Hello, {name}! 👋\n\n"
        "Welcome to *English Journey* — your path from zero to conversation.\n\n"
        "📚 Structured CEFR lessons (A1 → C2)\n"
        "🎤 Voice practice & pronunciation\n"
        "🧠 Smart spaced repetition\n"
        "🏆 Level exams & progress tracking\n"
        f"{streak_msg}\n\n"
        "Tap the button below to open your daily lesson!"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=_main_keyboard()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Commands:*\n"
        "/start — Welcome & open app\n"
        "/learn — Open mini-app\n"
        "/speak — Speaking practice tip\n"
        "/status — Your progress\n"
        "/streak — Streak info\n"
        "/help — This message\n\n"
        "*Voice practice:*\n"
        "• `say Thank you` — listen & send a voice reply\n"
        "• Send any voice → pronunciation score (A+/A/B/C)\n"
        "• Open the app → Speak tab for Shadow & Talk dialogues"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _get_or_create_user(update)
    phrases = [
        "Hello, how are you?",
        "Nice to meet you.",
        "I would like a coffee, please.",
        "Where is the train station?",
        "Can you speak slowly, please?",
    ]
    import random

    phrase = random.choice(phrases)
    context.user_data["expected_phrase"] = phrase
    path = await sync_to_async(text_to_speech)(phrase)
    caption = (
        f"🎤 *Speaking drill*\n\n"
        f"Listen, then send a *voice message* repeating:\n«{phrase}»\n\n"
        f"Or open the mini-app → Speak for full shadowing & dialogues."
    )
    if path:
        with open(path, "rb") as f:
            await update.message.reply_voice(f, caption=caption, parse_mode="Markdown", reply_markup=_webapp_keyboard())
    else:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=_webapp_keyboard())


async def cmd_learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Open the app to start today's lesson 👇",
        reply_markup=_webapp_keyboard(),
    )


@sync_to_async
def _get_stats(user):
    return get_dashboard_stats(user)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update)
    stats = await _get_stats(user)

    skills = stats["skills"]
    text = (
        f"📊 *Your Progress*\n\n"
        f"Level: *{stats['level_label']}* ({stats['level_progress']}%)\n"
        f"XP: {stats['total_xp']} ⭐\n"
        f"Streak: {stats['streak_days']} days 🔥 (best: {stats['longest_streak']})\n"
        f"Today: {stats['minutes_today']}/{stats['daily_goal']} min\n"
        f"Lessons: {stats['lessons_completed']}/{stats['lessons_total']}\n"
        f"Reviews due: {stats['due_reviews']}\n\n"
        f"*Skills:*\n"
        f"🎧 Listening {skills['listening']:.0f}%\n"
        f"📖 Reading {skills['reading']:.0f}%\n"
        f"✍️ Writing {skills['writing']:.0f}%\n"
        f"🗣 Speaking {skills['speaking']:.0f}%\n"
        f"📝 Grammar {skills['grammar']:.0f}%\n"
        f"📚 Vocabulary {skills['vocabulary']:.0f}%\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=_webapp_keyboard())


async def cmd_streak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update)
    s = user.streak_days
    best = user.longest_streak

    if s == 0:
        msg = "Start your streak today! Complete one lesson to begin 🔥"
    elif s < 7:
        msg = f"🔥 {s} days in a row! Keep going — 7 days unlocks a bonus!"
    elif s < 30:
        msg = f"🔥🔥 {s} days! You're building a real habit. Best: {best}"
    else:
        msg = f"🏆 Legendary! {s} day streak! Best ever: {best}"

    await update.message.reply_text(msg, reply_markup=_webapp_keyboard())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline buttons that previously produced a permanent loading spinner."""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user = await _get_or_create_user(update)

    if query.data == "progress":
        stats = await _get_stats(user)
        text = (
            "📊 *Ваш прогресс*\n\n"
            f"Уровень: *{stats['level_label']}* ({stats['level_progress']}%)\n"
            f"XP: {stats['total_xp']} ⭐\n"
            f"Серия: {stats['streak_days']} дн. 🔥\n"
            f"Сегодня: {stats['minutes_today']}/{stats['daily_goal']} мин\n"
            f"Уроки: {stats['lessons_completed']}/{stats['lessons_total']}"
        )
    elif query.data == "streak":
        text = (
            f"🔥 Текущая серия: *{user.streak_days}* дн.\n"
            f"Лучший результат: *{user.longest_streak}* дн.\n\n"
            "Серия растёт, когда вы выполняете хотя бы одно упражнение в день."
        )
    else:
        return

    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=_webapp_keyboard())


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_or_create_user(update)
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    await update.message.reply_text("🎧 Listening & scoring...")

    file = await context.bot.get_file(voice.file_id)
    audio_bytes = await file.download_as_bytearray()

    spoken = await sync_to_async(speech_to_text)(bytes(audio_bytes))
    expected = context.user_data.get("expected_phrase", "hello")

    from apps.learning.speaking_services import record_pronunciation

    result = await sync_to_async(record_pronunciation)(user, expected, spoken, "telegram")

    tips = "\n".join(f"• {t}" for t in (result.get("tips") or [])[:2])
    tips_block = f"\n\n💡 {tips}" if tips else ""

    feedback = (
        f"{'✅' if result['passed'] else '🔄'} *Pronunciation: {result.get('grade', '?')}*\n\n"
        f"You said: _{result['spoken'] or '(unclear)'}_\n"
        f"Expected: _{result['expected']}_\n"
        f"Score: *{result['score']}%* · +{result.get('xp_earned', 0)} XP\n\n"
        f"{result['feedback']}"
        f"{tips_block}\n\n"
        f"🗣 Speaking today: {result.get('speak_minutes_today', 0)}/{result.get('speak_goal', 10)} min"
    )
    await update.message.reply_text(feedback, parse_mode="Markdown", reply_markup=_webapp_keyboard())

    path = await sync_to_async(text_to_speech)(expected)
    if path and not result["passed"]:
        with open(path, "rb") as f:
            await update.message.reply_voice(f, caption=f"Listen again: «{expected}»")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text in ("hello", "hi", "hey"):
        context.user_data["expected_phrase"] = "hello"
        await update.message.reply_text(
            "Great! Now send a *voice message* saying «hello» 🎤",
            parse_mode="Markdown",
        )
    elif text.startswith("say "):
        phrase = update.message.text.strip()[4:]
        context.user_data["expected_phrase"] = phrase
        path = await sync_to_async(text_to_speech)(phrase)
        msg = f"Repeat after me: «{phrase}» 🎤"
        if path:
            with open(path, "rb") as f:
                await update.message.reply_voice(f, caption=msg)
        else:
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text(
            "Type `say hello` to practice, or open the app 👇",
            parse_mode="Markdown",
            reply_markup=_webapp_keyboard(),
        )
