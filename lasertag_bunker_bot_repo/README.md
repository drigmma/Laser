# LaserTag Bunker Telegram Bot

Телеграм-бот для лазертага **Bunker**, который:

- выдаёт пользователю персональный промокод на сертификат для сборной игры;
- собирает телефон и возраст с согласием на обработку персональных данных;
- записывает данные в Google Sheets;
- даёт возможность пользователю задать вопрос в поддержку;
- даёт админам команды для ответа пользователям и рассылки сообщений.

## Стек

- Python 3.10+
- [aiogram](https://docs.aiogram.dev/)
- Google Sheets (через `gspread` + `google-auth`)
- `.env` для хранения секретов (через `python-dotenv`)

## Подготовка

1. **Клонируй репозиторий**:

```bash
git clone https://github.com/your-username/lasertag-bunker-bot.git
cd lasertag-bunker-bot
```

2. **Создай и активируй виртуальное окружение (по желанию)**:

```bash
python -m venv venv
source venv/bin/activate  # Linux / macOS
# или
venv\Scripts\activate   # Windows
```

3. **Установи зависимости**:

```bash
pip install -r requirements.txt
```

4. **Создай сервисный аккаунт Google** и скачай `credentials.json`:

   - Зайди в Google Cloud Console.
   - Создай сервисный аккаунт.
   - Дай ему доступ к Google Sheets / Google Drive.
   - Скачай JSON-ключ и сохрани как `credentials.json` в корень проекта.
   - В самой таблице Google Sheets дай доступ этому сервисному аккаунту по email.

5. **Создай `.env` в корне проекта** (файл в репозиторий не добавляй):

```env
API_TOKEN=твой_телеграм_токен
ADMIN_IDS=923499545,227900124
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_SHEET_ID=ID_ТВОЕЙ_ТАБЛИЦЫ
```

Где:

- `API_TOKEN` — токен бота от BotFather.
- `ADMIN_IDS` — список ID админов через запятую.
- `GOOGLE_CREDENTIALS_PATH` — путь к JSON-ключу (по умолчанию `credentials.json`).
- `GOOGLE_SHEET_ID` — ID таблицы из URL:
  `https://docs.google.com/spreadsheets/d/ID_ТАБЛИЦЫ/edit#gid=0`

## Запуск

```bash
python bot.py
```

Бот запустится в режиме long polling.

## Основные команды

- `/start` — приветствие, меню с кнопками.
- `/support` — запуск сценария получения сертификата.
- `/question` — задать вопрос поддержке.
- `/reply` — (для админов) ответ пользователю по ID.
- `/message` — (для админов) массовая рассылка всем, кто получил код.

## Структура

- `bot.py` — основной код бота.
- `requirements.txt` — список зависимостей.
- `README.md` — описание проекта.

`.env` и `credentials.json` **специально не входят** в репозиторий — их нужно создавать локально и не коммитить.
