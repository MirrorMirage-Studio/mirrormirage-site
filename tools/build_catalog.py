#!/usr/bin/env python3
"""Собирает каталоги программ из programs.json и релизов GitHub:
  - programs.html: полные карточки всех программ (между CATALOG:START / CATALOG:END);
  - index.html: компактные карточки блока «Другие программы» (между HOME-CATALOG:START / HOME-CATALOG:END),
    без программы-витрины Azure Player.

Запуск: python tools/build_catalog.py
Токен (необязательно) берётся из переменной GITHUB_TOKEN — так лимит запросов выше.
Если что-то не так (нет меток, лимит GitHub, нет сети), скрипт останавливается с понятной
фразой и не меняет ни один файл.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

КОРЕНЬ = Path(__file__).resolve().parent.parent
МЕСЯЦЫ = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
БОТ = "https://t.me/Mirrormiragebot?start="
НАЧАЛО, КОНЕЦ = "<!-- CATALOG:START -->", "<!-- CATALOG:END -->"
HOME_НАЧАЛО, HOME_КОНЕЦ = "<!-- HOME-CATALOG:START -->", "<!-- HOME-CATALOG:END -->"
ВИТРИНА = "azure-player"  # эта программа показана на главной отдельным крупным блоком


def последний_релиз(репозиторий):
    """Возвращает данные последнего релиза или None, если релиза/репозитория нет."""
    запрос = urllib.request.Request(
        f"https://api.github.com/repos/{репозиторий}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "mirrormirage-site"})
    токен = os.environ.get("GITHUB_TOKEN")
    if токен:
        запрос.add_header("Authorization", f"Bearer {токен}")
    try:
        with urllib.request.urlopen(запрос, timeout=30) as ответ:
            return json.load(ответ)
    except urllib.error.HTTPError as ошибка:
        # 404 — релизов (или репозитория) ещё нет. Превышение лимита (403) — это сбой, а не "нет релиза"
        if ошибка.code == 404 or (ошибка.code == 403 and "rate limit" not in ошибка.read().decode("utf-8", "replace").lower()):
            return None
        raise


def дата_по_русски(iso):
    д = datetime.strptime(iso[:10], "%Y-%m-%d")
    return f"{д.day} {МЕСЯЦЫ[д.month - 1]} {д.year}"


def найти_установщик(релиз):
    """Первый файл-установщик среди файлов релиза или None."""
    return next((a for a in (релиз or {}).get("assets", [])
                 if a["name"].lower().endswith((".exe", ".zip", ".msi"))), None)


def карточка(п, релиз):
    e = html.escape
    # Картинка: скриншот программы или заглушка
    if п.get("image"):
        картинка = f'<img src="{e(п["image"])}" alt="{e(п["name"])}" style="width:100%;border-radius:12px;margin-bottom:16px">'
        if п.get("page"):
            картинка = f'<a href="{e(п["page"])}">{картинка}</a>'
    else:
        картинка = '<div class="placeholder-shot">скриншот программы</div>'

    установщик = найти_установщик(релиз)
    if релиз and установщик:
        версия = релиз["tag_name"].lstrip("vV")
        метка = f'Windows · версия {e(версия)} · {e(дата_по_русски(релиз["published_at"]))}'
        подробнее = (f'<a class="btn ghost" href="{e(п["page"])}">Подробнее</a>' if п.get("page")
                     else f'<a class="btn ghost" href="{e(установщик["browser_download_url"])}">Скачать</a>')
        # Кнопка «Купить» ведёт в Telegram-бота на нужный товар
        кнопка = (f'<a class="btn" href="{БОТ}{e(п["buy"])}">Купить</a> {подробнее}'
                  if п.get("buy") else подробнее)
    else:
        метка = "В разработке"
        кнопка = '<a class="btn ghost" href="contacts.html">Следить за новостями</a>'

    примечание = f' <small>{e(п["price_note"])}</small>' if п.get("price_note") else ""
    return (f'      <div class="card">\n        {картинка}\n'
            f'        <span class="tag">{метка}</span>\n'
            f'        <h3>{e(п["name"])}</h3>\n'
            f'        <p>{e(п["description"])}</p>\n'
            f'        <div class="price">{e(п["price"])}{примечание}</div>\n'
            f'        {кнопка}\n      </div>\n')


def компактная_карточка(п, релиз):
    """Маленькая карточка для блока «Другие программы» на главной."""
    e = html.escape
    if п.get("image"):
        картинка = f'<img class="thumb" src="{e(п["image"])}" alt="{e(п["name"])}" loading="lazy">'
        if п.get("page"):
            картинка = f'<a href="{e(п["page"])}">{картинка}</a>'
    else:
        картинка = '<div class="placeholder-shot">скриншот программы</div>'

    установщик = найти_установщик(релиз)
    if п.get("page"):
        ссылка = f'<a href="{e(п["page"])}">Подробнее →</a>'
    elif установщик:
        ссылка = f'<a href="{e(установщик["browser_download_url"])}">Скачать →</a>'
    else:
        ссылка = '<a href="contacts.html">Следить →</a>'

    return (f'      <div class="card mini" data-program="{e(п.get("id", ""))}">\n        {картинка}\n'
            f'        <h3>{e(п["name"])}</h3>\n'
            f'        <div class="price">{e(п["price"])}</div>\n'
            f'        {ссылка}\n      </div>\n')


def вставить_между(текст, начало, конец, блок, файл):
    """Заменяет всё между метками на блок. Нет меток: остановка с понятной фразой."""
    шаблон = re.compile("(" + re.escape(начало) + ").*?([ \\t]*)(" + re.escape(конец) + ")", re.DOTALL)
    if not шаблон.search(текст):
        sys.exit(f"В {файл} нет меток {начало} и {конец}. Файлы не изменены.")
    # отступ перед закрывающей меткой сохраняем как был, чтобы повторный запуск ничего не менял
    return шаблон.sub(lambda m: f"{m.group(1)}\n{блок}{m.group(2)}{m.group(3)}", текст, count=1)


def главная():
    данные = json.loads((КОРЕНЬ / "programs.json").read_text(encoding="utf-8"))
    программы = данные["programs"]

    # 1. Сначала спрашиваем GitHub обо всех релизах. Любой сбой: выходим, ничего не записав.
    релизы = {}
    try:
        for п in программы:
            релизы[п["id"]] = последний_релиз(п["releases_repo"])
            print(f'{п["name"]}: {релизы[п["id"]]["tag_name"] if релизы[п["id"]] else "релиза нет"}')
    except urllib.error.HTTPError as ошибка:
        if ошибка.code == 403:
            sys.exit("GitHub не отвечает: превышен лимит запросов (403). "
                     "Попробуйте позже или задайте GITHUB_TOKEN. Файлы не изменены.")
        sys.exit(f"GitHub ответил ошибкой {ошибка.code}. Файлы не изменены.")
    except urllib.error.URLError as ошибка:
        sys.exit(f"Нет связи с GitHub ({ошибка.reason}). Файлы не изменены.")

    # 2. Собираем оба новых текста в памяти (нет меток: остановка тут же).
    def блок(отбор, делать):
        готовые = [делать(п, релизы[п["id"]]) for п in программы if отбор(п) and релизы[п["id"]]]
        будущие = [делать(п, релизы[п["id"]]) for п in программы if отбор(п) and not релизы[п["id"]]]
        return "\n".join(готовые + будущие)

    задания = [
        (КОРЕНЬ / "programs.html", НАЧАЛО, КОНЕЦ, блок(lambda п: True, карточка)),
        (КОРЕНЬ / "index.html", HOME_НАЧАЛО, HOME_КОНЕЦ, блок(lambda п: п["id"] != ВИТРИНА, компактная_карточка)),
    ]
    результат = []
    for путь, начало, конец, текст_блока in задания:
        старый = путь.read_text(encoding="utf-8")
        результат.append((путь, старый, вставить_между(старый, начало, конец, текст_блока, путь.name)))

    # 3. Только теперь пишем файлы.
    изменено = False
    for путь, старый, новый in результат:
        if новый != старый:
            путь.write_text(новый, encoding="utf-8", newline="\n")
            print(f"{путь.name} обновлён")
            изменено = True
    if not изменено:
        print("Изменений нет")


if __name__ == "__main__":
    главная()
