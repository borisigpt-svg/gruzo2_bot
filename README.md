# GRUZO2 — СВОЙ ЭКСПРЕСС (MVP v1.1)

## 1) Требования
- Python 3.10+ (лучше 3.11)
- Windows: PowerShell

## 2) Установка
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env
python main.py
```

Если PowerShell ругается на политики — можно без активации:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
notepad .env
.\.venv\Scripts\python.exe main.py
```

## 3) Назначить админа (рекомендуется)
С аккаунта Boris36912 напиши боту:
- `/claim_admin`

Бот сохранит `admin.json`, и заявки будут приходить админу.

## 4) Команды BotFather (/setcommands)
```
start - Запуск меню
debug_chatid - Показать chat_id
claim_admin - Назначить админа (только Boris36912)
```

Dev setup verified: Windows + Cursor + gh (noreply).