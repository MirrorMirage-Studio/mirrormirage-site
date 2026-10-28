"""Тесты-сторожа страниц сайта: каркас, шрифты, отсутствие внешних ресурсов."""
import re
from html.parser import HTMLParser
from pathlib import Path

КОРЕНЬ = Path(__file__).resolve().parent.parent
СЛУЖЕБНЫЕ = {"oferta", "privacy", "refund", "paid", "fail", "404"}
СТРАНИЦЫ = sorted(КОРЕНЬ.glob("*.html"))


class Разбор(HTMLParser):
    """Собирает из страницы теги, нужные проверкам."""

    def __init__(self):
        super().__init__()
        self.теги = []  # (имя, {атрибуты})
        self.в_head = False
        self.скрипты_в_head = []  # тексты встроенных скриптов в <head>
        self._скрипт_в_head = False

    def handle_starttag(self, tag, attrs):
        self.теги.append((tag, dict(attrs)))
        if tag == "head":
            self.в_head = True
        if tag == "script" and self.в_head and "src" not in dict(attrs):
            self._скрипт_в_head = True

    def handle_endtag(self, tag):
        if tag == "head":
            self.в_head = False
        if tag == "script":
            self._скрипт_в_head = False

    def handle_data(self, data):
        if self._скрипт_в_head:
            self.скрипты_в_head.append(data)


def разобрать(путь: Path) -> Разбор:
    р = Разбор()
    р.feed(путь.read_text(encoding="utf-8"))
    return р


def классы(атрибуты: dict) -> set:
    return set((атрибуты.get("class") or "").split())


def test_twelve_pages_found():
    assert len(СТРАНИЦЫ) == 12


def test_every_page_loads_crystals_js_deferred():
    # на 404 путь абсолютный (страница открывается по любому адресу), поэтому допускаем «/» в начале
    for путь in СТРАНИЦЫ:
        скрипты = [
            а for т, а in разобрать(путь).теги
            if т == "script" and re.fullmatch(r"/?crystals\.js", а.get("src", ""))
        ]
        assert len(скрипты) == 1, f"{путь.name}: подключений crystals.js {len(скрипты)}, нужно 1"
        assert "defer" in скрипты[0], f"{путь.name}: у crystals.js нет defer"


def test_js_class_script_in_head():
    for путь in СТРАНИЦЫ:
        код = "".join(разобрать(путь).скрипты_в_head)
        assert "classList.add('js')" in код, f"{путь.name}: в <head> нет скрипта, ставящего класс js"


def test_service_pages_are_calm():
    for путь in СТРАНИЦЫ:
        body = next(а for т, а in разобрать(путь).теги if т == "body")
        спокойная = "calm" in классы(body)
        должна = путь.stem in СЛУЖЕБНЫЕ
        assert спокойная == должна, f"{путь.name}: calm={спокойная}, а должно быть {должна}"
        assert "bg-portal" in классы(body), f"{путь.name}: у body нет bg-portal"


def test_no_external_resources():
    for путь in СТРАНИЦЫ:
        for тег, а in разобрать(путь).теги:
            if тег == "script":
                ссылка = а.get("src", "")
            elif тег == "link" and "stylesheet" in (а.get("rel") or ""):
                ссылка = а.get("href", "")
            else:
                continue
            assert not re.match(r"(https?:)?//", ссылка), f"{путь.name}: внешний ресурс {ссылка}"
    for путь in [*СТРАНИЦЫ, КОРЕНЬ / "style.css"]:
        assert "fonts.googleapis" not in путь.read_text(encoding="utf-8"), f"{путь.name}: Google Fonts"


def test_fonts_exist():
    css = (КОРЕНЬ / "style.css").read_text(encoding="utf-8")
    файлы = re.findall(r"url\(\s*['\"]?(fonts/[^'\")\s]+)", css)
    assert len(set(файлы)) == 8, f"в style.css нужно 8 файлов шрифтов, найдено {len(set(файлы))}"
    for ф in файлы:
        assert (КОРЕНЬ / ф).is_file(), f"нет файла {ф}"
    assert (КОРЕНЬ / "fonts" / "OFL.txt").is_file(), "нет fonts/OFL.txt"


def test_menu_toggle_on_every_page():
    for путь in СТРАНИЦЫ:
        теги = разобрать(путь).теги
        кнопки = [
            а for т, а in теги
            if т == "button" and "menu-toggle" in классы(а)
            and а.get("aria-controls") == "site-nav" and а.get("aria-expanded") == "false"
        ]
        меню = [а for т, а in теги if т == "nav" and а.get("id") == "site-nav"]
        assert len(кнопки) == 1, f"{путь.name}: кнопка menu-toggle не найдена"
        assert len(меню) == 1, f"{путь.name}: нет nav#site-nav"
