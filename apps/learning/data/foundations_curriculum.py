"""Reading foundations for a Russian-speaking adult starting from zero."""

from .curriculum_v2 import unit


def foundation(code, title, can_do, rule, phrases, mission, reading, alphabet=None):
    item = unit("PRE_A1", code, title, can_do, rule, phrases, mission)
    item.update({"track": "main", "foundation": True, "foundation_reading": reading})
    if alphabet:
        item["alphabet"] = alphabet
    return item


FIRST_HALF = [
    ("A a", "/eɪ/ эй"), ("B b", "/biː/ би"), ("C c", "/siː/ си"),
    ("D d", "/diː/ ди"), ("E e", "/iː/ и"), ("F f", "/ef/ эф"),
    ("G g", "/dʒiː/ джи"), ("H h", "/eɪtʃ/ эйч"), ("I i", "/aɪ/ ай"),
    ("J j", "/dʒeɪ/ джей"), ("K k", "/keɪ/ кей"), ("L l", "/el/ эл"),
    ("M m", "/em/ эм"),
]

SECOND_HALF = [
    ("N n", "/en/ эн"), ("O o", "/əʊ/ оу"), ("P p", "/piː/ пи"),
    ("Q q", "/kjuː/ кью"), ("R r", "/ɑːr/ ар"), ("S s", "/es/ эс"),
    ("T t", "/tiː/ ти"), ("U u", "/juː/ ю"), ("V v", "/viː/ ви"),
    ("W w", "/ˈdʌbəl.juː/ дабл-ю"), ("X x", "/eks/ экс"),
    ("Y y", "/waɪ/ уай"), ("Z z", "/zed/ зед"),
]


