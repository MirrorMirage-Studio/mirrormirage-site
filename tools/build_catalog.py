#!/usr/bin/env python3
"""Собирает каталог программ на programs.html из programs.json и релизов GitHub.

Запуск: python tools/build_catalog.py
Токен (необязательно) берётся из переменной GITHUB_TOKEN — так лимит запросов выше.
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


def карточка(п, релиз):
    e = html.escape
    # Картинка: скриншот программы или заглушка
    if п.get("image"):
        картинка = f'<img src="{e(п["image"])}" alt="{e(п["name"])}" style="width:100%;border-radius:12px;margin-bottom:16px">'
        if п.get("page"):
            картинка = f'<a href="{e(п["page"])}">{картинка}</a>'
    else:
        картинка = '<div class="placeholder-shot">скриншот программы</div>'

    установщик = next((a for a in (релиз or {}).get("assets", [])
                       if a["name"].lower().endswith((".exe", ".zip", ".msi"))), None)
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


def главная():
    данные = json.loads((КОРЕНЬ / "programs.json").read_text(encoding="utf-8"))
    готовые, будущие = [], []
    for п in данные["programs"]:
        релиз = последний_релиз(п["releases_repo"])
        (готовые if релиз else будущие).append(карточка(п, релиз))
        print(f'{п["name"]}: {релиз["tag_name"] if релиз else "релиза нет"}')

    блок = "\n".join(готовые + будущие)
    страница = КОРЕНЬ / "programs.html"
    текст = страница.read_text(encoding="utf-8")
    шаблон = re.compile(re.escape(НАЧАЛО) + r".*?" + re.escape(КОНЕЦ), re.S)
    if not шаблон.search(текст):
        sys.exit("В programs.html нет маркеров CATALOG:START / CATALOG:END")
    новый = шаблон.sub(lambda _: f"{НАЧАЛО}\n{блок}      {КОНЕЦ}", текст)
    if новый != текст:
        страница.write_text(новый, encoding="utf-8")
        print("programs.html обновлён")
    else:
        print("Изменений нет")


if __name__ == "__main__":
    главная()
