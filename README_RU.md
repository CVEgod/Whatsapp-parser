# WhatsApp Parser

Парсер номеров и ссылок WhatsApp с сайтов.

## Как работает

```
sites.txt  →  HTTP запрос  →  HTML  →  поиск wa.me / tel: / номеров  →  whatsapp_numbers.txt
```

## Установка

**Windows (рекомендуется):** один и тот же Python для pip и для запуска:

```bat
install.bat
run.bat
```

Или вручную:

```bat
py -3.13 -m pip install -r requirements.txt
py -3.13 parser.py
```

**Linux / macOS:**

```bash
python3 -m pip install -r requirements.txt
python3 parser.py
```

### Ошибка `No module named 'bs4'`, хотя pip пишет «already satisfied»

Команды `pip` и `python` часто указывают на **разные** интерпретаторы. Ставьте пакеты так:

```bat
python -m pip install -r requirements.txt
```

Проверка, какой Python запускается:

```bat
python -c "import sys; print(sys.executable)"
```

## Использование

1. Добавьте URL в `sites.txt` (по одному на строку):

```
https://example.com
example.org
# комментарии игнорируются
```

2. Запустите парсер:

```bat
run.bat
```

или `py -3.13 parser.py` / `python parser.py` (если `python -m pip` ставил зависимости в тот же интерпретатор).

3. Результат — в `whatsapp_numbers.txt` (формат `+E164`, например `+79001234567`, `+14155551234`).

## Параметры

| Параметр | Описание |
|----------|----------|
| `-i sites.txt` | Входной файл со сайтами |
| `-o whatsapp_numbers.txt` | Выходной файл |
| `-t 15` | Таймаут запроса (сек) |
| `-d 1` | Пауза между сайтами (сек) |
| `--append` | Дописать в конец, не перезаписывать |

Пример:

```bash
python parser.py -i my_sites.txt -o result.txt -d 2
```

## Что ищется

- Ссылки в HTML: `wa.me`, `api.whatsapp.com`, `tel:`
- Номера в **видимом тексте** (без `script`/`style`)
- Международные номера: E.164 с `+`, длина 8–15 цифр; для РФ также `8 (9xx) …` без плюса