FOUNDATION_UNITS = [
    foundation(
        "F01", "Алфавит A–M", "Узнать первые 13 букв и назвать их по-английски.",
        "Название буквы — не обязательно тот звук, который она даёт внутри слова.",
        [("A — /eɪ/ — apple", "A — эй — apple"), ("B — /biː/ — book", "B — би — book"),
         ("C — /siː/ — cat", "C — си — cat"), ("D — /diː/ — dog", "D — ди — dog"),
         ("E — /iː/ — egg", "E — и — egg"), ("F to M", "Буквы от F до M")],
        ("Say the letters A, B, C, D, E.", "Назовите пять букв по порядку.", ["A B C D E"]),
        "Слушайте название каждой буквы, затем произносите его. Заглавная A и строчная a — одна буква.", FIRST_HALF,
    ),
    foundation(
        "F02", "Алфавит N–Z", "Узнать оставшиеся 13 букв и продиктовать короткое слово.",
        "Особенно запомните R, W и Y: их английские названия не похожи на русские.",
        [("N — /en/ — name", "N — эн — name"), ("O — /əʊ/ — open", "O — оу — open"),
         ("P — /piː/ — pen", "P — пи — pen"), ("R — /ɑːr/ — red", "R — ар — red"),
         ("W — /ˈdʌbəl.juː/ — web", "W — дабл-ю — web"), ("X, Y, Z", "Буквы X, Y, Z")],
        ("Spell the word WEB.", "Назовите буквы W-E-B.", ["W E B"]),
        "После N–Z соедините обе части и дважды произнесите весь алфавит A–Z.", SECOND_HALF,
    ),
    foundation(
        "F03", "Буква и звук", "Понять, почему слова нельзя читать названиями букв.",
        "Букву мы записываем, звук произносим: A называется /eɪ/, но в cat звучит /æ/.",
        [("cat — /kæt/", "кот"), ("bed — /bed/", "кровать"), ("sit — /sɪt/", "сидеть"),
         ("hot — /hɒt/", "горячий"), ("cup — /kʌp/", "чашка"),
         ("A letter can make different sounds.", "Буква может давать разные звуки.")],
        ("Read: cat, bed, sit, hot, cup.", "Прочитайте пять слов, не называя буквы.", ["cat bed sit hot cup"]),
        "A называется /eɪ/, но в cat читается /æ/. Название буквы и звук внутри слова — разные вещи.",
    ),
    foundation(
        "F04", "Короткие гласные", "Читать слова типа согласная–гласная–согласная.",
        "В закрытом слоге гласная обычно короткая: a /æ/, e /e/, i /ɪ/, o /ɒ/, u /ʌ/.",
        [("map — /mæp/", "карта"), ("ten — /ten/", "десять"), ("fish — /fɪʃ/", "рыба"),
         ("box — /bɒks/", "коробка"), ("bus — /bʌs/", "автобус"),
         ("Read one sound at a time.", "Читайте по одному звуку.")],
        ("Read: map, ten, fish, box, bus.", "Прочитайте слова с короткими гласными.", ["map ten fish box bus"]),
        "Гласная закрыта согласной: c-a-t, p-e-n, s-i-t, h-o-t, s-u-n. Соединяйте звуки: /k/ + /æ/ + /t/ → cat.",
    ),
    foundation(
        "F05", "Silent e", "Увидеть немую e и прочитать пары cap–cape, kit–kite.",
        "Конечная e обычно не произносится и делает предыдущую гласную долгой.",
        [("cap — cape", "кепка — мыс"), ("kit — kite", "набор — воздушный змей"),
         ("hop — hope", "прыгать — надеяться"), ("cub — cube", "детёныш — куб"),
         ("not — note", "не — заметка"), ("The final e is silent.", "Последняя e немая.")],
        ("Read: cape, kite, hope, cube, note.", "Прочитайте слова с немой e.", ["cape kite hope cube note"]),
        "cap /kæp/ → cape /keɪp/ · kit /kɪt/ → kite /kaɪt/ · hop /hɒp/ → hope /həʊp/. Последнюю e видим, но не произносим.",
    ),
    foundation(
        "F06", "Трудные согласные", "Различать W/V, B/P и конечные звонкие согласные.",
        "W произносится округлёнными губами без контакта с зубами; V — с зубами на нижней губе.",
        [("west — vest", "запад — жилет"), ("berry — Perry", "ягода — имя Perry"),
         ("bad — bat", "плохой — бита"), ("pig — pick", "свинья — выбирать"),
         ("web — /web/", "веб"), ("Keep the final sound.", "Сохраняйте конечный звук.")],
        ("Say: web, vest, bad, bat.", "Произнесите слова, сохраняя различия.", ["web vest bad bat"]),
        "W: округлите губы, зубы их не касаются. V: верхние зубы касаются нижней губы. В bad последний /d/ остаётся звонким.",
    ),
    foundation(
        "F07", "Сочетания согласных", "Читать sh, ch, th, ph и ng как цельные звуки.",
        "Две буквы могут обозначать один звук: sh /ʃ/, ch /tʃ/, ph /f/, ng /ŋ/. TH имеет два варианта.",
        [("ship — /ʃɪp/", "корабль"), ("chat — /tʃæt/", "чат"), ("think — /θɪŋk/", "думать"),
         ("this — /ðɪs/", "это"), ("phone — /fəʊn/", "телефон"), ("sing — /sɪŋ/", "петь")],
        ("Read: ship, chat, think, this, phone, sing.", "Прочитайте сочетания как один звук.", ["ship chat think this phone sing"]),
        "TH: кончик языка слегка между зубами. Без голоса — think /θ/, с голосом — this /ð/. Не заменяйте звуки на «с», «з» или «т».",
    ),
    foundation(
        "F08", "Сочетания гласных", "Узнавать ee, ea, ai, ay, oa и два варианта oo.",
        "Комбинацию читаем целиком, но произношение нового слова всегда полезно проверить по аудио.",
        [("see — /siː/", "видеть"), ("team — /tiːm/", "команда"), ("mail — /meɪl/", "почта"),
         ("day — /deɪ/", "день"), ("road — /rəʊd/", "дорога"), ("book — /bʊk/", "книга")],
        ("Read: see, team, mail, day, road, book.", "Прочитайте сочетания гласных.", ["see team mail day road book"]),
        "ee/ea часто дают /iː/; ai/ay — /eɪ/; oa — /əʊ/. oo бывает /uː/ в food и /ʊ/ в book: слушайте образец.",
    ),
    foundation(
        "F09", "Гласная + R", "Читать частые сочетания ar, or, er, ir и ur.",
        "R меняет гласную. В американской речи r слышна сильнее, чем в британской.",
        [("car — /kɑːr/", "машина"), ("port — /pɔːrt/", "порт"), ("term — /tɜːrm/", "термин"),
         ("first — /fɜːrst/", "первый"), ("turn — /tɜːrn/", "повернуть"),
         ("server — /ˈsɜːrvər/", "сервер")],
        ("Read: car, port, term, first, turn, server.", "Прочитайте слова с гласной перед R.", ["car port term first turn server"]),
        "Для IT сразу тренируем server, terminal, port, card. Не вставляйте дополнительную русскую гласную между согласными.",
    ),
    foundation(
        "F10", "Слоги и ударение", "Разделить слово на слоги и выделить ударный.",
        "Знак ˈ в транскрипции стоит перед ударным слогом; он произносится сильнее остальных.",
        [("TA-ble — /ˈteɪ.bəl/", "стол"), ("WIN-dow — /ˈwɪn.dəʊ/", "окно"),
         ("com-PU-ter — /kəmˈpjuː.tər/", "компьютер"), ("de-VE-lop-er", "разработчик"),
         ("IN-ter-net", "интернет"), ("Stress one syllable.", "Выделяйте один слог.")],
        ("Say: computer, developer, internet.", "Произнесите слова с ударением.", ["computer developer internet"]),
        "Хлопните на сильном слоге: com-PU-ter, de-VE-lop-er. Без ударения слово бывает непонятно даже при верных звуках.",
    ),
    foundation(
        "F11", "Окончания -s и -ed", "Не терять окончания и узнавать их основные варианты.",
        "-s звучит /s/, /z/ или /ɪz/; -ed — /t/, /d/ или /ɪd/. Дополнительный слог появляется не всегда.",
        [("works — /wɜːrks/", "работает"), ("runs — /rʌnz/", "запускается"),
         ("changes — /ˈtʃeɪn.dʒɪz/", "изменяет"), ("worked — /wɜːrkt/", "работал"),
         ("failed — /feɪld/", "не сработал"), ("started — /ˈstɑːr.tɪd/", "запустился")],
        ("Read: works, runs, changes, worked, failed, started.", "Произнесите окончания.", ["works runs changes worked failed started"]),
        "Не говорите work-id: worked — один слог /wɜːrkt/. Но started — два слога, потому что после t окончание звучит /ɪd/.",
    ),
    foundation(
        "F12", "Первое чтение", "Самостоятельно прочитать и понять короткий связный текст.",
        "Читайте смысловыми группами и делайте паузу на точке; не переводите каждую букву отдельно.",
        [("My name is Max.", "Меня зовут Макс."), ("I am a developer.", "Я разработчик."),
         ("This is my computer.", "Это мой компьютер."), ("The screen is on.", "Экран включён."),
         ("I open a file.", "Я открываю файл."), ("The file is ready.", "Файл готов.")],
        ("Read the six-sentence text aloud.", "Прочитайте весь короткий текст вслух.",
         ["My name is Max I am a developer this is my computer the screen is on I open a file the file is ready"]),
        "My name is Max. / I am a developer. / This is my computer. / The screen is on. / I open a file. / The file is ready.",
    ),
]
