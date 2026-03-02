# SafePassage Telegram Bot

Standalone Telegram bot for emergency-contact activation.

## What it does
- Listens to Telegram updates via long polling.
- Supports `/start <phone>` activation in one message.
- Also supports sending phone in a follow-up message.
- Matches phone against `emergency_contacts.phone`.
- On match, updates:
  - `emergency_contacts.telegram_chat_id`
  - `emergency_contacts.telegram_bot_active = true`

## Setup
```powershell
cd telegram-bot
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
```

Set values in `.env`:
```dotenv
TELEGRAM_BOT_TOKEN=<your_bot_token>
SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://<user>:<pass>@<host>:5432/<db>
TELEGRAM_POLL_INTERVAL_SECONDS=2
```

## Run
```powershell
cd telegram-bot
.\.venv\Scripts\python.exe bot.py
```

## Activation examples
- `/start +919100000001`
- Send message: `+919100000001`

If phone matches an emergency contact row, that contact gets activated for Telegram notifications.
