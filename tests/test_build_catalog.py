"""Тесты скрипта каталога: компактные карточки главной и безопасная запись страниц."""
import importlib.util
import io
import json
import urllib.error
from email.message import Message
from pathlib import Path

import pytest

СКРИПТ = Path(__file__).resolve().parent.parent / "tools" / "build_catalog.py"
_spec = importlib.util.spec_from_file_location("build_catalog", СКРИПТ)
assert _spec and _spec.loader
каталог = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(каталог)

ДАННЫЕ = {"programs": [
    {"id": "azure-player", "name": "Azure Player", "description": "Плеер.", "image": "images/azure-player/library.png",
     "page": "azure-player.html", "releases_repo": "o/azure", "price": "199 ₽", "buy": "buy_azure_player"},
    {"id": "sleep-timer", "name": "Sleep Timer", "description": "Таймер.", "image": "images/sleep-timer/screens.png",
     "releases_repo": "o/sleep", "price": "Бесплатно"},
    {"id": "universal-vpn", "name": "VPN", "description": "Клиент.", "releases_repo": "o/vpn", "price": "Скоро бесплатно"},
]}


def релиз(имя_файла):
    return {"tag_name": "v1.4.1", "published_at": "2026-10-27T10:00:00Z",
            "assets": [{"name": имя_файла, "browser_download_url": "https://example.com/" + имя_файла}]}


РЕЛИЗЫ = {"o/azure": релиз("Azure.exe"), "o/sleep": релиз("Sleep.exe")}

ПРОГРАММЫ_HTML = "<main>\n      <!-- CATALOG:START -->\n      старое\n      <!-- CATALOG:END -->\n</main>\n"
ГЛАВНАЯ_HTML = "<main>\n    <!-- HOME-CATALOG:START -->\n    старое\n    <!-- HOME-CATALOG:END -->\n</main>\n"


@pytest.fixture
def сайт(tmp_path, monkeypatch):
    """Временная копия сайта: сеть заменена словарём релизов, КОРЕНЬ указывает на tmp_path."""
    (tmp_path / "programs.json").write_text(json.dumps(ДАННЫЕ, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "programs.html").write_text(ПРОГРАММЫ_HTML, encoding="utf-8")
    (tmp_path / "index.html").write_text(ГЛАВНАЯ_HTML, encoding="utf-8")
    monkeypatch.setattr(каталог, "КОРЕНЬ", tmp_path)
    monkeypatch.setattr(каталог, "последний_релиз", lambda репо: РЕЛИЗЫ.get(репо))
    return tmp_path


def байты(сайт):
    return {имя: (сайт / имя).read_bytes() for имя in ("programs.html", "index.html")}


def test_mini_card_without_release_and_image():
    п = {"id": "vpn", "name": "VPN", "description": "Клиент.", "price": "Скоро бесплатно"}
    текст = каталог.компактная_карточка(п, None)
    assert "card mini" in текст
    assert "placeholder-shot" in текст
    assert "Скоро бесплатно" in текст
    assert 'href="contacts.html"' in текст


def test_mini_card_escapes_name():
    п = {"id": "x", "name": "A<b>&", "description": "d", "price": "0"}
    текст = каталог.компактная_карточка(п, None)
    assert "A&lt;b&gt;&amp;" in текст
    assert "A<b>&" not in текст


def test_mini_card_link_page_then_installer_then_contacts():
    с_страницей = {"id": "a", "name": "A", "description": "d", "price": "0", "page": "a.html"}
    без_страницы = {"id": "b", "name": "B", "description": "d", "price": "0"}
    assert 'href="a.html">Подробнее' in каталог.компактная_карточка(с_страницей, релиз("A.exe"))
    assert 'href="https://example.com/B.exe">Скачать' in каталог.компактная_карточка(без_страницы, релиз("B.exe"))
    assert 'href="contacts.html">Следить' in каталог.компактная_карточка(без_страницы, None)


def test_home_excludes_showcase_program(сайт):
    каталог.главная()
    главная = (сайт / "index.html").read_text(encoding="utf-8")
    блок = главная.split(каталог.HOME_НАЧАЛО)[1].split(каталог.HOME_КОНЕЦ)[0]
    assert "azure-player" not in блок
    assert "sleep-timer" in блок
    assert "card mini" in блок
    # на странице программ азур-плеер по-прежнему есть
    assert "Azure Player" in (сайт / "programs.html").read_text(encoding="utf-8")


def test_missing_home_markers_changes_nothing(сайт):
    (сайт / "index.html").write_text("<main>без меток</main>\n", encoding="utf-8")
    до = байты(сайт)
    with pytest.raises(SystemExit) as ошибка:
        каталог.главная()
    assert "index.html" in str(ошибка.value)
    assert байты(сайт) == до


def test_rate_limit_changes_nothing(сайт, monkeypatch):
    def лимит(репо):
        raise urllib.error.HTTPError("https://api.github.com", 403, "rate limit exceeded", Message(), io.BytesIO(b"rate limit"))
    monkeypatch.setattr(каталог, "последний_релиз", лимит)
    до = байты(сайт)
    with pytest.raises(SystemExit) as ошибка:
        каталог.главная()
    assert "лимит" in str(ошибка.value)
    assert байты(сайт) == до


def test_idempotent(сайт):
    каталог.главная()
    после_первого = байты(сайт)
    assert "старое" not in после_первого["programs.html"].decode("utf-8")
    assert "старое" not in после_первого["index.html"].decode("utf-8")
    каталог.главная()
    assert байты(сайт) == после_первого
